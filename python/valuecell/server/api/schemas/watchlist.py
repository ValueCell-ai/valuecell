"""API schemas for watchlist operations."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WatchlistItemData(BaseModel):
    """Watchlist item data schema."""

    id: int = Field(..., description="Item ID")
    ticker: str = Field(..., description="Asset ticker in format 'EXCHANGE:SYMBOL'")
    display_name: Optional[str] = Field(
        None,
        description="Display name from search results, falls back to symbol if not available",
    )
    notes: Optional[str] = Field(None, description="User notes about the asset")
    order_index: int = Field(..., description="Display order in the watchlist")
    added_at: datetime = Field(..., description="When the asset was added")
    updated_at: datetime = Field(..., description="When the item was last updated")

    # Derived properties
    exchange: str = Field(..., description="Exchange extracted from ticker")
    symbol: str = Field(..., description="Symbol extracted from ticker")


class WatchlistData(BaseModel):
    """Watchlist data schema."""

    id: int = Field(..., description="Watchlist ID")
    user_id: str = Field(..., description="User ID who owns the watchlist")
    name: str = Field(..., description="Watchlist name")
    description: Optional[str] = Field(None, description="Watchlist description")
    is_default: bool = Field(..., description="Whether this is the default watchlist")
    is_public: bool = Field(..., description="Whether this watchlist is public")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    items_count: int = Field(..., description="Number of items in the watchlist")
    items: Optional[List[WatchlistItemData]] = Field(
        None, description="Watchlist items"
    )


class CreateWatchlistRequest(BaseModel):
    """Request schema for creating a watchlist."""

    name: str = Field(..., description="Watchlist name", min_length=1, max_length=200)
    description: Optional[str] = Field(
        None, description="Watchlist description", max_length=1000
    )
    is_default: bool = Field(False, description="Whether this is the default watchlist")
    is_public: bool = Field(False, description="Whether this watchlist is public")


class AddAssetRequest(BaseModel):
    """Request schema for adding a asset to watchlist."""

    ticker: str = Field(
        ...,
        description="Asset ticker in format 'EXCHANGE:SYMBOL'",
        min_length=1,
        max_length=50,
    )
    display_name: Optional[str] = Field(
        None, description="Display name from search results", max_length=200
    )
    watchlist_name: Optional[str] = Field(
        None, description="Watchlist name (uses default if not provided)"
    )
    notes: Optional[str] = Field(
        "", description="User notes about the asset", max_length=1000
    )


class UpdateAssetNotesRequest(BaseModel):
    """Request schema for updating asset notes."""

    notes: str = Field(..., description="Updated notes", max_length=1000)


class AssetSearchQuery(BaseModel):
    """Request schema for asset search."""

    query: str = Field(..., description="Search query", min_length=1)
    asset_types: Optional[List[str]] = Field(None, description="Filter by asset types")
    exchanges: Optional[List[str]] = Field(None, description="Filter by exchanges")
    countries: Optional[List[str]] = Field(None, description="Filter by countries")
    limit: int = Field(50, description="Maximum number of results", ge=1, le=200)
    language: Optional[str] = Field(None, description="Language for localized results")


class AssetInfoData(BaseModel):
    """Asset information data schema."""

    ticker: str = Field(..., description="Asset ticker")
    asset_type: str = Field(..., description="Asset type")
    asset_type_display: str = Field(
        ..., description="Localized asset type display name"
    )
    names: dict = Field(..., description="Asset names in different languages")
    display_name: str = Field(..., description="Display name in requested language")
    exchange: Optional[str] = Field(None, description="Exchange")
    country: Optional[str] = Field(None, description="Country")
    currency: Optional[str] = Field(None, description="Currency")
    market_status: Optional[str] = Field(None, description="Market status")
    market_status_display: Optional[str] = Field(
        None, description="Localized market status display"
    )


class AssetSearchResultData(BaseModel):
    """Asset search result data schema."""

    results: List[AssetInfoData] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results")
    query: str = Field(..., description="Original search query")
    filters: dict = Field(..., description="Applied filters")
    language: str = Field(..., description="Language used for results")


class AssetDetailData(BaseModel):
    """Asset detail data schema."""

    ticker: str = Field(..., description="Asset ticker")
    asset_type: str = Field(..., description="Asset type")
    asset_type_display: str = Field(
        ..., description="Localized asset type display name"
    )
    names: dict = Field(..., description="Asset names in different languages")
    display_name: str = Field(..., description="Display name in requested language")
    descriptions: Optional[dict] = Field(None, description="Asset descriptions")
    market_info: dict = Field(..., description="Market information")
    source_mappings: dict = Field(..., description="Source mappings")
    properties: Optional[dict] = Field(None, description="Additional properties")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Update timestamp")
    is_active: bool = Field(..., description="Whether the asset is active")


class AssetPriceData(BaseModel):
    """Asset price data schema."""

    ticker: str = Field(..., description="Asset ticker")
    price: float = Field(..., description="Current price")
    price_formatted: str = Field(..., description="Formatted price with currency")
    currency: str = Field(..., description="Currency")
    timestamp: str = Field(..., description="Price timestamp")
    volume: Optional[float] = Field(None, description="Trading volume")
    open_price: Optional[float] = Field(None, description="Opening price")
    high_price: Optional[float] = Field(None, description="High price")
    low_price: Optional[float] = Field(None, description="Low price")
    close_price: Optional[float] = Field(None, description="Closing price")
    change: Optional[float] = Field(None, description="Price change")
    change_percent: Optional[float] = Field(None, description="Percentage change")
    change_percent_formatted: Optional[str] = Field(
        None, description="Formatted percentage change"
    )
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    market_cap_formatted: Optional[str] = Field(
        None, description="Formatted market cap"
    )
    source: Optional[str] = Field(None, description="Data source")


class AssetHistoricalPriceData(BaseModel):
    """Historical price data for an asset."""

    ticker: str = Field(..., description="Asset ticker")
    timestamp: str = Field(..., description="Price timestamp")
    price: float = Field(..., description="Close price")
    open_price: Optional[float] = Field(None, description="Opening price")
    high_price: Optional[float] = Field(None, description="High price")
    low_price: Optional[float] = Field(None, description="Low price")
    close_price: Optional[float] = Field(None, description="Closing price")
    volume: Optional[float] = Field(None, description="Trading volume")
    change: Optional[float] = Field(None, description="Price change")
    change_percent: Optional[float] = Field(None, description="Percentage change")
    currency: str = Field(..., description="Currency")
    source: Optional[str] = Field(None, description="Data source")


class AssetHistoricalPricesData(BaseModel):
    """Historical prices data response."""

    ticker: str = Field(..., description="Asset ticker")
    start_date: str = Field(..., description="Start date")
    end_date: str = Field(..., description="End date")
    interval: str = Field(..., description="Data interval")
    currency: str = Field(..., description="Currency")
    prices: List[AssetHistoricalPriceData] = Field(
        ..., description="Historical price data"
    )
    count: int = Field(..., description="Number of price points")


class WatchlistWithPricesData(BaseModel):
    """Watchlist data with price information."""

    watchlist: WatchlistData = Field(..., description="Watchlist information")
    prices: Optional[dict] = Field(None, description="Price data for watchlist items")
