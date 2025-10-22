"""AKShare adapter for Chinese user-friendly financial market data.

This adapter provides integration with AKShare library to fetch comprehensive
Global financial market data including stocks, funds, bonds, and economic indicators.
"""

import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    import akshare as ak
except ImportError:
    ak = None

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


class AKShareAdapter(BaseDataAdapter):
    """AKShare data adapter for Chinese financial markets."""

    def __init__(self, **kwargs):
        """Initialize AKShare adapter.

        Args:
            **kwargs: Additional configuration parameters
        """
        super().__init__(DataSource.AKSHARE, **kwargs)

        if ak is None:
            raise ImportError(
                "akshare library is required. Install with: pip install akshare"
            )

    def _initialize(self) -> None:
        """Initialize AKShare adapter configuration."""
        self.timeout = self.config.get("timeout", 10)  # Reduced timeout duration

        # Field mapping - Handle AKShare API field changes
        self.field_mappings = {
            "a_shares": {
                "code": ["代码", "symbol", "ts_code"],
                "name": ["名称", "name", "short_name"],
                "price": ["最新价", "close", "price"],
                "open": ["今开", "开盘", "open"],
                "high": ["最高", "high"],
                "low": ["最低", "low"],
                "close": ["收盘", "close"],
                "volume": ["成交量", "volume", "vol"],
                "market_cap": ["总市值", "total_mv"],
                "change": ["涨跌额", "change"],
                "change_percent": ["涨跌幅", "change_percent", "pct_chg"],
                "date": ["日期", "date", "trade_date"],
                "time": ["时间", "time", "datetime"],
            },
            "hk_stocks": {
                "code": ["symbol", "code", "代码"],
                "name": ["name", "名称", "short_name"],
                "open": ["开盘", "open"],
                "high": ["最高", "high"],
                "low": ["最低", "low"],
                "close": ["收盘", "close"],
                "volume": ["成交量", "volume", "vol"],
                "change": ["涨跌额", "change"],
                "change_percent": ["涨跌幅", "change_percent", "pct_chg"],
                "date": ["日期", "date", "trade_date"],
                "time": ["时间", "time", "datetime"],
            },
            "us_stocks": {
                "code": ["代码", "symbol", "ticker"],
                "name": ["名称", "name", "short_name"],
                "open": ["开盘", "open"],
                "high": ["最高", "high"],
                "low": ["最低", "low"],
                "close": ["收盘", "close"],
                "volume": ["成交量", "volume", "vol"],
                "change": ["涨跌额", "change"],
                "change_percent": ["涨跌幅", "change_percent", "pct_chg"],
                "date": ["日期", "date", "trade_date"],
                "time": ["时间", "time", "datetime"],
            },
        }

        # Exchange mapping for AKShare
        self.exchange_mapping = {
            "SH": Exchange.SSE.value,  # Shanghai Stock Exchange
            "SZ": Exchange.SZSE.value,  # Shenzhen Stock Exchange
            "BJ": Exchange.BSE.value,  # Beijing Stock Exchange
            "HK": Exchange.HKEX.value,  # Hong Kong Stock Exchange
            "NYSE": Exchange.NYSE.value,  # New York Stock Exchange
            "NASDAQ": Exchange.NASDAQ.value,  # NASDAQ Exchange
            "AMEX": Exchange.AMEX.value,  # AMEX Exchange
        }

        # US exchange codes for AKShare API
        # AKShare requires exchange code prefix for US stocks and indices
        # Format: exchange_code.SYMBOL (e.g., 105.AAPL for NASDAQ:AAPL, 100.IXIC for INDEX)
        # Code 100: US Index data (for INDEX asset type)
        # Code 105: NASDAQ stocks
        # Code 106: NYSE stocks
        # Code 107: AMEX stocks
        self.us_exchange_codes = {
            Exchange.NASDAQ: "105",
            Exchange.NYSE: "106",
            Exchange.AMEX: "107",
        }

        # Special exchange code for US indices
        self.us_index_exchange_code = "100"

        # Reverse mapping for converting AKShare format back to internal format
        self.us_exchange_codes_reverse = {
            v: k for k, v in self.us_exchange_codes.items()
        }
        # Add index code to reverse mapping
        self.us_exchange_codes_reverse["100"] = None  # Special handling for indices

        logger.info("AKShare adapter initialized with caching and field mapping")

    def _get_market_type(self, exchange: Exchange) -> str:
        """Get market type identifier for field mapping.

        Args:
            exchange: Exchange enum

        Returns:
            Market type string ('a_shares', 'hk_stocks', or 'us_stocks')
        """
        if exchange in [Exchange.SSE, Exchange.SZSE, Exchange.BSE]:
            return "a_shares"
        elif exchange == Exchange.HKEX:
            return "hk_stocks"
        elif exchange in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
            return "us_stocks"
        else:
            return "a_shares"  # Default fallback

    def _get_currency(self, exchange: Exchange) -> str:
        """Get currency code based on exchange.

        Args:
            exchange: Exchange enum

        Returns:
            Currency code (CNY, HKD, or USD)
        """
        if exchange in [Exchange.SSE, Exchange.SZSE, Exchange.BSE]:
            return "CNY"
        elif exchange == Exchange.HKEX:
            return "HKD"
        elif exchange in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
            return "USD"
        else:
            return "USD"  # Default fallback

    def _get_field_name(
        self, df: pd.DataFrame, field: str, exchange: Exchange
    ) -> Optional[str]:
        """Get the actual field name from DataFrame based on exchange type.

        Args:
            df: DataFrame to search for field
            field: Standard field name (e.g., 'open', 'close', 'high')
            exchange: Exchange enum to determine which mapping to use

        Returns:
            Actual field name found in DataFrame, or None if not found
        """
        # Get market type for field mapping
        market = self._get_market_type(exchange)

        # Get possible field names for this field
        possible_names = self.field_mappings.get(market, {}).get(field, [])

        # Check which field name exists in the DataFrame
        for name in possible_names:
            if name in df.columns:
                return name

        # If not found, try the standard field name directly
        if field in df.columns:
            return field

        return None

    def search_assets(self, query: AssetSearchQuery) -> List[AssetSearchResult]:
        """AKShare does not support search assets."""
        return []

    def __get_xq_symbol(self, ticker: str) -> str:
        """Get XQ symbol for a specific asset.
        Args:
            ticker: Asset ticker in internal format (e.g., "SSE:601127", "HKEX:02097", "NASDAQ:NVDA")
        Returns:
            XQ symbol or None if not found
        """
        try:
            # Parse ticker to get exchange and symbol
            if ":" not in ticker:
                logger.warning(
                    f"Invalid ticker format: {ticker}, expected 'EXCHANGE:SYMBOL'"
                )
                return None

            exchange_str, symbol = ticker.split(":", 1)

            # Convert exchange string to Exchange enum
            try:
                exchange = Exchange(exchange_str)
            except ValueError:
                logger.warning(f"Unknown exchange '{exchange_str}' for ticker {ticker}")
                return None

            # For A-shares (SSE, SZSE, BSE): format is "SH600519", "SZ000001", "BJ430047"
            if exchange == Exchange.SSE:
                return f"SH{symbol}"
            elif exchange == Exchange.SZSE:
                return f"SZ{symbol}"
            elif exchange == Exchange.BSE:
                return f"BJ{symbol}"

            # For Hong Kong stocks: format is just the symbol without leading zeros (e.g., "00700" -> "700", or keep as is)
            elif exchange == Exchange.HKEX:
                # Remove leading zeros for XQ format
                return symbol.lstrip("0") or "0"  # Keep at least one zero if all zeros

            # For US stocks: format is just the symbol without exchange prefix
            elif exchange in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
                return symbol

            else:
                logger.warning(
                    f"Unsupported exchange for XQ symbol conversion: {exchange}"
                )
                return None

        except Exception as e:
            logger.error(f"Error converting ticker {ticker} to XQ symbol: {e}")
            return None

    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Get detailed information about a specific asset.
        Args:
            ticker: Asset ticker in internal format (e.g., "SSE:601127", "HKEX:02097", "NASDAQ:NVDA")
        Returns:
            Asset information or None if not found
        """
        try:
            # Get XQ symbol for the ticker
            xq_symbol = self.__get_xq_symbol(ticker)
            if not xq_symbol:
                logger.warning(f"Cannot get XQ symbol for ticker: {ticker}")
                return None

            # Parse ticker to get exchange and symbol
            exchange_str, symbol = ticker.split(":", 1)
            exchange = Exchange(exchange_str)

            # Call different AKShare APIs based on the market
            df = None

            # A-shares market (SSE, SZSE, BSE)
            if exchange in [Exchange.SSE, Exchange.SZSE, Exchange.BSE]:
                try:
                    df = ak.stock_individual_basic_info_xq(
                        symbol=xq_symbol, token=os.getenv("XUEQIU_TOKEN", None)
                    )
                except Exception as e:
                    logger.error(
                        f"Error fetching A-share info for {xq_symbol}: {e}",
                        exc_info=True,
                    )
                    return None

            # Hong Kong stock market
            elif exchange == Exchange.HKEX:
                try:
                    df = ak.stock_individual_basic_info_hk_xq(
                        symbol=xq_symbol, token=os.getenv("XUEQIU_TOKEN", None)
                    )
                except Exception as e:
                    logger.error(
                        f"Error fetching HK stock info for {xq_symbol}: {e}",
                        exc_info=True,
                    )
                    return None

            # US stock market (NASDAQ, NYSE, AMEX)
            elif exchange in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
                try:
                    df = ak.stock_individual_basic_info_us_xq(
                        symbol=xq_symbol, token=os.getenv("XUEQIU_TOKEN", None)
                    )
                except Exception as e:
                    logger.error(
                        f"Error fetching US stock info for {xq_symbol}: {e}",
                        exc_info=True,
                    )
                    return None

            else:
                logger.warning(f"Unsupported exchange for asset info: {exchange}")
                return None

            # Check if data was retrieved
            if df is None or df.empty:
                logger.warning(f"No data found for ticker: {ticker}")
                return None

            # Convert DataFrame to dictionary for easier access
            info_dict = {}
            for _, row in df.iterrows():
                item = row.get("item", "")
                value = row.get("value", "")
                if item and value:
                    info_dict[item] = value

            # Create Asset object based on market type
            return self._create_asset_from_info(ticker, exchange, info_dict)

        except Exception as e:
            logger.error(f"Error getting asset info for {ticker}: {e}", exc_info=True)
            return None

    def _create_asset_from_info(
        self, ticker: str, exchange: Exchange, info_dict: Dict[str, Any]
    ) -> Optional[Asset]:
        """Create Asset object from info dictionary.
        Args:
            ticker: Asset ticker in internal format
            exchange: Exchange enum
            info_dict: Dictionary containing asset information
        Returns:
            Asset object or None if creation fails
        """
        try:
            # Create localized names
            localized_names = LocalizedName()

            # Determine country and currency based on exchange
            if exchange in [Exchange.SSE, Exchange.SZSE, Exchange.BSE]:
                # A-shares
                country = "CN"
                currency = info_dict.get("currency", "CNY")
                timezone = "Asia/Shanghai"

                # Set Chinese and English names
                cn_name = info_dict.get(
                    "org_short_name_cn", info_dict.get("org_name_cn", "")
                )
                en_name = info_dict.get(
                    "org_short_name_en", info_dict.get("org_name_en", "")
                )

                if cn_name:
                    localized_names.set_name("zh-Hans", cn_name)
                    localized_names.set_name("zh-CN", cn_name)
                if en_name:
                    localized_names.set_name("en-US", en_name)
                    localized_names.set_name("en", en_name)

                # Use Chinese name as fallback if no English name
                if not en_name and cn_name:
                    localized_names.set_name("en-US", cn_name)

            elif exchange == Exchange.HKEX:
                # Hong Kong stocks
                country = "HK"
                currency = "HKD"
                timezone = "Asia/Hong_Kong"

                # Set Chinese and English names
                cn_name = info_dict.get("comcnname", "")
                en_name = info_dict.get("comenname", "")

                if cn_name:
                    localized_names.set_name("zh-Hant", cn_name)
                    localized_names.set_name("zh-HK", cn_name)
                if en_name:
                    localized_names.set_name("en-US", en_name)
                    localized_names.set_name("en", en_name)

                # Use English name as fallback if no Chinese name
                if not cn_name and en_name:
                    localized_names.set_name("zh-Hant", en_name)

            elif exchange in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
                # US stocks
                country = "US"
                currency = "USD"
                timezone = "America/New_York"

                # Set English and Chinese names
                en_name = info_dict.get(
                    "org_short_name_en", info_dict.get("org_name_en", "")
                )
                cn_name = info_dict.get(
                    "org_short_name_cn", info_dict.get("org_name_cn", "")
                )

                if en_name:
                    localized_names.set_name("en-US", en_name)
                    localized_names.set_name("en", en_name)
                if cn_name:
                    localized_names.set_name("zh-Hans", cn_name)
                    localized_names.set_name("zh-CN", cn_name)

                # Use symbol as fallback if no names available
                if not en_name and not cn_name:
                    symbol = ticker.split(":")[1]
                    localized_names.set_name("en-US", symbol)

            else:
                logger.warning(f"Unsupported exchange: {exchange}")
                return None

            # Create market info
            market_info = MarketInfo(
                exchange=exchange.value,
                country=country,
                currency=currency,
                timezone=timezone,
                market_status=MarketStatus.UNKNOWN,
            )

            # Create Asset object
            asset = Asset(
                ticker=ticker,
                asset_type=AssetType.STOCK,  # Default to stock, can be enhanced later
                names=localized_names,
                market_info=market_info,
            )

            # Add source mapping for AKShare
            asset.set_source_ticker(
                DataSource.AKSHARE, self.convert_to_source_ticker(ticker)
            )

            # Add additional properties from info_dict
            for key, value in info_dict.items():
                if value and str(value).strip() and str(value).lower() != "none":
                    asset.add_property(key, value)

            # Save asset metadata to database
            try:
                from ...server.db.repositories.asset_repository import (
                    get_asset_repository,
                )

                asset_repo = get_asset_repository()

                # Get the primary name for the asset
                primary_name = (
                    localized_names.get_name("en-US")
                    or localized_names.get_name("zh-Hans")
                    or localized_names.get_name("zh-Hant")
                    or ticker
                )

                asset_repo.upsert_asset(
                    symbol=ticker,
                    name=primary_name,
                    asset_type=asset.asset_type.value,
                    description=None,  # AKShare info_dict doesn't have structured description field
                    sector=info_dict.get("industry") or info_dict.get("sector"),
                    asset_metadata={
                        "currency": currency,
                        "country": country,
                        "timezone": timezone,
                        "source": "akshare",
                        "info": {
                            k: v
                            for k, v in info_dict.items()
                            if v and str(v).strip() and str(v).lower() != "none"
                        },
                    },
                )
                logger.debug(f"Saved asset info from AKShare for {ticker}")
            except Exception as e:
                # Don't fail the info fetch if database save fails
                logger.warning(
                    f"Failed to save asset info from AKShare for {ticker}: {e}"
                )

            return asset

        except Exception as e:
            logger.error(
                f"Error creating asset from info for {ticker}: {e}", exc_info=True
            )
            return None

    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time price data for an asset using Eastmoney 1-minute API.

        This method fetches the latest 1-minute price data to get real-time information.
        Supports US stocks, Hong Kong stocks, and A-shares.

        Args:
            ticker: Asset ticker in internal format (e.g., "SSE:600519", "HKEX:00700", "NASDAQ:AAPL")

        Returns:
            Latest AssetPrice object, or None if data not available
        """
        try:
            # Parse ticker to get exchange and symbol
            if ":" not in ticker:
                logger.warning(f"Invalid ticker format: {ticker}")
                return None

            exchange_str, symbol = ticker.split(":", 1)
            try:
                exchange = Exchange(exchange_str)
            except ValueError:
                logger.warning(f"Unknown exchange: {exchange_str}")
                return None

            # Convert to AKShare format
            source_ticker = self.convert_to_source_ticker(ticker)

            # Use current time as end time, and set start time to 1 day ago to ensure we get recent data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)

            df = None

            # A-shares (SSE, SZSE, BSE)
            if exchange in [Exchange.SSE, Exchange.SZSE, Exchange.BSE]:
                try:
                    # Get 1-minute data (returns recent 5 trading days, no adjustment)
                    df = ak.stock_zh_a_hist_min_em(
                        symbol=symbol,
                        start_date=start_date.strftime("%Y-%m-%d %H:%M:%S"),
                        end_date=end_date.strftime("%Y-%m-%d %H:%M:%S"),
                        period="1",
                        adjust="",  # 1-minute data cannot be adjusted
                    )
                except Exception as e:
                    logger.error(
                        f"Error fetching A-share real-time data for {symbol}: {e}"
                    )
                    return None

            # Hong Kong stocks
            elif exchange == Exchange.HKEX:
                try:
                    # Get 1-minute data for HK stocks
                    df = ak.stock_hk_hist_min_em(
                        symbol=symbol,
                        period="1",
                        adjust="",
                        start_date=start_date.strftime("%Y-%m-%d %H:%M:%S"),
                        end_date=end_date.strftime("%Y-%m-%d %H:%M:%S"),
                    )
                except Exception as e:
                    logger.error(
                        f"Error fetching HK stock real-time data for {symbol}: {e}"
                    )
                    return None

            # US stocks
            elif exchange in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
                try:
                    # US stock minute data API returns latest data
                    df = ak.stock_us_hist_min_em(symbol=source_ticker)
                except Exception as e:
                    logger.error(
                        f"Error fetching US stock real-time data for {source_ticker}: {e}"
                    )
                    return None

            else:
                logger.warning(f"Unsupported exchange for real-time data: {exchange}")
                return None

            # Check if data was retrieved
            if df is None or df.empty:
                logger.warning(f"No real-time data found for {ticker}")
                return None

            # Convert DataFrame to AssetPrice list (reuse existing conversion method)
            prices = self._convert_intraday_df_to_prices(df, ticker, exchange)

            # Return the most recent price (last entry)
            if prices:
                return prices[-1]
            else:
                logger.warning(f"Failed to convert real-time data for {ticker}")
                return None

        except Exception as e:
            logger.error(
                f"Error getting real-time price for {ticker}: {e}", exc_info=True
            )
            return None

    def get_historical_prices(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[AssetPrice]:
        """Get historical price data using Eastmoney API.

        Supports US stocks, Hong Kong stocks, and A-shares with qfq (forward adjusted) data.

        Args:
            ticker: Asset ticker in internal format (e.g., "SSE:600519", "HKEX:00700", "NASDAQ:AAPL")
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval using format like "1m", "5m", "15m", "30m", "60m", "1d", "1w", "1mo"
                     Supported intervals:
                     - Minute: "1m", "5m", "15m", "30m", "60m" (intraday data)
                     - Daily: "1d" (default)
                     - Weekly: "1w"
                     - Monthly: "1mo"

        Returns:
            List of historical price data

        Note:
            - 1-minute data returns only recent 5 trading days and cannot be adjusted
            - Intraday data uses separate API endpoints with different limitations per exchange
        """
        try:
            # Parse ticker to get exchange and symbol
            if ":" not in ticker:
                logger.warning(f"Invalid ticker format: {ticker}")
                return []

            exchange_str, symbol = ticker.split(":", 1)
            try:
                exchange = Exchange(exchange_str)
            except ValueError:
                logger.warning(f"Unknown exchange: {exchange_str}")
                return []

            # Convert to AKShare format
            source_ticker = self.convert_to_source_ticker(ticker)

            # Map interval to Eastmoney API format
            # For minute data: period='1'/'5'/'15'/'30'/'60'
            # For daily/weekly/monthly: period='daily'/'weekly'/'monthly'
            interval_mapping = {
                # Minute intervals (intraday)
                f"1{Interval.MINUTE}": "1",
                f"5{Interval.MINUTE}": "5",
                f"15{Interval.MINUTE}": "15",
                f"30{Interval.MINUTE}": "30",
                f"60{Interval.MINUTE}": "60",
                # Daily/Weekly/Monthly intervals
                f"1{Interval.DAY}": "daily",
                f"1{Interval.WEEK}": "weekly",
                f"1{Interval.MONTH}": "monthly",
            }

            # Get the period value from mapping
            period = interval_mapping.get(interval)
            if not period:
                logger.warning(
                    f"Unsupported interval: {interval}. "
                    f"Supported intervals: {', '.join(interval_mapping.keys())}"
                )
                return []

            # Determine if this is intraday (minute-level) data
            is_intraday = period in ["1", "5", "15", "30", "60"]

            if is_intraday:
                # Use intraday data method for minute-level intervals
                return self._get_intraday_prices(
                    ticker, exchange, source_ticker, start_date, end_date, period
                )

            # Format dates for daily/weekly/monthly data
            start_date_str = start_date.strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")

            # Get historical data based on exchange
            df = None

            # A-shares (SSE, SZSE, BSE)
            if exchange in [Exchange.SSE, Exchange.SZSE, Exchange.BSE]:
                try:
                    df = ak.stock_zh_a_hist(
                        symbol=symbol,
                        period=period,
                        start_date=start_date_str,
                        end_date=end_date_str,
                        adjust="qfq",  # Forward adjusted
                    )
                except Exception as e:
                    logger.error(
                        f"Error fetching A-share historical data for {symbol} with period {period}: {e}"
                    )
                    return []

            # Hong Kong stocks
            elif exchange == Exchange.HKEX:
                try:
                    df = ak.stock_hk_hist(
                        symbol=symbol,
                        period=period,
                        start_date=start_date_str,
                        end_date=end_date_str,
                        adjust="qfq",  # Forward adjusted
                    )
                except Exception as e:
                    logger.error(
                        f"Error fetching HK stock historical data for {symbol} with period {period}: {e}"
                    )
                    return []

            # US stocks
            elif exchange in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
                try:
                    df = ak.stock_us_hist(
                        symbol=source_ticker,  # US stocks need exchange code prefix
                        period=period,
                        start_date=start_date_str,
                        end_date=end_date_str,
                        adjust="qfq",  # Forward adjusted
                    )
                except Exception as e:
                    logger.error(
                        f"Error fetching US stock historical data for {source_ticker} with period {period}: {e}"
                    )
                    return []

            else:
                logger.warning(f"Unsupported exchange for historical data: {exchange}")
                return []

            # Check if data was retrieved
            if df is None or df.empty:
                logger.warning(f"No historical data found for {ticker}")
                return []

            # Convert DataFrame to AssetPrice list
            return self._convert_df_to_prices(df, ticker, exchange)

        except Exception as e:
            logger.error(
                f"Error getting historical prices for {ticker}: {e}", exc_info=True
            )
            return []

    def _get_intraday_prices(
        self,
        ticker: str,
        exchange: Exchange,
        source_ticker: str,
        start_date: datetime,
        end_date: datetime,
        period: str,
    ) -> List[AssetPrice]:
        """Get intraday (minute-level) price data using Eastmoney API.

        Args:
            ticker: Asset ticker in internal format
            exchange: Exchange enum
            source_ticker: Ticker in AKShare format
            start_date: Start date and time
            end_date: End date and time
            period: Period value for Eastmoney API ('1', '5', '15', '30', '60')

        Returns:
            List of intraday price data

        Note:
            - period='1': 1-minute data, returns only recent 5 trading days, no adjustment
            - period='5': 5-minute data
            - period='15': 15-minute data
            - period='30': 30-minute data
            - period='60': 60-minute data (1 hour)
        """
        try:
            # Validate period value
            if period not in ["1", "5", "15", "30", "60"]:
                logger.warning(
                    f"Invalid period for intraday data: {period}. Expected one of: 1, 5, 15, 30, 60"
                )
                return []

            # Format datetime strings
            start_datetime_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
            end_datetime_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

            # Get symbol from ticker
            symbol = ticker.split(":", 1)[1]

            df = None

            # A-shares (SSE, SZSE, BSE)
            if exchange in [Exchange.SSE, Exchange.SZSE, Exchange.BSE]:
                try:
                    # Note: 1-minute data only returns recent 5 trading days and cannot be adjusted
                    adjust = "" if period == "1" else "qfq"
                    df = ak.stock_zh_a_hist_min_em(
                        symbol=symbol,
                        start_date=start_datetime_str,
                        end_date=end_datetime_str,
                        period=period,
                        adjust=adjust,
                    )
                except Exception as e:
                    logger.error(
                        f"Error fetching A-share intraday data for {symbol}: {e}"
                    )
                    return []

            # Hong Kong stocks
            elif exchange == Exchange.HKEX:
                try:
                    # Note: HK stock minute data doesn't support adjust parameter
                    df = ak.stock_hk_hist_min_em(
                        symbol=symbol,
                        period=period,
                        adjust="",  # HK stocks don't support adjustment for minute data
                        start_date=start_datetime_str,
                        end_date=end_datetime_str,
                    )
                except Exception as e:
                    logger.error(
                        f"Error fetching HK stock intraday data for {symbol}: {e}"
                    )
                    return []

            # US stocks
            elif exchange in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
                try:
                    # Note: US stock minute data API only returns latest data, doesn't support date range
                    df = ak.stock_us_hist_min_em(symbol=source_ticker)
                except Exception as e:
                    logger.error(
                        f"Error fetching US stock intraday data for {source_ticker}: {e}"
                    )
                    return []

            else:
                logger.warning(f"Unsupported exchange for intraday data: {exchange}")
                return []

            # Check if data was retrieved
            if df is None or df.empty:
                logger.warning(f"No intraday data found for {ticker}")
                return []

            # Convert DataFrame to AssetPrice list
            return self._convert_intraday_df_to_prices(df, ticker, exchange)

        except Exception as e:
            logger.error(
                f"Error getting intraday prices for {ticker}: {e}", exc_info=True
            )
            return []

    def _convert_df_to_prices(
        self, df: pd.DataFrame, ticker: str, exchange: Exchange
    ) -> List[AssetPrice]:
        """Convert historical price DataFrame to list of AssetPrice objects.

        Args:
            df: DataFrame containing historical price data
            ticker: Asset ticker in internal format
            exchange: Exchange enum

        Returns:
            List of AssetPrice objects
        """
        prices = []

        try:
            # Get currency based on exchange
            currency = self._get_currency(exchange)

            # Use field mapping helper to get actual field names
            date_field = self._get_field_name(df, "date", exchange)
            open_field = self._get_field_name(df, "open", exchange)
            close_field = self._get_field_name(df, "close", exchange)
            high_field = self._get_field_name(df, "high", exchange)
            low_field = self._get_field_name(df, "low", exchange)
            volume_field = self._get_field_name(df, "volume", exchange)
            change_field = self._get_field_name(df, "change", exchange)
            change_pct_field = self._get_field_name(df, "change_percent", exchange)

            # Validate required fields
            if not date_field or not close_field:
                logger.error(
                    f"Missing required fields in DataFrame. date_field={date_field}, close_field={close_field}"
                )
                return []

            for _, row in df.iterrows():
                try:
                    # Parse date
                    date_str = str(row[date_field])
                    if len(date_str) == 8:  # Format: YYYYMMDD
                        timestamp = datetime.strptime(date_str, "%Y%m%d")
                    else:
                        # Try parsing as standard date format
                        timestamp = pd.to_datetime(date_str)

                    # Create AssetPrice object
                    price = AssetPrice(
                        ticker=ticker,
                        price=Decimal(str(row[close_field])),
                        currency=currency,
                        timestamp=timestamp,
                        open_price=Decimal(str(row[open_field]))
                        if open_field and pd.notna(row[open_field])
                        else None,
                        high_price=Decimal(str(row[high_field]))
                        if high_field and pd.notna(row[high_field])
                        else None,
                        low_price=Decimal(str(row[low_field]))
                        if low_field and pd.notna(row[low_field])
                        else None,
                        close_price=Decimal(str(row[close_field]))
                        if pd.notna(row[close_field])
                        else None,
                        volume=Decimal(str(row[volume_field]))
                        if volume_field and pd.notna(row[volume_field])
                        else None,
                        change=Decimal(str(row[change_field]))
                        if change_field and pd.notna(row[change_field])
                        else None,
                        change_percent=Decimal(str(row[change_pct_field]))
                        if change_pct_field and pd.notna(row[change_pct_field])
                        else None,
                        source=DataSource.AKSHARE,
                    )
                    prices.append(price)

                except Exception as e:
                    logger.warning(f"Error converting row to AssetPrice: {e}")
                    continue

            return prices

        except Exception as e:
            logger.error(f"Error converting DataFrame to prices: {e}", exc_info=True)
            return []

    def _convert_intraday_df_to_prices(
        self, df: pd.DataFrame, ticker: str, exchange: Exchange
    ) -> List[AssetPrice]:
        """Convert intraday price DataFrame to list of AssetPrice objects.

        Args:
            df: DataFrame containing intraday price data
            ticker: Asset ticker in internal format
            exchange: Exchange enum

        Returns:
            List of AssetPrice objects
        """
        prices = []

        try:
            # Get currency based on exchange
            currency = self._get_currency(exchange)

            # Use field mapping helper to get actual field names
            time_field = self._get_field_name(df, "time", exchange)
            open_field = self._get_field_name(df, "open", exchange)
            close_field = self._get_field_name(df, "close", exchange)
            high_field = self._get_field_name(df, "high", exchange)
            low_field = self._get_field_name(df, "low", exchange)
            volume_field = self._get_field_name(df, "volume", exchange)

            # Validate required fields
            if not time_field or not close_field:
                logger.error(
                    f"Missing required fields in DataFrame. time_field={time_field}, close_field={close_field}"
                )
                return []

            for _, row in df.iterrows():
                try:
                    # Parse datetime
                    time_str = str(row[time_field])
                    timestamp = pd.to_datetime(time_str)

                    # Create AssetPrice object
                    price = AssetPrice(
                        ticker=ticker,
                        price=Decimal(str(row[close_field])),
                        currency=currency,
                        timestamp=timestamp,
                        open_price=Decimal(str(row[open_field]))
                        if open_field
                        and pd.notna(row[open_field])
                        and row[open_field] != 0
                        else None,
                        high_price=Decimal(str(row[high_field]))
                        if high_field and pd.notna(row[high_field])
                        else None,
                        low_price=Decimal(str(row[low_field]))
                        if low_field and pd.notna(row[low_field])
                        else None,
                        close_price=Decimal(str(row[close_field]))
                        if pd.notna(row[close_field])
                        else None,
                        volume=Decimal(str(row[volume_field]))
                        if volume_field and pd.notna(row[volume_field])
                        else None,
                        source=DataSource.AKSHARE,
                    )
                    prices.append(price)

                except Exception as e:
                    logger.warning(f"Error converting intraday row to AssetPrice: {e}")
                    continue

            return prices

        except Exception as e:
            logger.error(
                f"Error converting intraday DataFrame to prices: {e}", exc_info=True
            )
            return []

    def get_capabilities(self) -> List[AdapterCapability]:
        """Get detailed capabilities of AKShare adapter.

        AKShare primarily supports Chinese and Hong Kong markets.

        Returns:
            List of capabilities describing supported asset types and exchanges
        """
        return [
            AdapterCapability(
                asset_type=AssetType.STOCK,
                exchanges={
                    Exchange.SSE,
                    Exchange.SZSE,
                    Exchange.BSE,
                    Exchange.HKEX,
                    Exchange.NASDAQ,
                    Exchange.NYSE,
                    Exchange.AMEX,
                },
            ),
            AdapterCapability(
                asset_type=AssetType.ETF,
                exchanges={
                    Exchange.SSE,
                    Exchange.SZSE,
                    Exchange.BSE,
                    Exchange.HKEX,
                    Exchange.NASDAQ,
                    Exchange.NYSE,
                    Exchange.AMEX,
                },
            ),
            AdapterCapability(
                asset_type=AssetType.INDEX,
                exchanges={
                    Exchange.SSE,
                    Exchange.SZSE,
                    Exchange.BSE,
                    Exchange.HKEX,
                    Exchange.NASDAQ,
                    Exchange.NYSE,
                    Exchange.AMEX,
                },
            ),
        ]

    def convert_to_source_ticker(self, internal_ticker: str) -> str:
        """Convert internal ticker to data source format.
        Args:
            internal_ticker: Ticker in internal format (e.g., "NASDAQ:AAPL", "NYSE:GSPC")
            source: Target data source
        Returns:
            Ticker in data source specific format (e.g., "105.AAPL", "100.GSPC")
        """
        try:
            exchange, symbol = internal_ticker.split(":", 1)

            # Convert exchange string to Exchange enum if needed
            try:
                exchange_enum = Exchange(exchange)
            except ValueError:
                logger.warning(
                    f"Unknown exchange '{exchange}' for ticker {internal_ticker}"
                )
                return symbol

            # Check if this is an INDEX asset type from database
            # Use lazy import to avoid circular dependency
            try:
                from ...server.db.repositories.asset_repository import (
                    get_asset_repository,
                )

                asset_repo = get_asset_repository()
                asset = asset_repo.get_asset_by_symbol(internal_ticker)

                # For US INDEX assets, use special exchange code 100
                if asset and asset.asset_type == AssetType.INDEX.value:
                    if exchange_enum in [Exchange.NASDAQ, Exchange.NYSE, Exchange.AMEX]:
                        return f"{self.us_index_exchange_code}.{symbol}"
            except (ImportError, Exception) as e:
                # If repository is not available, skip database lookup
                logger.debug(
                    f"Asset repository not available for AKShare, skipping database lookup: {e}"
                )
                pass

            # Handle US stocks - add exchange code prefix
            if exchange_enum in self.us_exchange_codes:
                exchange_code = self.us_exchange_codes[exchange_enum]
                return f"{exchange_code}.{symbol}"

            # Handle Chinese A-shares and Hong Kong stocks
            # For Chinese markets, AKShare uses the symbol directly without suffix
            if exchange_enum in [
                Exchange.SSE,
                Exchange.SZSE,
                Exchange.BSE,
                Exchange.HKEX,
            ]:
                return symbol

            # For other exchanges, return symbol as-is
            logger.debug(
                f"No specific format mapping for exchange {exchange}, returning symbol: {symbol}"
            )
            return symbol

        except ValueError:
            logger.error(
                f"Invalid ticker format: {internal_ticker}, expected 'EXCHANGE:SYMBOL'"
            )
            return internal_ticker

    def convert_to_internal_ticker(
        self, source_ticker: str, default_exchange: Optional[str] = None
    ) -> str:
        """Convert data source ticker to internal format.
        Args:
            source_ticker: Ticker in data source format (e.g., "105.AAPL", "00700","600519")
            source: Source data provider
            default_exchange: Default exchange if cannot be determined from ticker
        Returns:
            Ticker in internal format (e.g., "NASDAQ:AAPL", "HKEX:00700", "SSE:600519")
        """
        # Handle US stocks with exchange code prefix (e.g., "105.AAPL" -> "NASDAQ:AAPL")
        if "." in source_ticker:
            parts = source_ticker.split(".", 1)
            if len(parts) == 2:
                exchange_code, symbol = parts
                # Check if this is a US exchange code
                if exchange_code in self.us_exchange_codes_reverse:
                    exchange_enum = self.us_exchange_codes_reverse[exchange_code]
                    return f"{exchange_enum.value}:{symbol}"

        # Handle Chinese A-shares by ticker format
        # Shanghai Stock Exchange: 6-digit codes starting with 6
        # Shenzhen Stock Exchange: 6-digit codes starting with 0 or 3
        # Beijing Stock Exchange: 6-digit codes starting with 4 or 8
        if source_ticker.isdigit():
            if len(source_ticker) == 6:
                first_digit = source_ticker[0]
                if first_digit == "6":
                    return f"{Exchange.SSE.value}:{source_ticker}"
                elif first_digit in ["0", "3"]:
                    return f"{Exchange.SZSE.value}:{source_ticker}"
                elif first_digit in ["4", "8"]:
                    return f"{Exchange.BSE.value}:{source_ticker}"

            # Handle Hong Kong stocks (5-digit codes, can have leading zeros)
            # Hong Kong stocks are typically 5 digits (e.g., "00700", "01810")
            elif len(source_ticker) == 5:
                return f"{Exchange.HKEX.value}:{source_ticker}"

            # For 4-digit codes, could be simplified HK stocks
            elif len(source_ticker) == 4:
                # Pad to 5 digits for Hong Kong stocks
                padded_symbol = source_ticker.zfill(5)
                return f"{Exchange.HKEX.value}:{padded_symbol}"

        # If default exchange is provided, use it
        if default_exchange:
            # Normalize default_exchange if it's an Exchange enum
            if isinstance(default_exchange, Exchange):
                exchange_value = default_exchange.value
            else:
                exchange_value = default_exchange
            return f"{exchange_value}:{source_ticker}"

        # Fallback: return with AKSHARE prefix if cannot determine exchange
        logger.warning(
            f"Cannot determine exchange for ticker '{source_ticker}', using AKSHARE as prefix"
        )
        return f"AKSHARE:{source_ticker}"

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker is supported by AKShare and matches standard format."""
        try:
            if ":" not in ticker:
                return False

            exchange, _ = ticker.split(":", 1)
            capabilities = self.get_capabilities()

            # Check if any capability supports this exchange
            return any(cap.supports_exchange(exchange) for cap in capabilities)
        except Exception:
            return False
