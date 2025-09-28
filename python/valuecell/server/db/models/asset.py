"""
ValueCell Server - Asset Models

This module defines the database models for assets in the ValueCell system.
"""

from typing import Any, Dict

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from .base import Base


class Asset(Base):
    """
    Asset model representing financial assets in the ValueCell system.

    This table stores information about financial assets including stocks, bonds,
    cryptocurrencies, and other investment instruments.
    """

    __tablename__ = "assets"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Basic asset information
    symbol = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Asset symbol/ticker (e.g., AAPL, BTC, etc.)",
    )
    name = Column(String(200), nullable=False, comment="Full name of the asset")
    description = Column(
        Text,
        nullable=True,
        comment="Detailed description of the asset",
    )

    # Asset classification
    asset_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of asset (stock, bond, crypto, commodity, etc.)",
    )
    sector = Column(
        String(100),
        nullable=True,
        comment="Industry sector (for stocks)",
    )

    # Market data
    current_price = Column(
        Numeric(precision=20, scale=8),
        nullable=True,
        comment="Current market price",
    )

    # Status and availability
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the asset is active",
    )

    # Metadata and configuration
    asset_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata (ISIN, CUSIP, fundamental data, etc.)",
    )
    config = Column(
        JSON,
        nullable=True,
        comment="Asset-specific configuration parameters",
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<Asset(id={self.id}, symbol='{self.symbol}', name='{self.name}', type='{self.asset_type}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert asset to dictionary representation."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "description": self.description,
            "asset_type": self.asset_type,
            "sector": self.sector,
            "current_price": float(self.current_price) if self.current_price else None,
            "is_active": self.is_active,
            "metadata": self.asset_metadata,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_config(cls, config_data: Dict[str, Any]) -> "Asset":
        """Create an Asset instance from configuration data."""
        return cls(
            symbol=config_data.get("symbol"),
            name=config_data.get("name"),
            description=config_data.get("description"),
            asset_type=config_data.get("asset_type", "stock"),
            sector=config_data.get("sector"),
            current_price=config_data.get("current_price"),
            is_active=config_data.get("is_active", True),
            asset_metadata=config_data.get("metadata"),
            config=config_data.get("config"),
        )
