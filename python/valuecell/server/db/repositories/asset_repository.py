"""Asset repository for ValueCell Server."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from ..models.asset import Asset, AssetPrice
from ...config.logging import get_logger

logger = get_logger(__name__)


class AssetRepository:
    """Repository for asset data access."""
    
    def __init__(self, db: Session):
        """Initialize asset repository."""
        self.db = db
    
    async def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Get asset by ID."""
        try:
            return self.db.query(Asset).filter(Asset.id == asset_id).first()
        except Exception as e:
            logger.error(f"Error getting asset {asset_id}", exc_info=True)
            return None
    
    async def get_asset_by_symbol(self, symbol: str) -> Optional[Asset]:
        """Get asset by symbol."""
        try:
            return self.db.query(Asset).filter(Asset.symbol == symbol.upper()).first()
        except Exception as e:
            logger.error(f"Error getting asset by symbol {symbol}", exc_info=True)
            return None
    
    async def list_assets(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        order_desc: bool = False,
    ) -> List[Asset]:
        """List assets with optional filtering and pagination."""
        try:
            query = self.db.query(Asset)
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if hasattr(Asset, key):
                        if isinstance(value, list):
                            query = query.filter(getattr(Asset, key).in_(value))
                        else:
                            query = query.filter(getattr(Asset, key) == value)
            
            # Apply ordering
            if hasattr(Asset, order_by):
                order_column = getattr(Asset, order_by)
                if order_desc:
                    query = query.order_by(order_column.desc())
                else:
                    query = query.order_by(order_column)
            
            # Apply pagination
            return query.offset(skip).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error listing assets", exc_info=True)
            return []
    
    async def search_assets(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Asset]:
        """Search assets by symbol, name, or description."""
        try:
            db_query = self.db.query(Asset)
            
            # Text search
            search_filter = or_(
                Asset.symbol.ilike(f"%{query}%"),
                Asset.name.ilike(f"%{query}%"),
                Asset.description.ilike(f"%{query}%")
            )
            db_query = db_query.filter(search_filter)
            
            # Apply additional filters
            if filters:
                for key, value in filters.items():
                    if hasattr(Asset, key):
                        if isinstance(value, list):
                            db_query = db_query.filter(getattr(Asset, key).in_(value))
                        else:
                            db_query = db_query.filter(getattr(Asset, key) == value)
            
            return db_query.limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error searching assets with query: {query}", exc_info=True)
            return []
    
    async def create_asset(self, asset: Asset) -> Asset:
        """Create a new asset."""
        try:
            self.db.add(asset)
            self.db.commit()
            self.db.refresh(asset)
            logger.info(f"Created asset: {asset.id}")
            return asset
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating asset", exc_info=True)
            raise
    
    async def update_asset(self, asset: Asset) -> Asset:
        """Update an existing asset."""
        try:
            self.db.commit()
            self.db.refresh(asset)
            logger.info(f"Updated asset: {asset.id}")
            return asset
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating asset {asset.id}", exc_info=True)
            raise
    
    async def delete_asset(self, asset_id: str) -> bool:
        """Delete an asset."""
        try:
            asset = await self.get_asset(asset_id)
            if asset:
                self.db.delete(asset)
                self.db.commit()
                logger.info(f"Deleted asset: {asset_id}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting asset {asset_id}", exc_info=True)
            return False
    
    # Asset Price methods
    
    async def get_latest_price(self, symbol: str) -> Optional[AssetPrice]:
        """Get the latest price for an asset."""
        try:
            return (
                self.db.query(AssetPrice)
                .filter(AssetPrice.symbol == symbol.upper())
                .order_by(desc(AssetPrice.timestamp))
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}", exc_info=True)
            return None
    
    async def get_price_history(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AssetPrice]:
        """Get price history for an asset."""
        try:
            query = (
                self.db.query(AssetPrice)
                .filter(AssetPrice.symbol == symbol.upper())
            )
            
            if start_date:
                query = query.filter(AssetPrice.timestamp >= start_date)
            if end_date:
                query = query.filter(AssetPrice.timestamp <= end_date)
            
            return (
                query
                .order_by(desc(AssetPrice.timestamp))
                .limit(limit)
                .all()
            )
            
        except Exception as e:
            logger.error(f"Error getting price history for {symbol}", exc_info=True)
            return []
    
    async def create_price(self, price: AssetPrice) -> AssetPrice:
        """Create a new price record."""
        try:
            self.db.add(price)
            self.db.commit()
            self.db.refresh(price)
            return price
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating price record", exc_info=True)
            raise
    
    async def bulk_create_prices(self, prices: List[AssetPrice]) -> bool:
        """Bulk create price records."""
        try:
            self.db.add_all(prices)
            self.db.commit()
            logger.info(f"Created {len(prices)} price records")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error bulk creating price records", exc_info=True)
            return False
    
    async def count_assets(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count assets with optional filtering."""
        try:
            query = self.db.query(Asset)
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if hasattr(Asset, key):
                        if isinstance(value, list):
                            query = query.filter(getattr(Asset, key).in_(value))
                        else:
                            query = query.filter(getattr(Asset, key) == value)
            
            return query.count()
            
        except Exception as e:
            logger.error(f"Error counting assets", exc_info=True)
            return 0