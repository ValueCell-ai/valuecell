import asyncio
import os
from datetime import datetime
from typing import Any, Literal, Optional

import httpx
import pandas as pd
from loguru import logger

from ..context import TaskContext


async def _fetch_alpha_vantage(
    function: str, symbol: str | None = None, extra_params: dict | None = None
) -> dict[str, Any]:
    """
    Robust fetcher for AlphaVantage API.

    Features:
    - Handles 'symbol' vs 'tickers' parameter automatically.
    - Detects API-level errors (Rate Limits, Invalid Token) even on HTTP 200.
    - Merges extra parameters (e.g. limit, sort, outputsize).
    """
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        logger.error("Missing ALPHA_VANTAGE_API_KEY environment variable")
        return {"error": "Configuration error: API key missing"}

    base_url = "https://www.alphavantage.co/query"

    # 1. Build Query Parameters
    params = {"function": function, "apikey": api_key}

    # Handle Symbol Mapping
    # NEWS_SENTIMENT uses 'tickers', most others use 'symbol'
    if symbol:
        if function == "NEWS_SENTIMENT":
            params["tickers"] = symbol
        else:
            params["symbol"] = symbol

    if extra_params:
        params.update(extra_params)

    # 2. Execute Request
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            logger.debug(f"AlphaVantage Request: {function} for {symbol or 'General'}")

            resp = await client.get(base_url, params=params)
            resp.raise_for_status()
            data = resp.json()

            # 3. AlphaVantage Specific Error Handling
            # AlphaVantage returns 200 OK even for errors, we must check the keys.

            # Case A: Rate Limit Hit (Common on free tier)
            # Usually contains "Note" or "Information"
            if "Note" in data or "Information" in data:
                msg = data.get("Note") or data.get("Information")
                logger.warning(f"AlphaVantage Rate Limit/Info: {msg}")
                # Optional: Implement retry logic here if needed
                return {"error": f"API Rate Limit reached: {msg}"}

            # Case B: Invalid API Call
            if "Error Message" in data:
                msg = data["Error Message"]
                logger.error(f"AlphaVantage API Error: {msg}")
                return {"error": f"Invalid API call: {msg}"}

            # Case C: Empty Result (Symbol not found)
            if not data:
                return {"error": "No data returned (Symbol might be invalid)"}

            return data

    except httpx.TimeoutException:
        logger.error("AlphaVantage Request Timed out")
        return {"error": "Data provider request timed out"}

    except Exception as exc:
        logger.exception(f"AlphaVantage Unhandled Error: {exc}")
        return {"error": str(exc)}


async def get_financial_metrics(
    symbol: str,
    period: Literal["annual", "quarterly"] = "annual",
    limit: int = 4,
    context: Optional[TaskContext] = None,
) -> str:
    """
    Retrieves detailed financial metrics for a stock symbol using AlphaVantage.
    Automatically calculates ratios like Margins, ROE, and Debt/Equity.

    Args:
        symbol: The stock ticker (e.g., 'IBM', 'AAPL').
        period: 'annual' for yearly reports, 'quarterly' for recent quarters.
        limit: Number of periods to return (default 4). Keep low to save tokens.
    """

    # Sequentially fetch endpoints with short delays to avoid AlphaVantage "burst" rate-limiting.
    try:
        # Emit progress event: starting income statement fetch
        if context:
            await context.emit_progress(
                f"Fetching Income Statement for {symbol}...", step="fetching_income"
            )

        # 1) Income Statement
        data_inc = await _fetch_alpha_vantage(
            symbol=symbol, function="INCOME_STATEMENT"
        )
        await asyncio.sleep(1.5)

        # Emit progress event: starting balance sheet fetch
        if context:
            await context.emit_progress(
                "Fetching Balance Sheet...", step="fetching_balance"
            )

        # 2) Balance Sheet
        data_bal = await _fetch_alpha_vantage(symbol=symbol, function="BALANCE_SHEET")
        await asyncio.sleep(1.5)

        # Emit progress event: starting cash flow fetch
        if context:
            await context.emit_progress("Fetching Cash Flow...", step="fetching_cash")

        # 3) Cash Flow
        data_cash = await _fetch_alpha_vantage(symbol=symbol, function="CASH_FLOW")

        # If any endpoint returned an API-level error, surface it for clarity.
        if isinstance(data_inc, dict) and "error" in data_inc:
            return f"API Error (Income): {data_inc['error']}"
        if isinstance(data_bal, dict) and "error" in data_bal:
            return f"API Error (Balance): {data_bal['error']}"
        if isinstance(data_cash, dict) and "error" in data_cash:
            return f"API Error (Cash): {data_cash['error']}"

        # Normalize any remaining error-bearing responses into empty dicts for downstream logic
        data_inc = (
            data_inc if not (isinstance(data_inc, dict) and "error" in data_inc) else {}
        )
        data_bal = (
            data_bal if not (isinstance(data_bal, dict) and "error" in data_bal) else {}
        )
        data_cash = (
            data_cash
            if not (isinstance(data_cash, dict) and "error" in data_cash)
            else {}
        )

    except Exception as e:
        return f"API Error: {str(e)}"

    report_key = "annualReports" if period == "annual" else "quarterlyReports"

    if not data_inc.get(report_key):
        return f"No {period} financial data found for {symbol}."

    def to_df(data_dict):
        reports = data_dict.get(report_key, [])
        if not reports:
            return pd.DataFrame()
        df = pd.DataFrame(reports)
        df = df.replace("None", pd.NA)
        if "fiscalDateEnding" in df.columns:
            df["fiscalDateEnding"] = pd.to_datetime(df["fiscalDateEnding"])
            df.set_index("fiscalDateEnding", inplace=True)
        return df

    df_inc = to_df(data_inc)
    df_bal = to_df(data_bal)
    df_cash = to_df(data_cash)

    df_merged = pd.concat([df_inc, df_bal, df_cash], axis=1)
    df_merged = df_merged.loc[:, ~df_merged.columns.duplicated()]
    df_merged.sort_index(ascending=False, inplace=True)
    df_final = df_merged.head(limit).copy()

    cols_to_convert = df_final.columns.drop("reportedCurrency", errors="ignore")
    for col in cols_to_convert:
        df_final[col] = pd.to_numeric(df_final[col], errors="coerce")

    try:
        # Profitability
        df_final["Gross Margin %"] = (
            df_final["grossProfit"] / df_final["totalRevenue"]
        ) * 100
        df_final["Net Margin %"] = (
            df_final["netIncome"] / df_final["totalRevenue"]
        ) * 100

        # Balance Sheet Health
        # debt = shortTerm + longTerm
        # 1) Data endpoints to request in parallel from AlphaVantage
        total_debt = df_final.get(
            "shortLongTermDebtTotal",
            df_final.get("shortTermDebt", 0) + df_final.get("longTermDebt", 0),
        )
        df_final["Total Debt"] = total_debt
        df_final["Debt/Equity"] = total_debt / df_final["totalShareholderEquity"]

        # Cash Flow
        # Free Cash Flow = Operating Cash Flow - Capital Expenditures
        df_final["Free Cash Flow"] = (
            df_final["operatingCashflow"] - df_final["capitalExpenditures"]
        )

    except KeyError:
        pass

    df_display = df_final.T
    metrics_map = {
        "totalRevenue": "Revenue",
        "grossProfit": "Gross Profit",
        "netIncome": "Net Income",
        "Gross Margin %": "Gross Margin %",
        "Net Margin %": "Net Margin %",
        "reportedEPS": "EPS",
        "totalAssets": "Total Assets",
        "totalShareholderEquity": "Total Equity",
        "Total Debt": "Total Debt",
        "Debt/Equity": "Debt/Equity Ratio",
        "operatingCashflow": "Operating Cash Flow",
        "Free Cash Flow": "Free Cash Flow",
    }
    existing_metrics = [m for m in metrics_map.keys() if m in df_display.index]
    df_display = df_display.loc[existing_metrics]
    df_display.rename(index=metrics_map, inplace=True)

    def fmt_val(val, metric_name):
        if pd.isna(val):
            return "-"
        if "%" in metric_name or "Ratio" in metric_name:
            return f"{val:.2f}" + ("%" if "%" in metric_name else "x")
        if abs(val) >= 1e9:
            return f"${val / 1e9:.2f}B"
        if abs(val) >= 1e6:
            return f"${val / 1e6:.2f}M"
        return f"{val:,.0f}"

    for col in df_display.columns:
        df_display[col] = df_display.apply(
            lambda row: fmt_val(row[col], row.name), axis=1
        )

    df_display.columns = [d.strftime("%Y-%m-%d") for d in df_display.columns]

    md_table = df_display.to_markdown()

    return (
        f"### Financial Metrics ({period.title()}, Last {limit} periods)\n\n{md_table}"
    )


async def get_stock_profile(symbol: str, context: Optional[TaskContext] = None) -> str:
    """
    Retrieves a comprehensive profile for a stock symbol.
    Includes company description, sector, real-time price, valuation metrics (PE, Market Cap),
    and analyst ratings.
    """
    # Note: fetching is performed sequentially below to avoid rate limits

    # Fetch sequentially with a short pause to avoid AlphaVantage burst detection
    try:
        # Emit progress event: starting quote fetch
        if context:
            await context.emit_progress(
                f"Fetching real-time quote for {symbol}...", step="fetching_quote"
            )

        # 1. Global Quote
        quote_data = await _fetch_alpha_vantage(symbol=symbol, function="GLOBAL_QUOTE")
        # Pause to avoid rapid-fire requests triggering rate limits
        await asyncio.sleep(1.5)

        # Emit progress event: starting overview fetch
        if context:
            await context.emit_progress(
                "Fetching company overview...", step="fetching_overview"
            )

        # 2. Overview
        overview_data = await _fetch_alpha_vantage(symbol=symbol, function="OVERVIEW")
    except Exception as e:
        return f"Error fetching profile for {symbol}: {str(e)}"

    # --- Parse the quote response ---
    # AlphaVantage formats GLOBAL_QUOTE keys like '01. symbol', '05. price'.
    # clean_quote extracts the human-friendly key (text after the numeric prefix).
    def clean_quote(q: dict) -> dict:
        # Return a mapping like {'price': '123.45', 'volume': '123456'}
        return {k.split(". ")[1]: v for k, v in q.get("Global Quote", {}).items()}

    quote = clean_quote(quote_data)
    overview = (
        overview_data
        if not (isinstance(overview_data, dict) and "error" in overview_data)
        else {}
    )

    # If neither quote nor overview has data, return early
    if not quote and not overview:
        return f"No profile data found for {symbol}."

    # Helper to format large numbers into human-friendly strings
    def fmt_num(val):
        if not val or val == "None":
            return "-"
        try:
            f = float(val)
            if abs(f) >= 1e9:
                return f"${f / 1e9:.2f}B"
            if abs(f) >= 1e6:
                return f"${f / 1e6:.2f}M"
            return f"{f:,.2f}"
        except Exception:
            return val

    # --- Assemble Markdown profile ---
    # Header / basic company info
    name = overview.get("Name", symbol)
    sector = overview.get("Sector", "-")
    industry = overview.get("Industry", "-")
    desc = overview.get("Description", "No description available.")
    # Truncate long descriptions to save tokens
    if len(desc) > 300:
        desc = desc[:300] + "..."

    profile_md = f"### Stock Profile: {name} ({symbol})\n\n"
    profile_md += f"**Sector**: {sector} | **Industry**: {industry}\n\n"
    profile_md += f"**Description**: {desc}\n\n"

    # --- Market snapshot table ---
    # Format price, change, market cap, volume and 52-week range
    price = fmt_num(quote.get("price"))
    change_pct = quote.get("change percent", "-")
    # Choose a simple textual indicator for trend (avoid emoji)
    trend = "Up" if change_pct and "-" not in change_pct else "Down"

    mkt_cap = fmt_num(overview.get("MarketCapitalization"))
    vol = fmt_num(quote.get("volume"))

    range_52w = (
        f"{fmt_num(overview.get('52WeekLow'))} - {fmt_num(overview.get('52WeekHigh'))}"
    )

    profile_md += "**Market Snapshot**\n"
    profile_md += "| Price | Change | Market Cap | Volume | 52W Range |\n"
    profile_md += "|---|---|---|---|---|\n"
    profile_md += (
        f"| {price} | {trend} {change_pct} | {mkt_cap} | {vol} | {range_52w} |\n\n"
    )

    # --- Valuation & Financials ---
    pe = overview.get("PERatio", "-")
    peg = overview.get("PEGRatio", "-")
    eps = overview.get("EPS", "-")
    div_yield = overview.get("DividendYield", "0")
    try:
        div_yield_pct = f"{float(div_yield) * 100:.2f}%"
    except Exception:
        div_yield_pct = "-"

    beta = overview.get("Beta", "-")
    profit_margin = overview.get("ProfitMargin", "-")
    try:
        pm_pct = f"{float(profit_margin) * 100:.1f}%"
    except Exception:
        pm_pct = "-"

    profile_md += "**Valuation & Financials**\n"
    profile_md += "| PE Ratio | PEG | EPS | Div Yield | Beta | Profit Margin |\n"
    profile_md += "|---|---|---|---|---|---|\n"
    profile_md += f"| {pe} | {peg} | {eps} | {div_yield_pct} | {beta} | {pm_pct} |\n\n"

    # --- Analyst Ratings (if provided) ---
    target = overview.get("AnalystTargetPrice")
    buy = overview.get("AnalystRatingBuy", "0")
    hold = overview.get("AnalystRatingHold", "0")
    sell = overview.get("AnalystRatingSell", "0")

    if target and target != "None":
        profile_md += f"**Analyst Consensus**: Target Price ${target} (Buy: {buy}, Hold: {hold}, Sell: {sell})"

    return profile_md


async def get_market_sentiment(symbol: str, limit: int = 10) -> str:
    """
    Retrieves and summarizes market sentiment and news for a specific stock symbol.
    Uses AlphaVantage News Sentiment API to get sentiment scores and summaries.

    Args:
        symbol: Stock ticker (e.g., 'AAPL', 'TSLA').
        limit: Max number of news items to analyze (default 10).
    """
    # 1. Fetch data
    # Note: 'tickers' param filters news mentioning this symbol
    data = await _fetch_alpha_vantage(
        function="NEWS_SENTIMENT",
        symbol=None,
        extra_params={"tickers": symbol, "limit": str(limit)},
    )

    feed = data.get("feed", [])
    if not feed:
        return f"No recent news found for {symbol}."

    # 2. Filter and Process News
    # We only want news where the ticker is RELEVANT (score > 0.1)
    relevant_news = []
    total_sentiment_score = 0.0
    valid_count = 0

    for item in feed:
        # Find sentiment for OUR symbol within the list of tickers mentioned in this article
        ticker_meta = next(
            (t for t in item.get("ticker_sentiment", []) if t["ticker"] == symbol), None
        )

        # Fallback: if symbol not explicitly in list (rare), use overall sentiment
        sentiment_score = (
            float(ticker_meta["ticker_sentiment_score"])
            if ticker_meta
            else item.get("overall_sentiment_score", 0)
        )
        relevance = float(ticker_meta["relevance_score"]) if ticker_meta else 0

        # Filter noise: Skip low relevance articles
        if relevance < 0.1:
            continue

        valid_count += 1
        total_sentiment_score += sentiment_score

        # Format date: 20251211T001038 -> 2025-12-11
        pub_date = item.get("time_published", "")[:8]
        try:
            pub_date = datetime.strptime(pub_date, "%Y%m%d").strftime("%Y-%m-%d")
        except Exception:
            pass

        relevant_news.append(
            {
                "title": item.get("title"),
                "summary": item.get("summary"),
                "source": item.get("source"),
                "date": pub_date,
                "url": item.get("url"),
                "sentiment_label": item.get(
                    "overall_sentiment_label"
                ),  # Use overall label for readability
                "score": sentiment_score,
            }
        )

    if not relevant_news:
        return f"Found news, but none were highly relevant to {symbol}."

    # 3. Calculate Aggregated Sentiment
    avg_score = total_sentiment_score / valid_count if valid_count > 0 else 0

    # Map score to label (based on AlphaVantage definition)
    if avg_score <= -0.15:
        aggregate_label = "Bearish 🐻"
    elif avg_score >= 0.15:
        aggregate_label = "Bullish 🐂"
    else:
        aggregate_label = "Neutral 😐"

    # 4. Construct Markdown Output
    # Header
    md = f"### Market Sentiment for {symbol}\n"
    md += f"**Overall Signal**: {aggregate_label} (Avg Score: {avg_score:.2f})\n"
    md += f"**Analysis Basis**: {len(relevant_news)} relevant articles\n\n"

    # Top News List (Markdown)
    md += "**Top Relevant News:**\n"
    for news in relevant_news[:5]:  # Show top 5 to save space
        label_icon = (
            "🟢"
            if "Bullish" in news["sentiment_label"]
            else "🔴"
            if "Bearish" in news["sentiment_label"]
            else "⚪"
        )

        md += f"- **{news['date']}** [{news['source']}]\n"
        md += f"  [{news['title']}]({news['url']})\n"
        md += f"  *Sentiment:* {label_icon} {news['sentiment_label']} | *Summary:* {news['summary'][:150]}...\n\n"

    return md
