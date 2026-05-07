import importlib.util
from pathlib import Path

import pytest
import requests


TOOLS_PATH = (
    Path(__file__).resolve().parents[1] / "agents" / "news_agent" / "tools.py"
)
TOOLS_SPEC = importlib.util.spec_from_file_location("news_agent_tools", TOOLS_PATH)
tools = importlib.util.module_from_spec(TOOLS_SPEC)
TOOLS_SPEC.loader.exec_module(tools)


class _Response:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_fetch_adanos_stock_sentiment_builds_expected_request(monkeypatch):
    calls = []

    def fake_get(url, headers, params, timeout):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
            }
        )
        return _Response({"ticker": "AAPL", "sentiment_score": 0.35})

    monkeypatch.setenv("ADANOS_API_KEY", "test-key")
    monkeypatch.setattr(requests, "get", fake_get)

    payload = tools._fetch_adanos_stock_sentiment(
        ticker=" aapl ",
        source="News",
        days=3,
    )

    assert payload == {"ticker": "AAPL", "sentiment_score": 0.35}
    assert calls == [
        {
            "url": "https://api.adanos.org/news/stocks/v1/stock/AAPL",
            "headers": {"X-API-Key": "test-key", "Accept": "application/json"},
            "params": {"days": 3},
            "timeout": 10,
        }
    ]


@pytest.mark.asyncio
async def test_get_market_sentiment_reports_missing_api_key(monkeypatch):
    monkeypatch.delenv("ADANOS_API_KEY", raising=False)

    result = await tools.get_market_sentiment("AAPL")

    assert result == "ADANOS_API_KEY is not configured"


def test_fetch_adanos_stock_sentiment_validates_inputs(monkeypatch):
    monkeypatch.setenv("ADANOS_API_KEY", "test-key")

    with pytest.raises(ValueError, match="ticker must not be empty"):
        tools._fetch_adanos_stock_sentiment("", "news", 7)

    with pytest.raises(ValueError, match="source must be one of"):
        tools._fetch_adanos_stock_sentiment("AAPL", "invalid", 7)


def test_format_adanos_stock_sentiment_includes_available_fields():
    result = tools._format_adanos_stock_sentiment(
        {
            "ticker": "TSLA",
            "company_name": "Tesla Inc.",
            "sentiment_score": 0.42,
            "buzz_score": 88.5,
            "trend": "rising",
            "mentions": 123,
            "bullish_pct": 0.61,
            "bearish_pct": 0.22,
            "summary": "Discussion is improving across news and social sources.",
        },
        ticker="tsla",
        source="News",
    )

    assert "Market sentiment for TSLA (Tesla Inc.)" in result
    assert "Source: news" in result
    assert "Sentiment score: 0.42" in result
    assert "Buzz score: 88.5" in result
    assert "Trend: rising" in result
    assert "Mentions: 123" in result
    assert "Bullish: 0.61" in result
    assert "Bearish: 0.22" in result
    assert "Summary: Discussion is improving" in result
