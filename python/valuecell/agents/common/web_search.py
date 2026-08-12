"""Shared web-search integrations for agent tools."""

import os
from collections.abc import Mapping
from typing import Any

import httpx

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TAVILY_CLIENT_NAME = "open-monitor/valuecell-ai/valuecell"
TAVILY_CLIENT_SOURCE = "open-monitor"
TAVILY_MAX_RESULTS = 5
TAVILY_MAX_CONTENT_CHARS = 2000
TAVILY_TIMEOUT_SECONDS = 15.0


def _text_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _format_result(result: Mapping[str, object], index: int) -> str:
    title = _text_value(result.get("title")) or "Untitled source"
    url = _text_value(result.get("url")) or "Unavailable"
    raw_content = _text_value(result.get("raw_content"))
    content = raw_content or _text_value(result.get("content"))
    content = content[:TAVILY_MAX_CONTENT_CHARS] or "No content snippet returned."

    return f"Source {index}: {title}\nURL: {url}\nContent: {content}"


def _format_results(results: list[object]) -> str:
    formatted = [
        _format_result(result, index)
        for index, result in enumerate(results[:TAVILY_MAX_RESULTS], start=1)
        if isinstance(result, Mapping)
    ]
    if not formatted:
        return "Tavily returned no usable search results."
    return "\n\n".join(formatted)


async def search_tavily(query: str, max_results: int = TAVILY_MAX_RESULTS) -> str:
    """Search Tavily and return source URLs with bounded content."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY must be set when WEB_SEARCH_PROVIDER=tavily.")

    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": min(max(max_results, 1), TAVILY_MAX_RESULTS),
        "include_answer": False,
        "include_raw_content": "markdown",
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Client-Name": TAVILY_CLIENT_NAME,
        "X-Client-Source": TAVILY_CLIENT_SOURCE,
    }

    try:
        async with httpx.AsyncClient(timeout=TAVILY_TIMEOUT_SECONDS) as client:
            response = await client.post(
                TAVILY_SEARCH_URL,
                headers=headers,
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise RuntimeError("Tavily search request failed.") from exc

    if not 200 <= response.status_code < 300:
        raise RuntimeError(
            f"Tavily search failed with HTTP status {response.status_code}."
        )

    try:
        response_data = response.json()
    except (httpx.DecodingError, TypeError, ValueError) as exc:
        raise RuntimeError("Tavily returned an invalid JSON response.") from exc

    if not isinstance(response_data, Mapping):
        raise RuntimeError("Tavily returned an invalid response format.")

    results = response_data.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Tavily response did not include a results list.")
    if not results:
        return "Tavily returned no search results."

    return _format_results(results)
