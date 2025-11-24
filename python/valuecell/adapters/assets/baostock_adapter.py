import logging
from datetime import datetime
from time import time
from decimal import Decimal
from typing import List, Optional, Tuple, Callable, Any
from func_timeout import func_timeout, FunctionTimedOut

import pandas as pd

try:
    import baostock as bs
except ImportError:
    bs = None

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

logger = logging.getLogger(__name__)


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
            ticker: Ticker in internal format, suppose the ticker has been validated before by the caller.
            (e.g., "NASDAQ:AAPL", "HKEX:00700", "CRYPTO:BTC")
        Returns:
            True if ticker is supported
        """
        if ":" not in ticker:
            return False

        result = self._get_exchange_and_ticker_code(ticker)
        if result is None:
            return False
        
        exchange, ticker_code = result

        # Validate exchange
        if exchange not in [
            exchange.value for exchange in self.get_supported_exchanges()
        ]:
            return False

        if len(ticker_code) != bs.cons.STOCK_CODE_LENGTH:
            return False

        return True

    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time price data for an asset from BaoStock.

        Args:
            ticker: Asset ticker in internal format
        Returns:
            AssetPrice object or None if not found
        """
        # BaoStock does not provide real-time price data via its free API
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
            logger.warning(f"Unsupported interval: {interval} for BaoStock")
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
        """Search for assets matching the query criteria from BaoStock."""
        results: List[AssetSearchResult] = []
        logger.error(f"Searching assets on BaoStock with query: {query.query}")
        try:
            rs = self._baostock_api_call_wrapper(
                lambda: bs.query_stock_basic(code=query.query)
            )
            if rs.error_code != "0":
                logger.warning(f"BaoStock asset search failed: {rs.error_msg}")
                return results

            data_frame = rs.get_data()
            for _, row in data_frame.iterrows():
                code = row["code"]
                code_name = row["code_name"]
                exchange_code = code[:2]
                if exchange_code == "sh":
                    exchange = Exchange.SSE
                elif exchange_code == "sz":
                    exchange = Exchange.SZSE
                else:
                    logger.warning(
                        f"Unknown exchange code: {exchange_code} for asset {code}"
                    )
                    continue
                type = row["type"]
                if str(type) == "1":
                    asset_type = AssetType.STOCK
                elif str(type) == "2":
                    asset_type = AssetType.INDEX
                else:
                    logger.warning(
                        f"Unsupported asset type: {type} for asset {code}"
                    )
                    continue

                ticker = f"{exchange.value}:{code[2:]}"
                result = AssetSearchResult(
                    ticker=ticker,
                    asset_type=asset_type,
                    names={
                        "zh-Hans": code_name,
                        "zh-CN": code_name,
                    },
                    exchange=exchange,
                    country="CN",
                    currency="CNY",
                    market_status=MarketStatus.UNKNOWN,
                )
                results.append(result)
        except Exception as e:
            logger.error(f"Error during BaoStock asset search: {e}")

        logger.error(f"Found {len(results)} assets matching query: {query.query}")
        return results

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
                logger.warning(f"Invalid BaoStock ticker format: {source_ticker}")
                return source_ticker  # Return as is if format is invalid

            exchange_code, symbol = source_ticker.split(".", 1)
            if exchange_code == "sh":
                exchange = Exchange.SSE
            elif exchange_code == "sz":
                exchange = Exchange.SZSE
            else:
                logger.warning(
                    f"Unknown exchange code: {exchange_code} for ticker {source_ticker}"
                )
                return source_ticker  # Return as is if unknown exchange

            return f"{exchange.value}:{symbol}"
        except Exception as e:
            logger.error(
                f"Error converting BaoStock ticker {source_ticker} to internal format: {e}"
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

        BaoStock only supports SSE and SZSE.

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
        ]

    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Fetch asset information for a given ticker from BaoStock.

        Args:
            ticker: Internal ticker symbol
        Returns:
            Asset information or None if not found
        """

        result = self._get_exchange_and_ticker_code(ticker)
        if result is None:
            return None
        exchange, ticker_code = result

        try:
            rs = self._baostock_api_call_wrapper(
                lambda: bs.query_stock_basic(code=ticker_code)
            )
            if rs.error_code != "0" or rs.next() is False:
                logger.warning(
                    f"Failed to fetch asset info for ticker {ticker}: {rs.error_msg}"
                )
                return None

            data = rs.get_data()
            if data.empty:
                logger.warning(f"No asset info found for ticker {ticker}")
                return None

            return self._create_asset_from_info(
                ticker=ticker, exchange=exchange, data=data
            )
        except Exception as e:
            logger.error(f"Error fetching asset info for ticker {ticker}: {e}")
            return None

    def _get_intraday_prices(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        period: str = "60",
    ) -> List[AssetPrice]:
        """Query intraday data from BaoStock.

        Args:
            ticker: BaoStock ticker code
            start_date: Start date for intraday data
            end_date: End date for intraday data if None, fetch until recent trading day
            period: Data interval code for BaoStock intraday data
        Returns:
            List of AssetPrice objects
        """
        if period not in ["5", "15", "30", "60"]:
            logger.warning(f"Unsupported intraday period: {period} for BaoStock")
            return []
        prices: List[AssetPrice] = []

        try:
            rs = self._baostock_api_call_wrapper(
                lambda: bs.query_history_k_data_plus(
                    code=ticker,
                    fields="date,time,code,open,high,low,close,volume,amount",
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d")
                    if end_date is not None
                    else None,
                    frequency=period,
                    adjustflag="2",  # pre-adjusted
                )
            )
            if rs is None or rs.error_code != "0":
                logger.warning(
                    f"BaoStock intraday data query failed for {ticker}: {rs.error_msg if rs else 'No response'}"
                )
                return prices

            data_frame = rs.get_data()
            for _, row in data_frame.iterrows():
                close_price = Decimal(str(row["close"]))
                time = str(row["time"])
                timestamp = datetime.strptime(time[:-3], "%Y%m%d%H%M%S")
                price = AssetPrice(
                    ticker=ticker,
                    price=close_price,
                    currency="CNY",
                    timestamp=timestamp,
                    open_price=Decimal(str(row["open"])),
                    high_price=Decimal(str(row["high"])),
                    low_price=Decimal(str(row["low"])),
                    close_price=close_price,
                    volume=Decimal(row["volume"]),
                    market_cap=Decimal(row["amount"]),
                    source=self.source,
                )
                prices.append(price)

        except Exception as e:
            logger.error(f"Error querying intraday data for {ticker}: {e}")

        return prices

    def _get_historical_k_data(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "d",
    ) -> List[AssetPrice]:
        """Query historical data from BaoStock.

        Args:
            ticker: BaoStock ticker code
            start_date: Start date for historical data
            end_date: End date for historical data, if None, fetch until recent trading day
            interval: Data interval code for BaoStock
        Returns:
            List of AssetPrice objects
        """
        prices: List[AssetPrice] = []
        result = self._get_exchange_and_ticker_code(ticker)
        if result is None:
            return prices
        _, ticker_code = result

        try:
            rs = self._baostock_api_call_wrapper(
                lambda: bs.query_history_k_data_plus(
                    code=ticker_code,
                    fields="date,code,open,high,low,close,volume,preclose,pctChg",
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d")
                    if end_date is not None
                    else None,
                    frequency=interval,
                    adjustflag="2",  # pre-adjusted
                )
            )
            if rs is None or rs.error_code != "0":
                logger.warning(
                    f"BaoStock historical data query failed for {ticker}: {rs.error_msg if rs else 'No response'}"
                )
                return prices

            data_frame = rs.get_data()
            for _, row in data_frame.iterrows():
                close_price = Decimal(str(row["close"]))
                preclose_price = Decimal(str(row["preclose"]))
                change = None
                if close_price is not None and preclose_price is not None:
                    change = close_price - preclose_price
                price = AssetPrice(
                    ticker=ticker,
                    price=close_price,
                    currency="CNY",
                    timestamp=datetime.strptime(row["date"], "%Y-%m-%d"),
                    open_price=Decimal(str(row["open"])),
                    high_price=Decimal(str(row["high"])),
                    low_price=Decimal(str(row["low"])),
                    close_price=close_price,
                    volume=Decimal(row["volume"]),
                    change=change,
                    change_percent=Decimal(row["pctChg"]),
                    source=self.source,
                )
                prices.append(price)
        except Exception as e:
            logger.error(f"Error querying historical data for {ticker}: {e}")

        return prices

    def _create_asset_from_info(
        self, ticker: str, exchange: Exchange, data: pd.DataFrame
    ) -> Optional[Asset]:
        """Create Asset object from fetched info dictionary.

        Args:
            ticker: Internal ticker symbol
            exchange: Exchange enum
            info_dict: List of asset information fields from BaoStock
        Returns:
            Asset object or None if creation fails
        """
        try:
            asset_data = data.iloc[0]

            country = "CN"
            currency = "CNY"
            timezone = "Asia/Shanghai"
            name = asset_data.get("code_name", ticker)
            type = asset_data.get("type")
            if str(type) == "1":
                asset_type = AssetType.STOCK
            elif str(type) == "2":
                asset_type = AssetType.INDEX
            else:
                asset_type = AssetType.STOCK  # Default to STOCK

            localized_names = LocalizedName()
            # Set localized names if not "ticker"
            if name != ticker:
                localized_names.set_name("zh-Hans", name)
                localized_names.set_name("zh-CN", name)

            # Create market info
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
            # Save asset metadata to database
            try:
                from ...server.db.repositories.asset_repository import (
                    get_asset_repository,
                )

                asset_repo = get_asset_repository()
                asset_repo.upsert_asset(
                    symbol=ticker,
                    name=name,
                    asset_type=asset.asset_type,
                    asset_metadata={
                        "currency": currency,
                        "country": country,
                        "timezone": timezone,
                        "source": self.source.value,
                    },
                )
                logger.debug(f"Saved asset info from BaoStock for {ticker}")
            except Exception as e:
                # Don"t fail the info fetch if database save fails
                logger.warning(f"Failed to save asset info for {ticker}: {e}")

            return asset

        except Exception as e:
            logger.error(f"Error creating Asset object for ticker {ticker}: {e}")
            return None

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
                    f"Invalid ticker format: {ticker}, expected EXCHANGE:SYMBOL"
                )
                return None

            exchange_str, symbol = ticker.split(":", 1)
            # Convert exchange string to Exchange enum
            try:
                exchange = Exchange(exchange_str)
            except ValueError:
                logger.warning(f"Unknown exchange: {exchange_str} for ticker {ticker}")
                return None

            if exchange not in self.get_supported_exchanges():
                logger.warning(
                    f"Exchange: {exchange_str} not supported by BaoStock for ticker {ticker}"
                )
                return None

            return (exchange, f"{self.exchange_mapping[exchange]}.{symbol}")

        except Exception as e:
            logger.error(f"Error converting ticker: {ticker} to BaoStock code: {e}")
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
        
    def _baostock_api_call_wrapper(
            self, api_call: Callable[..., Any]
        ) -> Any:
        """Wrapper for BaoStock API calls to handle login, session TTL and retries.

        - Ensures a valid login exists (with optional TTL `session_ttl` in config).
        - Uses `self.timeout` (or config `timeout`) for `func_timeout`.
        - Retries once after re-login when a timeout occurs or when the BaoStock
            response object has a non-'0' `error_code`.

        Args:
            api_call: callable BaoStock API function
            *args: positional args forwarded to `api_call`
            **kwargs: keyword args forwarded to `api_call`

        Returns:
            The raw result returned by the BaoStock API call.

        Raises:
            Exception: Last exception encountered if retries exhausted.
        """
        session_ttl = self.config.get("session_ttl", 300)
        now = time()

        # Ensure login and check TTL
        if (
            not hasattr(self, "_logging_status")
            or getattr(self._logging_status, "error_code", "1") != "0"
            or not hasattr(self, "_last_login_time")
            or (self._last_login_time is not None and now - self._last_login_time > session_ttl)
        ):
            self._baostock_login()

        timeout = getattr(self, "timeout", self.config.get("timeout", 10)) # seconds

        attempts = 0
        last_exc: Optional[BaseException] = None

        while attempts < 2:
            try:
                result = func_timeout(timeout, api_call)

                # If the result is a BaoStock response object, check its error_code
                if hasattr(result, "error_code") and getattr(result, "error_code") != "0":
                    logger.warning(
                        "BaoStock API returned error_code=%s, msg=%s - re-login and retry",
                        getattr(result, "error_code"),
                        getattr(result, "error_msg", None),
                    )
                    self._baostock_login()
                    attempts += 1
                    continue

                return result

            except FunctionTimedOut as exc:
                logger.warning("BaoStock API call timed out after %s seconds, retrying", timeout)
                last_exc = exc
                # try to re-login then retry
                try:
                    self._baostock_login()
                except Exception as login_exc:
                    logger.error("Re-login failed after timeout: %s", login_exc)
                    raise
                attempts += 1
                continue

            except Exception as exc:
                logger.error("Error during BaoStock API call: %s", exc)
                raise

        # Exhausted retries
        logger.error("BaoStock API call failed after %s attempts", attempts)
        if last_exc:
            raise last_exc
        raise RuntimeError("BaoStock API call failed after retries")
    