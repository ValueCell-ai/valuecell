"""
ValueCell Server - Watchlist Models

This module defines the database models for user watchlists in the ValueCell system.
"""

from typing import Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Watchlist(Base):
    """
    Watchlist model representing user's stock watchlists.

    This table stores information about user watchlists including name, description,
    and metadata.
    """

    __tablename__ = "watchlists"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # User identification (using string for flexibility)
    user_id = Column(
        String(100),
        nullable=False,
        index=True,
        comment="User identifier who owns this watchlist",
    )

    # Watchlist information
    name = Column(String(200), nullable=False, comment="Name of the watchlist")
    description = Column(Text, nullable=True, comment="Description of the watchlist")

    # Status
    is_default = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this is the user's default watchlist",
    )
    is_public = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this watchlist is public",
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

    # Relationships
    items = relationship(
        "WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan"
    )

    # Unique constraint for user_id + name
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_watchlist_name"),
    )

    def __repr__(self):
        return (
            f"<Watchlist(id={self.id}, user_id='{self.user_id}', name='{self.name}')>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert watchlist to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "is_default": self.is_default,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "items_count": len(self.items) if self.items else 0,
        }


class WatchlistItem(Base):
    """
    WatchlistItem model representing individual stocks in a watchlist.

    This table stores the relationship between watchlists and assets,
    using the format "EXCHANGE:SYMBOL" for stock identification.
    """

    __tablename__ = "watchlist_items"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to watchlist
    watchlist_id = Column(
        Integer,
        ForeignKey("watchlists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Stock information in format "EXCHANGE:SYMBOL" (e.g., "NASDAQ:AAPL", "NYSE:TSLA")
    ticker = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Stock ticker in format 'EXCHANGE:SYMBOL' (e.g., NASDAQ:AAPL)",
    )

    # User notes about this stock
    notes = Column(Text, nullable=True, comment="User notes about this stock")

    # Display order in the watchlist
    order_index = Column(
        Integer, default=0, nullable=False, comment="Display order in the watchlist"
    )

    # Timestamps
    added_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the stock was added to the watchlist",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    watchlist = relationship("Watchlist", back_populates="items")

    # Unique constraint for watchlist_id + ticker
    __table_args__ = (
        UniqueConstraint("watchlist_id", "ticker", name="uq_watchlist_ticker"),
    )

    def __repr__(self):
        return f"<WatchlistItem(id={self.id}, watchlist_id={self.watchlist_id}, ticker='{self.ticker}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert watchlist item to dictionary representation."""
        return {
            "id": self.id,
            "watchlist_id": self.watchlist_id,
            "ticker": self.ticker,
            "notes": self.notes,
            "order_index": self.order_index,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def exchange(self) -> str:
        """Extract exchange from ticker format 'EXCHANGE:SYMBOL'."""
        return self.ticker.split(":")[0] if ":" in self.ticker else ""

    @property
    def symbol(self) -> str:
        """Extract symbol from ticker format 'EXCHANGE:SYMBOL'."""
        return self.ticker.split(":")[1] if ":" in self.ticker else self.ticker
