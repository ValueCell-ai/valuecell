"""Assets router for ValueCell Server."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...config.database import get_db
from ...services.assets.asset_service import AssetService
from ..schemas.assets import (
    AssetResponse,
    AssetPriceResponse,
    AssetSearchRequest,
)

router = APIRouter()


@router.get("/search", response_model=List[AssetResponse])
async def search_assets(
    query: str = Query(..., description="Search query for assets"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """Search for assets by symbol or name."""
    asset_service = AssetService(db)
    return await asset_service.search_assets(query, limit)


@router.get("/{symbol}", response_model=AssetResponse)
async def get_asset(
    symbol: str,
    db: Session = Depends(get_db)
):
    """Get asset information by symbol."""
    asset_service = AssetService(db)
    asset = await asset_service.get_asset(symbol)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with symbol '{symbol}' not found"
        )
    return asset


@router.get("/{symbol}/price", response_model=AssetPriceResponse)
async def get_asset_price(
    symbol: str,
    period: Optional[str] = Query("1d", description="Time period (1d, 1w, 1m, 3m, 6m, 1y)"),
    db: Session = Depends(get_db)
):
    """Get current and historical price data for an asset."""
    asset_service = AssetService(db)
    price_data = await asset_service.get_asset_price(symbol, period)
    if not price_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Price data for asset '{symbol}' not found"
        )
    return price_data


@router.get("/", response_model=List[AssetResponse])
async def list_assets(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type (stock, crypto, forex)"),
    db: Session = Depends(get_db)
):
    """List assets with pagination and filtering."""
    asset_service = AssetService(db)
    return await asset_service.list_assets(skip, limit, asset_type)