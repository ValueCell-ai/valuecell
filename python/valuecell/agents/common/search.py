"""Shared search selection and anonymous Parallel Search MCP transport."""

import asyncio
import os

from httpx import AsyncClient
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent

from valuecell.config.manager import get_config_manager

PARALLEL_MCP_URL = "https://search.parallel.ai/mcp"
SEARCH_USER_AGENT = "ValueCell/0.1 (+https://github.com/ValueCell-ai/valuecell)"
SEARCH_TIMEOUT_SECONDS = 30


def resolve_web_search_provider(agent_name: str) -> str:
    """Honor saved search settings before selecting a usable default."""
    manager = get_config_manager()
    config = manager.get_agent_config(agent_name)
    if config is None:
        raise ValueError(f"Missing configuration for {agent_name}")

    search = config.capabilities.get("web_search", {})
    tool = config.extra_config.get("tools", {}).get("web_search", {})
    if (
        not config.enabled
        or not search.get("enabled", True)
        or not tool.get("enabled", True)
    ):
        raise PermissionError(f"Web search is disabled for {agent_name}")

    provider = os.getenv("WEB_SEARCH_PROVIDER", search.get("provider", "auto"))
    provider = provider.strip().lower()
    if not provider:
        provider = "auto"
    if provider == "none":
        raise PermissionError("Web search is disabled by WEB_SEARCH_PROVIDER=none")
    if provider not in {"auto", "parallel", "google", "perplexity"}:
        raise ValueError(f"Unsupported WEB_SEARCH_PROVIDER: {provider}")
    if provider != "auto":
        return provider

    # Keep credentialed installations on their existing search services.
    for name, selection in (("google", "google"), ("openrouter", "perplexity")):
        configured = manager.get_provider_config(name)
        if configured is not None and configured.enabled and configured.api_key:
            return selection
    return "parallel"


async def search_parallel(query: str) -> str:
    """Return source excerpts and URLs from free anonymous Search MCP.

    The deadline covers discovery, execution and cleanup. Cancellation propagates
    to the MCP session; an error never triggers another provider.
    """
    if not query.strip():
        raise ValueError("The search query must not be empty")

    async with asyncio.timeout(SEARCH_TIMEOUT_SECONDS):
        async with AsyncClient(
            headers={"User-Agent": SEARCH_USER_AGENT},
            timeout=SEARCH_TIMEOUT_SECONDS,
        ) as client:
            async with streamable_http_client(PARALLEL_MCP_URL, http_client=client) as (
                read,
                write,
                _,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    if not any(tool.name == "web_search" for tool in tools.tools):
                        raise RuntimeError("Parallel MCP does not offer web_search")
                    result = await session.call_tool(
                        "web_search", {"objective": query, "search_queries": [query]}
                    )

    text = "\n\n".join(
        block.text for block in result.content if isinstance(block, TextContent)
    )
    if result.isError:
        raise RuntimeError(f"Parallel web search failed: {text[:1000]}")
    if not text.strip():
        raise RuntimeError("Parallel web search returned no text content")
    return text
