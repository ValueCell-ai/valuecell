"""
ValueCell Server - Strategy Holding Model

This module defines the database model for strategy holdings (position snapshots).
Each row represents one symbol position at a specific snapshot time for a strategy.
"""

from typing import Any, Dict

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from .base import Base


class StrategyHolding(Base):
    """Strategy holding (position) snapshot for a strategy.

    Stores simplified position fields for a symbol at a given snapshot time.
    """

    __tablename__ = "strategy_holdings"

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

    # Position fields (simplified)
    symbol = Column(String(50), nullable=False, index=True, comment="Instrument symbol")
    type = Column(String(20), nullable=False, comment="Position type: LONG/SHORT")
    leverage = Column(Numeric(10, 4), nullable=True, comment="Leverage ratio")
    entry_price = Column(Numeric(20, 8), nullable=True, comment="Average entry price")
    quantity = Column(
        Numeric(20, 8), nullable=False, comment="Position quantity (absolute)"
    )
    unrealized_pnl = Column(
        Numeric(20, 8), nullable=True, comment="Unrealized PnL value"
    )
    unrealized_pnl_pct = Column(
        Numeric(10, 4), nullable=True, comment="Unrealized PnL percentage"
    )

    # Snapshot time
    snapshot_ts = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Snapshot timestamp (UTC)",
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

    # Uniqueness: same strategy_id + symbol + snapshot_ts should be unique
    __table_args__ = (
        UniqueConstraint(
            "strategy_id", "symbol", "snapshot_ts", name="uq_strategy_holding_snapshot"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<StrategyHolding(id={self.id}, strategy_id='{self.strategy_id}', symbol='{self.symbol}', "
            f"type='{self.type}', quantity={self.quantity}, snapshot_ts={self.snapshot_ts})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "type": self.type,
            "leverage": float(self.leverage) if self.leverage is not None else None,
            "entry_price": float(self.entry_price)
            if self.entry_price is not None
            else None,
            "quantity": float(self.quantity) if self.quantity is not None else None,
            "unrealized_pnl": float(self.unrealized_pnl)
            if self.unrealized_pnl is not None
            else None,
            "unrealized_pnl_pct": float(self.unrealized_pnl_pct)
            if self.unrealized_pnl_pct is not None
            else None,
            "snapshot_ts": self.snapshot_ts.isoformat() if self.snapshot_ts else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
