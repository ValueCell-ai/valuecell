"""
ValueCell Server - Strategy Stop Prices Model

This module defines the database model for strategy stop price records.
Each row represents a stop gain & loss info associated with a strategy and symbol.
"""

from typing import Any, Dict

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from .base import Base


class StrategyStopPrices(Base):
    """Strategy detail record for trades/positions associated with a strategy."""

    __tablename__ = "strategy_stop_prices"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to strategies (uses unique strategy_id)
    strategy_id = Column(
        String(100),
        ForeignKey("strategies.strategy_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Runtime strategy identifier",
    )

    # Instrument and trade info
    symbol = Column(String(50), nullable=False, index=True, comment="Instrument symbol")
    stop_gain_price = Column(
        Numeric(20, 8), nullable=True, comment="Price to stop gain"
    )
    stop_loss_price = Column(
        Numeric(20, 8), nullable=True, comment="Price to stop loss"
    )

    # Notes
    note = Column(Text, nullable=True, comment="Optional note")

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

    # Uniqueness: strategy_id + trade_id must be unique
    __table_args__ = (
        UniqueConstraint("strategy_id", "symbol", name="uq_strategy_id_symbol"),
    )

    def __repr__(self) -> str:
        return (
            f"<StrategyStopPrices(id={self.id}, strategy_id='{self.strategy_id}', symbol='{self.symbol}', "
            f"stop_gain_price='{self.stop_gain_price}', stop_loss_price='{self.stop_loss_price}', updated_at={self.updated_at})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "stop_gain_price": (
                float(self.stop_gain_price)
                if self.stop_gain_price is not None
                else None
            ),
            "stop_loss_price": (
                float(self.stop_loss_price)
                if self.stop_loss_price is not None
                else None
            ),
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
