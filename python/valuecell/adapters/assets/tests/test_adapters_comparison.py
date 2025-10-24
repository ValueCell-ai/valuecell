"""Test script to compare YFinance and AKShare adapters functionality."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from valuecell.adapters.assets.yfinance_adapter import YFinanceAdapter
from valuecell.adapters.assets.akshare_adapter import AKShareAdapter
from valuecell.adapters.assets.types import Asset, AssetPrice, Interval

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test data organized by asset type
TEST_TICKERS = {
    "STOCK": [
        "NASDAQ:AAPL",
        "AMEX:GORO",
        "NYSE:JPM",
        "HKEX:00700",
        "SSE:601398",
        "SZSE:002594",
        "SZSE:300750",
        "BSE:835368",
        "CRYPTO:BTC",
    ],
    "ETF": [
        "NASDAQ:QQQ",
        "AMEX:GLD",
        "NYSE:SPY",
        "HKEX:03033",
        "SSE:510050",
        "SZSE:159919",
        "BSE:560800",
    ],
    "INDEX": [
        "NASDAQ:IXIC",
        "AMEX:RUT",
        "NYSE:DJI",
        "HKEX:HSI",
        "SSE:000001",
        "SZSE:399001",
        "BSE:899050",
    ],
}


class AdapterTestResult:
    """Store test results for a single adapter and ticker."""

    def __init__(self, ticker: str, adapter_name: str):
        self.ticker = ticker
        self.adapter_name = adapter_name
        self.asset_info_success = False
        self.asset_info_data: Optional[Asset] = None
        self.asset_info_error: Optional[str] = None

        self.real_time_price_success = False
        self.real_time_price_data: Optional[AssetPrice] = None
        self.real_time_price_error: Optional[str] = None

        self.historical_prices_success = False
        self.historical_prices_count = 0
        self.historical_prices_error: Optional[str] = None


class AdapterTester:
    """Test adapter functionality and generate comparison reports."""

    def __init__(self):
        self.yfinance_adapter = YFinanceAdapter()
        self.akshare_adapter = AKShareAdapter()
        self.results: Dict[str, Dict[str, AdapterTestResult]] = {}

    def test_get_asset_info(
        self, adapter, ticker: str
    ) -> tuple[bool, Optional[Asset], Optional[str]]:
        """Test get_asset_info function."""
        try:
            asset = adapter.get_asset_info(ticker)
            if asset:
                return True, asset, None
            else:
                return False, None, "No data returned"
        except Exception as e:
            return False, None, str(e)

    def test_get_real_time_price(
        self, adapter, ticker: str
    ) -> tuple[bool, Optional[AssetPrice], Optional[str]]:
        """Test get_real_time_price function."""
        try:
            price = adapter.get_real_time_price(ticker)
            if price:
                return True, price, None
            else:
                return False, None, "No data returned"
        except Exception as e:
            return False, None, str(e)

    def test_get_historical_prices(
        self, adapter, ticker: str
    ) -> tuple[bool, int, Optional[str]]:
        """Test get_historical_prices function."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            # Use proper interval format: "1" + Interval.DAY
            interval = f"1{Interval.DAY}"
            prices = adapter.get_historical_prices(
                ticker, start_date, end_date, interval=interval
            )
            if prices:
                return True, len(prices), None
            else:
                return False, 0, "No data returned"
        except Exception as e:
            return False, 0, str(e)

    def test_ticker(self, ticker: str) -> None:
        """Test a single ticker with both adapters."""
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Testing ticker: {ticker}")
        logger.info(f"{'=' * 80}")

        # Initialize results storage
        if ticker not in self.results:
            self.results[ticker] = {}

        # Test YFinance adapter
        logger.info("\n--- Testing YFinance Adapter ---")
        yf_result = AdapterTestResult(ticker, "YFinance")

        # Test asset info
        logger.info("Testing get_asset_info...")
        success, data, error = self.test_get_asset_info(self.yfinance_adapter, ticker)
        yf_result.asset_info_success = success
        yf_result.asset_info_data = data
        yf_result.asset_info_error = error
        logger.info(f"Result: {'✓ Success' if success else f'✗ Failed: {error}'}")

        # Test real-time price
        logger.info("Testing get_real_time_price...")
        success, data, error = self.test_get_real_time_price(
            self.yfinance_adapter, ticker
        )
        yf_result.real_time_price_success = success
        yf_result.real_time_price_data = data
        yf_result.real_time_price_error = error
        logger.info(f"Result: {'✓ Success' if success else f'✗ Failed: {error}'}")

        # Test historical prices
        logger.info("Testing get_historical_prices...")
        success, count, error = self.test_get_historical_prices(
            self.yfinance_adapter, ticker
        )
        yf_result.historical_prices_success = success
        yf_result.historical_prices_count = count
        yf_result.historical_prices_error = error
        logger.info(
            f"Result: {'✓ Success' if success else f'✗ Failed: {error}'} (Count: {count})"
        )

        self.results[ticker]["yfinance"] = yf_result

        # Test AKShare adapter
        logger.info("\n--- Testing AKShare Adapter ---")
        ak_result = AdapterTestResult(ticker, "AKShare")

        # Test asset info
        logger.info("Testing get_asset_info...")
        success, data, error = self.test_get_asset_info(self.akshare_adapter, ticker)
        ak_result.asset_info_success = success
        ak_result.asset_info_data = data
        ak_result.asset_info_error = error
        logger.info(f"Result: {'✓ Success' if success else f'✗ Failed: {error}'}")

        # Test real-time price
        logger.info("Testing get_real_time_price...")
        success, data, error = self.test_get_real_time_price(
            self.akshare_adapter, ticker
        )
        ak_result.real_time_price_success = success
        ak_result.real_time_price_data = data
        ak_result.real_time_price_error = error
        logger.info(f"Result: {'✓ Success' if success else f'✗ Failed: {error}'}")

        # Test historical prices
        logger.info("Testing get_historical_prices...")
        success, count, error = self.test_get_historical_prices(
            self.akshare_adapter, ticker
        )
        ak_result.historical_prices_success = success
        ak_result.historical_prices_count = count
        ak_result.historical_prices_error = error
        logger.info(
            f"Result: {'✓ Success' if success else f'✗ Failed: {error}'} (Count: {count})"
        )

        self.results[ticker]["akshare"] = ak_result

    def run_all_tests(self) -> None:
        """Run tests for all tickers."""
        for asset_type, tickers in TEST_TICKERS.items():
            logger.info(f"\n\n{'#' * 80}")
            logger.info(f"# Testing {asset_type}")
            logger.info(f"{'#' * 80}")

            for ticker in tickers:
                try:
                    self.test_ticker(ticker)
                except Exception as e:
                    logger.error(f"Error testing ticker {ticker}: {e}", exc_info=True)

    def generate_report(self) -> str:
        """Generate a comprehensive comparison report."""
        report_lines = []
        report_lines.append("=" * 120)
        report_lines.append("ADAPTER COMPARISON REPORT: YFinance vs AKShare")
        report_lines.append("=" * 120)
        report_lines.append("")

        # Summary statistics
        yf_total_success = {
            "asset_info": 0,
            "real_time_price": 0,
            "historical_prices": 0,
        }
        ak_total_success = {
            "asset_info": 0,
            "real_time_price": 0,
            "historical_prices": 0,
        }
        total_tests = len(self.results)

        for asset_type, tickers in TEST_TICKERS.items():
            report_lines.append(f"\n{'=' * 120}")
            report_lines.append(f"ASSET TYPE: {asset_type}")
            report_lines.append(f"{'=' * 120}\n")

            for ticker in tickers:
                if ticker not in self.results:
                    continue

                yf_result = self.results[ticker].get("yfinance")
                ak_result = self.results[ticker].get("akshare")

                if not yf_result or not ak_result:
                    continue

                report_lines.append(f"\nTicker: {ticker}")
                report_lines.append("-" * 120)

                # Asset Info comparison
                report_lines.append("\n1. GET_ASSET_INFO:")
                report_lines.append(
                    f"   YFinance: {'✓ SUCCESS' if yf_result.asset_info_success else f'✗ FAILED - {yf_result.asset_info_error}'}"
                )
                if yf_result.asset_info_data:
                    report_lines.append(
                        f"      - Names: {yf_result.asset_info_data.names.get_name('en-US')}"
                    )
                    report_lines.append(
                        f"      - Exchange: {yf_result.asset_info_data.market_info.exchange}"
                    )
                    report_lines.append(
                        f"      - Currency: {yf_result.asset_info_data.market_info.currency}"
                    )

                report_lines.append(
                    f"   AKShare:  {'✓ SUCCESS' if ak_result.asset_info_success else f'✗ FAILED - {ak_result.asset_info_error}'}"
                )
                if ak_result.asset_info_data:
                    report_lines.append(
                        f"      - Names: {ak_result.asset_info_data.names.get_name('en-US')}"
                    )
                    report_lines.append(
                        f"      - Exchange: {ak_result.asset_info_data.market_info.exchange}"
                    )
                    report_lines.append(
                        f"      - Currency: {ak_result.asset_info_data.market_info.currency}"
                    )

                # Real-time price comparison
                report_lines.append("\n2. GET_REAL_TIME_PRICE:")
                report_lines.append(
                    f"   YFinance: {'✓ SUCCESS' if yf_result.real_time_price_success else f'✗ FAILED - {yf_result.real_time_price_error}'}"
                )
                if yf_result.real_time_price_data:
                    report_lines.append(
                        f"      - Price: {yf_result.real_time_price_data.price} {yf_result.real_time_price_data.currency}"
                    )
                    report_lines.append(
                        f"      - Timestamp: {yf_result.real_time_price_data.timestamp}"
                    )
                    report_lines.append(
                        f"      - Change: {yf_result.real_time_price_data.change} ({yf_result.real_time_price_data.change_percent}%)"
                    )

                report_lines.append(
                    f"   AKShare:  {'✓ SUCCESS' if ak_result.real_time_price_success else f'✗ FAILED - {ak_result.real_time_price_error}'}"
                )
                if ak_result.real_time_price_data:
                    report_lines.append(
                        f"      - Price: {ak_result.real_time_price_data.price} {ak_result.real_time_price_data.currency}"
                    )
                    report_lines.append(
                        f"      - Timestamp: {ak_result.real_time_price_data.timestamp}"
                    )
                    report_lines.append(
                        f"      - Change: {ak_result.real_time_price_data.change} ({ak_result.real_time_price_data.change_percent}%)"
                    )

                # Historical prices comparison
                report_lines.append("\n3. GET_HISTORICAL_PRICES (Last 30 days):")
                report_lines.append(
                    f"   YFinance: {'✓ SUCCESS' if yf_result.historical_prices_success else f'✗ FAILED - {yf_result.historical_prices_error}'}"
                )
                report_lines.append(
                    f"      - Data Points: {yf_result.historical_prices_count}"
                )

                report_lines.append(
                    f"   AKShare:  {'✓ SUCCESS' if ak_result.historical_prices_success else f'✗ FAILED - {ak_result.historical_prices_error}'}"
                )
                report_lines.append(
                    f"      - Data Points: {ak_result.historical_prices_count}"
                )

                # Update statistics
                if yf_result.asset_info_success:
                    yf_total_success["asset_info"] += 1
                if yf_result.real_time_price_success:
                    yf_total_success["real_time_price"] += 1
                if yf_result.historical_prices_success:
                    yf_total_success["historical_prices"] += 1

                if ak_result.asset_info_success:
                    ak_total_success["asset_info"] += 1
                if ak_result.real_time_price_success:
                    ak_total_success["real_time_price"] += 1
                if ak_result.historical_prices_success:
                    ak_total_success["historical_prices"] += 1

        # Summary section
        report_lines.append(f"\n\n{'=' * 120}")
        report_lines.append("SUMMARY STATISTICS")
        report_lines.append(f"{'=' * 120}\n")
        report_lines.append(f"Total Tickers Tested: {total_tests}\n")

        report_lines.append("YFinance Adapter Success Rate:")
        report_lines.append(
            f"   - get_asset_info:        {yf_total_success['asset_info']}/{total_tests} ({yf_total_success['asset_info'] / total_tests * 100:.1f}%)"
        )
        report_lines.append(
            f"   - get_real_time_price:   {yf_total_success['real_time_price']}/{total_tests} ({yf_total_success['real_time_price'] / total_tests * 100:.1f}%)"
        )
        report_lines.append(
            f"   - get_historical_prices: {yf_total_success['historical_prices']}/{total_tests} ({yf_total_success['historical_prices'] / total_tests * 100:.1f}%)"
        )

        report_lines.append("\nAKShare Adapter Success Rate:")
        report_lines.append(
            f"   - get_asset_info:        {ak_total_success['asset_info']}/{total_tests} ({ak_total_success['asset_info'] / total_tests * 100:.1f}%)"
        )
        report_lines.append(
            f"   - get_real_time_price:   {ak_total_success['real_time_price']}/{total_tests} ({ak_total_success['real_time_price'] / total_tests * 100:.1f}%)"
        )
        report_lines.append(
            f"   - get_historical_prices: {ak_total_success['historical_prices']}/{total_tests} ({ak_total_success['historical_prices'] / total_tests * 100:.1f}%)"
        )

        report_lines.append(f"\n{'=' * 120}")

        return "\n".join(report_lines)

    def save_report(self, filename: str = "adapter_comparison_report.txt") -> None:
        """Save the report to a file."""
        report = self.generate_report()
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"\nReport saved to: {filename}")


def main():
    """Main test execution."""
    logger.info("Starting adapter comparison tests...")

    tester = AdapterTester()

    # Run all tests
    tester.run_all_tests()

    # Generate and save report
    report = tester.generate_report()
    print("\n\n")
    print(report)

    # Save to file
    tester.save_report("adapter_comparison_report.txt")

    logger.info("\nAll tests completed!")


if __name__ == "__main__":
    main()
