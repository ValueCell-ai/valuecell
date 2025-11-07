"""
ValueCell Server - Strategy Models

This module defines the database model for strategies created via StrategyAgent.
"""

from typing import Any, Dict

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from .base import Base


class Strategy(Base):
    """Strategy model representing created strategies in the ValueCell system."""

    __tablename__ = "strategies"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Strategy identifiers and basic info
    strategy_id = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Runtime strategy identifier from StrategyAgent",
    )
    name = Column(String(200), nullable=True, comment="User-defined strategy name")
    description = Column(Text, nullable=True, comment="Optional description")

    # Ownership and status
    user_id = Column(String(100), nullable=True, index=True, comment="Owner user id")
    status = Column(
        String(50), nullable=False, default="running", comment="Strategy status"
    )

    # Configuration and metadata
    config = Column(JSON, nullable=True, comment="Original UserRequest configuration")
    strategy_metadata = Column(
        JSON, nullable=True, comment="Additional metadata (agent, model provider, etc.)"
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
        return f"<Strategy(id={self.id}, strategy_id='{self.strategy_id}', name='{self.name}', status='{self.status}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy to dictionary representation."""
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "status": self.status,
            "config": self.config,
            "metadata": self.strategy_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
