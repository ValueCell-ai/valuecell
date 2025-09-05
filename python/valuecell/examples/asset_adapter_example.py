"""Example usage of the ValueCell Asset Data Adapter system.

This example demonstrates how to configure and use the asset data adapters
for financial data retrieval, search, and watchlist management with i18n support.
"""

import logging

from valuecell.adapters.assets import (
    get_adapter_manager,
    get_asset_api,
    search_assets,
    get_asset_info,
    get_asset_price,
    add_to_watchlist,
    get_watchlist,
)
from valuecell.i18n import set_i18n_config, I18nConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_adapters():
    """Configure and initialize data adapters."""
    logger.info("Setting up data adapters...")

    # Get adapter manager
    manager = get_adapter_manager()

    # Configure Yahoo Finance (free, no API key required)
    try:
        manager.configure_yfinance()
        logger.info("✓ Yahoo Finance adapter configured")
    except Exception as e:
        logger.warning(f"✗ Yahoo Finance adapter failed: {e}")

    # Configure TuShare (requires API key)
    try:
        # Replace with your actual TuShare API key
        tushare_api_key = "your_tushare_api_key_here"
        if tushare_api_key != "your_tushare_api_key_here":
            manager.configure_tushare(api_key=tushare_api_key)
            logger.info("✓ TuShare adapter configured")
        else:
            logger.warning("✗ TuShare API key not provided, skipping")
    except Exception as e:
        logger.warning(f"✗ TuShare adapter failed: {e}")

    # Configure CoinMarketCap (requires API key for crypto data)
    try:
        # Replace with your actual CoinMarketCap API key
        cmc_api_key = "your_coinmarketcap_api_key_here"
        if cmc_api_key != "your_coinmarketcap_api_key_here":
            manager.configure_coinmarketcap(api_key=cmc_api_key)
            logger.info("✓ CoinMarketCap adapter configured")
        else:
            logger.warning("✗ CoinMarketCap API key not provided, skipping")
    except Exception as e:
        logger.warning(f"✗ CoinMarketCap adapter failed: {e}")

    # Configure AKShare (free, no API key required)
    try:
        manager.configure_akshare()
        logger.info("✓ AKShare adapter configured")
    except Exception as e:
        logger.warning(f"✗ AKShare adapter failed: {e}")

    # Configure Finnhub (requires API key)
    try:
        # Replace with your actual Finnhub API key
        finnhub_api_key = "your_finnhub_api_key_here"
        if finnhub_api_key != "your_finnhub_api_key_here":
            manager.configure_finnhub(api_key=finnhub_api_key)
            logger.info("✓ Finnhub adapter configured")
        else:
            logger.warning("✗ Finnhub API key not provided, skipping")
    except Exception as e:
        logger.warning(f"✗ Finnhub adapter failed: {e}")

    # Check system health
    api = get_asset_api()
    health = api.get_system_health()
    logger.info(
        f"System health: {health['overall_status']} "
        f"({health['healthy_adapters']}/{health['total_adapters']} adapters)"
    )

    return manager


def demonstrate_asset_search():
    """Demonstrate asset search functionality with i18n."""
    logger.info("\n=== Asset Search Demo ===")

    # Search in English
    logger.info("Searching for 'AAPL' in English...")
    results_en = search_assets("AAPL", language="en-US", limit=5)

    if results_en["success"]:
        logger.info(f"Found {results_en['count']} results:")
        for result in results_en["results"]:
            logger.info(
                f"  - {result['ticker']}: {result['display_name']} "
                f"({result['asset_type_display']})"
            )

    # Search in Chinese
    logger.info("\nSearching for 'Apple' in Chinese...")
    results_zh = search_assets("Apple", language="zh-Hans", limit=5)

    if results_zh["success"]:
        logger.info(f"找到 {results_zh['count']} 个结果:")
        for result in results_zh["results"]:
            logger.info(
                f"  - {result['ticker']}: {result['display_name']} "
                f"({result['asset_type_display']})"
            )

    # Search for Chinese stocks
    logger.info("\nSearching for Chinese stocks...")
    results_cn = search_assets("茅台", asset_types=["stock"], limit=3)

    if results_cn["success"]:
        logger.info(f"Found {results_cn['count']} Chinese stocks:")
        for result in results_cn["results"]:
            logger.info(f"  - {result['ticker']}: {result['display_name']}")

    # Search for cryptocurrencies
    logger.info("\nSearching for cryptocurrencies...")
    results_crypto = search_assets("Bitcoin", asset_types=["crypto"], limit=3)

    if results_crypto["success"]:
        logger.info(f"Found {results_crypto['count']} cryptocurrencies:")
        for result in results_crypto["results"]:
            logger.info(f"  - {result['ticker']}: {result['display_name']}")


def demonstrate_asset_info():
    """Demonstrate getting detailed asset information."""
    logger.info("\n=== Asset Information Demo ===")

    # Get info for Apple stock
    tickers = ["NASDAQ:AAPL", "SSE:600519", "CRYPTO:BTC"]

    for ticker in tickers:
        logger.info(f"\nGetting info for {ticker}...")

        # Get in English
        info_en = get_asset_info(ticker, language="en-US")
        if info_en["success"]:
            logger.info(
                f"  English: {info_en['display_name']} "
                f"({info_en['asset_type_display']})"
            )
            logger.info(f"  Exchange: {info_en['market_info']['exchange']}")
            logger.info(f"  Country: {info_en['market_info']['country']}")

        # Get in Chinese
        info_zh = get_asset_info(ticker, language="zh-Hans")
        if info_zh["success"]:
            logger.info(
                f"  中文: {info_zh['display_name']} ({info_zh['asset_type_display']})"
            )


def demonstrate_price_data():
    """Demonstrate real-time price data retrieval."""
    logger.info("\n=== Price Data Demo ===")

    tickers = ["NASDAQ:AAPL", "NASDAQ:MSFT", "NASDAQ:GOOGL"]

    # Get individual price
    logger.info("Getting individual price for AAPL...")
    price_data = get_asset_price("NASDAQ:AAPL", language="zh-Hans")

    if price_data["success"]:
        logger.info(f"  价格: {price_data['price_formatted']}")
        if price_data["change_percent_formatted"]:
            logger.info(f"  涨跌幅: {price_data['change_percent_formatted']}")
        if price_data["market_cap_formatted"]:
            logger.info(f"  市值: {price_data['market_cap_formatted']}")

    # Get multiple prices
    logger.info(f"\nGetting prices for multiple assets: {tickers}")
    api = get_asset_api()
    prices_data = api.get_multiple_prices(tickers, language="en-US")

    if prices_data["success"]:
        logger.info(f"Successfully retrieved {prices_data['count']} prices:")
        for ticker, price_info in prices_data["prices"].items():
            if price_info:
                logger.info(
                    f"  {ticker}: {price_info['price_formatted']} "
                    f"({price_info.get('change_percent_formatted', 'N/A')})"
                )
            else:
                logger.info(f"  {ticker}: Price not available")


def demonstrate_watchlist_management():
    """Demonstrate watchlist creation and management."""
    logger.info("\n=== Watchlist Management Demo ===")

    user_id = "demo_user_123"
    api = get_asset_api()

    # Create a watchlist
    logger.info("Creating a new watchlist...")
    create_result = api.create_watchlist(
        user_id=user_id,
        name="My Tech Stocks",
        description="Technology companies I'm watching",
        is_default=True,
    )

    if create_result["success"]:
        logger.info("✓ Watchlist created successfully")

    # Add assets to watchlist
    assets_to_add = [
        ("NASDAQ:AAPL", "Apple - iPhone maker"),
        ("NASDAQ:MSFT", "Microsoft - Cloud and software"),
        ("NASDAQ:GOOGL", "Google - Search and ads"),
        ("NASDAQ:TSLA", "Tesla - Electric vehicles"),
    ]

    logger.info("Adding assets to watchlist...")
    for ticker, notes in assets_to_add:
        result = add_to_watchlist(user_id=user_id, ticker=ticker, notes=notes)
        if result["success"]:
            logger.info(f"  ✓ Added {ticker}")
        else:
            logger.warning(f"  ✗ Failed to add {ticker}: {result.get('error')}")

    # Get watchlist with prices
    logger.info("\nRetrieving watchlist with current prices...")
    watchlist_data = get_watchlist(
        user_id=user_id, include_prices=True, language="zh-Hans"
    )

    if watchlist_data["success"]:
        watchlist = watchlist_data["watchlist"]
        logger.info(f"观察列表: {watchlist['name']}")
        logger.info(f"资产数量: {watchlist['items_count']}")

        for asset in watchlist["assets"]:
            display_name = asset["display_name"]
            notes = asset["notes"]

            price_info = ""
            if "price_data" in asset and asset["price_data"]:
                price_data = asset["price_data"]
                price_info = f" - {price_data['price_formatted']}"
                if price_data.get("change_percent_formatted"):
                    price_info += f" ({price_data['change_percent_formatted']})"

            logger.info(f"  • {display_name}{price_info}")
            if notes:
                logger.info(f"    备注: {notes}")

    # List all user watchlists
    logger.info("\nListing all user watchlists...")
    all_watchlists = api.get_user_watchlists(user_id)

    if all_watchlists["success"]:
        logger.info(f"用户 {user_id} 有 {all_watchlists['count']} 个观察列表:")
        for wl in all_watchlists["watchlists"]:
            default_marker = " (默认)" if wl["is_default"] else ""
            logger.info(f"  • {wl['name']}{default_marker} - {wl['items_count']} 资产")


def demonstrate_i18n_features():
    """Demonstrate internationalization features."""
    logger.info("\n=== Internationalization Demo ===")

    # Test different languages
    languages = ["en-US", "zh-Hans", "zh-Hant"]
    ticker = "NASDAQ:AAPL"

    for lang in languages:
        logger.info(f"\nTesting language: {lang}")

        # Set language configuration
        config = I18nConfig(language=lang)
        set_i18n_config(config)

        # Search for assets
        results = search_assets("Apple", language=lang, limit=1)
        if results["success"] and results["results"]:
            result = results["results"][0]
            logger.info(
                f"  搜索结果: {result['display_name']} ({result['asset_type_display']})"
            )

        # Get price with localized formatting
        price_data = get_asset_price(ticker, language=lang)
        if price_data["success"]:
            logger.info(f"  价格: {price_data['price_formatted']}")
            if price_data.get("change_percent_formatted"):
                logger.info(f"  涨跌: {price_data['change_percent_formatted']}")


def main():
    """Main demonstration function."""
    logger.info("=== ValueCell Asset Data Adapter Demo ===")

    try:
        # Setup adapters
        setup_adapters()

        # Run demonstrations
        demonstrate_asset_search()
        demonstrate_asset_info()
        demonstrate_price_data()
        demonstrate_watchlist_management()
        demonstrate_i18n_features()

        logger.info("\n=== Demo completed successfully! ===")

    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
