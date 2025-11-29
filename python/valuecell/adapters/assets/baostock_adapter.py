import threading
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from time import time
from typing import Any, Callable, List, Optional, Tuple

import pandas as pd
from func_timeout import FunctionTimedOut, func_timeout
from loguru import logger

from .base import AdapterCapability, BaseDataAdapter
from .types import (
    Asset,
    AssetPrice,
    AssetSearchQuery,
    AssetSearchResult,
    AssetType,
    DataSource,
    Exchange,
    Interval,
    LocalizedName,
    MarketInfo,
    MarketStatus,
)

try:
    import baostock as bs
except ImportError:
    bs = None

# Global lock for BaoStock API calls (baostock uses global session state)
_baostock_lock = threading.Lock()


# BaoStock type mapping: 1=Stock, 2=Index, 3=Other, 4=Convertible, 5=ETF
BAOSTOCK_TYPE_STOCK = "1"
BAOSTOCK_TYPE_INDEX = "2"
BAOSTOCK_TYPE_OTHER = "3"
BAOSTOCK_TYPE_CONVERTIBLE = "4"
BAOSTOCK_TYPE_ETF = "5"

# BaoStock code length for symbols like "sh.600000" or "sz.000001"
BAOSTOCK_CODE_LENGTH = 9  # "sh.600000" is 9 characters


class BaoStockAdapter(BaseDataAdapter):
    """Baostock data adapter implementation, only supports SSE and SZSE."""

    def __init__(self, **kwargs):
        """Initialize BaoStock adapter.

        Args:
            **kwargs: Additional configuration parameters
        """
        super().__init__(DataSource.BAOSTOCK, **kwargs)

        if bs is None:
            raise ImportError("baostock library is not installed.")

    def _initialize(self) -> None:
        """Initialize BaoStock adapter configuration."""

        self.timeout = self.config.get("timeout", 10)

        self.exchange_mapping = {
            Exchange.SSE: "sh",
            Exchange.SZSE: "sz",
        }

        self.interval_mapping = {
            f"5{Interval.MINUTE.value}": "5",
            f"15{Interval.MINUTE.value}": "15",
            f"30{Interval.MINUTE.value}": "30",
            f"60{Interval.MINUTE.value}": "60",
            f"1{Interval.DAY.value}": "d",
            f"1{Interval.WEEK.value}": "w",
            f"1{Interval.MONTH.value}": "m",
        }

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker is supported by BaoStock.

        Args:
            ticker: Ticker in internal format (e.g., "SSE:600000", "SZSE:000001")

        Returns:
            True if ticker is supported by BaoStock
        """
        if ":" not in ticker:
            return False

        result = self._get_exchange_and_ticker_code(ticker)
        if result is None:
            return False

        exchange, baostock_code = result

        # Validate exchange is supported
        if exchange not in self.get_supported_exchanges():
            return False

        # Validate baostock code format (e.g., "sh.600000" should be 9 chars)
        if len(baostock_code) != BAOSTOCK_CODE_LENGTH:
            return False

        return True

    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time price data for an asset from BaoStock.

        Note: BaoStock doesn't have true real-time API. This method fetches
        the most recent daily price data as "current" price (similar to yfinance).

        Args:
            ticker: Asset ticker in internal format (e.g., "SSE:600000")

        Returns:
            AssetPrice object with most recent price or None if not available
        """
        result = self._get_exchange_and_ticker_code(ticker)
        if result is None:
            return None
        _, baostock_code = result

        is_index = self._is_index_code(baostock_code)

        # Fetch most recent daily data (last 5 trading days to ensure we get data)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)

        # Use appropriate fields based on asset type
        fields = "date,code,open,high,low,close,volume,preclose,pctChg"

        try:
            rs = self._baostock_api_call_wrapper(
                lambda: bs.query_history_k_data_plus(
                    code=baostock_code,
                    fields=fields,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    frequency="d",
                    adjustflag="2" if not is_index else "3",
                )
            )
            if rs is None or rs.error_code != "0":
                logger.warning(
                    "BaoStock real-time price query failed for {ticker}: {msg}",
                    ticker=ticker,
                    msg=rs.error_msg if rs else "No response",
                )
                return None

            data_frame = self._get_data_safe(rs)
            if data_frame.empty:
                logger.debug("No recent price data for {ticker}", ticker=ticker)
                return None

            # Get the most recent row
            latest_row = data_frame.iloc[-1]

            close_price = self._safe_decimal(latest_row["close"])
            if close_price is None:
                return None

            preclose_price = self._safe_decimal(latest_row.get("preclose"))
            change = None
            if close_price is not None and preclose_price is not None:
                change = close_price - preclose_price

            change_percent = self._safe_decimal(latest_row.get("pctChg"))

            return AssetPrice(
                ticker=ticker,
                price=close_price,
                currency="CNY",
                timestamp=datetime.strptime(latest_row["date"], "%Y-%m-%d"),
                open_price=self._safe_decimal(latest_row["open"]),
                high_price=self._safe_decimal(latest_row["high"]),
                low_price=self._safe_decimal(latest_row["low"]),
                close_price=close_price,
                volume=self._safe_decimal(latest_row["volume"]),
                change=change,
                change_percent=change_percent,
                source=self.source,
            )

        except Exception as e:
            logger.error(
                "Error fetching real-time price for {ticker}: {err}",
                ticker=ticker,
                err=e,
            )
            return None

    def get_historical_prices(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[AssetPrice]:
        """Get historical price data for an asset from BaoStock.

        Args:
            ticker: Asset ticker in internal format
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval using format like "5m", "15m", "30m", "60m", "1d", "1w", "1mo"
                     Supported intervals:
                     - Minute: "5m", "15m", "30m", "60m" (intraday data)
                     - Daily: "1d" (default)
                     - Weekly: "1w"
                     - Monthly: "1mo"
        Returns:
            List of historical price data
        """
        query_interval = self.interval_mapping.get(interval)
        if query_interval is None:
            logger.warning(
                "Unsupported interval: {interval} for BaoStock", interval=interval
            )
            return []

        if query_interval in ["5", "15", "30", "60"]:
            return self._get_intraday_prices(
                ticker, start_date, end_date, period=query_interval
            )
        else:
            return self._get_historical_k_data(
                ticker, start_date, end_date, interval=query_interval
            )

    def search_assets(self, query: AssetSearchQuery) -> List[AssetSearchResult]:
        """Search for assets matching the query criteria from BaoStock.

        BaoStock supports searching by:
        - code: Stock code in BaoStock format (e.g., "sh.600000")
        - code_name: Stock name, supports fuzzy search (e.g., "浦发银行")

        Args:
            query: Search query parameters

        Returns:
            List of matching AssetSearchResult objects
        """
        results: List[AssetSearchResult] = []
        search_term = query.query.strip()
        logger.debug("Searching assets on BaoStock with query: {q}", q=search_term)

        try:
            # Try searching by code first, then by name
            # BaoStock expects code in format "sh.600000" or just name for fuzzy search
            baostock_code = self._normalize_search_query(search_term)

            if baostock_code:
                rs = self._baostock_api_call_wrapper(
                    lambda: bs.query_stock_basic(code=baostock_code)
                )
            else:
                # Search by name (fuzzy search)
                rs = self._baostock_api_call_wrapper(
                    lambda: bs.query_stock_basic(code_name=search_term)
                )

            if rs.error_code != "0":
                logger.warning("BaoStock asset search failed: {msg}", msg=rs.error_msg)
                return results

            data_frame = self._get_data_safe(rs)
            for _, row in data_frame.iterrows():
                search_result = self._create_search_result_from_row(row)
                if search_result is not None:
                    results.append(search_result)

        except Exception as e:
            logger.error("Error during BaoStock asset search: {err}", err=e)

        logger.debug(
            "Found {count} assets matching query: {q}",
            count=len(results),
            q=search_term,
        )
        return results[: query.limit]

    def _normalize_search_query(self, search_term: str) -> Optional[str]:
        """Normalize search term to BaoStock code format if it looks like a stock code.

        Args:
            search_term: User input search term

        Returns:
            BaoStock format code (e.g., "sh.600000") or None if not a code
        """
        # Already in BaoStock format
        if "." in search_term and len(search_term) == BAOSTOCK_CODE_LENGTH:
            return search_term.lower()

        # Check if it's an internal ticker format (SSE:600000)
        if ":" in search_term:
            result = self._get_exchange_and_ticker_code(search_term)
            if result is not None:
                _, baostock_code = result
                return baostock_code

        # Check if it's just a 6-digit code
        if search_term.isdigit() and len(search_term) == 6:
            # Try to determine exchange from code prefix
            if search_term.startswith("6") or search_term.startswith("000"):
                return f"sh.{search_term}"
            elif search_term.startswith("0") or search_term.startswith("3"):
                return f"sz.{search_term}"

        # Not a code, will search by name
        return None

    def _create_search_result_from_row(
        self, row: pd.Series
    ) -> Optional[AssetSearchResult]:
        """Create AssetSearchResult from BaoStock query_stock_basic row.

        Args:
            row: Pandas Series with stock basic data

        Returns:
            AssetSearchResult or None if parsing fails
        """
        try:
            code = row["code"]
            code_name = row.get("code_name", "")
            exchange_code = code[:2]

            if exchange_code == "sh":
                exchange = Exchange.SSE
            elif exchange_code == "sz":
                exchange = Exchange.SZSE
            else:
                logger.debug(
                    "Unknown exchange code: {ex} for asset {code}",
                    ex=exchange_code,
                    code=code,
                )
                return None

            # Map BaoStock type to AssetType
            type_code = str(row.get("type", "1"))
            if type_code == BAOSTOCK_TYPE_STOCK:
                asset_type = AssetType.STOCK
            elif type_code == BAOSTOCK_TYPE_INDEX:
                asset_type = AssetType.INDEX
            elif type_code == BAOSTOCK_TYPE_ETF:
                asset_type = AssetType.ETF
            else:
                logger.debug(
                    "Unsupported asset type: {t} for asset {code}",
                    t=type_code,
                    code=code,
                )
                return None

            # Extract symbol from BaoStock code (remove "sh." or "sz." prefix)
            symbol = code[3:]
            ticker = f"{exchange.value}:{symbol}"

            return AssetSearchResult(
                ticker=ticker,
                asset_type=asset_type,
                names={
                    "zh-Hans": code_name,
                    "zh-CN": code_name,
                },
                exchange=exchange.value,
                country="CN",
                currency="CNY",
                market_status=MarketStatus.UNKNOWN,
            )
        except (KeyError, ValueError) as e:
            logger.warning("Failed to parse search result row: {err}", err=e)
            return None

    def convert_to_internal_ticker(
        self, source_ticker: str, default_exchange: Optional[str] = None
    ) -> str:
        """Convert BaoStock ticker code to internal ticker format.

        Args:
            source_ticker: BaoStock ticker code (e.g., "sh.600000")
            default_exchange: Default exchange if cannot be determined from ticker
        Returns:
            Ticker in internal format (e.g., "SSE:600000")
        """
        try:
            if "." not in source_ticker:
                logger.warning(
                    "Invalid BaoStock ticker format: {ticker}", ticker=source_ticker
                )
                return source_ticker  # Return as is if format is invalid

            exchange_code, symbol = source_ticker.split(".", 1)
            if exchange_code == "sh":
                exchange = Exchange.SSE
            elif exchange_code == "sz":
                exchange = Exchange.SZSE
            else:
                logger.warning(
                    "Unknown exchange code: {ex} for ticker {ticker}",
                    ex=exchange_code,
                    ticker=source_ticker,
                )
                return source_ticker  # Return as is if unknown exchange

            return f"{exchange.value}:{symbol}"
        except Exception as e:
            logger.error(
                "Error converting BaoStock ticker {ticker} to internal format: {err}",
                ticker=source_ticker,
                err=e,
            )
            return source_ticker  # Return as is on error

    def convert_to_source_ticker(self, internal_ticker: str) -> str:
        """Convert internal ticker to BaoStock ticker code.

        Args:
            internal_ticker: Internal ticker symbol

        Returns:
            Corresponding BaoStock ticker code
        """
        result = self._get_exchange_and_ticker_code(internal_ticker)
        if result is None:
            return internal_ticker  # Return as is if conversion fails
        _, ticker_code = result
        return ticker_code

    def get_capabilities(self) -> List[AdapterCapability]:
        """Get detailed capabilities of BaoStock adapter.

        BaoStock supports:
        - Stocks (SSE, SZSE)
        - Indices (SSE, SZSE) - note: no minute data for indices
        - ETFs (SSE, SZSE)

        Returns:
            List of capabilities describing supported asset types and exchanges
        """
        return [
            AdapterCapability(
                asset_type=AssetType.STOCK,
                exchanges={Exchange.SSE, Exchange.SZSE},
            ),
            AdapterCapability(
                asset_type=AssetType.INDEX,
                exchanges={Exchange.SSE, Exchange.SZSE},
            ),
            AdapterCapability(
                asset_type=AssetType.ETF,
                exchanges={Exchange.SSE, Exchange.SZSE},
            ),
        ]

    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Fetch asset information for a given ticker from BaoStock.

        Args:
            ticker: Internal ticker symbol (e.g., "SSE:600000")

        Returns:
            Asset information or None if not found
        """
        result = self._get_exchange_and_ticker_code(ticker)
        if result is None:
            return None
        exchange, baostock_code = result

        try:
            rs = self._baostock_api_call_wrapper(
                lambda: bs.query_stock_basic(code=baostock_code)
            )
            if rs.error_code != "0":
                logger.warning(
                    "Failed to fetch asset info for ticker {ticker}: {msg}",
                    ticker=ticker,
                    msg=rs.error_msg,
                )
                return None

            data = self._get_data_safe(rs)
            if data.empty:
                logger.warning("No asset info found for ticker {ticker}", ticker=ticker)
                return None

            return self._create_asset_from_info(
                ticker=ticker, exchange=exchange, data=data
            )
        except Exception as e:
            logger.error(
                "Error fetching asset info for ticker {ticker}: {err}",
                ticker=ticker,
                err=e,
            )
            return None

    def _get_intraday_prices(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        period: str = "60",
    ) -> List[AssetPrice]:
        """Query intraday data from BaoStock.

        Note: BaoStock does NOT support minute data for indices (only stocks).

        Args:
            ticker: Internal ticker format (e.g., "SSE:600000")
            start_date: Start date for intraday data
            end_date: End date for intraday data
            period: Data interval code for BaoStock ("5", "15", "30", "60")

        Returns:
            List of AssetPrice objects
        """
        if period not in ["5", "15", "30", "60"]:
            logger.warning(
                "Unsupported intraday period: {period} for BaoStock", period=period
            )
            return []

        prices: List[AssetPrice] = []

        # Convert internal ticker to BaoStock format
        result = self._get_exchange_and_ticker_code(ticker)
        if result is None:
            logger.warning(
                "Failed to convert ticker {ticker} to BaoStock format", ticker=ticker
            )
            return prices

        _, baostock_code = result

        # Check if this is an index - BaoStock doesn't support minute data for indices
        if self._is_index_code(baostock_code):
            logger.info(
                "BaoStock does not support minute data for indices: {ticker}",
                ticker=ticker,
            )
            return prices

        try:
            rs = self._baostock_api_call_wrapper(
                lambda: bs.query_history_k_data_plus(
                    code=baostock_code,
                    fields="date,time,code,open,high,low,close,volume,amount",
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    frequency=period,
                    adjustflag="2",  # pre-adjusted
                )
            )
            if rs is None or rs.error_code != "0":
                logger.warning(
                    "BaoStock intraday data query failed for {ticker}: {msg}",
                    ticker=ticker,
                    msg=rs.error_msg if rs else "No response",
                )
                return prices

            data_frame = self._get_data_safe(rs)
            for _, row in data_frame.iterrows():
                price = self._parse_intraday_row(ticker, row)
                if price is not None:
                    prices.append(price)

        except Exception as e:
            logger.error(
                "Error querying intraday data for {ticker}: {err}", ticker=ticker, err=e
            )

        return prices

    def _parse_intraday_row(self, ticker: str, row: pd.Series) -> Optional[AssetPrice]:
        """Parse a single row of intraday data into AssetPrice.

        Args:
            ticker: Internal ticker format
            row: Pandas Series with intraday data

        Returns:
            AssetPrice object or None if parsing fails
        """
        try:
            time_str = str(row["time"])
            # BaoStock time format: YYYYMMDDHHMMSSsss (remove milliseconds)
            timestamp = datetime.strptime(time_str[:-3], "%Y%m%d%H%M%S")

            close_price = self._safe_decimal(row["close"])
            if close_price is None:
                return None

            return AssetPrice(
                ticker=ticker,
                price=close_price,
                currency="CNY",
                timestamp=timestamp,
                open_price=self._safe_decimal(row["open"]),
                high_price=self._safe_decimal(row["high"]),
                low_price=self._safe_decimal(row["low"]),
                close_price=close_price,
                volume=self._safe_decimal(row["volume"]),
                market_cap=self._safe_decimal(
                    row["amount"]
                ),  # amount is turnover, not market cap
                source=self.source,
            )
        except (ValueError, KeyError) as e:
            logger.warning("Failed to parse intraday row: {err}", err=e)
            return None

    def _is_index_code(self, baostock_code: str) -> bool:
        """Check if the BaoStock code is an index.

        Index codes typically start with:
        - sh.000xxx (Shanghai indices)
        - sz.399xxx (Shenzhen indices)

        Args:
            baostock_code: BaoStock format code (e.g., "sh.000001")

        Returns:
            True if it's an index code
        """
        if len(baostock_code) != BAOSTOCK_CODE_LENGTH:
            return False

        symbol = baostock_code[3:]  # Remove "sh." or "sz." prefix
        if baostock_code.startswith("sh."):
            # Shanghai indices start with 000
            return symbol.startswith("000")
        elif baostock_code.startswith("sz."):
            # Shenzhen indices start with 399
            return symbol.startswith("399")
        return False

    def _safe_decimal(self, value: Any) -> Optional[Decimal]:
        """Safely convert a value to Decimal.

        Args:
            value: Value to convert

        Returns:
            Decimal value or None if conversion fails
        """
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    def _get_data_safe(self, rs: Any) -> pd.DataFrame:
        """Safely get DataFrame from BaoStock response, avoiding pandas 2.0 issues.

        BaoStock's get_data() internally uses DataFrame.append() which is removed
        in pandas 2.0+. This method creates DataFrame directly from raw data.

        Args:
            rs: BaoStock ResultData object

        Returns:
            DataFrame with results or empty DataFrame if no data
        """
        try:
            # First try the standard method (works if baostock is fixed)
            return rs.get_data()
        except AttributeError as e:
            if "append" in str(e):
                # pandas 2.0 compatibility workaround:
                # Create DataFrame directly from rs.data and rs.fields
                if hasattr(rs, "data") and hasattr(rs, "fields"):
                    if rs.data:
                        return pd.DataFrame(rs.data, columns=rs.fields)
                    return pd.DataFrame(columns=rs.fields if rs.fields else [])
            raise

    def _get_historical_k_data(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "d",
    ) -> List[AssetPrice]:
        """Query historical K-line data from BaoStock.

        Handles both stocks and indices with appropriate fields for each type.

        Args:
            ticker: Internal ticker format (e.g., "SSE:600000")
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval code ("d", "w", "m")

        Returns:
            List of AssetPrice objects
        """
        prices: List[AssetPrice] = []
        result = self._get_exchange_and_ticker_code(ticker)
        if result is None:
            return prices
        _, baostock_code = result

        is_index = self._is_index_code(baostock_code)

        # Different fields for stocks vs indices
        # For stocks (daily): date,code,open,high,low,close,volume,preclose,pctChg
        # For indices: date,code,open,high,low,close,volume,amount,preclose,pctChg
        # For weekly/monthly: date,code,open,high,low,close,volume,amount,pctChg (no preclose)
        if interval == "d":
            fields = "date,code,open,high,low,close,volume,preclose,pctChg"
        else:
            # Weekly and monthly don't have preclose field
            fields = "date,code,open,high,low,close,volume,amount,pctChg"

        try:
            rs = self._baostock_api_call_wrapper(
                lambda: bs.query_history_k_data_plus(
                    code=baostock_code,
                    fields=fields,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    frequency=interval,
                    adjustflag="2"
                    if not is_index
                    else "3",  # indices don't need adjustment
                )
            )
            if rs is None or rs.error_code != "0":
                logger.warning(
                    "BaoStock historical data query failed for {ticker}: {msg}",
                    ticker=ticker,
                    msg=rs.error_msg if rs else "No response",
                )
                return prices

            data_frame = self._get_data_safe(rs)
            for _, row in data_frame.iterrows():
                price = self._parse_historical_row(ticker, row, interval)
                if price is not None:
                    prices.append(price)

        except Exception as e:
            logger.error(
                "Error querying historical data for {ticker}: {err}",
                ticker=ticker,
                err=e,
            )

        return prices

    def _parse_historical_row(
        self, ticker: str, row: pd.Series, interval: str
    ) -> Optional[AssetPrice]:
        """Parse a single row of historical data into AssetPrice.

        Args:
            ticker: Internal ticker format
            row: Pandas Series with historical data
            interval: Data interval ("d", "w", "m")

        Returns:
            AssetPrice object or None if parsing fails
        """
        try:
            close_price = self._safe_decimal(row["close"])
            if close_price is None:
                return None

            # Calculate change if preclose is available (daily data only)
            change = None
            preclose_price = self._safe_decimal(row.get("preclose"))
            if close_price is not None and preclose_price is not None:
                change = close_price - preclose_price

            change_percent = self._safe_decimal(row.get("pctChg"))

            return AssetPrice(
                ticker=ticker,
                price=close_price,
                currency="CNY",
                timestamp=datetime.strptime(row["date"], "%Y-%m-%d"),
                open_price=self._safe_decimal(row["open"]),
                high_price=self._safe_decimal(row["high"]),
                low_price=self._safe_decimal(row["low"]),
                close_price=close_price,
                volume=self._safe_decimal(row["volume"]),
                change=change,
                change_percent=change_percent,
                source=self.source,
            )
        except (ValueError, KeyError) as e:
            logger.warning("Failed to parse historical row: {err}", err=e)
            return None

    def _create_asset_from_info(
        self, ticker: str, exchange: Exchange, data: pd.DataFrame
    ) -> Optional[Asset]:
        """Create Asset object from BaoStock query_stock_basic data.

        Args:
            ticker: Internal ticker symbol (e.g., "SSE:600000")
            exchange: Exchange enum
            data: DataFrame from query_stock_basic

        Returns:
            Asset object or None if creation fails
        """
        try:
            asset_data = data.iloc[0]

            country = "CN"
            currency = "CNY"
            timezone = "Asia/Shanghai"
            name = asset_data.get("code_name", ticker)

            # Map BaoStock type to AssetType
            type_code = str(asset_data.get("type", "1"))
            if type_code == BAOSTOCK_TYPE_STOCK:
                asset_type = AssetType.STOCK
            elif type_code == BAOSTOCK_TYPE_INDEX:
                asset_type = AssetType.INDEX
            elif type_code == BAOSTOCK_TYPE_ETF:
                asset_type = AssetType.ETF
            else:
                asset_type = AssetType.STOCK  # Default to STOCK

            localized_names = LocalizedName()
            if name and name != ticker:
                localized_names.set_name("zh-Hans", name)
                localized_names.set_name("zh-CN", name)

            market_info = MarketInfo(
                exchange=exchange.value,
                country=country,
                currency=currency,
                timezone=timezone,
                market_status=MarketStatus.UNKNOWN,
            )

            asset = Asset(
                ticker=ticker,
                asset_type=asset_type,
                names=localized_names,
                market_info=market_info,
            )

            asset.set_source_ticker(self.source, self.convert_to_source_ticker(ticker))

            # Save asset metadata to database for future lookups
            self._save_asset_to_database(
                ticker=ticker,
                name=name,
                asset_type=asset_type,
                currency=currency,
                country=country,
                timezone=timezone,
            )

            return asset

        except Exception as e:
            logger.error(
                "Error creating Asset object for ticker {ticker}: {err}",
                ticker=ticker,
                err=e,
            )
            return None

    def _save_asset_to_database(
        self,
        ticker: str,
        name: str,
        asset_type: AssetType,
        currency: str,
        country: str,
        timezone: str,
    ) -> None:
        """Save asset metadata to database.

        Args:
            ticker: Internal ticker symbol
            name: Asset name
            asset_type: Asset type enum
            currency: Currency code
            country: Country code
            timezone: Timezone string
        """
        try:
            from ...server.db.repositories.asset_repository import (
                get_asset_repository,
            )

            asset_repo = get_asset_repository()
            asset_repo.upsert_asset(
                symbol=ticker,
                name=name,
                asset_type=asset_type,
                asset_metadata={
                    "currency": currency,
                    "country": country,
                    "timezone": timezone,
                    "source": self.source.value,
                },
            )
            logger.debug("Saved asset info from BaoStock for {ticker}", ticker=ticker)
        except Exception as e:
            # Don't fail the info fetch if database save fails
            logger.warning(
                "Failed to save asset info for {ticker}: {err}",
                ticker=ticker,
                err=e,
            )

    def _get_exchange_and_ticker_code(
        self, ticker: str
    ) -> Optional[Tuple[Exchange, str]]:
        """Convert internal ticker to BaoStock ticker code.

        Args:
            ticker: Internal ticker symbol

        Returns:
            Exchange and corresponding BaoStock ticker code
            None if conversion fails
        """
        try:
            # Parse ticker to get exchange and symbol
            if ":" not in ticker:
                logger.warning(
                    "Invalid ticker format: {ticker}, expected EXCHANGE:SYMBOL",
                    ticker=ticker,
                )
                return None

            exchange_str, symbol = ticker.split(":", 1)
            # Convert exchange string to Exchange enum
            try:
                exchange = Exchange(exchange_str)
            except ValueError:
                logger.warning(
                    "Unknown exchange: {ex} for ticker {ticker}",
                    ex=exchange_str,
                    ticker=ticker,
                )
                return None

            if exchange not in self.get_supported_exchanges():
                logger.warning(
                    "Exchange {ex} not supported by BaoStock for ticker {ticker}",
                    ex=exchange_str,
                    ticker=ticker,
                )
                return None

            return (exchange, f"{self.exchange_mapping[exchange]}.{symbol}")

        except Exception as e:
            logger.error(
                "Error converting ticker {ticker} to BaoStock code: {err}",
                ticker=ticker,
                err=e,
            )
            return None

    def _baostock_login(self):
        """Login to BaoStock service."""
        self._logging_status = bs.login()
        if self._logging_status.error_code != "0":
            raise ConnectionError(
                f"BaoStock login failed: {self._logging_status.error_msg}"
            )
        # record last successful login time (seconds since epoch)
        try:
            self._last_login_time = time()
        except Exception:
            # fallback: don't block if time cannot be recorded
            self._last_login_time = None

    def _baostock_api_call_wrapper(self, api_call: Callable[..., Any]) -> Any:
        """Wrapper for BaoStock API calls to handle login, session TTL and retries.

        - Uses a global lock to prevent concurrent BaoStock API calls (baostock
          uses global session state that isn't thread-safe).
        - Ensures a valid login exists (with optional TTL `session_ttl` in config).
        - Uses `self.timeout` (or config `timeout`) for `func_timeout`.
        - Retries once after re-login when a timeout occurs or when the BaoStock
          response object has a non-'0' `error_code`.

        Args:
            api_call: callable BaoStock API function

        Returns:
            The raw result returned by the BaoStock API call.

        Raises:
            Exception: Last exception encountered if retries exhausted.
        """
        with _baostock_lock:
            session_ttl = self.config.get("session_ttl", 300)
            now = time()

            # Ensure login and check TTL
            if (
                not hasattr(self, "_logging_status")
                or getattr(self._logging_status, "error_code", "1") != "0"
                or not hasattr(self, "_last_login_time")
                or (
                    self._last_login_time is not None
                    and now - self._last_login_time > session_ttl
                )
            ):
                self._baostock_login()

            timeout = getattr(self, "timeout", self.config.get("timeout", 10))

            attempts = 0
            last_exc: Optional[BaseException] = None

            while attempts < 2:
                try:
                    result = func_timeout(timeout, api_call)

                    # If the result is a BaoStock response object, check its error_code
                    if (
                        hasattr(result, "error_code")
                        and getattr(result, "error_code") != "0"
                    ):
                        logger.warning(
                            "BaoStock API returned error_code={code}, msg={msg} - re-login and retry",
                            code=getattr(result, "error_code"),
                            msg=getattr(result, "error_msg", None),
                        )
                        self._baostock_login()
                        attempts += 1
                        continue

                    return result

                except FunctionTimedOut as exc:
                    logger.warning(
                        "BaoStock API call timed out after {timeout}s, retrying",
                        timeout=timeout,
                    )
                    last_exc = exc
                    # try to re-login then retry
                    try:
                        self._baostock_login()
                    except Exception as login_exc:
                        logger.error(
                            "Re-login failed after timeout: {err}", err=login_exc
                        )
                        raise
                    attempts += 1
                    continue

                except Exception as exc:
                    logger.error("Error during BaoStock API call: {err}", err=exc)
                    raise

            # Exhausted retries
            logger.error(
                "BaoStock API call failed after {attempts} attempts", attempts=attempts
            )
            if last_exc:
                raise last_exc
            raise RuntimeError("BaoStock API call failed after retries")
