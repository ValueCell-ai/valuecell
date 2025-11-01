"""Watchlist related API routes."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query
from starlette.concurrency import run_in_threadpool

from ....utils.i18n_utils import parse_and_validate_utc_dates
from ...db.repositories.watchlist_repository import get_watchlist_repository
from ...services.assets.asset_service import get_asset_service
from ..schemas import (
    AddAssetRequest,
    AssetDetailData,
    AssetHistoricalPriceData,
    AssetHistoricalPricesData,
    AssetInfoData,
    AssetPriceData,
    AssetSearchResultData,
    CreateWatchlistRequest,
    SuccessResponse,
    UpdateAssetNotesRequest,
    WatchlistData,
    WatchlistItemData,
)

# Global default user ID for open source API
DEFAULT_USER_ID = "default_user"


def create_watchlist_router() -> APIRouter:
    """Create watchlist related routes."""
    router = APIRouter(prefix="/watchlist", tags=["Watchlist"])

    # Get dependencies
    asset_service = get_asset_service()
    watchlist_repo = get_watchlist_repository()

    @router.get(
        "/asset/search",
        response_model=SuccessResponse[AssetSearchResultData],
        summary="Search assets",
        description="Search for financial assets (stocks, etc.) with filtering options",
    )
    async def search_assets(
        q: str = Query(..., description="Search query", min_length=1),
        asset_types: Optional[str] = Query(
            None, description="Comma-separated asset types"
        ),
        exchanges: Optional[str] = Query(None, description="Comma-separated exchanges"),
        countries: Optional[str] = Query(None, description="Comma-separated countries"),
        limit: int = Query(50, description="Maximum results", ge=1, le=200),
        language: Optional[str] = Query(
            None, description="Language for localized results"
        ),
    ):
        """Search for financial assets."""
        try:
            # Parse comma-separated filters
            asset_types_list = asset_types.split(",") if asset_types else None
            exchanges_list = exchanges.split(",") if exchanges else None
            countries_list = countries.split(",") if countries else None

            # Perform search using asset service
            result = await run_in_threadpool(
                asset_service.search_assets,
                query=q,
                asset_types=asset_types_list,
                exchanges=exchanges_list,
                countries=countries_list,
                limit=limit,
                language=language,
            )

            if not result.get("success", False):
                raise HTTPException(
                    status_code=500, detail=result.get("error", "Search failed")
                )

            # Convert to response format
            search_result = AssetSearchResultData(
                results=[AssetInfoData(**asset) for asset in result["results"]],
                count=result["count"],
                query=result["query"],
                filters=result["filters"],
                language=result["language"],
            )

            return SuccessResponse.create(
                data=search_result, msg="Asset search completed successfully"
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

    @router.get(
        "/asset/{ticker}",
        response_model=SuccessResponse[AssetDetailData],
        summary="Get asset details",
        description="Get detailed information about a specific asset",
    )
    async def get_asset_detail(
        ticker: str = Path(..., description="Asset ticker"),
        language: Optional[str] = Query(
            None, description="Language for localized content"
        ),
    ):
        """Get detailed asset information."""
        try:
            result = await run_in_threadpool(
                asset_service.get_asset_info, ticker, language=language
            )

            if not result.get("success", False):
                if "not found" in result.get("error", "").lower():
                    raise HTTPException(
                        status_code=404, detail=f"Asset '{ticker}' not found"
                    )
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "Failed to get asset info"),
                )

            # Remove success field from result for AssetDetailData
            asset_data = {k: v for k, v in result.items() if k != "success"}
            asset_detail = AssetDetailData(**asset_data)

            return SuccessResponse.create(
                data=asset_detail, msg="Asset details retrieved successfully"
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Asset detail error: {str(e)}")

    @router.get(
        "/asset/{ticker}/price",
        response_model=SuccessResponse[AssetPriceData],
        summary="Get asset price",
        description="Get current price information for an asset",
    )
    async def get_asset_price(
        ticker: str = Path(..., description="Asset ticker"),
        language: Optional[str] = Query(
            None, description="Language for localized formatting"
        ),
    ):
        """Get current asset price."""
        try:
            result = await run_in_threadpool(
                asset_service.get_asset_price, ticker, language=language
            )

            if not result.get("success", False):
                if "not available" in result.get("error", "").lower():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Price data not available for '{ticker}'",
                    )
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "Failed to get price data"),
                )

            # Remove success field from result for AssetPriceData
            price_data = {k: v for k, v in result.items() if k != "success"}
            asset_price = AssetPriceData(**price_data)

            return SuccessResponse.create(
                data=asset_price, msg="Asset price retrieved successfully"
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Price data error: {str(e)}")

    @router.get(
        "/",
        response_model=SuccessResponse[List[WatchlistData]],
        summary="Get watchlists",
        description="Get all watchlists for the default user",
    )
    async def get_watchlists():
        """Get all watchlists for the default user."""
        try:
            watchlists = watchlist_repo.get_user_watchlists(DEFAULT_USER_ID)

            watchlist_data = []
            for watchlist in watchlists:
                # Convert items to data format
                items_data = []
                for item in watchlist.items:
                    item_dict = item.to_dict()
                    item_dict["exchange"] = item.exchange
                    item_dict["symbol"] = item.symbol
                    # Use display_name if available, otherwise fallback to symbol
                    if not item_dict.get("display_name"):
                        item_dict["display_name"] = item.symbol
                    items_data.append(WatchlistItemData(**item_dict))

                # Convert watchlist to data format
                watchlist_dict = watchlist.to_dict()
                watchlist_dict["items"] = items_data
                watchlist_data.append(WatchlistData(**watchlist_dict))

            return SuccessResponse.create(
                data=watchlist_data, msg=f"Retrieved {len(watchlist_data)} watchlists"
            )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get watchlists: {str(e)}"
            )

    @router.get(
        "/{watchlist_name}",
        response_model=SuccessResponse[WatchlistData],
        summary="Get specific watchlist",
        description="Get a specific watchlist by name with optional price data",
    )
    async def get_watchlist(
        watchlist_name: str = Path(..., description="Watchlist name"),
        include_prices: bool = Query(True, description="Include current prices"),
        language: Optional[str] = Query(
            None, description="Language for localized content"
        ),
    ):
        """Get a specific watchlist."""
        try:
            # Use asset service to get watchlist with prices
            result = await run_in_threadpool(
                asset_service.get_watchlist,
                user_id=DEFAULT_USER_ID,
                watchlist_name=watchlist_name,
                include_prices=include_prices,
                language=language,
            )

            if not result.get("success", False):
                if "not found" in result.get("error", "").lower():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Watchlist '{watchlist_name}' not found",
                    )
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "Failed to get watchlist"),
                )

            # Convert watchlist data
            watchlist_info = result["watchlist"]

            # Convert assets to WatchlistItemData format
            items_data = []
            for asset in watchlist_info.get("assets", []):
                symbol = (
                    asset["ticker"].split(":")[1]
                    if ":" in asset["ticker"]
                    else asset["ticker"]
                )
                item_data = {
                    "id": 0,  # This would be set from database
                    "ticker": asset["ticker"],
                    "display_name": asset.get("display_name")
                    or symbol,  # Use display_name or fallback to symbol
                    "notes": asset.get("notes", ""),
                    "order_index": asset.get("order", 0),
                    "added_at": asset["added_at"],
                    "updated_at": asset["added_at"],  # Fallback
                    "exchange": asset["ticker"].split(":")[0]
                    if ":" in asset["ticker"]
                    else "",
                    "symbol": symbol,
                }
                items_data.append(WatchlistItemData(**item_data))

            watchlist_data = WatchlistData(
                id=0,  # This would be set from database
                user_id=watchlist_info["user_id"],
                name=watchlist_info["name"],
                description=watchlist_info.get("description", ""),
                is_default=watchlist_info.get("is_default", False),
                is_public=watchlist_info.get("is_public", False),
                created_at=watchlist_info["created_at"],
                updated_at=watchlist_info["updated_at"],
                items_count=watchlist_info["items_count"],
                items=items_data,
            )

            return SuccessResponse.create(
                data=watchlist_data, msg="Watchlist retrieved successfully"
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get watchlist: {str(e)}"
            )

    @router.post(
        "/",
        response_model=SuccessResponse[WatchlistData],
        summary="Create watchlist",
        description="Create a new watchlist",
    )
    async def create_watchlist(
        request: CreateWatchlistRequest,
    ):
        """Create a new watchlist."""
        try:
            watchlist = watchlist_repo.create_watchlist(
                user_id=DEFAULT_USER_ID,
                name=request.name,
                description=request.description or "",
                is_default=request.is_default,
                is_public=request.is_public,
            )

            if not watchlist:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to create watchlist. Watchlist '{request.name}' may already exist.",
                )

            # Convert to response format
            watchlist_dict = watchlist.to_dict()
            watchlist_dict["items"] = []
            watchlist_data = WatchlistData(**watchlist_dict)

            return SuccessResponse.create(
                data=watchlist_data, msg="Watchlist created successfully"
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create watchlist: {str(e)}"
            )

    @router.post(
        "/asset",
        response_model=SuccessResponse[dict],
        summary="Add asset to watchlist",
        description="Add a asset to a watchlist",
    )
    async def add_asset_to_watchlist(request: AddAssetRequest):
        """Add a asset to a watchlist."""
        try:
            success = watchlist_repo.add_asset_to_watchlist(
                user_id=DEFAULT_USER_ID,
                ticker=request.ticker,
                watchlist_name=request.watchlist_name,
                display_name=request.display_name,
                notes=request.notes or "",
            )

            if not success:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to add asset '{request.ticker}' to watchlist. Asset may already exist or watchlist not found.",
                )

            return SuccessResponse.create(
                data={
                    "ticker": request.ticker,
                    "watchlist_name": request.watchlist_name,
                    "notes": request.notes,
                },
                msg="Asset added to watchlist successfully",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to add asset: {str(e)}"
            )

    @router.delete(
        "/asset/{ticker}",
        response_model=SuccessResponse[dict],
        summary="Remove asset from watchlist",
        description="Remove a asset from a watchlist",
    )
    async def remove_asset_from_watchlist(
        ticker: str = Path(..., description="Asset ticker to remove"),
        watchlist_name: Optional[str] = Query(
            None, description="Watchlist name (uses default if not provided)"
        ),
    ):
        """Remove a asset from a watchlist."""
        try:
            success = watchlist_repo.remove_asset_from_watchlist(
                user_id=DEFAULT_USER_ID, ticker=ticker, watchlist_name=watchlist_name
            )

            if not success:
                raise HTTPException(
                    status_code=404,
                    detail=f"Asset '{ticker}' not found in watchlist or watchlist not found",
                )

            return SuccessResponse.create(
                data={
                    "ticker": ticker,
                    "watchlist_name": watchlist_name,
                },
                msg="Asset removed from watchlist successfully",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to remove asset: {str(e)}"
            )

    @router.delete(
        "/{watchlist_name}",
        response_model=SuccessResponse[dict],
        summary="Delete watchlist",
        description="Delete a watchlist",
    )
    async def delete_watchlist(
        watchlist_name: str = Path(..., description="Watchlist name to delete"),
    ):
        """Delete a watchlist."""
        try:
            success = watchlist_repo.delete_watchlist(
                user_id=DEFAULT_USER_ID, watchlist_name=watchlist_name
            )

            if not success:
                raise HTTPException(
                    status_code=404,
                    detail=f"Watchlist '{watchlist_name}' not found",
                )

            return SuccessResponse.create(
                data={"watchlist_name": watchlist_name},
                msg="Watchlist deleted successfully",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete watchlist: {str(e)}"
            )

    @router.put(
        "/asset/{ticker}/notes",
        response_model=SuccessResponse[dict],
        summary="Update asset notes",
        description="Update notes for a asset in a watchlist",
    )
    async def update_asset_notes(
        request: UpdateAssetNotesRequest,
        ticker: str = Path(..., description="Asset ticker"),
        watchlist_name: Optional[str] = Query(
            None, description="Watchlist name (uses default if not provided)"
        ),
    ):
        """Update notes for a asset in a watchlist."""
        try:
            success = watchlist_repo.update_asset_notes(
                user_id=DEFAULT_USER_ID,
                ticker=ticker,
                notes=request.notes,
                watchlist_name=watchlist_name,
            )

            if not success:
                raise HTTPException(
                    status_code=404,
                    detail=f"Asset '{ticker}' not found in watchlist or watchlist not found",
                )

            return SuccessResponse.create(
                data={
                    "ticker": ticker,
                    "notes": request.notes,
                    "watchlist_name": watchlist_name,
                },
                msg="Asset notes updated successfully",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update notes: {str(e)}"
            )

    @router.get(
        "/asset/{ticker}/price/historical",
        response_model=SuccessResponse[AssetHistoricalPricesData],
        summary="Get historical asset prices",
        description="Get historical price data for a specific asset",
    )
    async def get_asset_historical_prices(
        ticker: str = Path(..., description="Asset ticker"),
        start_date: Optional[str] = Query(
            None,
            description="Start date in UTC format (YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS.fffZ), defaults to 30 days ago",
        ),
        end_date: Optional[str] = Query(
            None,
            description="End date in UTC format (YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS.fffZ), defaults to now",
        ),
        interval: str = Query("1d", description="Data interval (1d, 1h, 5m, etc.)"),
        language: Optional[str] = Query(
            None, description="Language for localized formatting"
        ),
    ):
        """Get historical prices for a asset."""
        try:
            # Parse and validate UTC dates using i18n_utils
            start_dt, end_dt = parse_and_validate_utc_dates(start_date, end_date)

            # Get historical price data
            result = await run_in_threadpool(
                asset_service.get_historical_prices,
                ticker,
                start_dt,
                end_dt,
                interval,
                language,
            )

            if not result.get("success", False):
                if "not available" in result.get("error", "").lower():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Historical price data not available for '{ticker}'",
                    )
                raise HTTPException(
                    status_code=500,
                    detail=result.get("error", "Failed to get historical price data"),
                )

            # Convert prices to AssetHistoricalPriceData format
            historical_prices = []
            for price_data in result.get("prices", []):
                historical_price = AssetHistoricalPriceData(**price_data)
                historical_prices.append(historical_price)

            # Create response data
            historical_data = AssetHistoricalPricesData(
                ticker=result["ticker"],
                start_date=result["start_date"],
                end_date=result["end_date"],
                interval=result["interval"],
                currency=result["currency"],
                prices=historical_prices,
                count=result["count"],
            )

            return SuccessResponse.create(
                data=historical_data, msg="Historical prices retrieved successfully"
            )

        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid UTC datetime format: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Historical price error: {str(e)}"
            )

    return router
