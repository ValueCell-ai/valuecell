"""Yahoo Finance adapter for asset data.

This adapter provides integration with Yahoo Finance API through the yfinance library
to fetch stock market data, including real-time prices and historical data.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

import yfinance as yf

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


class YFinanceAdapter(BaseDataAdapter):
    """Yahoo Finance data adapter implementation."""

    def __init__(self, **kwargs):
        """Initialize Yahoo Finance adapter."""
        super().__init__(DataSource.YFINANCE, **kwargs)

        if yf is None:
            raise ImportError(
                "yfinance library is required. Install with: pip install yfinance"
            )

    def _initialize(self) -> None:
        """Initialize Yahoo Finance adapter configuration."""
        self.timeout = self.config.get("timeout", 30)

        # Asset type mapping for Yahoo Finance
        self.quote_type_to_asset_type_mapping = {
            "EQUITY": AssetType.STOCK,
            "ETF": AssetType.ETF,
            "INDEX": AssetType.INDEX,
            "CRYPTOCURRENCY": AssetType.CRYPTO,
        }

        # Map yfinance exchanges to our internal exchanges
        self.exchange_mapping = {
            "NMS": Exchange.NASDAQ,
            "NYQ": Exchange.NYSE,
            "ASE": Exchange.AMEX,
            "SHH": Exchange.SSE,
            "SHZ": Exchange.SZSE,
            "HKG": Exchange.HKEX,
            "PCX": Exchange.NYSE,
            "CCC": Exchange.CRYPTO,
        }

        self.yfinance_exchange_suffix_mapping = {
            Exchange.NASDAQ.value: "",
            Exchange.NYSE.value: "",
            Exchange.AMEX.value: "",
            Exchange.SSE.value: ".SS",
            Exchange.SZSE.value: ".SZ",
            Exchange.HKEX.value: ".HK",
            Exchange.CRYPTO.value: "-USD",
        }

        logger.info("Yahoo Finance adapter initialized")

    def search_assets(self, query: AssetSearchQuery) -> List[AssetSearchResult]:
        """Search for assets using Yahoo Finance Search API.

        Uses yfinance.Search for better search results across stocks, ETFs, and other assets.
        Falls back to direct ticker lookup for specific symbols.

        This method
        """
        results = []
        search_term = query.query.strip()

        try:
            # Use yfinance Search API for comprehensive search
            search_obj = yf.Search(search_term)

            # Get search results from different categories
            search_quotes = getattr(search_obj, "quotes", [])

            # Process search results
            for quote in search_quotes:
                try:
                    result = self._create_search_result_from_quote(quote)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.debug(f"Error processing search quote: {e}")
                    continue

        except Exception as e:
            logger.error(f"yfinance Search API failed for '{search_term}': {e}")

        return results[: query.limit]

    def _create_search_result_from_quote(
        self, quote: Dict
    ) -> Optional[AssetSearchResult]:
        """Create search result from Yahoo Finance search quote."""
        try:
            symbol = quote.get("symbol", "")
            if not symbol:
                return None

            # Get exchange information first
            exchange = quote.get("exchange")
            if not exchange:
                return None

            mapped_exchange = self.exchange_mapping.get(exchange)

            # Filter: Only support specific exchanges
            if mapped_exchange not in self.exchange_mapping.values():
                logger.debug(
                    f"Skipping unsupported exchange: {mapped_exchange} for symbol {symbol}"
                )
                return None

            # Convert to internal ticker format and normalize
            # Remove any suffixes that yfinance might include
            internal_ticker = self.convert_to_internal_ticker(
                symbol, mapped_exchange.value
            )

            # Validate the ticker format
            if not self.validate_ticker(internal_ticker):
                logger.debug(
                    f"Invalid ticker format after conversion: {internal_ticker}"
                )
                return None

            # Get asset type from quote type
            quote_type = quote.get("quoteType", "").upper()
            asset_type = self.quote_type_to_asset_type_mapping.get(
                quote_type, AssetType.STOCK
            )

            # Get country information
            country = "US"  # Default
            if mapped_exchange in [Exchange.SSE, Exchange.SZSE]:
                country = "CN"
            elif mapped_exchange == Exchange.HKEX:
                country = "HK"
            elif mapped_exchange == Exchange.CRYPTO:
                country = "US"

            # Get names in different languages
            long_name = quote.get("longname", quote.get("shortname", symbol))
            short_name = quote.get("shortname", symbol)

            names = {
                "en-US": long_name or short_name,
                "en-GB": long_name or short_name,
            }

            # Create search result
            search_result = AssetSearchResult(
                ticker=internal_ticker,
                asset_type=asset_type,
                names=names,
                exchange=mapped_exchange.value,
                country=country,
                currency=quote.get("currency", "USD"),
                market_status=MarketStatus.UNKNOWN,
            )

            # Save asset metadata to database for future lookups
            try:
                from ...server.db.repositories.asset_repository import (
                    get_asset_repository,
                )

                asset_repo = get_asset_repository()
                asset_repo.upsert_asset(
                    symbol=internal_ticker,
                    name=long_name or short_name,
                    asset_type=asset_type.value,
                    description=quote.get("longname"),
                    sector=quote.get("sector"),
                    asset_metadata={
                        "currency": quote.get("currency", "USD"),
                        "exchange_code": exchange,  # Original yfinance exchange code
                        "quote_type": quote_type,
                    },
                )
                logger.debug(f"Saved asset metadata for {internal_ticker}")
            except Exception as e:
                # Don't fail the search if database save fails
                logger.warning(
                    f"Failed to save asset metadata for {internal_ticker}: {e}"
                )

            return search_result

        except Exception as e:
            logger.error(f"Error creating search result from quote: {e}")
            return None

    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Get detailed asset information from Yahoo Finance."""
        try:
            source_ticker = self.convert_to_source_ticker(ticker)
            ticker_obj = yf.Ticker(source_ticker)
            info = ticker_obj.info

            if not info or "symbol" not in info:
                return None

            # Create localized names
            names = LocalizedName()
            long_name = info.get("longName", info.get("shortName", ticker))
            names.set_name("en-US", long_name)

            exchange = None
            if info.get("exchange"):
                exchange = self.exchange_mapping.get(info.get("exchange"))

            # Create market info
            market_info = MarketInfo(
                exchange=exchange.value if exchange else "UNKNOWN",
                country=info.get("country", "US"),
                currency=info.get("currency", "USD"),
                timezone=info.get("exchangeTimezoneName", "America/New_York"),
            )

            # Determine asset type
            asset_type = self.quote_type_to_asset_type_mapping.get(
                info.get("quoteType", "").upper(), AssetType.STOCK
            )

            # Create asset object
            asset = Asset(
                ticker=ticker,
                asset_type=asset_type,
                names=names,
                market_info=market_info,
            )

            # Set source mapping
            asset.set_source_ticker(self.source, source_ticker)

            # Add additional properties
            properties = {
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "website": info.get("website"),
                "business_summary": info.get("longBusinessSummary"),
            }

            # Filter out None values
            properties = {k: v for k, v in properties.items() if v is not None}
            asset.properties.update(properties)

            # Save asset metadata to database
            try:
                from ...server.db.repositories.asset_repository import (
                    get_asset_repository,
                )

                asset_repo = get_asset_repository()
                asset_repo.upsert_asset(
                    symbol=ticker,
                    name=long_name,
                    asset_type=asset_type.value,
                    description=info.get("longBusinessSummary"),
                    sector=info.get("sector"),
                    asset_metadata={
                        "currency": info.get("currency", "USD"),
                        "exchange_code": info.get("exchange"),
                        "quote_type": info.get("quoteType"),
                        "industry": info.get("industry"),
                        "market_cap": info.get("marketCap"),
                    },
                )
                logger.debug(f"Saved asset info for {ticker}")
            except Exception as e:
                # Don't fail the info fetch if database save fails
                logger.warning(f"Failed to save asset info for {ticker}: {e}")

            return asset

        except Exception as e:
            logger.error(f"Error fetching asset info for {ticker}: {e}")
            return None

    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time price data from Yahoo Finance."""
        try:
            source_ticker = self.convert_to_source_ticker(ticker)
            ticker_obj = yf.Ticker(source_ticker)

            # Get current data
            data = ticker_obj.history(period="1d", interval="1m")
            if data.empty:
                return None

            # Get the most recent data point
            latest = data.iloc[-1]
            info = ticker_obj.info

            # Calculate change
            current_price = Decimal(str(latest["Close"]))
            previous_close = Decimal(str(info.get("previousClose", latest["Close"])))
            change = current_price - previous_close
            change_percent = (
                (change / previous_close) * 100 if previous_close else Decimal("0")
            )

            return AssetPrice(
                ticker=ticker,
                price=current_price,
                currency=info.get("currency", "USD"),
                timestamp=latest.name.to_pydatetime(),
                volume=Decimal(str(latest["Volume"])) if latest["Volume"] else None,
                open_price=Decimal(str(latest["Open"])),
                high_price=Decimal(str(latest["High"])),
                low_price=Decimal(str(latest["Low"])),
                close_price=current_price,
                change=change,
                change_percent=change_percent,
                market_cap=Decimal(str(info["marketCap"]))
                if info.get("marketCap")
                else None,
                source=self.source,
            )

        except Exception as e:
            logger.error(f"Error fetching real-time price for {ticker}: {e}")
            return None

    def get_historical_prices(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[AssetPrice]:
        """Get historical price data from Yahoo Finance."""
        try:
            source_ticker = self.convert_to_source_ticker(ticker)
            ticker_obj = yf.Ticker(source_ticker)

            # Map interval to Yahoo Finance format
            interval_mapping = {
                f"1{Interval.MINUTE.value}": "1m",
                f"2{Interval.MINUTE.value}": "2m",
                f"5{Interval.MINUTE.value}": "5m",
                f"15{Interval.MINUTE.value}": "15m",
                f"30{Interval.MINUTE.value}": "30m",
                f"60{Interval.MINUTE.value}": "60m",
                f"90{Interval.MINUTE.value}": "90m",
                f"1{Interval.HOUR.value}": "1h",
                f"1{Interval.DAY.value}": "1d",
                f"5{Interval.DAY.value}": "5d",
                f"1{Interval.WEEK.value}": "1wk",
                f"1{Interval.MONTH.value}": "1mo",
                f"3{Interval.MONTH.value}": "3mo",
            }
            yf_interval = interval_mapping.get(interval, "1d")

            # Fetch historical data
            data = ticker_obj.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=yf_interval,
            )

            if data.empty:
                return []

            # Get currency from ticker info
            info = ticker_obj.info
            currency = info.get("currency", "USD")

            prices = []
            for timestamp, row in data.iterrows():
                # Calculate change from previous day
                change = None
                change_percent = None

                if len(prices) > 0:
                    prev_close = prices[-1].close_price
                    change = Decimal(str(row["Close"])) - prev_close
                    change_percent = (
                        (change / prev_close) * 100 if prev_close else Decimal("0")
                    )

                price = AssetPrice(
                    ticker=ticker,
                    price=Decimal(str(row["Close"])),
                    currency=currency,
                    timestamp=timestamp.to_pydatetime(),
                    volume=Decimal(str(row["Volume"])) if row["Volume"] else None,
                    open_price=Decimal(str(row["Open"])),
                    high_price=Decimal(str(row["High"])),
                    low_price=Decimal(str(row["Low"])),
                    close_price=Decimal(str(row["Close"])),
                    change=change,
                    change_percent=change_percent,
                    source=self.source,
                )
                prices.append(price)

            return prices

        except Exception as e:
            logger.error(f"Error fetching historical prices for {ticker}: {e}")
            return []

    def get_multiple_prices(
        self, tickers: List[str]
    ) -> Dict[str, Optional[AssetPrice]]:
        """Get real-time prices for multiple assets efficiently."""
        try:
            # Convert to source tickers
            source_tickers = [self.convert_to_source_ticker(t) for t in tickers]

            # Try minute data first, then fall back to daily data
            data = None
            for interval, period in [("1m", "1d"), ("1d", "5d")]:
                try:
                    data = yf.download(
                        source_tickers,
                        period=period,
                        interval=interval,
                        group_by="ticker",
                    )
                    if not data.empty:
                        break
                    logger.warning(f"No data with {interval} interval, trying next...")
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch data with {interval} interval: {e}"
                    )
                    continue

            if data is None or data.empty:
                logger.error("Failed to fetch data with all intervals")
                return {ticker: None for ticker in tickers}

            results = {}

            for i, ticker in enumerate(tickers):
                try:
                    source_ticker = source_tickers[i]

                    if len(source_tickers) == 1:
                        # Single ticker case
                        ticker_data = data
                    else:
                        # Multiple tickers case
                        ticker_data = data[source_ticker]

                    if ticker_data.empty:
                        results[ticker] = None
                        continue

                    # Get the most recent data point
                    latest = ticker_data.iloc[-1]

                    # Check if we have valid price data
                    import pandas as pd

                    if pd.isna(latest["Close"]) or latest["Close"] is None:
                        # Try to find the most recent valid data point
                        valid_data = ticker_data.dropna(subset=["Close"])
                        if valid_data.empty:
                            logger.warning(f"No valid price data found for {ticker}")
                            results[ticker] = None
                            continue
                        latest = valid_data.iloc[-1]

                    # Get additional info for currency and market cap
                    ticker_obj = yf.Ticker(source_ticker)
                    info = ticker_obj.info

                    # Safe Decimal conversion with NaN check
                    def safe_decimal(value, default=None):
                        if pd.isna(value) or value is None:
                            return default
                        try:
                            return Decimal(str(float(value)))
                        except (ValueError, TypeError, OverflowError):
                            return default

                    current_price = safe_decimal(latest["Close"])
                    if current_price is None:
                        logger.warning(f"Invalid price data for {ticker}")
                        results[ticker] = None
                        continue

                    previous_close = safe_decimal(
                        info.get("previousClose"), current_price
                    )
                    change = (
                        current_price - previous_close
                        if previous_close
                        else Decimal("0")
                    )
                    change_percent = (
                        (change / previous_close) * 100
                        if previous_close and previous_close != 0
                        else Decimal("0")
                    )

                    results[ticker] = AssetPrice(
                        ticker=ticker,
                        price=current_price,
                        currency=info.get("currency", "USD"),
                        timestamp=latest.name.to_pydatetime(),
                        volume=safe_decimal(latest["Volume"]),
                        open_price=safe_decimal(latest["Open"]),
                        high_price=safe_decimal(latest["High"]),
                        low_price=safe_decimal(latest["Low"]),
                        close_price=current_price,
                        change=change,
                        change_percent=change_percent,
                        market_cap=safe_decimal(info.get("marketCap")),
                        source=self.source,
                    )

                except Exception as e:
                    logger.error(f"Error processing ticker {ticker}: {e}")
                    results[ticker] = None

            return results

        except Exception as e:
            logger.error(f"Error fetching multiple prices: {e}")
            # Fallback to individual requests
            return super().get_multiple_prices(tickers)

    def get_capabilities(self) -> List[AdapterCapability]:
        """Get detailed capabilities of Yahoo Finance adapter.

        Yahoo Finance supports major US, Hong Kong, and Chinese exchanges.

        Returns:
            List of capabilities describing supported asset types and exchanges
        """
        return [
            AdapterCapability(
                asset_type=AssetType.STOCK,
                exchanges={
                    Exchange.NASDAQ,
                    Exchange.NYSE,
                    Exchange.AMEX,
                    Exchange.SSE,
                    Exchange.SZSE,
                    Exchange.HKEX,
                },
            ),
            AdapterCapability(
                asset_type=AssetType.ETF,
                exchanges={
                    Exchange.NASDAQ,
                    Exchange.NYSE,
                    Exchange.AMEX,
                    Exchange.SSE,
                    Exchange.SZSE,
                    Exchange.HKEX,
                },
            ),
            AdapterCapability(
                asset_type=AssetType.INDEX,
                exchanges={
                    Exchange.NASDAQ,
                    Exchange.NYSE,
                    Exchange.SSE,
                    Exchange.SZSE,
                    Exchange.HKEX,
                },
            ),
            AdapterCapability(
                asset_type=AssetType.CRYPTO,
                exchanges={Exchange.CRYPTO},
            ),
        ]

    def get_supported_asset_types(self) -> List[AssetType]:
        """Get asset types supported by Yahoo Finance."""
        return [
            AssetType.STOCK,
            AssetType.ETF,
            AssetType.INDEX,
            AssetType.CRYPTO,
        ]

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker is supported by Yahoo Finance.
        Args:
            ticker: Ticker in internal format, suppose the ticker has been validated before by the caller.
            (e.g., "NASDAQ:AAPL", "HKEX:00700", "CRYPTO:BTC")
        Returns:
            True if ticker is supported
        """

        if ":" not in ticker:
            return False

        exchange, symbol = ticker.split(":", 1)

        # Validate exchange
        if exchange not in [
            exchange.value for exchange in self.exchange_mapping.values()
        ]:
            return False

        return True

    def convert_to_source_ticker(self, internal_ticker: str) -> str:
        """Convert internal ticker to Yahoo Finance source ticker.

        For INDEX assets, adds ^ prefix (e.g., NASDAQ:IXIC -> ^IXIC).
        For other assets, applies exchange-specific suffix rules.
        """
        try:
            exchange, symbol = internal_ticker.split(":", 1)

            # Check asset type from database to determine if it's an index
            # Use lazy import to avoid circular dependency
            try:
                from ...server.db.repositories.asset_repository import (
                    get_asset_repository,
                )

                asset_repo = get_asset_repository()
                asset = asset_repo.get_asset_by_symbol(internal_ticker)

                if (
                    asset
                    and asset.asset_type == AssetType.INDEX.value
                    and exchange != Exchange.SSE.value
                    and exchange != Exchange.SZSE.value
                ):
                    # For indices, add ^ prefix
                    return f"^{symbol}"
            except (ImportError, Exception) as e:
                # If repository is not available, skip database lookup
                logger.debug(
                    f"Asset repository not available, skipping database lookup: {e}"
                )
                pass

            # For non-index assets, apply exchange-specific formatting
            if exchange == Exchange.HKEX.value:
                # Hong Kong stock codes need to be in proper format
                # e.g., "700" -> "0700.HK", "00700" -> "0700.HK", "1234" -> "1234.HK"
                if symbol.isdigit():
                    # Remove leading zeros first, then pad to 4 digits
                    clean_symbol = str(int(symbol))  # Remove leading zeros
                    padded_symbol = clean_symbol.zfill(4)  # Pad to 4 digits
                    return f"{padded_symbol}{self.yfinance_exchange_suffix_mapping.get(exchange, '')}"
                else:
                    # For non-numeric symbols, use as-is with .HK suffix
                    return f"{symbol}{self.yfinance_exchange_suffix_mapping.get(exchange, '')}"

            if exchange in self.yfinance_exchange_suffix_mapping.keys():
                return (
                    f"{symbol}{self.yfinance_exchange_suffix_mapping.get(exchange, '')}"
                )
            else:
                logger.warning(f"No mapping found for exchange: {exchange} in Yfinance")
                return symbol

        except ValueError:
            logger.error(f"Invalid ticker format: {internal_ticker}, Yfinance adapter.")
            return internal_ticker

    def convert_to_internal_ticker(
        self, source_ticker: str, default_exchange: Optional[str] = None
    ) -> str:
        """Convert Yahoo Finance source ticker to internal ticker.

        Simply removes yfinance-specific prefixes/suffixes and formats the symbol.
        Asset type determination (e.g., INDEX) is done during search/info retrieval.
        """
        # Special handling for indices from yfinance - remove ^ prefix
        if source_ticker.startswith("^"):
            symbol = source_ticker[1:]  # Remove ^ prefix
            # Use default exchange if provided, otherwise try to infer from symbol
            if default_exchange:
                return f"{default_exchange}:{symbol}"
            # Common index exchange inference (simplified)
            # Most major indices use their primary exchange
            return (
                f"{default_exchange}:{symbol}"
                if default_exchange
                else f"UNKNOWN:{symbol}"
            )

        # Special handling for crypto from yfinance - remove currency suffix
        if (
            "-USD" in source_ticker
            or "-CAD" in source_ticker
            or "-EUR" in source_ticker
        ):
            # Remove any currency suffix
            crypto_symbol = source_ticker.split("-")[0].upper()
            return f"CRYPTO:{crypto_symbol}"

        # Special handling for Hong Kong stocks from yfinance
        if ".HK" in source_ticker:
            symbol = source_ticker.replace(".HK", "")  # Remove .HK suffix
            # Keep as digits only, no leading zero removal for internal format
            if symbol.isdigit():
                # Pad to 5 digits for Hong Kong stocks
                symbol = symbol.zfill(5)
            return f"HKEX:{symbol}"

        # Special handling for Shanghai stocks from yfinance
        if ".SS" in source_ticker:
            symbol = source_ticker.replace(".SS", "")
            return f"SSE:{symbol}"

        # Special handling for Shenzhen stocks from yfinance
        if ".SZ" in source_ticker:
            symbol = source_ticker.replace(".SZ", "")
            return f"SZSE:{symbol}"

        # If no suffix found and default exchange provided
        if default_exchange:
            # For US stocks from yfinance, symbol is already clean
            return f"{default_exchange}:{source_ticker}"

        # For other assets without clear exchange mapping
        # Fallback to using the source as exchange
        return f"YFINANCE:{source_ticker}"
