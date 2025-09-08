"""AKShare adapter for Chinese financial market data.

This adapter provides integration with AKShare library to fetch comprehensive
Chinese financial market data including stocks, funds, bonds, and economic indicators.
"""

import logging
from typing import List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd

try:
    import akshare as ak
except ImportError:
    ak = None

from .base import BaseDataAdapter
from .types import (
    Asset,
    AssetPrice,
    AssetSearchResult,
    AssetSearchQuery,
    DataSource,
    AssetType,
    MarketInfo,
    LocalizedName,
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
        self.timeout = self.config.get("timeout", 30)

        # Asset type mapping for AKShare
        self.asset_type_mapping = {
            "stock": AssetType.STOCK,
            "fund": AssetType.ETF,
            # "bond": AssetType.BOND,
            "index": AssetType.INDEX,
            "crypto": AssetType.CRYPTO,
        }

        # Exchange mapping for AKShare
        self.exchange_mapping = {
            "SH": "SSE",  # Shanghai Stock Exchange
            "SZ": "SZSE",  # Shenzhen Stock Exchange
            "BJ": "BSE",  # Beijing Stock Exchange
        }

        logger.info("AKShare adapter initialized")

    def search_assets(self, query: AssetSearchQuery) -> List[AssetSearchResult]:
        """Search for assets using AKShare stock info."""
        try:
            results = []
            search_term = query.query.strip()

            # Get stock basic info from AKShare
            try:
                # Get A-share stock list
                df_stocks = ak.stock_zh_a_spot_em()

                if df_stocks is None or df_stocks.empty:
                    return results

                # Search by code or name
                mask = df_stocks["代码"].astype(str).str.contains(
                    search_term, case=False, na=False
                ) | df_stocks["名称"].str.contains(search_term, case=False, na=False)

                matched_stocks = df_stocks[mask].head(query.limit)

                for _, row in matched_stocks.iterrows():
                    try:
                        # Parse stock code and exchange
                        stock_code = str(row["代码"])
                        stock_name = row["名称"]

                        # Determine exchange from code
                        if stock_code.startswith("6"):
                            exchange = "SSE"  # Shanghai
                            internal_ticker = f"SSE:{stock_code}"
                        elif stock_code.startswith(("0", "3")):
                            exchange = "SZSE"  # Shenzhen
                            internal_ticker = f"SZSE:{stock_code}"
                        elif stock_code.startswith("8"):
                            exchange = "BSE"  # Beijing
                            internal_ticker = f"BSE:{stock_code}"
                        else:
                            continue  # Skip unknown exchanges

                        # Create localized names
                        names = {
                            "zh-Hans": stock_name,
                            "zh-Hant": stock_name,
                            "en-US": stock_name,  # AKShare primarily has Chinese names
                        }

                        result = AssetSearchResult(
                            ticker=internal_ticker,
                            asset_type=AssetType.STOCK,
                            names=names,
                            exchange=exchange,
                            country="CN",
                            currency="CNY",
                            market_status=MarketStatus.UNKNOWN,
                            relevance_score=self._calculate_relevance(
                                search_term, stock_code, stock_name
                            ),
                        )

                        results.append(result)

                    except Exception as e:
                        logger.warning(
                            f"Error processing search result for {row.get('代码')}: {e}"
                        )
                        continue

            except Exception as e:
                logger.error(f"Error fetching stock list from AKShare: {e}")

            # Try to search funds if no stock results or if fund type is requested
            if not results or (
                query.asset_types and AssetType.ETF in query.asset_types
            ):
                try:
                    df_funds = ak.fund_etf_spot_em()

                    if df_funds is not None and not df_funds.empty:
                        # Search funds
                        fund_mask = df_funds["代码"].astype(str).str.contains(
                            search_term, case=False, na=False
                        ) | df_funds["名称"].str.contains(
                            search_term, case=False, na=False
                        )

                        matched_funds = df_funds[fund_mask].head(
                            max(5, query.limit - len(results))
                        )

                        for _, row in matched_funds.iterrows():
                            try:
                                fund_code = str(row["代码"])
                                fund_name = row["名称"]

                                # Determine exchange for funds
                                if fund_code.startswith("5"):
                                    exchange = "SSE"
                                    internal_ticker = f"SSE:{fund_code}"
                                else:
                                    exchange = "SZSE"
                                    internal_ticker = f"SZSE:{fund_code}"

                                names = {
                                    "zh-Hans": fund_name,
                                    "zh-Hant": fund_name,
                                    "en-US": fund_name,
                                }

                                result = AssetSearchResult(
                                    ticker=internal_ticker,
                                    asset_type=AssetType.ETF,
                                    names=names,
                                    exchange=exchange,
                                    country="CN",
                                    currency="CNY",
                                    market_status=MarketStatus.UNKNOWN,
                                    relevance_score=self._calculate_relevance(
                                        search_term, fund_code, fund_name
                                    ),
                                )

                                results.append(result)

                            except Exception as e:
                                logger.warning(
                                    f"Error processing fund result for {row.get('代码')}: {e}"
                                )
                                continue

                except Exception as e:
                    logger.warning(f"Error fetching fund list from AKShare: {e}")

            # Apply filters
            if query.asset_types:
                results = [r for r in results if r.asset_type in query.asset_types]

            if query.exchanges:
                results = [r for r in results if r.exchange in query.exchanges]

            if query.countries:
                results = [r for r in results if r.country in query.countries]

            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)

            return results[: query.limit]

        except Exception as e:
            logger.error(f"Error searching assets: {e}")
            return []

    def _calculate_relevance(self, search_term: str, code: str, name: str) -> float:
        """Calculate relevance score for search results."""
        search_term_lower = search_term.lower()
        code_lower = code.lower()
        name_lower = name.lower()

        # Exact matches get highest score
        if search_term_lower == code_lower or search_term_lower == name_lower:
            return 2.0

        # Code starts with search term
        if code_lower.startswith(search_term_lower):
            return 1.8

        # Name starts with search term
        if name_lower.startswith(search_term_lower):
            return 1.6

        # Code contains search term
        if search_term_lower in code_lower:
            return 1.4

        # Name contains search term
        if search_term_lower in name_lower:
            return 1.2

        return 1.0

    def get_asset_info(self, ticker: str) -> Optional[Asset]:
        """Get detailed asset information from AKShare."""
        try:
            exchange, symbol = ticker.split(":")

            # Get stock individual info
            try:
                df_info = ak.stock_individual_info_em(symbol=symbol)

                if df_info is None or df_info.empty:
                    return None

                # Convert DataFrame to dict for easier access
                info_dict = {}
                for _, row in df_info.iterrows():
                    info_dict[row["item"]] = row["value"]

                # Create localized names
                names = LocalizedName()
                stock_name = info_dict.get("股票名称", symbol)
                names.set_name("zh-Hans", stock_name)
                names.set_name("zh-Hant", stock_name)
                names.set_name("en-US", stock_name)

                # Create market info
                market_info = MarketInfo(
                    exchange=exchange,
                    country="CN",
                    currency="CNY",
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
                asset.set_source_ticker(self.source, symbol)

                # Add additional properties from AKShare
                properties = {
                    "stock_name": info_dict.get("股票名称"),
                    "stock_code": info_dict.get("股票代码"),
                    "listing_date": info_dict.get("上市时间"),
                    "total_share_capital": info_dict.get("总股本"),
                    "circulating_share_capital": info_dict.get("流通股本"),
                    "industry": info_dict.get("所处行业"),
                    "main_business": info_dict.get("主营业务"),
                    "business_scope": info_dict.get("经营范围"),
                    "chairman": info_dict.get("董事长"),
                    "general_manager": info_dict.get("总经理"),
                    "secretary": info_dict.get("董秘"),
                    "registered_capital": info_dict.get("注册资本"),
                    "employees": info_dict.get("员工人数"),
                    "province": info_dict.get("所属省份"),
                    "city": info_dict.get("所属城市"),
                    "office_address": info_dict.get("办公地址"),
                    "company_website": info_dict.get("公司网址"),
                    "email": info_dict.get("电子邮箱"),
                    "main_business_income": info_dict.get("主营业务收入"),
                    "net_profit": info_dict.get("净利润"),
                }

                # Filter out None values
                properties = {k: v for k, v in properties.items() if v is not None}
                asset.properties.update(properties)

                return asset

            except Exception as e:
                logger.error(f"Error fetching individual stock info for {symbol}: {e}")
                return None

        except Exception as e:
            logger.error(f"Error getting asset info for {ticker}: {e}")
            return None

    def get_real_time_price(self, ticker: str) -> Optional[AssetPrice]:
        """Get real-time price data from AKShare."""
        try:
            exchange, symbol = ticker.split(":")

            # Get real-time stock data
            try:
                df_realtime = ak.stock_zh_a_spot_em()

                if df_realtime is None or df_realtime.empty:
                    return None

                # Find the specific stock
                stock_data = df_realtime[df_realtime["代码"] == symbol]

                if stock_data.empty:
                    return None

                stock_info = stock_data.iloc[0]

                # Extract price information
                current_price = Decimal(str(stock_info["最新价"]))
                open_price = Decimal(str(stock_info["今开"]))
                high_price = Decimal(str(stock_info["最高"]))
                low_price = Decimal(str(stock_info["最低"]))
                pre_close = Decimal(str(stock_info["昨收"]))

                # Calculate change
                change = current_price - pre_close
                change_percent = (
                    (change / pre_close) * 100 if pre_close else Decimal("0")
                )

                # Get volume and market cap
                volume = (
                    Decimal(str(stock_info["成交量"])) if stock_info["成交量"] else None
                )
                market_cap = (
                    Decimal(str(stock_info["总市值"])) if stock_info["总市值"] else None
                )

                return AssetPrice(
                    ticker=ticker,
                    price=current_price,
                    currency="CNY",
                    timestamp=datetime.now(),  # AKShare doesn't provide exact timestamp
                    volume=volume,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=current_price,
                    change=change,
                    change_percent=change_percent,
                    market_cap=market_cap,
                    source=self.source,
                )

            except Exception as e:
                logger.error(f"Error fetching real-time price for {symbol}: {e}")
                return None

        except Exception as e:
            logger.error(f"Error getting real-time price for {ticker}: {e}")
            return None

    def get_historical_prices(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    ) -> List[AssetPrice]:
        """Get historical price data from AKShare."""
        try:
            exchange, symbol = ticker.split(":")

            # Format dates for AKShare
            start_date_str = start_date.strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")

            # Map interval to AKShare format
            if interval in ["1d", "daily"]:
                period = "daily"
            else:
                logger.warning(
                    f"AKShare primarily supports daily data. Requested interval: {interval}"
                )
                period = "daily"

            # Get historical data
            try:
                df_hist = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=period,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    adjust="",  # No adjustment
                )

                if df_hist is None or df_hist.empty:
                    return []

                prices = []
                for _, row in df_hist.iterrows():
                    # Parse date
                    trade_date = pd.to_datetime(row["日期"]).to_pydatetime()

                    # Extract price data
                    open_price = Decimal(str(row["开盘"]))
                    high_price = Decimal(str(row["最高"]))
                    low_price = Decimal(str(row["最低"]))
                    close_price = Decimal(str(row["收盘"]))
                    volume = Decimal(str(row["成交量"])) if row["成交量"] else None

                    # Calculate change from previous day
                    change = None
                    change_percent = None
                    if len(prices) > 0:
                        prev_close = prices[-1].close_price
                        change = close_price - prev_close
                        change_percent = (
                            (change / prev_close) * 100 if prev_close else Decimal("0")
                        )

                    price = AssetPrice(
                        ticker=ticker,
                        price=close_price,
                        currency="CNY",
                        timestamp=trade_date,
                        volume=volume,
                        open_price=open_price,
                        high_price=high_price,
                        low_price=low_price,
                        close_price=close_price,
                        change=change,
                        change_percent=change_percent,
                        source=self.source,
                    )
                    prices.append(price)

                return prices

            except Exception as e:
                logger.error(f"Error fetching historical data for {symbol}: {e}")
                return []

        except Exception as e:
            logger.error(f"Error getting historical prices for {ticker}: {e}")
            return []

    def get_supported_asset_types(self) -> List[AssetType]:
        """Get asset types supported by AKShare."""
        return [
            AssetType.STOCK,
            AssetType.ETF,
            # AssetType.BOND,
            AssetType.INDEX,
        ]

    def _perform_health_check(self) -> Any:
        """Perform health check by fetching stock list."""
        try:
            # Test with a simple query to get stock list
            df = ak.stock_zh_a_spot_em()

            if df is not None and not df.empty:
                return {
                    "status": "ok",
                    "stocks_count": len(df),
                    "sample_stock": df.iloc[0]["代码"] if len(df) > 0 else None,
                }
            else:
                return {"status": "error", "message": "No data received"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def validate_ticker(self, ticker: str) -> bool:
        """Validate if ticker is supported by AKShare (Chinese markets only)."""
        try:
            exchange, symbol = ticker.split(":", 1)

            # AKShare supports Chinese exchanges
            supported_exchanges = ["SSE", "SZSE", "BSE"]

            if exchange not in supported_exchanges:
                return False

            # Validate symbol format (6 digits for Chinese stocks)
            if not symbol.isdigit() or len(symbol) != 6:
                return False

            return True

        except ValueError:
            return False

    def get_market_calendar(
        self, start_date: datetime, end_date: datetime
    ) -> List[datetime]:
        """Get trading calendar for Chinese markets."""
        try:
            # Get trading calendar from AKShare
            df_calendar = ak.tool_trade_date_hist_sina()

            if df_calendar is None or df_calendar.empty:
                return []

            # Convert to datetime and filter by date range
            df_calendar["trade_date"] = pd.to_datetime(df_calendar["trade_date"])

            mask = (df_calendar["trade_date"] >= start_date) & (
                df_calendar["trade_date"] <= end_date
            )
            filtered_dates = df_calendar[mask]["trade_date"]

            return [date.to_pydatetime() for date in filtered_dates]

        except Exception as e:
            logger.error(f"Error fetching market calendar: {e}")
            return []

    def get_sector_stocks(self, sector: str) -> List[AssetSearchResult]:
        """Get stocks from a specific sector."""
        try:
            # Get sector classification
            df_industry = ak.stock_board_industry_name_em()

            if df_industry is None or df_industry.empty:
                return []

            # Find matching sectors
            sector_matches = df_industry[
                df_industry["板块名称"].str.contains(sector, na=False)
            ]

            results = []
            for _, sector_row in sector_matches.iterrows():
                try:
                    # Get stocks in this sector
                    sector_name = sector_row["板块名称"]
                    df_sector_stocks = ak.stock_board_industry_cons_em(
                        symbol=sector_name
                    )

                    if df_sector_stocks is not None and not df_sector_stocks.empty:
                        for _, stock_row in df_sector_stocks.iterrows():
                            stock_code = str(stock_row["代码"])
                            stock_name = stock_row["名称"]

                            # Determine exchange
                            if stock_code.startswith("6"):
                                exchange = "SSE"
                                internal_ticker = f"SSE:{stock_code}"
                            elif stock_code.startswith(("0", "3")):
                                exchange = "SZSE"
                                internal_ticker = f"SZSE:{stock_code}"
                            else:
                                continue

                            names = {
                                "zh-Hans": stock_name,
                                "zh-Hant": stock_name,
                                "en-US": stock_name,
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
                        f"Error processing sector {sector_row.get('板块名称')}: {e}"
                    )
                    continue

            return results

        except Exception as e:
            logger.error(f"Error getting sector stocks for {sector}: {e}")
            return []

    def is_market_open(self, exchange: str) -> bool:
        """Check if Chinese market is currently open."""
        if exchange not in ["SSE", "SZSE", "BSE"]:
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
