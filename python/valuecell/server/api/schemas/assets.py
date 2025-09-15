"""Asset schemas for ValueCell Server."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class AssetBase(BaseModel):
    """Base asset model."""
    
    symbol: str = Field(..., description="Asset symbol (e.g., AAPL, BTC)")
    name: str = Field(..., description="Asset name")
    asset_type: str = Field(..., description="Asset type (stock, crypto, forex, etc.)")
    exchange: Optional[str] = Field(None, description="Exchange where the asset is traded")
    currency: str = Field("USD", description="Base currency")


class AssetResponse(AssetBase):
    """Response model for asset data."""
    
    id: str = Field(..., description="Asset ID")
    market_cap: Optional[Decimal] = Field(None, description="Market capitalization")
    sector: Optional[str] = Field(None, description="Asset sector")
    industry: Optional[str] = Field(None, description="Asset industry")
    description: Optional[str] = Field(None, description="Asset description")
    is_active: bool = Field(True, description="Whether the asset is actively traded")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "asset_123",
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "asset_type": "stock",
                "exchange": "NASDAQ",
                "currency": "USD",
                "market_cap": "3000000000000",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "description": "Apple Inc. designs, manufactures, and markets smartphones...",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class PricePoint(BaseModel):
    """Single price point model."""
    
    timestamp: datetime = Field(..., description="Price timestamp")
    open: Decimal = Field(..., description="Opening price")
    high: Decimal = Field(..., description="Highest price")
    low: Decimal = Field(..., description="Lowest price")
    close: Decimal = Field(..., description="Closing price")
    volume: Optional[int] = Field(None, description="Trading volume")
    
    class Config:
        schema_extra = {
            "example": {
                "timestamp": "2024-01-01T00:00:00Z",
                "open": "150.00",
                "high": "155.00",
                "low": "149.00",
                "close": "154.00",
                "volume": 1000000
            }
        }


class AssetPriceResponse(BaseModel):
    """Response model for asset price data."""
    
    symbol: str = Field(..., description="Asset symbol")
    current_price: Decimal = Field(..., description="Current price")
    price_change: Decimal = Field(..., description="Price change from previous close")
    price_change_percent: Decimal = Field(..., description="Price change percentage")
    period: str = Field(..., description="Time period for historical data")
    historical_data: List[PricePoint] = Field(..., description="Historical price data")
    last_updated: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "current_price": "154.00",
                "price_change": "2.50",
                "price_change_percent": "1.65",
                "period": "1d",
                "historical_data": [
                    {
                        "timestamp": "2024-01-01T00:00:00Z",
                        "open": "150.00",
                        "high": "155.00",
                        "low": "149.00",
                        "close": "154.00",
                        "volume": 1000000
                    }
                ],
                "last_updated": "2024-01-01T16:00:00Z"
            }
        }


class AssetSearchRequest(BaseModel):
    """Request model for asset search."""
    
    query: str = Field(..., description="Search query")
    asset_types: Optional[List[str]] = Field(None, description="Filter by asset types")
    exchanges: Optional[List[str]] = Field(None, description="Filter by exchanges")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Apple",
                "asset_types": ["stock"],
                "exchanges": ["NASDAQ"],
                "limit": 10
            }
        }