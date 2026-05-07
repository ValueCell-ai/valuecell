"""News-related tools for the News Agent."""

import asyncio
import os
from datetime import datetime
from typing import Optional

import requests
from agno.agent import Agent
from loguru import logger

from valuecell.adapters.models import create_model

ADANOS_API_BASE_URL = "https://api.adanos.org"
ADANOS_SOURCES = {"reddit", "x", "news", "polymarket"}


async def web_search(query: str) -> str:
    """Search web for the given query and return a summary of the top results.

    This function uses the centralized configuration system to create model instances.
    It supports multiple search providers:
    - Google (Gemini with search enabled) - when WEB_SEARCH_PROVIDER=google and GOOGLE_API_KEY is set
    - Perplexity (via OpenRouter) - default fallback

    Args:
        query: The search query string.

    Returns:
        A summary of the top search results.
    """
    # Check which provider to use based on environment configuration
    if os.getenv("WEB_SEARCH_PROVIDER", "google").lower() == "google" and os.getenv(
        "GOOGLE_API_KEY"
    ):
        return await _web_search_google(query)

    # Use Perplexity Sonar via OpenRouter for web search
    # Perplexity models are optimized for web search and real-time information
    model = create_model(
        provider="openrouter",
        model_id="perplexity/sonar",
        max_tokens=None,
    )
    response = await Agent(model=model).arun(query)
    return response.content


async def _web_search_google(query: str) -> str:
    """Search Google for the given query and return a summary of the top results.

    Uses Google Gemini with search grounding enabled for real-time web information.

    Args:
        query: The search query string.

    Returns:
        A summary of the top search results.
    """
    # Use Google Gemini with search enabled
    # The search=True parameter enables Google Search grounding for real-time information
    model = create_model(
        provider="google",
        model_id="gemini-2.5-flash",
        search=True,  # Enable Google Search grounding
    )
    response = await Agent(model=model).arun(query)
    return response.content


async def get_breaking_news() -> str:
    """Get breaking news and urgent updates.

    Returns:
        Formatted string containing breaking news
    """
    try:
        search_query = "breaking news urgent updates today"
        logger.info("Fetching breaking news")

        news_content = await web_search(search_query)
        return news_content

    except Exception as e:
        logger.error(f"Error fetching breaking news: {e}")
        return f"Error fetching breaking news: {str(e)}"


async def get_financial_news(
    ticker: Optional[str] = None, sector: Optional[str] = None
) -> str:
    """Get financial and market news.

    Args:
        ticker: Stock ticker symbol for company-specific news
        sector: Industry sector for sector-specific news

    Returns:
        Formatted string containing financial news
    """
    try:
        search_query = "financial market news"

        if ticker:
            search_query = f"{ticker} stock news financial market"
        elif sector:
            search_query = f"{sector} sector financial news market"

        # Add time constraint for recent news
        today = datetime.now().strftime("%Y-%m-%d")
        search_query += f" {today}"

        logger.info(f"Searching for financial news with query: {search_query}")

        news_content = await web_search(search_query)
        return news_content

    except Exception as e:
        logger.error(f"Error fetching financial news: {e}")
        return f"Error fetching financial news: {str(e)}"


async def get_market_sentiment(
    ticker: str,
    source: str = "news",
    days: int = 7,
) -> str:
    """Get stock market sentiment from Adanos Market Sentiment API.

    Use this tool when users ask about stock sentiment, market mood, social
    discussion, FinTwit/X sentiment, news sentiment, or Polymarket signals for
    a US-listed equity.

    Args:
        ticker: Stock ticker symbol, for example "AAPL" or "TSLA".
        source: Sentiment source. One of: reddit, x, news, polymarket.
        days: Lookback window in days. Defaults to 7.

    Returns:
        Formatted sentiment summary or configuration/error guidance.
    """

    try:
        payload = await asyncio.to_thread(
            _fetch_adanos_stock_sentiment,
            ticker=ticker,
            source=source,
            days=days,
        )
    except ValueError as e:
        return str(e)
    except requests.RequestException as e:
        logger.error(f"Error fetching Adanos market sentiment: {e}")
        return f"Error fetching market sentiment: {str(e)}"

    return _format_adanos_stock_sentiment(payload, ticker=ticker, source=source)


def _fetch_adanos_stock_sentiment(
    ticker: str,
    source: str,
    days: int,
) -> dict:
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("ticker must not be empty")

    source = source.strip().lower()
    if source not in ADANOS_SOURCES:
        raise ValueError("source must be one of: reddit, x, news, polymarket")

    api_key = os.getenv("ADANOS_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ADANOS_API_KEY is not configured")

    response = requests.get(
        f"{ADANOS_API_BASE_URL}/{source}/stocks/v1/stock/{ticker}",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
        params={"days": days},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _format_adanos_stock_sentiment(
    payload: dict,
    ticker: str,
    source: str,
) -> str:
    ticker = str(payload.get("ticker") or ticker).upper()
    company_name = payload.get("company_name") or payload.get("company") or ticker
    sentiment_score = payload.get("sentiment_score")
    buzz_score = payload.get("buzz_score")
    trend = payload.get("trend")
    mentions = payload.get("mentions")
    bullish_pct = payload.get("bullish_pct")
    bearish_pct = payload.get("bearish_pct")

    lines = [
        f"Market sentiment for {ticker} ({company_name})",
        f"Source: {source.strip().lower()}",
    ]
    if sentiment_score is not None:
        lines.append(f"Sentiment score: {sentiment_score}")
    if buzz_score is not None:
        lines.append(f"Buzz score: {buzz_score}")
    if trend:
        lines.append(f"Trend: {trend}")
    if mentions is not None:
        lines.append(f"Mentions: {mentions}")
    if bullish_pct is not None:
        lines.append(f"Bullish: {bullish_pct}")
    if bearish_pct is not None:
        lines.append(f"Bearish: {bearish_pct}")

    summary = payload.get("summary") or payload.get("explanation")
    if summary:
        lines.append(f"Summary: {summary}")

    return "\n".join(lines)
