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
            "NMS": "NASDAQ",
            "NYQ": "NYSE",
            "ASE": "AMEX",
            "SHH": "SSE",
            "SHZ": "SZSE",
            "HKG": "HKEX",
            "PCX": "NYSE",
            "CCC": "CRYPTO",
            # "TYO": "TSE",
            # "LSE": "LSE",
            # "PAR": "EURONEXT",
            # "FRA": "XETRA",
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
            exchange = quote.get("exchange", "UNKNOWN")

            mapped_exchange = self.exchange_mapping.get(exchange, exchange)

            # Filter: Only support specific exchanges
            supported_exchanges = ["NASDAQ", "NYSE", "SSE", "SZSE", "HKEX", "CRYPTO"]
            if mapped_exchange not in supported_exchanges:
                logger.debug(
                    f"Skipping unsupported exchange: {mapped_exchange} for symbol {symbol}"
                )
                return None

            # Convert to internal ticker format and normalize
            # Remove any suffixes that yfinance might include
            internal_ticker = self.convert_to_internal_ticker(symbol, mapped_exchange)

            # Validate the ticker format
            if not self._is_valid_internal_ticker(internal_ticker):
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
            if mapped_exchange in ["SSE", "SZSE"]:
                country = "CN"
            elif mapped_exchange == "HKEX":
                country = "HK"
            elif mapped_exchange == "CRYPTO":
                country = "US"

            # Get names in different languages
            long_name = quote.get("longname", quote.get("shortname", symbol))
            short_name = quote.get("shortname", symbol)

            names = {
                "en-US": long_name or short_name,
                "en-GB": long_name or short_name,
            }

            # Calculate relevance score based on match quality
            relevance_score = self._calculate_search_relevance(
                quote, symbol, long_name or short_name
            )

            return AssetSearchResult(
                ticker=internal_ticker,
                asset_type=asset_type,
                names=names,
                exchange=mapped_exchange,
                country=country,
                currency=quote.get("currency", "USD"),
                market_status=MarketStatus.UNKNOWN,
                relevance_score=relevance_score,
            )

        except Exception as e:
            logger.error(f"Error creating search result from quote: {e}")
            return None

    def _fallback_ticker_search(
        self, search_term: str, query: AssetSearchQuery
    ) -> List[AssetSearchResult]:
        """Fallback search using direct ticker lookup with common suffixes."""
        results = []

        # Try direct ticker lookup first
        try:
            ticker_obj = yf.Ticker(search_term)
            info = ticker_obj.info

            if info and "symbol" in info and info.get("symbol"):
                result = self._create_search_result_from_info(info)
                if result:
                    results.append(result)
        except Exception as e:
            logger.debug(f"Direct ticker lookup failed for {search_term}: {e}")

        # Try with common suffixes for international markets
        if not results:
            suffixes = [".SS", ".SZ", ".HK", ".T", ".L", ".PA", ".DE", ".TO", ".AX"]
            for suffix in suffixes:
                try:
                    test_ticker = f"{search_term}{suffix}"
                    ticker_obj = yf.Ticker(test_ticker)
                    info = ticker_obj.info

                    if info and "symbol" in info and info.get("symbol"):
                        result = self._create_search_result_from_info(
                            info, query.language
                        )
                        if result:
                            results.append(result)
                            break  # Found one, stop searching
                except Exception:
                    continue

        return results

    def _create_search_result_from_info(
        self, info: Dict
    ) -> Optional[AssetSearchResult]:
        """Create search result from Yahoo Finance info dictionary."""
        try:
            symbol = info.get("symbol", "")
            if not symbol:
                return None

            # Convert to internal ticker format
            internal_ticker = self.convert_to_internal_ticker(symbol)

            # Get asset type
            asset_type = self.quote_type_to_asset_type_mapping.get(
                info.get("quoteType", "").upper(), AssetType.STOCK
            )

            # Get exchange and country
            exchange = info.get("exchange", "UNKNOWN")
            country = info.get("country", "US")  # Default to US

            # Get names in different languages
            names = {
                "en-US": info.get("longName", info.get("shortName", symbol)),
            }

            # For Chinese markets, try to get Chinese name
            if exchange in ["SSE", "SZSE"]:
                # This would require additional API calls or data sources
                # For now, use English name as fallback
                pass

            return AssetSearchResult(
                ticker=internal_ticker,
                asset_type=asset_type,
                names=names,
                exchange=exchange,
                country=country,
                currency=info.get("currency", "USD"),
                market_status=MarketStatus.UNKNOWN,  # Would need real-time data
                relevance_score=1.0,  # Simple relevance scoring
            )

        except Exception as e:
            logger.error(f"Error creating search result: {e}")
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

            # Create market info
            market_info = MarketInfo(
                exchange=info.get("exchange", "UNKNOWN"),
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
                f"1{Interval.MINUTE}": "1m",
                f"2{Interval.MINUTE}": "2m",
                f"5{Interval.MINUTE}": "5m",
                f"15{Interval.MINUTE}": "15m",
                f"30{Interval.MINUTE}": "30m",
                f"60{Interval.MINUTE}": "60m",
                f"90{Interval.MINUTE}": "90m",
                f"1{Interval.HOUR}": "1h",
                f"1{Interval.DAY}": "1d",
                f"5{Interval.DAY}": "5d",
                f"1{Interval.WEEK}": "1wk",
                f"1{Interval.MONTH}": "1mo",
                f"3{Interval.MONTH}": "3mo",
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
        supported_exchanges = ["NASDAQ", "NYSE", "SSE", "SZSE", "HKEX", "CRYPTO"]
        if exchange not in supported_exchanges:
            return False

        return True

    def convert_to_source_ticker(self, internal_ticker: str) -> str:
        """Convert internal ticker to Yahoo Finance source ticker."""
        try:
            exchange, symbol = internal_ticker.split(":", 1)
            exchange_mapping = {
                "NASDAQ": "",  # NASDAQ stocks don't need suffix in yfinance
                "NYSE": "",  # NYSE stocks don't need suffix in yfinance
                "SSE": ".SS",  # Shanghai Stock Exchange
                "SZSE": ".SZ",  # Shenzhen Stock Exchange
                "HKEX": ".HK",  # Hong Kong Exchange
                "TSE": ".T",  # Tokyo Stock Exchange
                "CRYPTO": "-USD",  # Crypto
            }

            if exchange == "HKEX":
                # Hong Kong stock codes need to be in proper format
                # e.g., "700" -> "0700.HK", "00700" -> "0700.HK", "1234" -> "1234.HK"
                if symbol.isdigit():
                    # Remove leading zeros first, then pad to 4 digits
                    clean_symbol = str(int(symbol))  # Remove leading zeros
                    padded_symbol = clean_symbol.zfill(4)  # Pad to 4 digits
                    return f"{padded_symbol}{exchange_mapping.get(exchange, '')}"
                else:
                    # For non-numeric symbols, use as-is with .HK suffix
                    return f"{symbol}{exchange_mapping.get(exchange, '')}"

            if exchange in exchange_mapping.keys():
                return f"{symbol}{exchange_mapping.get(exchange, '')}"
            else:
                logger.warning("No mapping found for data source: Yfinance")
                return symbol

        except ValueError:
            logger.error(f"Invalid ticker format: {internal_ticker}, Yfinance adapter.")
            return internal_ticker

    def convert_to_internal_ticker(
        self, source_ticker: str, default_exchange: Optional[str] = None
    ) -> str:
        """Convert Yahoo Finance source ticker to internal ticker."""

        # Special handling for indices from yfinance (reverse ^ prefix mapping)
        if source_ticker.startswith("^"):
            index_reverse_mapping = {
                # US Indices
                "^IXIC": "NASDAQ:IXIC",  # NASDAQ Composite
                "^DJI": "NYSE:DJI",  # Dow Jones Industrial Average
                "^GSPC": "NYSE:GSPC",  # S&P 500
                "^NDX": "NASDAQ:NDX",  # NASDAQ 100
                # Hong Kong Indices
                "^HSI": "HKEX:HSI",  # Hang Seng Index
                "^HSCEI": "HKEX:HSCEI",  # Hang Seng China Enterprises Index
                # European Indices
                "^FTSE": "LSE:FTSE",  # FTSE 100
                "^FCHI": "EURONEXT:FCHI",  # CAC 40
                "^GDAXI": "XETRA:GDAXI",  # DAX
            }

            if source_ticker in index_reverse_mapping:
                return index_reverse_mapping[source_ticker]

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
