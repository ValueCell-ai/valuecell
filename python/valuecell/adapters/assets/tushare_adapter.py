"""TuShare adapter for Chinese stock market data.

This adapter provides integration with TuShare API to fetch Chinese stock market data,
including A-shares, indices, and fundamental data.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

try:
    import tushare as ts
except ImportError:
    ts = None

from .base import AuthenticationError, BaseDataAdapter
from .types import (
    Asset,
    AssetPrice,
    AssetSearchQuery,
    AssetSearchResult,
    AssetType,
    DataSource,
    LocalizedName,
    MarketInfo,
    MarketStatus,
)

logger = logging.getLogger(__name__)


class TuShareAdapter(BaseDataAdapter):
    """TuShare data adapter for Chinese stock markets."""

    def __init__(self, api_key: str, **kwargs):
        """Initialize TuShare adapter.

        Args:
            api_key: TuShare API token
            **kwargs: Additional configuration parameters
        """
        super().__init__(DataSource.TUSHARE, api_key, **kwargs)

        if ts is None:
            raise ImportError(
                "tushare library is required. Install with: pip install tushare"
            )

        if not api_key:
            raise AuthenticationError("TuShare API key is required")

    def _initialize(self) -> None:
        """Initialize TuShare adapter configuration."""
        try:
            # Set TuShare token
            ts.set_token(self.api_key)
            self.pro = ts.pro_api()

            # Test connection
            self.pro.query(
                "stock_basic",
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,area,industry,list_date",
            )

            logger.info("TuShare adapter initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize TuShare adapter: {e}")
            raise AuthenticationError(f"TuShare initialization failed: {e}")

    def search_assets(self, query: AssetSearchQuery) -> List[AssetSearchResult]:
        """Search for assets using TuShare stock basic info."""
        try:
            results = []
            search_term = query.query.strip()

            # Get all stock basic info
            df = self.pro.query(
                "stock_basic",
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,area,industry,market,exchange,list_date",
            )

            if df.empty:
                return results

            # Search by symbol or name
            mask = (
                df["symbol"].str.contains(search_term, case=False, na=False)
                | df["name"].str.contains(search_term, case=False, na=False)
                | df["ts_code"].str.contains(search_term, case=False, na=False)
            )

            matched_stocks = df[mask]

            for _, row in matched_stocks.iterrows():
                try:
                    # Convert TuShare code to internal format
                    ts_code = row["ts_code"]  # Format: 000001.SZ
                    internal_ticker = self.convert_to_internal_ticker(ts_code)

                    # Determine exchange
                    exchange_suffix = ts_code.split(".")[1]
                    exchange_mapping = {"SH": "SSE", "SZ": "SZSE"}
                    exchange = exchange_mapping.get(exchange_suffix, exchange_suffix)

                    # Create localized names
                    names = {
                        "zh-Hans": row["name"],
                        "en-US": row["name"],  # TuShare primarily has Chinese names
                    }

                    result = AssetSearchResult(
                        ticker=internal_ticker,
                        asset_type=AssetType.STOCK,
                        names=names,
                        exchange=exchange,
                        country="CN",
                        currency="CNY",
                        market_status=MarketStatus.UNKNOWN,
                        relevance_score=1.0,
                    )

                    results.append(result)

                except Exception as e:
                    logger.warning(
                        f"Error processing search result for {row.get('ts_code')}: {e}"
                    )
                    continue

            # Apply filters
            if query.asset_types:
                results = [r for r in results if r.asset_type in query.asset_types]

            if query.exchanges:
                results = [r for r in results if r.exchange in query.exchanges]

            if query.countries:
                results = [r for r in results if r.country in query.countries]

            return results[: query.limit]

        except Exception as e:
            logger.error(f"Error searching assets: {e}")
            return []

    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Get detailed asset information from TuShare."""
        try:
            source_ticker = self.convert_to_source_ticker(ticker)

            # Get basic stock info
            df_basic = self.pro.query(
                "stock_basic",
                ts_code=source_ticker,
                fields="ts_code,symbol,name,area,industry,market,exchange,curr_type,list_date,delist_date,is_hs",
            )

            if df_basic.empty:
                return None

            stock_info = df_basic.iloc[0]

            # Create localized names
            names = LocalizedName()
            names.set_name("zh-Hans", stock_info["name"])
            names.set_name(
                "en-US", stock_info["name"]
            )  # Could be enhanced with translation

            # Determine exchange
            exchange_suffix = source_ticker.split(".")[1]
            exchange_mapping = {"SH": "SSE", "SZ": "SZSE"}
            exchange = exchange_mapping.get(exchange_suffix, exchange_suffix)

            # Create market info
            market_info = MarketInfo(
                exchange=exchange,
                country="CN",
                currency=stock_info.get("curr_type", "CNY"),
                timezone="Asia/Shanghai",
            )

            # Create asset
            asset = Asset(
                ticker=ticker,
                asset_type=AssetType.STOCK,
                names=names,
                market_info=market_info,
            )

            # Set source mapping
            asset.set_source_ticker(self.source, source_ticker)

            # Add additional properties
            properties = {
                "area": stock_info.get("area"),
                "industry": stock_info.get("industry"),
                "market": stock_info.get("market"),
                "list_date": stock_info.get("list_date"),
                "is_hs": stock_info.get("is_hs"),  # Hong Kong-Shanghai Stock Connect
            }

            # Get company info if available
            try:
                df_company = self.pro.query(
                    "stock_company",
                    ts_code=source_ticker,
                    fields="ts_code,chairman,manager,secretary,reg_capital,setup_date,province,city,introduction,website,email,office,employees,main_business,business_scope",
                )

                if not df_company.empty:
                    company_info = df_company.iloc[0]
                    properties.update(
                        {
                            "chairman": company_info.get("chairman"),
                            "manager": company_info.get("manager"),
                            "reg_capital": company_info.get("reg_capital"),
                            "setup_date": company_info.get("setup_date"),
                            "province": company_info.get("province"),
                            "city": company_info.get("city"),
                            "introduction": company_info.get("introduction"),
                            "website": company_info.get("website"),
                            "employees": company_info.get("employees"),
                            "main_business": company_info.get("main_business"),
                        }
                    )
            except Exception as e:
                logger.warning(f"Could not fetch company info for {source_ticker}: {e}")

            # Filter out None values
            properties = {k: v for k, v in properties.items() if v is not None}
            asset.properties.update(properties)

            return asset

        except Exception as e:
            logger.error(f"Error fetching asset info for {ticker}: {e}")
            return None

    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time price data from TuShare."""
        try:
            source_ticker = self.convert_to_source_ticker(ticker)

            # Get real-time quotes
            df = self.pro.query(
                "daily",
                ts_code=source_ticker,
                trade_date="",
                start_date="",
                end_date="",
            )

            if df.empty:
                return None

            # Get the most recent trading day
            latest_data = df.iloc[0]  # TuShare returns data in descending order

            # Convert to AssetPrice
            current_price = Decimal(str(latest_data["close"]))
            open_price = Decimal(str(latest_data["open"]))

            # Calculate change
            change = (
                Decimal(str(latest_data["change"]))
                if latest_data["change"]
                else Decimal("0")
            )
            change_percent = (
                Decimal(str(latest_data["pct_chg"]))
                if latest_data["pct_chg"]
                else Decimal("0")
            )

            # Parse trade date
            trade_date_str = str(latest_data["trade_date"])
            trade_date = datetime.strptime(trade_date_str, "%Y%m%d")

            return AssetPrice(
                ticker=ticker,
                price=current_price,
                currency="CNY",
                timestamp=trade_date,
                volume=Decimal(str(latest_data["vol"])) if latest_data["vol"] else None,
                open_price=open_price,
                high_price=Decimal(str(latest_data["high"])),
                low_price=Decimal(str(latest_data["low"])),
                close_price=current_price,
                change=change,
                change_percent=change_percent,
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
        """Get historical price data from TuShare."""
        try:
            source_ticker = self.convert_to_source_ticker(ticker)

            # TuShare uses YYYYMMDD format
            start_date_str = start_date.strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")

            # TuShare primarily supports daily data
            if interval not in ["1d", "daily"]:
                logger.warning(
                    f"TuShare primarily supports daily data. Requested interval: {interval}"
                )

            # Get daily price data
            df = self.pro.query(
                "daily",
                ts_code=source_ticker,
                start_date=start_date_str,
                end_date=end_date_str,
            )

            if df.empty:
                return []

            # Sort by trade_date ascending
            df = df.sort_values("trade_date")

            prices = []
            for _, row in df.iterrows():
                # Parse trade date
                trade_date_str = str(row["trade_date"])
                trade_date = datetime.strptime(trade_date_str, "%Y%m%d")

                # Calculate change and change_percent
                change = Decimal(str(row["change"])) if row["change"] else Decimal("0")
                change_percent = (
                    Decimal(str(row["pct_chg"])) if row["pct_chg"] else Decimal("0")
                )

                price = AssetPrice(
                    ticker=ticker,
                    price=Decimal(str(row["close"])),
                    currency="CNY",
                    timestamp=trade_date,
                    volume=Decimal(str(row["vol"])) if row["vol"] else None,
                    open_price=Decimal(str(row["open"])),
                    high_price=Decimal(str(row["high"])),
                    low_price=Decimal(str(row["low"])),
                    close_price=Decimal(str(row["close"])),
                    change=change,
                    change_percent=change_percent,
                    source=self.source,
                )
                prices.append(price)

            return prices

        except Exception as e:
            logger.error(f"Error fetching historical prices for {ticker}: {e}")
            return []

    def get_supported_asset_types(self) -> List[AssetType]:
        """Get asset types supported by TuShare."""
        return [
            AssetType.STOCK,
            AssetType.INDEX,
            AssetType.ETF,
            AssetType.BOND,
        ]

    def _perform_health_check(self) -> Any:
        """Perform health check by fetching stock basic info."""
        try:
            # Test with a simple query
            df = self.pro.query(
                "stock_basic",
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name",
            )

            if not df.empty:
                return {
                    "status": "ok",
                    "stocks_count": len(df),
                    "sample_stock": df.iloc[0]["ts_code"] if len(df) > 0 else None,
                }
            else:
                return {"status": "error", "message": "No data received"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker is supported by TuShare (Chinese markets only)."""
        try:
            exchange, symbol = ticker.split(":", 1)

            # TuShare supports Chinese exchanges
            supported_exchanges = ["SSE", "SZSE"]

            return exchange in supported_exchanges

        except ValueError:
            return False

    def get_market_calendar(
        self, start_date: datetime, end_date: datetime
    ) -> List[datetime]:
        """Get trading calendar for Chinese markets."""
        try:
            start_date_str = start_date.strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")

            df = self.pro.query(
                "trade_cal",
                exchange="SSE",
                start_date=start_date_str,
                end_date=end_date_str,
                is_open="1",
            )

            if df.empty:
                return []

            trading_days = []
            for _, row in df.iterrows():
                trade_date = datetime.strptime(str(row["cal_date"]), "%Y%m%d")
                trading_days.append(trade_date)

            return trading_days

        except Exception as e:
            logger.error(f"Error fetching market calendar: {e}")
            return []

    def get_stock_financials(
        self, ticker: str, year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get financial data for a stock."""
        try:
            source_ticker = self.convert_to_source_ticker(ticker)

            # Get income statement
            params = {"ts_code": source_ticker}
            if year:
                params["period"] = f"{year}1231"  # Year-end

            financials = {}

            # Income statement
            try:
                df_income = self.pro.query("income", **params)
                if not df_income.empty:
                    financials["income_statement"] = df_income.to_dict("records")
            except Exception as e:
                logger.warning(f"Could not fetch income statement: {e}")

            # Balance sheet
            try:
                df_balance = self.pro.query("balancesheet", **params)
                if not df_balance.empty:
                    financials["balance_sheet"] = df_balance.to_dict("records")
            except Exception as e:
                logger.warning(f"Could not fetch balance sheet: {e}")

            # Cash flow
            try:
                df_cashflow = self.pro.query("cashflow", **params)
                if not df_cashflow.empty:
                    financials["cash_flow"] = df_cashflow.to_dict("records")
            except Exception as e:
                logger.warning(f"Could not fetch cash flow: {e}")

            return financials

        except Exception as e:
            logger.error(f"Error fetching financials for {ticker}: {e}")
            return {}

    def is_market_open(self, exchange: str) -> bool:
        """Check if Chinese market is currently open."""
        if exchange not in ["SSE", "SZSE"]:
            return False

        # Chinese market hours: 9:30-11:30, 13:00-15:00 (GMT+8)
        now = datetime.utcnow()
        # Convert to Beijing time (UTC+8)
        beijing_time = now.replace(tzinfo=None) + timedelta(hours=8)

        # Check if it's a weekday
        if beijing_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        # Check trading hours
        current_time = beijing_time.time()
        morning_open = datetime.strptime("09:30", "%H:%M").time()
        morning_close = datetime.strptime("11:30", "%H:%M").time()
        afternoon_open = datetime.strptime("13:00", "%H:%M").time()
        afternoon_close = datetime.strptime("15:00", "%H:%M").time()

        return (
            morning_open <= current_time <= morning_close
            or afternoon_open <= current_time <= afternoon_close
        )
