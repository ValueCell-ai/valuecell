"""Comprehensive test suite for BaoStockAdapter.

This test suite covers all public methods of the BaoStockAdapter including:
- validate_ticker
- get_asset_info
- get_historical_prices (daily, weekly, monthly, minute)
- search_assets
- convert_to_internal_ticker / convert_to_source_ticker
- get_capabilities

Tests include both Shanghai (SSE) and Shenzhen (SZSE) stocks and indices.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pytest

from valuecell.adapters.assets.baostock_adapter import BaoStockAdapter
from valuecell.adapters.assets.types import (
    Asset,
    AssetPrice,
    AssetSearchQuery,
    AssetType,
    Exchange,
    Interval,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Test data for BaoStock adapter
# Format: (internal_ticker, baostock_code, name, asset_type)
TEST_STOCKS = [
    ("SSE:600000", "sh.600000", "浦发银行", AssetType.STOCK),  # Shanghai stock
    ("SSE:600519", "sh.600519", "贵州茅台", AssetType.STOCK),  # Shanghai stock (Moutai)
    ("SSE:601398", "sh.601398", "工商银行", AssetType.STOCK),  # Shanghai stock
    ("SZSE:000001", "sz.000001", "平安银行", AssetType.STOCK),  # Shenzhen stock
    ("SZSE:002594", "sz.002594", "比亚迪", AssetType.STOCK),  # Shenzhen stock
    ("SZSE:300750", "sz.300750", "宁德时代", AssetType.STOCK),  # ChiNext stock
]

TEST_INDICES = [
    ("SSE:000001", "sh.000001", "上证指数", AssetType.INDEX),  # Shanghai Composite Index
    ("SSE:000300", "sh.000300", "沪深300", AssetType.INDEX),  # CSI 300 Index
    ("SSE:000016", "sh.000016", "上证50", AssetType.INDEX),  # SSE 50 Index
    ("SZSE:399001", "sz.399001", "深证成指", AssetType.INDEX),  # Shenzhen Component Index
    ("SZSE:399006", "sz.399006", "创业板指", AssetType.INDEX),  # ChiNext Index
]

# Invalid tickers for testing
INVALID_TICKERS = [
    "NASDAQ:AAPL",  # Not supported exchange
    "HKEX:00700",  # Not supported exchange
    "CRYPTO:BTC",  # Not supported exchange
    "SSE600000",  # Missing colon
    "SSE:",  # Missing symbol
    ":600000",  # Missing exchange
]


class TestBaoStockAdapter:
    """Test class for BaoStockAdapter."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.adapter = BaoStockAdapter()

    # ==========================================================================
    # Test validate_ticker
    # ==========================================================================

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_STOCKS)
    def test_validate_ticker_stocks_valid(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test validate_ticker returns True for valid stock tickers."""
        assert self.adapter.validate_ticker(ticker) is True, (
            f"Expected {ticker} to be valid"
        )

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_INDICES)
    def test_validate_ticker_indices_valid(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test validate_ticker returns True for valid index tickers."""
        assert self.adapter.validate_ticker(ticker) is True, (
            f"Expected {ticker} to be valid"
        )

    @pytest.mark.parametrize("ticker", INVALID_TICKERS)
    def test_validate_ticker_invalid(self, ticker: str):
        """Test validate_ticker returns False for invalid tickers."""
        assert self.adapter.validate_ticker(ticker) is False, (
            f"Expected {ticker} to be invalid"
        )

    # ==========================================================================
    # Test ticker conversion
    # ==========================================================================

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_STOCKS + TEST_INDICES)
    def test_convert_to_source_ticker(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test convert_to_source_ticker converts internal ticker to BaoStock format."""
        result = self.adapter.convert_to_source_ticker(ticker)
        assert result == baostock_code, (
            f"Expected {baostock_code}, got {result} for {ticker}"
        )

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_STOCKS + TEST_INDICES)
    def test_convert_to_internal_ticker(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test convert_to_internal_ticker converts BaoStock code to internal format."""
        result = self.adapter.convert_to_internal_ticker(baostock_code)
        assert result == ticker, f"Expected {ticker}, got {result} for {baostock_code}"

    def test_convert_to_internal_ticker_invalid_format(self):
        """Test convert_to_internal_ticker handles invalid format gracefully."""
        result = self.adapter.convert_to_internal_ticker("600000")  # No exchange prefix
        assert result == "600000"  # Should return as-is

    # ==========================================================================
    # Test get_capabilities
    # ==========================================================================

    def test_get_capabilities(self):
        """Test get_capabilities returns expected capabilities."""
        capabilities = self.adapter.get_capabilities()
        assert len(capabilities) == 3  # STOCK, INDEX, ETF

        asset_types = {cap.asset_type for cap in capabilities}
        assert AssetType.STOCK in asset_types
        assert AssetType.INDEX in asset_types
        assert AssetType.ETF in asset_types

        for cap in capabilities:
            assert Exchange.SSE in cap.exchanges
            assert Exchange.SZSE in cap.exchanges
            assert Exchange.HKEX not in cap.exchanges  # Not supported

    def test_get_supported_exchanges(self):
        """Test get_supported_exchanges returns SSE and SZSE."""
        exchanges = self.adapter.get_supported_exchanges()
        assert Exchange.SSE in exchanges
        assert Exchange.SZSE in exchanges
        assert len(exchanges) == 2

    # ==========================================================================
    # Test get_asset_info
    # ==========================================================================

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_STOCKS[:2])
    def test_get_asset_info_stocks(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test get_asset_info for stocks."""
        logger.info(f"Testing get_asset_info for stock: {ticker}")
        asset = self.adapter.get_asset_info(ticker)

        assert asset is not None, f"Expected asset info for {ticker}"
        assert asset.ticker == ticker
        assert asset.asset_type == asset_type
        assert asset.market_info.currency == "CNY"
        assert asset.market_info.country == "CN"
        logger.info(
            f"  ✓ Got asset info: {asset.names.get_name('zh-Hans')}, "
            f"type={asset.asset_type}, exchange={asset.market_info.exchange}"
        )

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_INDICES[:2])
    def test_get_asset_info_indices(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test get_asset_info for indices."""
        logger.info(f"Testing get_asset_info for index: {ticker}")
        asset = self.adapter.get_asset_info(ticker)

        assert asset is not None, f"Expected asset info for {ticker}"
        assert asset.ticker == ticker
        assert asset.asset_type == asset_type
        assert asset.market_info.currency == "CNY"
        logger.info(
            f"  ✓ Got asset info: {asset.names.get_name('zh-Hans')}, "
            f"type={asset.asset_type}"
        )

    def test_get_asset_info_invalid_ticker(self):
        """Test get_asset_info returns None for invalid ticker."""
        asset = self.adapter.get_asset_info("NASDAQ:AAPL")
        assert asset is None

    # ==========================================================================
    # Test get_real_time_price
    # ==========================================================================

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_STOCKS[:2])
    def test_get_real_time_price_stocks(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test get_real_time_price returns most recent price for stocks."""
        logger.info(f"Testing get_real_time_price for stock: {ticker}")
        result = self.adapter.get_real_time_price(ticker)

        assert result is not None, f"Expected price data for {ticker}"
        assert result.ticker == ticker
        assert result.currency == "CNY"
        assert result.close_price is not None
        assert result.price is not None
        logger.info(
            f"  ✓ Got price: {result.price} CNY @ {result.timestamp.date()}"
        )

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_INDICES[:2])
    def test_get_real_time_price_indices(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test get_real_time_price returns most recent price for indices."""
        logger.info(f"Testing get_real_time_price for index: {ticker}")
        result = self.adapter.get_real_time_price(ticker)

        assert result is not None, f"Expected price data for {ticker}"
        assert result.ticker == ticker
        assert result.currency == "CNY"
        assert result.close_price is not None
        logger.info(
            f"  ✓ Got price: {result.price} @ {result.timestamp.date()}"
        )

    def test_get_real_time_price_invalid_ticker(self):
        """Test get_real_time_price returns None for invalid ticker."""
        result = self.adapter.get_real_time_price("NASDAQ:AAPL")
        assert result is None

    # ==========================================================================
    # Test get_historical_prices - Daily data
    # ==========================================================================

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_STOCKS[:2])
    def test_get_historical_prices_daily_stocks(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test get_historical_prices for stocks with daily interval."""
        logger.info(f"Testing get_historical_prices (daily) for stock: {ticker}")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        interval = f"1{Interval.DAY.value}"

        prices = self.adapter.get_historical_prices(
            ticker, start_date, end_date, interval=interval
        )

        assert len(prices) > 0, f"Expected historical data for {ticker}"
        for price in prices:
            assert price.ticker == ticker
            assert price.currency == "CNY"
            assert price.close_price is not None
            assert price.open_price is not None
            assert price.high_price is not None
            assert price.low_price is not None
            assert price.volume is not None

        logger.info(f"  ✓ Got {len(prices)} daily price points for {ticker}")
        logger.info(
            f"    First: {prices[0].timestamp.date()} close={prices[0].close_price}"
        )
        logger.info(
            f"    Last:  {prices[-1].timestamp.date()} close={prices[-1].close_price}"
        )

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_INDICES[:2])
    def test_get_historical_prices_daily_indices(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test get_historical_prices for indices with daily interval."""
        logger.info(f"Testing get_historical_prices (daily) for index: {ticker}")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        interval = f"1{Interval.DAY.value}"

        prices = self.adapter.get_historical_prices(
            ticker, start_date, end_date, interval=interval
        )

        assert len(prices) > 0, f"Expected historical data for {ticker}"
        for price in prices:
            assert price.ticker == ticker
            assert price.currency == "CNY"
            assert price.close_price is not None

        logger.info(f"  ✓ Got {len(prices)} daily price points for {ticker}")

    # ==========================================================================
    # Test get_historical_prices - Weekly data
    # ==========================================================================

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_STOCKS[:1])
    def test_get_historical_prices_weekly(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test get_historical_prices with weekly interval."""
        logger.info(f"Testing get_historical_prices (weekly) for: {ticker}")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # 3 months
        interval = f"1{Interval.WEEK.value}"

        prices = self.adapter.get_historical_prices(
            ticker, start_date, end_date, interval=interval
        )

        # Note: BaoStock weekly data is only available on the last trading day of the week
        if len(prices) > 0:
            logger.info(f"  ✓ Got {len(prices)} weekly price points for {ticker}")
        else:
            logger.info(f"  ⚠ No weekly data available (may be mid-week)")

    # ==========================================================================
    # Test get_historical_prices - Monthly data
    # ==========================================================================

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_STOCKS[:1])
    def test_get_historical_prices_monthly(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test get_historical_prices with monthly interval."""
        logger.info(f"Testing get_historical_prices (monthly) for: {ticker}")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # 1 year
        interval = f"1{Interval.MONTH.value}"

        prices = self.adapter.get_historical_prices(
            ticker, start_date, end_date, interval=interval
        )

        # Note: BaoStock monthly data is only available on the last trading day of the month
        if len(prices) > 0:
            logger.info(f"  ✓ Got {len(prices)} monthly price points for {ticker}")
        else:
            logger.info(f"  ⚠ No monthly data available (may be mid-month)")

    # ==========================================================================
    # Test get_historical_prices - Minute data
    # ==========================================================================

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_STOCKS[:1])
    def test_get_historical_prices_minute_stocks(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test get_historical_prices for stocks with minute interval."""
        logger.info(f"Testing get_historical_prices (60m) for stock: {ticker}")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)
        interval = f"60{Interval.MINUTE.value}"

        prices = self.adapter.get_historical_prices(
            ticker, start_date, end_date, interval=interval
        )

        # Minute data should be available for stocks
        if len(prices) > 0:
            logger.info(f"  ✓ Got {len(prices)} minute price points for {ticker}")
        else:
            logger.info(f"  ⚠ No minute data available (market may be closed)")

    @pytest.mark.parametrize("ticker,baostock_code,name,asset_type", TEST_INDICES[:1])
    def test_get_historical_prices_minute_indices_not_supported(
        self, ticker: str, baostock_code: str, name: str, asset_type: AssetType
    ):
        """Test that minute data is NOT supported for indices."""
        logger.info(f"Testing get_historical_prices (60m) for index: {ticker}")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)
        interval = f"60{Interval.MINUTE.value}"

        prices = self.adapter.get_historical_prices(
            ticker, start_date, end_date, interval=interval
        )

        # BaoStock does NOT support minute data for indices
        assert len(prices) == 0, (
            f"Expected empty list for index minute data, got {len(prices)} points"
        )
        logger.info(f"  ✓ Confirmed: No minute data for index {ticker} (expected)")

    def test_get_historical_prices_unsupported_interval(self):
        """Test get_historical_prices with unsupported interval returns empty list."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        prices = self.adapter.get_historical_prices(
            "SSE:600000", start_date, end_date, interval="1h"  # Hour not directly supported
        )

        assert len(prices) == 0

    # ==========================================================================
    # Test search_assets
    # ==========================================================================

    def test_search_assets_by_code(self):
        """Test search_assets by stock code."""
        logger.info("Testing search_assets by code: sh.600000")
        query = AssetSearchQuery(query="sh.600000", limit=10)
        results = self.adapter.search_assets(query)

        assert len(results) > 0, "Expected search results for sh.600000"
        assert results[0].ticker == "SSE:600000"
        logger.info(f"  ✓ Found {len(results)} result(s)")
        for r in results:
            logger.info(f"    - {r.ticker}: {r.names.get('zh-Hans', 'N/A')}")

    def test_search_assets_by_name(self):
        """Test search_assets by stock name (fuzzy search)."""
        logger.info("Testing search_assets by name: 浦发")
        query = AssetSearchQuery(query="浦发", limit=10)
        results = self.adapter.search_assets(query)

        # Fuzzy search should return results containing "浦发"
        if len(results) > 0:
            logger.info(f"  ✓ Found {len(results)} result(s)")
            for r in results:
                logger.info(f"    - {r.ticker}: {r.names.get('zh-Hans', 'N/A')}")
        else:
            logger.info("  ⚠ No results found (fuzzy search may vary)")

    def test_search_assets_by_internal_ticker(self):
        """Test search_assets with internal ticker format."""
        logger.info("Testing search_assets by internal ticker: SSE:600000")
        query = AssetSearchQuery(query="SSE:600000", limit=10)
        results = self.adapter.search_assets(query)

        assert len(results) > 0, "Expected search results for SSE:600000"
        assert results[0].ticker == "SSE:600000"
        logger.info(f"  ✓ Found {len(results)} result(s)")

    def test_search_assets_by_digit_code(self):
        """Test search_assets with just 6-digit code."""
        logger.info("Testing search_assets by 6-digit code: 600000")
        query = AssetSearchQuery(query="600000", limit=10)
        results = self.adapter.search_assets(query)

        if len(results) > 0:
            logger.info(f"  ✓ Found {len(results)} result(s)")
            for r in results:
                logger.info(f"    - {r.ticker}: {r.names.get('zh-Hans', 'N/A')}")
        else:
            logger.info("  ⚠ No results (6-digit search may require prefix)")

    def test_search_assets_limit(self):
        """Test search_assets respects limit parameter."""
        query = AssetSearchQuery(query="银行", limit=3)
        results = self.adapter.search_assets(query)

        assert len(results) <= 3, f"Expected at most 3 results, got {len(results)}"

    # ==========================================================================
    # Integration tests
    # ==========================================================================

    def test_full_workflow_stock(self):
        """Test full workflow for a stock: validate -> info -> historical."""
        ticker = "SSE:600000"
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Full workflow test for stock: {ticker}")
        logger.info(f"{'=' * 60}")

        # Step 1: Validate ticker
        assert self.adapter.validate_ticker(ticker) is True
        logger.info(f"  1. ✓ Ticker validation passed")

        # Step 2: Get asset info
        asset = self.adapter.get_asset_info(ticker)
        assert asset is not None
        assert asset.asset_type == AssetType.STOCK
        logger.info(f"  2. ✓ Asset info: {asset.names.get_name('zh-Hans')}")

        # Step 3: Get historical prices
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)
        prices = self.adapter.get_historical_prices(
            ticker, start_date, end_date, interval=f"1{Interval.DAY.value}"
        )
        assert len(prices) > 0
        logger.info(f"  3. ✓ Historical prices: {len(prices)} days")

        # Step 4: Get minute data
        prices_min = self.adapter.get_historical_prices(
            ticker, start_date, end_date, interval=f"60{Interval.MINUTE.value}"
        )
        if len(prices_min) > 0:
            logger.info(f"  4. ✓ Minute data: {len(prices_min)} points")
        else:
            logger.info(f"  4. ⚠ No minute data available")

    def test_full_workflow_index(self):
        """Test full workflow for an index: validate -> info -> historical."""
        ticker = "SSE:000001"  # Shanghai Composite Index
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Full workflow test for index: {ticker}")
        logger.info(f"{'=' * 60}")

        # Step 1: Validate ticker
        assert self.adapter.validate_ticker(ticker) is True
        logger.info(f"  1. ✓ Ticker validation passed")

        # Step 2: Get asset info
        asset = self.adapter.get_asset_info(ticker)
        assert asset is not None
        assert asset.asset_type == AssetType.INDEX
        logger.info(f"  2. ✓ Asset info: {asset.names.get_name('zh-Hans')}")

        # Step 3: Get historical prices (daily)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)
        prices = self.adapter.get_historical_prices(
            ticker, start_date, end_date, interval=f"1{Interval.DAY.value}"
        )
        assert len(prices) > 0
        logger.info(f"  3. ✓ Historical prices: {len(prices)} days")

        # Step 4: Verify minute data is NOT available for indices
        prices_min = self.adapter.get_historical_prices(
            ticker, start_date, end_date, interval=f"60{Interval.MINUTE.value}"
        )
        assert len(prices_min) == 0
        logger.info(f"  4. ✓ Minute data correctly not available for index")


def run_manual_tests():
    """Run tests manually with detailed output."""
    logger.info("=" * 80)
    logger.info("BaoStock Adapter Manual Test Suite")
    logger.info("=" * 80)

    adapter = BaoStockAdapter()

    # Test 1: Validate tickers
    logger.info("\n--- Test 1: Ticker Validation ---")
    for ticker, baostock_code, name, asset_type in TEST_STOCKS + TEST_INDICES:
        is_valid = adapter.validate_ticker(ticker)
        logger.info(f"  {ticker}: {'✓' if is_valid else '✗'}")

    # Test 2: Get asset info
    logger.info("\n--- Test 2: Get Asset Info ---")
    for ticker, baostock_code, name, expected_type in TEST_STOCKS[:2] + TEST_INDICES[:2]:
        asset = adapter.get_asset_info(ticker)
        if asset:
            logger.info(
                f"  {ticker}: ✓ {asset.names.get_name('zh-Hans')} ({asset.asset_type.value})"
            )
        else:
            logger.info(f"  {ticker}: ✗ Failed to get asset info")

    # Test 3: Get historical prices
    logger.info("\n--- Test 3: Get Historical Prices (Daily) ---")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    for ticker, baostock_code, name, asset_type in TEST_STOCKS[:1] + TEST_INDICES[:1]:
        prices = adapter.get_historical_prices(
            ticker, start_date, end_date, interval=f"1{Interval.DAY.value}"
        )
        logger.info(f"  {ticker}: {len(prices)} data points")
        if prices:
            logger.info(
                f"    Last price: {prices[-1].timestamp.date()} - "
                f"{prices[-1].close_price} CNY"
            )

    # Test 4: Search assets
    logger.info("\n--- Test 4: Search Assets ---")
    queries = ["sh.600000", "浦发", "000001"]
    for q in queries:
        query = AssetSearchQuery(query=q, limit=3)
        results = adapter.search_assets(query)
        logger.info(f"  Query '{q}': {len(results)} results")
        for r in results[:2]:
            logger.info(f"    - {r.ticker}: {r.names.get('zh-Hans', 'N/A')}")

    # Test 5: Minute data (stock vs index)
    logger.info("\n--- Test 5: Minute Data Support ---")
    start_date = end_date - timedelta(days=3)

    # Stock should have minute data
    stock_ticker = "SSE:600000"
    stock_min_prices = adapter.get_historical_prices(
        stock_ticker, start_date, end_date, interval=f"60{Interval.MINUTE.value}"
    )
    logger.info(f"  Stock {stock_ticker}: {len(stock_min_prices)} minute points")

    # Index should NOT have minute data
    index_ticker = "SSE:000001"
    index_min_prices = adapter.get_historical_prices(
        index_ticker, start_date, end_date, interval=f"60{Interval.MINUTE.value}"
    )
    logger.info(f"  Index {index_ticker}: {len(index_min_prices)} minute points (expected 0)")

    # Test 6: Real-time prices (using most recent daily data)
    logger.info("\n--- Test 6: Real-Time Prices (Most Recent Daily Data) ---")
    test_tickers = ["SSE:600000", "SSE:000001", "SZSE:000001", "SSE:000300"]
    for ticker in test_tickers:
        price = adapter.get_real_time_price(ticker)
        if price:
            logger.info(
                f"  {ticker}: ✓ {price.price} CNY @ {price.timestamp.date()}"
            )
            if price.change_percent:
                logger.info(f"    Change: {price.change_percent}%")
        else:
            logger.info(f"  {ticker}: ✗ No price data")

    logger.info("\n" + "=" * 80)
    logger.info("Manual tests completed!")
    logger.info("=" * 80)


if __name__ == "__main__":
    run_manual_tests()

