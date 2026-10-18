"""Exercise provider selection and real Agno/MCP dispatch with scripted HTTP peers."""

import asyncio
import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from agno.models.openai import OpenAIChat
from agno.tools.function import Function

from valuecell.agents.common import search
from valuecell.agents.news_agent import core as news_core
from valuecell.agents.news_agent import tools as news_tools
from valuecell.agents.research_agent import core as research_core
from valuecell.agents.research_agent import sources as research_sources
from valuecell.config.loader import ConfigLoader
from valuecell.config.manager import ConfigManager

SOURCE = "Official results\nhttps://investor.example.com/results\nRevenue increased."
QUERY = "company official quarterly results"
REAL_ASYNC_CLIENT = httpx.AsyncClient


class McpPeer:
    def __init__(self):
        self.requests = []
        self.error = False
        self.text = SOURCE
        self.http_status = 200
        self.block = False
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def handle(self, request):
        self.requests.append(request)
        assert str(request.url) == search.PARALLEL_MCP_URL
        assert request.headers["User-Agent"] == search.SEARCH_USER_AGENT
        assert "authorization" not in request.headers
        if request.method != "POST":
            return httpx.Response(405)
        payload = json.loads(request.content)
        method = payload["method"]
        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "initialize":
            result = {
                "protocolVersion": payload["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "scripted-parallel", "version": "1"},
            }
        elif method == "tools/list":
            result = {
                "tools": [{"name": "web_search", "inputSchema": {"type": "object"}}]
            }
        else:
            assert method == "tools/call"
            assert payload["params"]["name"] == "web_search"
            assert payload["params"]["arguments"] == {
                "objective": QUERY,
                "search_queries": [QUERY],
            }
            self.started.set()
            if self.block:
                try:
                    await asyncio.Event().wait()
                finally:
                    self.cancelled.set()
            if self.http_status != 200:
                return httpx.Response(self.http_status)
            result = {
                "content": [{"type": "text", "text": self.text}],
                "isError": self.error,
            }
        return httpx.Response(
            200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result}
        )


class ModelPeer:
    """Script a model tool call, then consume the returned sources."""

    def __init__(self):
        self.consumed = None

    def handle(self, request):
        body = json.loads(request.content)
        tool_messages = [m for m in body["messages"] if m["role"] == "tool"]
        if tool_messages:
            self.consumed = tool_messages[-1]["content"]
            delta = {"role": "assistant", "content": self.consumed}
            finish = "stop"
        else:
            assert "web_search" in [t["function"]["name"] for t in body["tools"]]
            delta = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "search-1",
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": json.dumps({"query": QUERY}),
                        },
                    }
                ],
            }
            finish = "tool_calls"
        chunks = []
        for value, reason in ((delta, None), ({}, finish)):
            chunk = {
                "id": "scripted",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "scripted",
                "choices": [{"index": 0, "delta": value, "finish_reason": reason}],
            }
            chunks.append("data: " + json.dumps(chunk) + "\n\n")
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream"},
            text="".join(chunks) + "data: [DONE]\n\n",
        )


@pytest.fixture
def configuration(monkeypatch, tmp_path):
    for key in list(os.environ):
        if key.endswith("_API_KEY") or key == "WEB_SEARCH_PROVIDER":
            monkeypatch.delenv(key)
    config_dir = tmp_path / "configs"
    shutil.copytree(Path(__file__).resolve().parents[4] / "configs", config_dir)
    manager = ConfigManager(ConfigLoader(config_dir))
    monkeypatch.setattr(search, "get_config_manager", lambda: manager)
    monkeypatch.setattr(news_core, "get_config_manager", lambda: manager)
    return manager


@pytest.fixture
def mcp_peer(monkeypatch):
    peer = McpPeer()
    monkeypatch.setattr(
        search,
        "AsyncClient",
        lambda **kwargs: REAL_ASYNC_CLIENT(
            transport=httpx.MockTransport(peer.handle), **kwargs
        ),
    )
    return peer


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", ["research", "news"])
async def test_agent_stream_consumes_anonymous_search(
    agent_name, configuration, mcp_peer, monkeypatch
):
    peer = ModelPeer()
    async with REAL_ASYNC_CLIENT(transport=httpx.MockTransport(peer.handle)) as client:
        model = OpenAIChat(id="scripted", api_key="fixture", http_client=client)
        if agent_name == "research":
            monkeypatch.setattr(
                research_core.model_utils_mod, "get_model_for_agent", lambda _: model
            )
            monkeypatch.setattr(research_core, "get_knowledge", lambda: None)
            agent = research_core.ResearchAgent()
            agent.knowledge_research_agent.enable_session_summaries = False
        else:
            monkeypatch.setattr(news_core, "create_model_for_agent", lambda _: model)
            agent = news_core.NewsAgent()
        events = [event async for event in agent.stream(QUERY, "conversation", "task")]
    assert peer.consumed == SOURCE
    assert any(event.content == SOURCE for event in events)
    assert any(
        event.metadata and event.metadata.get("tool_result") == SOURCE
        for event in events
    )
    methods = [
        json.loads(r.content)["method"] for r in mcp_peer.requests if r.method == "POST"
    ]
    assert (
        "initialize" in methods and "tools/list" in methods and "tools/call" in methods
    )


@pytest.mark.parametrize("agent_name", ["research_agent", "news_agent"])
def test_defaults_credentials_and_overrides(configuration, monkeypatch, agent_name):
    assert search.resolve_web_search_provider(agent_name) == "parallel"
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", " ")
    assert search.resolve_web_search_provider(agent_name) == "parallel"
    monkeypatch.delenv("WEB_SEARCH_PROVIDER")
    monkeypatch.setenv("OPENROUTER_API_KEY", "saved-openrouter")
    assert search.resolve_web_search_provider(agent_name) == "perplexity"
    monkeypatch.setenv("GOOGLE_API_KEY", "saved-google")
    assert search.resolve_web_search_provider(agent_name) == "google"
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "parallel")
    assert search.resolve_web_search_provider(agent_name) == "parallel"
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "perplexity")
    assert search.resolve_web_search_provider(agent_name) == "perplexity"


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["google", "perplexity"])
@pytest.mark.parametrize("agent_name", ["news", "research"])
async def test_existing_provider_dispatch(
    configuration, mcp_peer, monkeypatch, provider, agent_name
):
    module = news_tools if agent_name == "news" else research_sources
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", provider)
    create_model = Mock()
    if module is news_tools:
        monkeypatch.setattr(module, "create_model", create_model)
    else:
        monkeypatch.setattr(
            research_core.model_utils_mod, "create_model_with_provider", create_model
        )
    legacy_agent = SimpleNamespace(
        arun=AsyncMock(return_value=SimpleNamespace(content=SOURCE))
    )
    monkeypatch.setattr(module, "Agent", lambda **kwargs: legacy_agent)
    assert await module.web_search(QUERY) == SOURCE
    args = create_model.call_args.kwargs
    assert args["provider"] == ("google" if provider == "google" else "openrouter")
    if module is news_tools:
        assert args["use_fallback"] is False
    assert not mcp_peer.requests


@pytest.mark.asyncio
@pytest.mark.parametrize("agent_name", ["research", "news"])
async def test_explicit_provider_error_never_switches(
    agent_name, configuration, mcp_peer, monkeypatch
):
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "google")
    module = research_sources if agent_name == "research" else news_tools
    monkeypatch.setattr(
        module, "_web_search_google", AsyncMock(side_effect=ValueError("missing key"))
    )
    with pytest.raises(ValueError, match="missing key"):
        await module.web_search(QUERY)
    assert not mcp_peer.requests


@pytest.mark.asyncio
@pytest.mark.parametrize("disabled_by", ["provider", "capability", "tool", "agent"])
async def test_disabled_search_cannot_send_requests(
    disabled_by, configuration, mcp_peer, monkeypatch
):
    config = configuration.get_agent_config("news_agent")
    if disabled_by == "provider":
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "none")
    elif disabled_by == "capability":
        config.capabilities["web_search"]["enabled"] = False
    elif disabled_by == "tool":
        config.extra_config["tools"]["web_search"]["enabled"] = False
    else:
        config.enabled = False
    monkeypatch.setattr(configuration, "get_agent_config", lambda _: config)
    with pytest.raises(PermissionError, match="disabled"):
        await news_tools.web_search(QUERY)
    assert "disabled" in await news_tools.get_breaking_news()
    assert "disabled" in await news_tools.get_financial_news()
    assert not mcp_peer.requests


def test_saved_yaml_selection(configuration):
    path = configuration.loader.config_dir / "agents" / "research_agent.yaml"
    path.write_text(
        path.read_text().replace('provider: "auto"', 'provider: "perplexity"')
    )
    assert search.resolve_web_search_provider("research_agent") == "perplexity"


@pytest.mark.asyncio
async def test_agno_confirmation_gate_blocks_search(
    configuration, mcp_peer, monkeypatch
):
    peer = ModelPeer()
    async with REAL_ASYNC_CLIENT(transport=httpx.MockTransport(peer.handle)) as client:
        model = OpenAIChat(id="scripted", api_key="fixture", http_client=client)
        monkeypatch.setattr(news_core, "create_model_for_agent", lambda _: model)
        agent = news_core.NewsAgent()
        tool = Function.from_callable(news_tools.web_search)
        tool.requires_confirmation = True
        agent.knowledge_news_agent.tools = [tool]
        events = [event async for event in agent.stream(QUERY, "conversation", "task")]
    assert events
    assert peer.consumed is None
    assert not mcp_peer.requests


@pytest.mark.asyncio
async def test_empty_query_and_unknown_provider(configuration, mcp_peer, monkeypatch):
    with pytest.raises(ValueError, match="empty"):
        await news_tools.web_search("  ")
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "typo")
    with pytest.raises(ValueError, match="Unsupported"):
        await news_tools.web_search(QUERY)
    assert not mcp_peer.requests


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["tool_error", "empty", "http_error"])
async def test_mcp_errors(configuration, mcp_peer, failure):
    if failure == "tool_error":
        mcp_peer.error = True
        mcp_peer.text = "Search quota reached"
    elif failure == "empty":
        mcp_peer.text = ""
    else:
        mcp_peer.http_status = 403
    if failure == "http_error":
        with pytest.raises(ExceptionGroup) as raised:
            await news_tools.web_search(QUERY)
        assert raised.value.subgroup(httpx.HTTPStatusError) is not None
    else:
        message = "quota" if failure == "tool_error" else "no text content"
        with pytest.raises(RuntimeError, match=message):
            await news_tools.web_search(QUERY)


@pytest.mark.asyncio
async def test_deadline_and_cancellation(configuration, mcp_peer, monkeypatch):
    mcp_peer.block = True
    monkeypatch.setattr(search, "SEARCH_TIMEOUT_SECONDS", 0.05)
    with pytest.raises(TimeoutError):
        await news_tools.web_search(QUERY)
    assert mcp_peer.cancelled.is_set()
    mcp_peer.started.clear()
    mcp_peer.cancelled.clear()
    monkeypatch.setattr(search, "SEARCH_TIMEOUT_SECONDS", 30)
    task = asyncio.create_task(news_tools.web_search(QUERY))
    await asyncio.wait_for(mcp_peer.started.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert mcp_peer.cancelled.is_set()
