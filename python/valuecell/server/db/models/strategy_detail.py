"""
ValueCell Server - Strategy Detail Model

This module defines the database model for strategy trade/details records.
Each row represents one trade/position detail associated with a strategy.
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


class StrategyDetail(Base):
    """Strategy detail record for trades/positions associated with a strategy."""

    __tablename__ = "strategy_details"

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

    # Trade identifier (unique per strategy)
    trade_id = Column(String(200), nullable=False, comment="Unique trade identifier")

    # Instrument and trade info
    symbol = Column(String(50), nullable=False, index=True, comment="Instrument symbol")
    type = Column(String(20), nullable=False, comment="Position type: LONG/SHORT")
    side = Column(String(20), nullable=False, comment="Trade side: BUY/SELL")
    leverage = Column(Numeric(10, 4), nullable=True, comment="Leverage ratio")
    quantity = Column(
        Numeric(20, 8), nullable=False, comment="Trade quantity (absolute)"
    )

    # Prices and PnL
    entry_price = Column(Numeric(20, 8), nullable=True, comment="Entry price")
    exit_price = Column(Numeric(20, 8), nullable=True, comment="Exit price (if closed)")
    unrealized_pnl = Column(
        Numeric(20, 8), nullable=True, comment="Unrealized PnL value"
    )

    # Timing
    holding_ms = Column(
        Integer, nullable=True, comment="Holding duration in milliseconds"
    )
    event_time = Column(
        DateTime(timezone=True), nullable=True, comment="Entry time (UTC)"
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
        UniqueConstraint("strategy_id", "trade_id", name="uq_strategy_trade_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<StrategyDetail(id={self.id}, strategy_id='{self.strategy_id}', trade_id='{self.trade_id}', "
            f"symbol='{self.symbol}', type='{self.type}', side='{self.side}', quantity={self.quantity})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "type": self.type,
            "side": self.side,
            "leverage": float(self.leverage) if self.leverage is not None else None,
            "quantity": float(self.quantity) if self.quantity is not None else None,
            "entry_price": float(self.entry_price)
            if self.entry_price is not None
            else None,
            "exit_price": float(self.exit_price)
            if self.exit_price is not None
            else None,
            "unrealized_pnl": float(self.unrealized_pnl)
            if self.unrealized_pnl is not None
            else None,
            "holding_ms": int(self.holding_ms) if self.holding_ms is not None else None,
            "time": self.event_time.isoformat() if self.event_time else None,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
