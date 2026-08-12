import httpx
import pytest

from valuecell.agents.common import web_search


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: object = None):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeAsyncClient:
    response = FakeResponse(
        payload={
            "results": [
                {
                    "title": "Company release",
                    "url": "https://example.com/release",
                    "content": "A source snippet.",
                }
            ]
        }
    )
    calls = []

    def __init__(self, **kwargs: object):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


@pytest.mark.asyncio
async def test_search_tavily_sends_attribution_and_formats_sources(
    monkeypatch: pytest.MonkeyPatch,
):
    FakeAsyncClient.calls = []
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(web_search.httpx, "AsyncClient", FakeAsyncClient)

    result = await web_search.search_tavily("company news")

    assert "Company release" in result
    assert "https://example.com/release" in result
    assert "A source snippet." in result

    _, request = FakeAsyncClient.calls[0]
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["headers"]["X-Client-Name"] == (
        "open-monitor/valuecell-ai/valuecell"
    )
    assert request["headers"]["X-Client-Source"] == "open-monitor"
    assert request["json"]["include_answer"] is False
    assert request["json"]["include_raw_content"] == "markdown"


@pytest.mark.asyncio
async def test_search_tavily_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        await web_search.search_tavily("company news")


@pytest.mark.asyncio
async def test_search_tavily_rejects_invalid_responses(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(web_search.httpx, "AsyncClient", FakeAsyncClient)

    FakeAsyncClient.response = FakeResponse(status_code=500, payload={})
    with pytest.raises(RuntimeError, match="HTTP status 500"):
        await web_search.search_tavily("company news")

    FakeAsyncClient.response = FakeResponse(payload=httpx.DecodingError("invalid"))
    with pytest.raises(RuntimeError, match="invalid JSON"):
        await web_search.search_tavily("company news")

    FakeAsyncClient.response = FakeResponse(payload={"results": []})
    assert await web_search.search_tavily("company news") == (
        "Tavily returned no search results."
    )


@pytest.mark.asyncio
async def test_news_and_research_tools_select_tavily(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("WEB_SEARCH_PROVIDER", "tavily")

    async def fake_search(query: str) -> str:
        return query

    from valuecell.agents.news_agent import tools as news_tools
    from valuecell.agents.research_agent import sources as research_sources

    monkeypatch.setattr(news_tools, "search_tavily", fake_search)
    monkeypatch.setattr(research_sources, "search_tavily", fake_search)

    assert await news_tools.web_search("news query") == "news query"
    assert await research_sources.web_search("research query") == "research query"
