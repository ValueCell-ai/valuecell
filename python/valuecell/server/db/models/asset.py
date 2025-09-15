"""Asset model for ValueCell Server."""

from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, String, Text, Boolean, DateTime, DECIMAL, Integer
from sqlalchemy.sql import func
import uuid
from .base import Base


class Asset(Base):
    """Asset model for storing financial instruments and market data."""
    
    __tablename__ = "assets"
    
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    symbol = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    asset_type = Column(String(50), nullable=False, index=True)  # stock, crypto, forex, etc.
    exchange = Column(String(100), nullable=True, index=True)
    currency = Column(String(10), nullable=False, default="USD")
    
    # Market data
    market_cap = Column(DECIMAL(20, 2), nullable=True)
    sector = Column(String(100), nullable=True, index=True)
    industry = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Metadata
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Data source tracking
    data_source = Column(String(100), nullable=True)  # yahoo, alpha_vantage, etc.
    last_price_update = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<Asset(id='{self.id}', symbol='{self.symbol}', name='{self.name}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert asset to dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "asset_type": self.asset_type,
            "exchange": self.exchange,
            "currency": self.currency,
            "market_cap": str(self.market_cap) if self.market_cap else None,
            "sector": self.sector,
            "industry": self.industry,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "data_source": self.data_source,
            "last_price_update": self.last_price_update.isoformat() if self.last_price_update else None,
        }


class AssetPrice(Base):
    """Asset price model for storing historical price data."""
    
    __tablename__ = "asset_prices"
    
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    asset_id = Column(String, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    
    # Price data
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open_price = Column(DECIMAL(20, 8), nullable=False)
    high_price = Column(DECIMAL(20, 8), nullable=False)
    low_price = Column(DECIMAL(20, 8), nullable=False)
    close_price = Column(DECIMAL(20, 8), nullable=False)
    volume = Column(Integer, nullable=True)
    
    # Adjusted prices (for stocks)
    adjusted_close = Column(DECIMAL(20, 8), nullable=True)
    
    # Metadata
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    data_source = Column(String(100), nullable=True)
    
    def __repr__(self) -> str:
        return f"<AssetPrice(symbol='{self.symbol}', timestamp='{self.timestamp}', close='{self.close_price}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert asset price to dictionary."""
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "open": str(self.open_price),
            "high": str(self.high_price),
            "low": str(self.low_price),
            "close": str(self.close_price),
            "volume": self.volume,
            "adjusted_close": str(self.adjusted_close) if self.adjusted_close else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "data_source": self.data_source,
        }