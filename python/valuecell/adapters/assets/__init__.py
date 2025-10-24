"""ValueCell Asset Data Adapter Module.

This module provides a comprehensive system for managing financial asset data
across multiple data sources with support for internationalization and user
watchlists.

Key Features:
- Multi-source data adapters (Yahoo Finance, TuShare, CoinMarketCap, etc.)
- Standardized asset representation with ticker format [EXCHANGE]:[SYMBOL]
- User watchlist management with persistent storage
- Internationalization support for asset names and UI text
- Real-time and historical price data
- Asset search across different markets and types

Usage Example:
    ```python
    from valuecell.adapters.assets import (
        get_adapter_manager, get_watchlist_manager
    )
    from valuecell.services.assets import (
        get_asset_service, search_assets, add_to_watchlist
    )

    # Search for assets (now via service layer)
    results = search_assets("AAPL", language="zh-Hans")

    # Add to watchlist (now via service layer)
    add_to_watchlist(user_id="user123", ticker="NASDAQ:AAPL")
    ```
"""

from .akshare_adapter import AKShareAdapter

# Base adapter classes
from .base import (
    AdapterCapability,
    BaseDataAdapter,
)

# Internationalization support
from .i18n_integration import (
    AssetI18nService,
    get_asset_i18n_service,
    reset_asset_i18n_service,
)

# Management and coordination
from .manager import (
    AdapterManager,
    WatchlistManager,
    get_adapter_manager,
    get_watchlist_manager,
    reset_managers,
)

# Core types and data structures
from .types import (
    Asset,
    AssetPrice,
    AssetSearchQuery,
    AssetSearchResult,
    AssetType,
    DataSource,
    Exchange,
    LocalizedName,
    MarketInfo,
    MarketStatus,
    Watchlist,
    WatchlistItem,
)

# Specific adapter implementations
from .yfinance_adapter import YFinanceAdapter

# Note: High-level asset service functions have been moved to valuecell.services.assets
# Import from there for asset search, price retrieval, and watchlist operations

__version__ = "1.0.0"

__all__ = [
    # Types
    "Asset",
    "AssetPrice",
    "AssetSearchResult",
    "AssetSearchQuery",
    "AssetType",
    "MarketStatus",
    "DataSource",
    "Exchange",
    "MarketInfo",
    "LocalizedName",
    "Watchlist",
    "WatchlistItem",
    # Base classes
    "BaseDataAdapter",
    "AdapterCapability",
    # Adapters
    "YFinanceAdapter",
    "AKShareAdapter",
    # Managers
    "AdapterManager",
    "WatchlistManager",
    "get_adapter_manager",
    "get_watchlist_manager",
    "reset_managers",
    # I18n
    "AssetI18nService",
    "get_asset_i18n_service",
    "reset_asset_i18n_service",
]
