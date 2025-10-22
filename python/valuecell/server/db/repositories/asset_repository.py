"""
ValueCell Server - Asset Repository

This module provides database operations for asset management.
"""

from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..connection import get_database_manager
from ..models.asset import Asset


class AssetRepository:
    """Repository class for asset database operations."""

    def __init__(self, db_session: Optional[Session] = None):
        """Initialize repository with optional database session."""
        self.db_session = db_session

    def _get_session(self) -> Session:
        """Get database session."""
        if self.db_session:
            return self.db_session
        return get_database_manager().get_session()

    def create_asset(
        self,
        symbol: str,
        name: str,
        asset_type: str,
        description: Optional[str] = None,
        sector: Optional[str] = None,
        current_price: Optional[float] = None,
        is_active: bool = True,
        asset_metadata: Optional[dict] = None,
        config: Optional[dict] = None,
    ) -> Optional[Asset]:
        """Create a new asset.

        Args:
            symbol: Asset symbol/ticker (e.g., NASDAQ:AAPL)
            name: Full name of the asset
            asset_type: Type of asset (stock, bond, crypto, etc.)
            description: Detailed description of the asset
            sector: Industry sector (for stocks)
            current_price: Current market price
            is_active: Whether the asset is active
            asset_metadata: Additional metadata
            config: Asset-specific configuration parameters

        Returns:
            Created Asset object or None if creation fails
        """
        session = self._get_session()

        try:
            asset = Asset(
                symbol=symbol,
                name=name,
                asset_type=asset_type,
                description=description,
                sector=sector,
                current_price=current_price,
                is_active=is_active,
                asset_metadata=asset_metadata,
                config=config,
            )

            session.add(asset)
            session.commit()
            session.refresh(asset)

            # Expunge to avoid session issues
            session.expunge(asset)

            return asset

        except IntegrityError:
            session.rollback()
            return None
        except Exception:
            session.rollback()
            return None
        finally:
            if not self.db_session:
                session.close()

    def get_asset_by_symbol(self, symbol: str) -> Optional[Asset]:
        """Get asset by symbol.

        Args:
            symbol: Asset symbol/ticker

        Returns:
            Asset object or None if not found
        """
        session = self._get_session()

        try:
            asset = session.query(Asset).filter_by(symbol=symbol).first()

            if asset:
                # Expunge to avoid session issues
                session.expunge(asset)

            return asset

        finally:
            if not self.db_session:
                session.close()

    def get_asset_by_id(self, asset_id: int) -> Optional[Asset]:
        """Get asset by ID.

        Args:
            asset_id: Asset ID

        Returns:
            Asset object or None if not found
        """
        session = self._get_session()

        try:
            asset = session.query(Asset).filter_by(id=asset_id).first()

            if asset:
                # Expunge to avoid session issues
                session.expunge(asset)

            return asset

        finally:
            if not self.db_session:
                session.close()

    def get_all_assets(
        self, is_active: Optional[bool] = None, limit: Optional[int] = None
    ) -> List[Asset]:
        """Get all assets with optional filtering.

        Args:
            is_active: Filter by active status (None for all)
            limit: Maximum number of results

        Returns:
            List of Asset objects
        """
        session = self._get_session()

        try:
            query = session.query(Asset)

            if is_active is not None:
                query = query.filter(Asset.is_active == is_active)

            if limit:
                query = query.limit(limit)

            assets = query.all()

            # Expunge all assets to avoid session issues
            for asset in assets:
                session.expunge(asset)

            return assets

        finally:
            if not self.db_session:
                session.close()

    def update_asset(
        self,
        symbol: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        asset_type: Optional[str] = None,
        sector: Optional[str] = None,
        current_price: Optional[float] = None,
        is_active: Optional[bool] = None,
        asset_metadata: Optional[dict] = None,
        config: Optional[dict] = None,
    ) -> Optional[Asset]:
        """Update an existing asset.

        Args:
            symbol: Asset symbol/ticker
            name: Full name of the asset (if updating)
            description: Detailed description (if updating)
            asset_type: Type of asset (if updating)
            sector: Industry sector (if updating)
            current_price: Current market price (if updating)
            is_active: Whether the asset is active (if updating)
            asset_metadata: Additional metadata (if updating)
            config: Asset-specific configuration (if updating)

        Returns:
            Updated Asset object or None if not found
        """
        session = self._get_session()

        try:
            asset = session.query(Asset).filter_by(symbol=symbol).first()

            if not asset:
                return None

            # Update fields if provided
            if name is not None:
                asset.name = name
            if description is not None:
                asset.description = description
            if asset_type is not None:
                asset.asset_type = asset_type
            if sector is not None:
                asset.sector = sector
            if current_price is not None:
                asset.current_price = current_price
            if is_active is not None:
                asset.is_active = is_active
            if asset_metadata is not None:
                asset.asset_metadata = asset_metadata
            if config is not None:
                asset.config = config

            session.commit()
            session.refresh(asset)

            # Expunge to avoid session issues
            session.expunge(asset)

            return asset

        except Exception:
            session.rollback()
            return None
        finally:
            if not self.db_session:
                session.close()

    def update_asset_metadata(
        self, symbol: str, metadata_updates: dict
    ) -> Optional[Asset]:
        """Update asset metadata by merging new data with existing.

        Args:
            symbol: Asset symbol/ticker
            metadata_updates: Dictionary of metadata updates to merge

        Returns:
            Updated Asset object or None if not found
        """
        session = self._get_session()

        try:
            asset = session.query(Asset).filter_by(symbol=symbol).first()

            if not asset:
                return None

            # Merge metadata
            existing_metadata = asset.asset_metadata or {}
            existing_metadata.update(metadata_updates)
            asset.asset_metadata = existing_metadata

            session.commit()
            session.refresh(asset)

            # Expunge to avoid session issues
            session.expunge(asset)

            return asset

        except Exception:
            session.rollback()
            return None
        finally:
            if not self.db_session:
                session.close()

    def delete_asset(self, symbol: str) -> bool:
        """Delete an asset by symbol.

        Args:
            symbol: Asset symbol/ticker

        Returns:
            True if deleted successfully, False otherwise
        """
        session = self._get_session()

        try:
            asset = session.query(Asset).filter_by(symbol=symbol).first()

            if not asset:
                return False

            session.delete(asset)
            session.commit()

            return True

        except Exception:
            session.rollback()
            return False
        finally:
            if not self.db_session:
                session.close()

    def asset_exists(self, symbol: str) -> bool:
        """Check if an asset exists by symbol.

        Args:
            symbol: Asset symbol/ticker

        Returns:
            True if asset exists, False otherwise
        """
        session = self._get_session()

        try:
            exists = session.query(Asset).filter_by(symbol=symbol).first() is not None
            return exists

        finally:
            if not self.db_session:
                session.close()

    def upsert_asset(
        self,
        symbol: str,
        name: str,
        asset_type: str,
        description: Optional[str] = None,
        sector: Optional[str] = None,
        current_price: Optional[float] = None,
        is_active: bool = True,
        asset_metadata: Optional[dict] = None,
        config: Optional[dict] = None,
    ) -> Optional[Asset]:
        """Create or update an asset by symbol.

        If asset exists, updates all provided fields.
        If asset doesn't exist, creates a new one.

        Args:
            symbol: Asset symbol/ticker (e.g., NASDAQ:AAPL)
            name: Full name of the asset
            asset_type: Type of asset (stock, bond, crypto, index, etc.)
            description: Detailed description of the asset
            sector: Industry sector (for stocks)
            current_price: Current market price
            is_active: Whether the asset is active
            asset_metadata: Additional metadata
            config: Asset-specific configuration parameters

        Returns:
            Created or updated Asset object or None if operation fails
        """
        session = self._get_session()

        try:
            # Try to find existing asset
            asset = session.query(Asset).filter_by(symbol=symbol).first()

            if asset:
                # Update existing asset
                asset.name = name
                asset.asset_type = asset_type
                if description is not None:
                    asset.description = description
                if sector is not None:
                    asset.sector = sector
                if current_price is not None:
                    asset.current_price = current_price
                asset.is_active = is_active
                if asset_metadata is not None:
                    asset.asset_metadata = asset_metadata
                if config is not None:
                    asset.config = config
            else:
                # Create new asset
                asset = Asset(
                    symbol=symbol,
                    name=name,
                    asset_type=asset_type,
                    description=description,
                    sector=sector,
                    current_price=current_price,
                    is_active=is_active,
                    asset_metadata=asset_metadata,
                    config=config,
                )
                session.add(asset)

            session.commit()
            session.refresh(asset)

            # Expunge to avoid session issues
            session.expunge(asset)

            return asset

        except Exception:
            session.rollback()
            return None
        finally:
            if not self.db_session:
                session.close()


# Global repository instance
_asset_repository: Optional[AssetRepository] = None


def get_asset_repository(db_session: Optional[Session] = None) -> AssetRepository:
    """Get global asset repository instance or create with custom session.

    Args:
        db_session: Optional database session. If provided, creates new instance.

    Returns:
        AssetRepository instance
    """
    global _asset_repository

    if db_session:
        # Return new instance with custom session
        return AssetRepository(db_session)

    if _asset_repository is None:
        _asset_repository = AssetRepository()

    return _asset_repository


def reset_asset_repository() -> None:
    """Reset global asset repository instance (mainly for testing)."""
    global _asset_repository
    _asset_repository = None
