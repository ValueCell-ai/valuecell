"""Asset service for asset management and watchlist operations.

This module provides high-level service functions for asset search, watchlist management,
and price data retrieval with i18n support.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ....adapters.assets.i18n_integration import get_asset_i18n_service
from ....adapters.assets.manager import get_adapter_manager, get_watchlist_manager
from ....adapters.assets.types import AssetSearchQuery, AssetType
from ...config.i18n import get_i18n_config

logger = logging.getLogger(__name__)


class AssetService:
    """High-level service for asset operations with i18n support."""

    def __init__(self):
        """Initialize asset service."""
        self.adapter_manager = get_adapter_manager()
        self.watchlist_manager = get_watchlist_manager()
        self.i18n_service = get_asset_i18n_service()
        self._watchlist_repository = None

    @property
    def watchlist_repository(self):
        """Lazy load watchlist repository to avoid circular imports."""
        if self._watchlist_repository is None:
            from ...db.repositories.watchlist_repository import get_watchlist_repository

            self._watchlist_repository = get_watchlist_repository()
        return self._watchlist_repository

    def search_assets(
        self,
        query: str,
        asset_types: Optional[List[str]] = None,
        exchanges: Optional[List[str]] = None,
        countries: Optional[List[str]] = None,
        limit: int = 50,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search for assets with localization support.

        Args:
            query: Search query string
            asset_types: Filter by asset types (optional)
            exchanges: Filter by exchanges (optional)
            countries: Filter by countries (optional)
            limit: Maximum number of results
            language: Language for localized results

        Returns:
            Dictionary containing search results and metadata
        """
        try:
            # Convert string asset types to enum
            parsed_asset_types = None
            if asset_types:
                parsed_asset_types = []
                for asset_type_str in asset_types:
                    try:
                        parsed_asset_types.append(AssetType(asset_type_str.lower()))
                    except ValueError:
                        logger.warning(f"Invalid asset type: {asset_type_str}")

            # Create search query
            search_query = AssetSearchQuery(
                query=query,
                asset_types=parsed_asset_types,
                exchanges=exchanges,
                countries=countries,
                limit=limit,
                language=language or get_i18n_config().language,
            )

            # Perform search
            results = self.adapter_manager.search_assets(search_query)

            # Localize results
            localized_results = self.i18n_service.localize_search_results(
                results, language
            )

            # Convert to dictionary format
            result_dicts = []
            for result in localized_results:
                result_dict = {
                    "ticker": result.ticker,
                    "asset_type": result.asset_type.value,
                    "asset_type_display": self.i18n_service.get_asset_type_display_name(
                        result.asset_type, language
                    ),
                    "names": result.names,
                    "display_name": result.get_display_name(
                        language or get_i18n_config().language
                    ),
                    "exchange": result.exchange,
                    "country": result.country,
                }
                result_dicts.append(result_dict)

            return {
                "success": True,
                "results": result_dicts,
                "count": len(result_dicts),
                "query": query,
                "filters": {
                    "asset_types": asset_types,
                    "exchanges": exchanges,
                    "countries": countries,
                    "limit": limit,
                },
                "language": language or get_i18n_config().language,
            }

        except Exception as e:
            logger.error(f"Error searching assets: {e}")
            return {"success": False, "error": str(e), "results": [], "count": 0}

    def get_asset_info(
        self, ticker: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get detailed asset information with localization.

        Args:
            ticker: Asset ticker in internal format
            language: Language for localized content

        Returns:
            Dictionary containing asset information
        """
        try:
            asset = self.adapter_manager.get_asset_info(ticker)

            if not asset:
                return {"success": False, "error": "Asset not found", "ticker": ticker}

            # Localize asset
            localized_asset = self.i18n_service.localize_asset(asset, language)

            # Convert to dictionary
            asset_dict = {
                "success": True,
                "ticker": localized_asset.ticker,
                "asset_type": localized_asset.asset_type.value,
                "asset_type_display": self.i18n_service.get_asset_type_display_name(
                    localized_asset.asset_type, language
                ),
                "names": localized_asset.names.names,
                "display_name": localized_asset.get_localized_name(
                    language or get_i18n_config().language
                ),
                "descriptions": localized_asset.descriptions,
                "market_info": {
                    "exchange": localized_asset.market_info.exchange,
                    "country": localized_asset.market_info.country,
                    "currency": localized_asset.market_info.currency,
                    "timezone": localized_asset.market_info.timezone,
                    "trading_hours": localized_asset.market_info.trading_hours,
                    "market_status": localized_asset.market_info.market_status.value,
                },
                "source_mappings": {
                    k.value: v for k, v in localized_asset.source_mappings.items()
                },
                "properties": localized_asset.properties,
                "created_at": localized_asset.created_at.isoformat(),
                "updated_at": localized_asset.updated_at.isoformat(),
                "is_active": localized_asset.is_active,
            }

            return asset_dict

        except Exception as e:
            logger.error(f"Error getting asset info for {ticker}: {e}")
            return {"success": False, "error": str(e), "ticker": ticker}

    def get_asset_price(
        self, ticker: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current price for an asset with localized formatting.

        Args:
            ticker: Asset ticker in internal format
            language: Language for localized formatting

        Returns:
            Dictionary containing price information
        """
        try:
            price_data = self.adapter_manager.get_real_time_price(ticker)

            if not price_data:
                return {
                    "success": False,
                    "error": "Price data not available",
                    "ticker": ticker,
                }

            # Get asset_type from database to handle formatting correctly
            asset_type = None
            try:
                from ...db.repositories.asset_repository import get_asset_repository

                asset_repo = get_asset_repository()
                db_asset = asset_repo.get_asset_by_symbol(ticker)
                if db_asset:
                    asset_type = db_asset.asset_type
            except Exception as e:
                logger.debug(
                    f"Could not get asset_type from database for {ticker}: {e}"
                )
                # If asset not in database, it will be treated as a regular asset with currency

            # Format price data with localization
            formatted_price = {
                "success": True,
                "ticker": price_data.ticker,
                "price": float(price_data.price),
                "price_formatted": self.i18n_service.format_currency_amount(
                    float(price_data.price),
                    price_data.currency,
                    language,
                    asset_type,
                ),
                "currency": price_data.currency,
                "timestamp": price_data.timestamp.isoformat(),
                "volume": float(price_data.volume) if price_data.volume else None,
                "open_price": float(price_data.open_price)
                if price_data.open_price
                else None,
                "high_price": float(price_data.high_price)
                if price_data.high_price
                else None,
                "low_price": float(price_data.low_price)
                if price_data.low_price
                else None,
                "close_price": float(price_data.close_price)
                if price_data.close_price
                else None,
                "change": float(price_data.change) if price_data.change else None,
                "change_percent": float(price_data.change_percent)
                if price_data.change_percent
                else None,
                "change_percent_formatted": self.i18n_service.format_percentage_change(
                    float(price_data.change_percent), language
                )
                if price_data.change_percent
                else None,
                "market_cap": float(price_data.market_cap)
                if price_data.market_cap
                else None,
                "market_cap_formatted": self.i18n_service.format_market_cap(
                    float(price_data.market_cap), price_data.currency, language
                )
                if price_data.market_cap
                else None,
                "source": price_data.source.value if price_data.source else None,
            }

            return formatted_price

        except Exception as e:
            logger.error(f"Error getting price for {ticker}: {e}")
            return {"success": False, "error": str(e), "ticker": ticker}

    def get_multiple_prices(
        self, tickers: List[str], language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get prices for multiple assets efficiently.

        Args:
            tickers: List of asset tickers
            language: Language for localized formatting

        Returns:
            Dictionary containing price data for all tickers
        """
        try:
            price_data = self.adapter_manager.get_multiple_prices(tickers)

            # Get asset_types from database for all tickers in batch
            asset_types = {}
            try:
                from ...db.repositories.asset_repository import get_asset_repository

                asset_repo = get_asset_repository()
                for ticker in tickers:
                    db_asset = asset_repo.get_asset_by_symbol(ticker)
                    if db_asset:
                        asset_types[ticker] = db_asset.asset_type
            except Exception as e:
                logger.debug(f"Could not get asset_types from database: {e}")

            formatted_prices = {}

            for ticker, price in price_data.items():
                if price:
                    asset_type = asset_types.get(ticker)
                    formatted_prices[ticker] = {
                        "price": float(price.price),
                        "price_formatted": self.i18n_service.format_currency_amount(
                            float(price.price), price.currency, language, asset_type
                        ),
                        "currency": price.currency,
                        "timestamp": price.timestamp.isoformat(),
                        "change": float(price.change) if price.change else None,
                        "change_percent": float(price.change_percent)
                        if price.change_percent
                        else None,
                        "change_percent_formatted": self.i18n_service.format_percentage_change(
                            float(price.change_percent), language
                        )
                        if price.change_percent
                        else None,
                        "volume": float(price.volume) if price.volume else None,
                        "market_cap": float(price.market_cap)
                        if price.market_cap
                        else None,
                        "market_cap_formatted": self.i18n_service.format_market_cap(
                            float(price.market_cap), price.currency, language
                        )
                        if price.market_cap
                        else None,
                        "source": price.source.value if price.source else None,
                    }
                else:
                    formatted_prices[ticker] = None

            return {
                "success": True,
                "prices": formatted_prices,
                "count": len([p for p in formatted_prices.values() if p is not None]),
                "requested_count": len(tickers),
            }

        except Exception as e:
            logger.error(f"Error getting multiple prices: {e}")
            return {"success": False, "error": str(e), "prices": {}}

    def get_historical_prices(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get historical price data for an asset with localized formatting.

        Args:
            ticker: Asset ticker in internal format
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval (e.g., "1d", "1h", "5m")
            language: Language for localized formatting

        Returns:
            Dictionary containing historical price data
        """
        try:
            historical_prices = self.adapter_manager.get_historical_prices(
                ticker, start_date, end_date, interval
            )

            if not historical_prices:
                return {
                    "success": False,
                    "error": "Historical price data not available",
                    "ticker": ticker,
                }

            # Format historical price data with localization
            formatted_prices = []
            for price_data in historical_prices:
                formatted_price = {
                    "ticker": price_data.ticker,
                    "timestamp": price_data.timestamp.isoformat(),
                    "price": float(price_data.price),
                    "open_price": float(price_data.open_price)
                    if price_data.open_price
                    else None,
                    "high_price": float(price_data.high_price)
                    if price_data.high_price
                    else None,
                    "low_price": float(price_data.low_price)
                    if price_data.low_price
                    else None,
                    "close_price": float(price_data.close_price)
                    if price_data.close_price
                    else None,
                    "volume": float(price_data.volume) if price_data.volume else None,
                    "change": float(price_data.change) if price_data.change else None,
                    "change_percent": float(price_data.change_percent)
                    if price_data.change_percent
                    else None,
                    "currency": price_data.currency,
                    "source": price_data.source.value if price_data.source else None,
                }
                formatted_prices.append(formatted_price)

            return {
                "success": True,
                "ticker": ticker,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "interval": interval,
                "currency": historical_prices[0].currency
                if historical_prices
                else "USD",
                "prices": formatted_prices,
                "count": len(formatted_prices),
            }

        except Exception as e:
            logger.error(f"Error getting historical prices for {ticker}: {e}")
            return {"success": False, "error": str(e), "ticker": ticker}

    def create_watchlist(
        self,
        user_id: str,
        name: str = "My Watchlist",
        description: str = "",
        is_default: bool = False,
    ) -> Dict[str, Any]:
        """Create a new watchlist for a user.

        Args:
            user_id: User identifier
            name: Watchlist name
            description: Watchlist description
            is_default: Whether this is the default watchlist

        Returns:
            Dictionary containing created watchlist information
        """
        try:
            watchlist = self.watchlist_manager.create_watchlist(
                user_id, name, description, is_default
            )

            return {
                "success": True,
                "watchlist": {
                    "user_id": watchlist.user_id,
                    "name": watchlist.name,
                    "description": watchlist.description,
                    "created_at": watchlist.created_at.isoformat(),
                    "updated_at": watchlist.updated_at.isoformat(),
                    "is_default": watchlist.is_default,
                    "is_public": watchlist.is_public,
                    "items_count": len(watchlist.items),
                },
            }

        except Exception as e:
            logger.error(f"Error creating watchlist: {e}")
            return {"success": False, "error": str(e)}

    def add_to_watchlist(
        self,
        user_id: str,
        ticker: str,
        watchlist_name: Optional[str] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Add an asset to a watchlist.

        Args:
            user_id: User identifier
            ticker: Asset ticker to add
            watchlist_name: Watchlist name (uses default if None)
            notes: User notes about the asset

        Returns:
            Dictionary containing operation result
        """
        try:
            success = self.watchlist_manager.add_asset_to_watchlist(
                user_id, ticker, watchlist_name, notes
            )

            if success:
                return {
                    "success": True,
                    "message": "Asset added to watchlist successfully",
                    "ticker": ticker,
                    "user_id": user_id,
                    "watchlist_name": watchlist_name,
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to add asset to watchlist",
                    "ticker": ticker,
                }

        except Exception as e:
            logger.error(f"Error adding {ticker} to watchlist: {e}")
            return {"success": False, "error": str(e), "ticker": ticker}

    def remove_from_watchlist(
        self, user_id: str, ticker: str, watchlist_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Remove an asset from a watchlist.

        Args:
            user_id: User identifier
            ticker: Asset ticker to remove
            watchlist_name: Watchlist name (uses default if None)

        Returns:
            Dictionary containing operation result
        """
        try:
            success = self.watchlist_manager.remove_asset_from_watchlist(
                user_id, ticker, watchlist_name
            )

            if success:
                return {
                    "success": True,
                    "message": "Asset removed from watchlist successfully",
                    "ticker": ticker,
                    "user_id": user_id,
                    "watchlist_name": watchlist_name,
                }
            else:
                return {
                    "success": False,
                    "error": "Asset not found in watchlist or watchlist not found",
                    "ticker": ticker,
                }

        except Exception as e:
            logger.error(f"Error removing {ticker} from watchlist: {e}")
            return {"success": False, "error": str(e), "ticker": ticker}

    def get_watchlist(
        self,
        user_id: str,
        watchlist_name: Optional[str] = None,
        include_prices: bool = True,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get watchlist with asset information and prices.

        Args:
            user_id: User identifier
            watchlist_name: Watchlist name (uses default if None)
            include_prices: Whether to include current prices
            language: Language for localized content

        Returns:
            Dictionary containing watchlist data
        """
        try:
            # Get watchlist from database
            if watchlist_name:
                watchlist = self.watchlist_repository.get_watchlist(
                    user_id, watchlist_name
                )
            else:
                watchlist = self.watchlist_repository.get_default_watchlist(user_id)

            if not watchlist:
                return {
                    "success": False,
                    "error": "Watchlist not found",
                    "user_id": user_id,
                    "watchlist_name": watchlist_name,
                }

            # Get asset information and prices
            assets_data = []
            tickers = [item.ticker for item in watchlist.items]

            # Get prices if requested
            prices_data = {}
            if include_prices and tickers:
                prices_result = self.get_multiple_prices(tickers, language)
                if prices_result["success"]:
                    prices_data = prices_result["prices"]

            # Build asset data
            for item in sorted(watchlist.items, key=lambda x: x.order_index):
                asset_data = {
                    "ticker": item.ticker,
                    "display_name": self.i18n_service.get_localized_asset_name(
                        item.ticker, language
                    ),
                    "added_at": item.added_at.isoformat(),
                    "order": item.order_index,
                    "notes": item.notes or "",
                    "alerts": [],  # Database model doesn't have alerts field
                }

                # Add price data if available
                if item.ticker in prices_data and prices_data[item.ticker]:
                    asset_data["price_data"] = prices_data[item.ticker]

                assets_data.append(asset_data)

            return {
                "success": True,
                "watchlist": {
                    "user_id": watchlist.user_id,
                    "name": watchlist.name,
                    "description": watchlist.description or "",
                    "created_at": watchlist.created_at.isoformat(),
                    "updated_at": watchlist.updated_at.isoformat(),
                    "is_default": watchlist.is_default,
                    "is_public": watchlist.is_public,
                    "items_count": len(watchlist.items),
                    "assets": assets_data,
                },
            }

        except Exception as e:
            logger.error(f"Error getting watchlist: {e}")
            return {"success": False, "error": str(e), "user_id": user_id}

    def get_user_watchlists(self, user_id: str) -> Dict[str, Any]:
        """Get all watchlists for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary containing all user watchlists
        """
        try:
            watchlists = self.watchlist_manager.get_user_watchlists(user_id)

            watchlists_data = []
            for watchlist in watchlists:
                watchlist_data = {
                    "name": watchlist.name,
                    "description": watchlist.description,
                    "created_at": watchlist.created_at.isoformat(),
                    "updated_at": watchlist.updated_at.isoformat(),
                    "is_default": watchlist.is_default,
                    "is_public": watchlist.is_public,
                    "items_count": len(watchlist.items),
                }
                watchlists_data.append(watchlist_data)

            return {
                "success": True,
                "user_id": user_id,
                "watchlists": watchlists_data,
                "count": len(watchlists_data),
            }

        except Exception as e:
            logger.error(f"Error getting user watchlists: {e}")
            return {"success": False, "error": str(e), "user_id": user_id}


# Global service instance
_asset_service: Optional[AssetService] = None


def get_asset_service() -> AssetService:
    """Get global asset service instance."""
    global _asset_service
    if _asset_service is None:
        _asset_service = AssetService()
    return _asset_service


def reset_asset_service() -> None:
    """Reset global asset service instance (mainly for testing)."""
    global _asset_service
    _asset_service = None


# Convenience functions for direct service access
def search_assets(query: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for asset search."""
    return get_asset_service().search_assets(query, **kwargs)


def get_asset_info(ticker: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for getting asset info."""
    return get_asset_service().get_asset_info(ticker, **kwargs)


def get_asset_price(ticker: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for getting asset price."""
    return get_asset_service().get_asset_price(ticker, **kwargs)


def add_to_watchlist(user_id: str, ticker: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for adding to watchlist."""
    return get_asset_service().add_to_watchlist(user_id, ticker, **kwargs)


def get_watchlist(user_id: str, **kwargs) -> Dict[str, Any]:
    """Convenience function for getting watchlist."""
    return get_asset_service().get_watchlist(user_id, **kwargs)
