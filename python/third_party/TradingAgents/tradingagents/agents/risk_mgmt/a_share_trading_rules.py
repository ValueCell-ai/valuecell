"""A-share (China Stock Market) Trading Rules and Constraints.

This module defines trading rules specific to the Chinese stock market,
including T+1 trading, price limit restrictions, and lot size requirements.
"""

from typing import Dict, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AShareTradingRules:
    """Trading rules and constraints for A-share market."""

    # Trading lot sizes
    STANDARD_LOT_SIZE = 100  # 1 lot = 100 shares
    MIN_TRADE_SHARES = 100   # Minimum trade size (1 lot)

    # Price limit percentages (as decimals)
    NORMAL_PRICE_LIMIT = 0.10     # ±10% for normal stocks
    ST_PRICE_LIMIT = 0.05         # ±5% for ST stocks
    STAR_PRICE_LIMIT = 0.20       # ±20% for STAR Market (科创板)
    GEM_PRICE_LIMIT = 0.20        # ±20% for GEM (创业板)

    # Market identifiers from stock code
    SHANGHAI_PREFIX = '6'         # Shanghai Stock Exchange
    SHENZHEN_MAIN_PREFIX = '00'   # Shenzhen Main Board
    SHENZHEN_SME_PREFIX = '002'   # SME Board (中小板)
    GEM_PREFIX = '3'              # Growth Enterprise Market (创业板)
    STAR_PREFIX = '688'           # STAR Market (科创板)
    BEIJING_PREFIX = '8'          # Beijing Stock Exchange

    @staticmethod
    def is_a_share(ticker: str) -> bool:
        """Check if ticker is an A-share stock.

        Args:
            ticker: Stock code

        Returns:
            True if it's an A-share stock
        """
        return (
            ticker.isdigit()
            and len(ticker) == 6
            and ticker[0] in ['0', '3', '6', '8']
        )

    @staticmethod
    def is_st_stock(ticker: str, company_name: str = "") -> bool:
        """Check if stock is ST (Special Treatment) stock.

        Args:
            ticker: Stock code
            company_name: Company name (may contain 'ST' prefix)

        Returns:
            True if it's an ST stock
        """
        # ST stocks usually have 'ST' or '*ST' in their name
        return 'ST' in company_name.upper()

    @staticmethod
    def get_market_type(ticker: str) -> str:
        """Identify which market the stock belongs to.

        Args:
            ticker: Stock code

        Returns:
            Market type: 'SSE', 'SZSE-Main', 'SZSE-SME', 'GEM', 'STAR', 'BSE'
        """
        if ticker.startswith('6'):
            if ticker.startswith('688'):
                return 'STAR'  # STAR Market (科创板)
            return 'SSE'  # Shanghai Stock Exchange

        elif ticker.startswith('00'):
            if ticker.startswith('002'):
                return 'SZSE-SME'  # SME Board
            return 'SZSE-Main'  # Shenzhen Main Board

        elif ticker.startswith('3'):
            return 'GEM'  # Growth Enterprise Market

        elif ticker.startswith('8'):
            return 'BSE'  # Beijing Stock Exchange

        return 'Unknown'

    @classmethod
    def get_price_limit(cls, ticker: str, company_name: str = "") -> Tuple[float, float]:
        """Get price limit percentage for a stock.

        Args:
            ticker: Stock code
            company_name: Company name

        Returns:
            Tuple of (lower_limit_pct, upper_limit_pct)
        """
        # Check if ST stock
        if cls.is_st_stock(ticker, company_name):
            return (-cls.ST_PRICE_LIMIT, cls.ST_PRICE_LIMIT)

        # Check market type
        market_type = cls.get_market_type(ticker)

        if market_type in ['STAR', 'GEM']:
            # STAR and GEM have ±20% limit
            return (-cls.STAR_PRICE_LIMIT, cls.STAR_PRICE_LIMIT)
        else:
            # Normal stocks have ±10% limit
            return (-cls.NORMAL_PRICE_LIMIT, cls.NORMAL_PRICE_LIMIT)

    @classmethod
    def calculate_price_limits(
        cls,
        ticker: str,
        prev_close: float,
        company_name: str = ""
    ) -> Tuple[float, float]:
        """Calculate actual price limit values based on previous close.

        Args:
            ticker: Stock code
            prev_close: Previous closing price
            company_name: Company name

        Returns:
            Tuple of (lower_limit_price, upper_limit_price)
        """
        lower_pct, upper_pct = cls.get_price_limit(ticker, company_name)

        lower_limit = prev_close * (1 + lower_pct)
        upper_limit = prev_close * (1 + upper_pct)

        # Round to 2 decimal places
        return (round(lower_limit, 2), round(upper_limit, 2))

    @classmethod
    def validate_trade_size(cls, shares: int) -> Tuple[bool, str]:
        """Validate if trade size meets A-share requirements.

        Args:
            shares: Number of shares to trade

        Returns:
            Tuple of (is_valid, error_message)
        """
        if shares < cls.MIN_TRADE_SHARES:
            return False, f"Trade size must be at least {cls.MIN_TRADE_SHARES} shares (1 lot)"

        if shares % cls.STANDARD_LOT_SIZE != 0:
            return False, f"Trade size must be in multiples of {cls.STANDARD_LOT_SIZE} shares"

        return True, ""

    @classmethod
    def validate_trade_price(
        cls,
        ticker: str,
        trade_price: float,
        prev_close: float,
        company_name: str = ""
    ) -> Tuple[bool, str]:
        """Validate if trade price is within price limits.

        Args:
            ticker: Stock code
            trade_price: Proposed trade price
            prev_close: Previous closing price
            company_name: Company name

        Returns:
            Tuple of (is_valid, warning_message)
        """
        lower_limit, upper_limit = cls.calculate_price_limits(ticker, prev_close, company_name)

        if trade_price < lower_limit:
            return False, f"Price {trade_price} below lower limit {lower_limit} (limit down)"

        if trade_price > upper_limit:
            return False, f"Price {trade_price} above upper limit {upper_limit} (limit up)"

        # Warning if close to limits
        if abs(trade_price - upper_limit) / prev_close < 0.01:
            return True, "Warning: Price approaching upper limit (limit up)"

        if abs(trade_price - lower_limit) / prev_close < 0.01:
            return True, "Warning: Price approaching lower limit (limit down)"

        return True, ""

    @staticmethod
    def check_t_plus_1_restriction(
        ticker: str,
        buy_date: datetime,
        sell_date: datetime
    ) -> Tuple[bool, str]:
        """Check T+1 trading restriction.

        In A-share market, stocks bought on day T can only be sold on day T+1 or later.

        Args:
            ticker: Stock code
            buy_date: Date when stock was bought
            sell_date: Proposed sell date

        Returns:
            Tuple of (is_allowed, message)
        """
        days_held = (sell_date - buy_date).days

        if days_held < 1:
            return False, (
                "T+1 Restriction: Stocks bought today cannot be sold until next trading day. "
                f"Bought on {buy_date.strftime('%Y-%m-%d')}, "
                f"can sell from {(buy_date + timedelta(days=1)).strftime('%Y-%m-%d')}"
            )

        return True, ""

    @classmethod
    def get_trading_hours(cls, market_type: str) -> Dict[str, str]:
        """Get trading hours for different market sessions.

        Args:
            market_type: Market type ('SSE', 'SZSE', etc.)

        Returns:
            Dictionary of trading sessions and their hours
        """
        # All Chinese markets have the same trading hours
        return {
            "morning_session": "09:30-11:30",
            "afternoon_session": "13:00-15:00",
            "call_auction_open": "09:15-09:25",  # Opening call auction
            "call_auction_close": "14:57-15:00",  # Closing call auction (for STAR/GEM)
        }

    @classmethod
    def generate_risk_assessment(
        cls,
        ticker: str,
        trade_action: str,
        trade_price: float,
        trade_shares: int,
        prev_close: float,
        company_name: str = "",
        buy_date: Optional[datetime] = None,
    ) -> Dict[str, any]:
        """Generate comprehensive risk assessment for A-share trade.

        Args:
            ticker: Stock code
            trade_action: 'BUY' or 'SELL'
            trade_price: Proposed trade price
            trade_shares: Number of shares
            prev_close: Previous closing price
            company_name: Company name
            buy_date: Original buy date (for SELL orders)

        Returns:
            Risk assessment dictionary
        """
        assessment = {
            "ticker": ticker,
            "market_type": cls.get_market_type(ticker),
            "is_st_stock": cls.is_st_stock(ticker, company_name),
            "trade_action": trade_action,
            "issues": [],
            "warnings": [],
            "passed": True,
        }

        # Check trade size
        size_valid, size_msg = cls.validate_trade_size(trade_shares)
        if not size_valid:
            assessment["issues"].append(size_msg)
            assessment["passed"] = False

        # Check price limits
        price_valid, price_msg = cls.validate_trade_price(
            ticker, trade_price, prev_close, company_name
        )
        if not price_valid:
            assessment["issues"].append(price_msg)
            assessment["passed"] = False
        elif price_msg:  # Warning message
            assessment["warnings"].append(price_msg)

        # Check T+1 restriction for SELL orders
        if trade_action == "SELL" and buy_date:
            t1_valid, t1_msg = cls.check_t_plus_1_restriction(
                ticker, buy_date, datetime.now()
            )
            if not t1_valid:
                assessment["issues"].append(t1_msg)
                assessment["passed"] = False

        # Add price limit info
        lower_limit, upper_limit = cls.calculate_price_limits(ticker, prev_close, company_name)
        assessment["price_limits"] = {
            "lower": lower_limit,
            "upper": upper_limit,
            "percentage": cls.get_price_limit(ticker, company_name),
        }

        return assessment


# Import for datetime
from datetime import timedelta
