"""ValueCell Asset Service Module.

This module provides high-level asset service functionality for financial asset management,
search, price retrieval, and watchlist operations with internationalization support.

Key Features:
- Asset search with localization
- Real-time and historical price data
- Watchlist management
- Multi-language support
- Integration with multiple data adapters

Usage Example:
    ```python
    from valuecell.services.assets import (
        get_asset_service, search_assets, add_to_watchlist
    )

    # Search for assets
    results = search_assets("AAPL", language="zh-Hans")

    # Add to watchlist
    add_to_watchlist(user_id="user123", ticker="NASDAQ:AAPL")
    ```
"""

from .asset_service import (
    AssetService,
    add_to_watchlist,
    get_asset_info,
    get_asset_price,
    get_asset_service,
    get_watchlist,
    reset_asset_service,
    search_assets,
)

__version__ = "1.0.0"

__all__ = [
    # Service class
    "AssetService",
    "get_asset_service",
    "reset_asset_service",
    # Convenience functions
    "search_assets",
    "get_asset_info",
    "get_asset_price",
    "add_to_watchlist",
    "get_watchlist",
]
