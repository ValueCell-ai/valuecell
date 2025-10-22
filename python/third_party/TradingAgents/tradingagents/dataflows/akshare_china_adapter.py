"""AKShare adapter for A-share (China stock market) data.

This module provides data interfaces for Chinese stock markets (SSE, SZSE, BSE)
using the AKShare library. It serves as a replacement for Finnhub/SimFin data
sources when analyzing A-share stocks.
"""

import os
import json
import logging
from typing import Annotated, Optional, List, Dict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd

try:
    import akshare as ak
except ImportError:
    ak = None
    logging.warning("AKShare not installed. Install with: pip install akshare")

logger = logging.getLogger(__name__)


class AShareDataAdapter:
    """Adapter for A-share market data using AKShare."""

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize A-share data adapter.

        Args:
            cache_dir: Directory for caching data (optional)
        """
        if ak is None:
            raise ImportError("AKShare is required. Install with: pip install akshare")

        self.cache_dir = cache_dir
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

    @staticmethod
    def is_a_share_symbol(symbol: str) -> bool:
        """Check if symbol is an A-share stock code.

        Args:
            symbol: Stock symbol/code

        Returns:
            True if it's an A-share code (6 digits starting with 0, 3, or 6)
        """
        return (
            symbol.isdigit()
            and len(symbol) == 6
            and symbol[0] in ['0', '3', '6', '8']
        )

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """Normalize symbol format for A-share stocks.

        Args:
            symbol: Stock symbol (may include exchange prefix)

        Returns:
            Normalized 6-digit stock code
        """
        # Remove common prefixes like SSE:, SZSE:, etc.
        symbol = symbol.upper().replace('SSE:', '').replace('SZSE:', '').replace('BSE:', '')

        # Extract 6-digit code
        if symbol.isdigit() and len(symbol) == 6:
            return symbol

        raise ValueError(f"Invalid A-share symbol: {symbol}")


# ============================================================================
# News and Information Functions
# ============================================================================

def get_a_share_news(
    ticker: Annotated[str, "A-share stock code (6 digits)"],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "How many days to look back"] = 7,
) -> str:
    """Retrieve news about an A-share company.

    Args:
        ticker: A-share stock code (e.g., '600519' for Moutai)
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back

    Returns:
        Formatted news report string
    """
    try:
        adapter = AShareDataAdapter()
        ticker = adapter.normalize_symbol(ticker)

        # Get company news from East Money
        df_news = ak.stock_news_em(symbol=ticker)

        if df_news is None or df_news.empty:
            return f"No news available for {ticker}"

        # Filter by date range
        curr_date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
        start_date = curr_date_obj - timedelta(days=look_back_days)

        # Convert date column
        df_news['发布时间'] = pd.to_datetime(df_news['发布时间'])
        df_news = df_news[
            (df_news['发布时间'] >= start_date) &
            (df_news['发布时间'] <= curr_date_obj)
        ]

        if df_news.empty:
            return f"No news in the past {look_back_days} days for {ticker}"

        # Format news
        news_list = []
        for _, row in df_news.head(20).iterrows():  # Limit to 20 most recent
            news_item = (
                f"### {row['新闻标题']} ({row['发布时间'].strftime('%Y-%m-%d')})\n"
                f"{row['新闻内容']}\n"
            )
            news_list.append(news_item)

        result = (
            f"## News for {ticker} from "
            f"{start_date.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
            + "\n".join(news_list)
        )

        return result

    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        return f"Error fetching news: {str(e)}"


def get_a_share_announcements(
    ticker: Annotated[str, "A-share stock code"],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "How many days to look back"] = 30,
) -> str:
    """Retrieve official announcements for an A-share company.

    Args:
        ticker: A-share stock code
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back

    Returns:
        Formatted announcements report
    """
    try:
        adapter = AShareDataAdapter()
        ticker = adapter.normalize_symbol(ticker)

        # Get company announcements
        df_announce = ak.stock_notice_report(symbol=ticker)

        if df_announce is None or df_announce.empty:
            return f"No announcements available for {ticker}"

        # Filter by date
        curr_date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
        start_date = curr_date_obj - timedelta(days=look_back_days)

        df_announce['发布日期'] = pd.to_datetime(df_announce['发布日期'])
        df_announce = df_announce[
            (df_announce['发布日期'] >= start_date) &
            (df_announce['发布日期'] <= curr_date_obj)
        ]

        if df_announce.empty:
            return f"No announcements in the past {look_back_days} days for {ticker}"

        # Format announcements
        announce_list = []
        for _, row in df_announce.head(15).iterrows():
            announce_item = (
                f"### {row['公告标题']} ({row['发布日期'].strftime('%Y-%m-%d')})\n"
                f"公告类型: {row.get('公告类型', 'N/A')}\n"
            )
            announce_list.append(announce_item)

        result = (
            f"## Official Announcements for {ticker} from "
            f"{start_date.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
            + "\n".join(announce_list)
        )

        return result

    except Exception as e:
        logger.error(f"Error fetching announcements for {ticker}: {e}")
        return f"Error fetching announcements: {str(e)}"


# ============================================================================
# Financial Statement Functions
# ============================================================================

def get_a_share_balance_sheet(
    ticker: Annotated[str, "A-share stock code"],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
) -> str:
    """Get balance sheet for an A-share company.

    Args:
        ticker: A-share stock code
        curr_date: Current date in yyyy-mm-dd format

    Returns:
        Formatted balance sheet report
    """
    try:
        adapter = AShareDataAdapter()
        ticker = adapter.normalize_symbol(ticker)

        # Get balance sheet from East Money
        df_balance = ak.stock_balance_sheet_by_report_em(symbol=ticker)

        if df_balance is None or df_balance.empty:
            return f"No balance sheet data available for {ticker}"

        # Get the most recent report before curr_date
        curr_date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
        df_balance['REPORT_DATE'] = pd.to_datetime(df_balance['REPORT_DATE'])
        df_balance = df_balance[df_balance['REPORT_DATE'] <= curr_date_obj]

        if df_balance.empty:
            return f"No balance sheet data before {curr_date} for {ticker}"

        # Get most recent report
        latest_report = df_balance.sort_values('REPORT_DATE', ascending=False).iloc[0]

        # Format key metrics
        report_date = latest_report['REPORT_DATE'].strftime('%Y-%m-%d')

        result = f"## Balance Sheet for {ticker} (Report Date: {report_date}):\n\n"
        result += f"### Assets:\n"
        result += f"- Total Assets: {latest_report.get('TOTAL_ASSETS', 'N/A'):,.2f}\n"
        result += f"- Current Assets: {latest_report.get('TOTAL_CURRENT_ASSETS', 'N/A'):,.2f}\n"
        result += f"- Non-current Assets: {latest_report.get('TOTAL_NONCURRENT_ASSETS', 'N/A'):,.2f}\n"
        result += f"- Cash and Equivalents: {latest_report.get('MONETARY_CAP', 'N/A'):,.2f}\n"
        result += f"\n### Liabilities:\n"
        result += f"- Total Liabilities: {latest_report.get('TOTAL_LIABILITIES', 'N/A'):,.2f}\n"
        result += f"- Current Liabilities: {latest_report.get('TOTAL_CURRENT_LIAB', 'N/A'):,.2f}\n"
        result += f"- Non-current Liabilities: {latest_report.get('TOTAL_NONCURRENT_LIAB', 'N/A'):,.2f}\n"
        result += f"\n### Equity:\n"
        result += f"- Total Equity: {latest_report.get('TOTAL_EQUITY', 'N/A'):,.2f}\n"
        result += f"- Parent Company Equity: {latest_report.get('EQUITY_PARENT_COMPANY', 'N/A'):,.2f}\n"

        return result

    except Exception as e:
        logger.error(f"Error fetching balance sheet for {ticker}: {e}")
        return f"Error fetching balance sheet: {str(e)}"


def get_a_share_income_statement(
    ticker: Annotated[str, "A-share stock code"],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
) -> str:
    """Get income statement for an A-share company.

    Args:
        ticker: A-share stock code
        curr_date: Current date in yyyy-mm-dd format

    Returns:
        Formatted income statement report
    """
    try:
        adapter = AShareDataAdapter()
        ticker = adapter.normalize_symbol(ticker)

        # Get income statement
        df_income = ak.stock_profit_sheet_by_report_em(symbol=ticker)

        if df_income is None or df_income.empty:
            return f"No income statement data available for {ticker}"

        # Filter by date
        curr_date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
        df_income['REPORT_DATE'] = pd.to_datetime(df_income['REPORT_DATE'])
        df_income = df_income[df_income['REPORT_DATE'] <= curr_date_obj]

        if df_income.empty:
            return f"No income statement data before {curr_date} for {ticker}"

        # Get most recent report
        latest_report = df_income.sort_values('REPORT_DATE', ascending=False).iloc[0]
        report_date = latest_report['REPORT_DATE'].strftime('%Y-%m-%d')

        result = f"## Income Statement for {ticker} (Report Date: {report_date}):\n\n"
        result += f"### Revenue:\n"
        result += f"- Total Revenue: {latest_report.get('TOTAL_OPERATE_INCOME', 'N/A'):,.2f}\n"
        result += f"- Operating Revenue: {latest_report.get('OPERATE_INCOME', 'N/A'):,.2f}\n"
        result += f"\n### Costs and Expenses:\n"
        result += f"- Operating Costs: {latest_report.get('OPERATE_COST', 'N/A'):,.2f}\n"
        result += f"- Total Operating Expenses: {latest_report.get('TOTAL_OPERATE_COST', 'N/A'):,.2f}\n"
        result += f"\n### Profit:\n"
        result += f"- Operating Profit: {latest_report.get('OPERATE_PROFIT', 'N/A'):,.2f}\n"
        result += f"- Total Profit: {latest_report.get('TOTAL_PROFIT', 'N/A'):,.2f}\n"
        result += f"- Net Profit: {latest_report.get('NETPROFIT', 'N/A'):,.2f}\n"
        result += f"- Net Profit (Parent): {latest_report.get('PARENT_NETPROFIT', 'N/A'):,.2f}\n"
        result += f"\n### Per Share:\n"
        result += f"- Basic EPS: {latest_report.get('BASIC_EPS', 'N/A')}\n"
        result += f"- Diluted EPS: {latest_report.get('DILUTED_EPS', 'N/A')}\n"

        return result

    except Exception as e:
        logger.error(f"Error fetching income statement for {ticker}: {e}")
        return f"Error fetching income statement: {str(e)}"


def get_a_share_cashflow_statement(
    ticker: Annotated[str, "A-share stock code"],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
) -> str:
    """Get cash flow statement for an A-share company.

    Args:
        ticker: A-share stock code
        curr_date: Current date in yyyy-mm-dd format

    Returns:
        Formatted cash flow statement report
    """
    try:
        adapter = AShareDataAdapter()
        ticker = adapter.normalize_symbol(ticker)

        # Get cash flow statement
        df_cashflow = ak.stock_cash_flow_sheet_by_report_em(symbol=ticker)

        if df_cashflow is None or df_cashflow.empty:
            return f"No cash flow data available for {ticker}"

        # Filter by date
        curr_date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
        df_cashflow['REPORT_DATE'] = pd.to_datetime(df_cashflow['REPORT_DATE'])
        df_cashflow = df_cashflow[df_cashflow['REPORT_DATE'] <= curr_date_obj]

        if df_cashflow.empty:
            return f"No cash flow data before {curr_date} for {ticker}"

        # Get most recent report
        latest_report = df_cashflow.sort_values('REPORT_DATE', ascending=False).iloc[0]
        report_date = latest_report['REPORT_DATE'].strftime('%Y-%m-%d')

        result = f"## Cash Flow Statement for {ticker} (Report Date: {report_date}):\n\n"
        result += f"### Operating Activities:\n"
        result += f"- Operating Cash Inflow: {latest_report.get('SALES_SERVICES', 'N/A'):,.2f}\n"
        result += f"- Operating Cash Outflow: {latest_report.get('BUY_SERVICES', 'N/A'):,.2f}\n"
        result += f"- Net Operating Cash Flow: {latest_report.get('OPERATE_NET_CASH_FLOW', 'N/A'):,.2f}\n"
        result += f"\n### Investing Activities:\n"
        result += f"- Investment Cash Outflow: {latest_report.get('INVEST_PAY_CASH', 'N/A'):,.2f}\n"
        result += f"- Net Investing Cash Flow: {latest_report.get('INVEST_NET_CASH_FLOW', 'N/A'):,.2f}\n"
        result += f"\n### Financing Activities:\n"
        result += f"- Financing Cash Inflow: {latest_report.get('ACCEPT_INVEST_CASH', 'N/A'):,.2f}\n"
        result += f"- Net Financing Cash Flow: {latest_report.get('FINANCE_NET_CASH_FLOW', 'N/A'):,.2f}\n"
        result += f"\n### Net Change:\n"
        result += f"- Net Increase in Cash: {latest_report.get('CCE_ADD', 'N/A'):,.2f}\n"

        return result

    except Exception as e:
        logger.error(f"Error fetching cash flow statement for {ticker}: {e}")
        return f"Error fetching cash flow statement: {str(e)}"


# ============================================================================
# Insider Trading & Major Shareholder Functions
# ============================================================================

def get_a_share_major_holder_trades(
    ticker: Annotated[str, "A-share stock code"],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "How many days to look back"] = 90,
) -> str:
    """Get major shareholder trading information for A-share company.

    This is similar to insider trading data for US stocks.

    Args:
        ticker: A-share stock code
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back

    Returns:
        Formatted major holder trades report
    """
    try:
        adapter = AShareDataAdapter()
        ticker = adapter.normalize_symbol(ticker)

        # Get major holder reduction data
        df_reduction = ak.stock_em_dxjy_xx(symbol=ticker)

        if df_reduction is None or df_reduction.empty:
            return f"No major holder trading data available for {ticker}"

        # Filter by date
        curr_date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
        start_date = curr_date_obj - timedelta(days=look_back_days)

        df_reduction['变动日期'] = pd.to_datetime(df_reduction['变动日期'])
        df_reduction = df_reduction[
            (df_reduction['变动日期'] >= start_date) &
            (df_reduction['变动日期'] <= curr_date_obj)
        ]

        if df_reduction.empty:
            return f"No major holder trades in the past {look_back_days} days for {ticker}"

        # Format trades
        trades_list = []
        for _, row in df_reduction.head(20).iterrows():
            trade_item = (
                f"### {row['股东名称']} - {row['变动日期'].strftime('%Y-%m-%d')}:\n"
                f"- Change Type: {row.get('变动方向', 'N/A')}\n"
                f"- Shares Changed: {row.get('变动股本', 'N/A'):,.0f}\n"
                f"- Price Range: {row.get('成交均价', 'N/A')}\n"
                f"- Current Holdings: {row.get('持股数', 'N/A'):,.0f}\n"
                f"- Holding Ratio: {row.get('占总股本比例', 'N/A')}%\n"
            )
            trades_list.append(trade_item)

        result = (
            f"## Major Shareholder Trades for {ticker} from "
            f"{start_date.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
            + "\n".join(trades_list)
        )

        return result

    except Exception as e:
        logger.error(f"Error fetching major holder trades for {ticker}: {e}")
        return f"Error fetching major holder trades: {str(e)}"


# ============================================================================
# Social Media & Sentiment Functions
# ============================================================================

def get_a_share_eastmoney_guba_sentiment(
    ticker: Annotated[str, "A-share stock code"],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "How many days to look back"] = 7,
) -> str:
    """Get sentiment from East Money Guba (股吧) - Chinese stock forum.

    Args:
        ticker: A-share stock code
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back

    Returns:
        Formatted sentiment report from Guba
    """
    try:
        adapter = AShareDataAdapter()
        ticker = adapter.normalize_symbol(ticker)

        # Get Guba posts
        df_guba = ak.stock_guba_em(symbol=ticker)

        if df_guba is None or df_guba.empty:
            return f"No Guba sentiment data available for {ticker}"

        # Filter by date if date column exists
        curr_date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
        start_date = curr_date_obj - timedelta(days=look_back_days)

        if '发布时间' in df_guba.columns:
            df_guba['发布时间'] = pd.to_datetime(df_guba['发布时间'])
            df_guba = df_guba[
                (df_guba['发布时间'] >= start_date) &
                (df_guba['发布时间'] <= curr_date_obj)
            ]

        if df_guba.empty:
            return f"No recent Guba posts for {ticker}"

        # Analyze sentiment from posts
        posts_list = []
        total_reads = 0
        total_comments = 0

        for _, row in df_guba.head(30).iterrows():
            post_date = row['发布时间'].strftime('%Y-%m-%d') if '发布时间' in row else 'N/A'
            reads = row.get('阅读', 0)
            comments = row.get('评论', 0)

            total_reads += reads if isinstance(reads, (int, float)) else 0
            total_comments += comments if isinstance(comments, (int, float)) else 0

            post_item = (
                f"### {row['标题']} ({post_date})\n"
                f"- Reads: {reads:,} | Comments: {comments:,}\n"
            )
            posts_list.append(post_item)

        result = (
            f"## East Money Guba Sentiment for {ticker} from "
            f"{start_date.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
            f"**Overall Statistics:**\n"
            f"- Total Posts Analyzed: {len(df_guba)}\n"
            f"- Total Reads: {total_reads:,}\n"
            f"- Total Comments: {total_comments:,}\n"
            f"- Average Engagement: {(total_reads / len(df_guba) if len(df_guba) > 0 else 0):,.0f} reads per post\n\n"
            f"**Recent Hot Posts:**\n\n"
            + "\n".join(posts_list[:10])
        )

        return result

    except Exception as e:
        logger.error(f"Error fetching Guba sentiment for {ticker}: {e}")
        return f"Error fetching Guba sentiment: {str(e)}"


# ============================================================================
# Toolkit Integration Class
# ============================================================================

class AShareToolkit:
    """Toolkit providing A-share data functions for TradingAgents."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize A-share toolkit.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.adapter = AShareDataAdapter()

    # News functions
    get_a_share_news = staticmethod(get_a_share_news)
    get_a_share_announcements = staticmethod(get_a_share_announcements)

    # Financial statement functions
    get_a_share_balance_sheet = staticmethod(get_a_share_balance_sheet)
    get_a_share_income_statement = staticmethod(get_a_share_income_statement)
    get_a_share_cashflow_statement = staticmethod(get_a_share_cashflow_statement)

    # Insider/Major holder functions
    get_a_share_major_holder_trades = staticmethod(get_a_share_major_holder_trades)

    # Sentiment functions
    get_a_share_eastmoney_guba_sentiment = staticmethod(get_a_share_eastmoney_guba_sentiment)
