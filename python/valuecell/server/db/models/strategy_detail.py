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

    # Linkage identifiers
    compose_id = Column(
        String(200), nullable=True, index=True, comment="Compose cycle identifier"
    )
    # Trade identifier (unique per strategy)
    trade_id = Column(String(200), nullable=False, comment="Unique trade identifier")
    instruction_id = Column(
        String(200), nullable=True, index=True, comment="Originating instruction id"
    )

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
    avg_exec_price = Column(
        Numeric(20, 8), nullable=True, comment="Average execution price for fills"
    )
    unrealized_pnl = Column(
        Numeric(20, 8), nullable=True, comment="Unrealized PnL value"
    )
    realized_pnl = Column(
        Numeric(20, 8), nullable=True, comment="Realized PnL value (on close)"
    )
    realized_pnl_pct = Column(
        Numeric(10, 6), nullable=True, comment="Realized PnL percentage"
    )
    notional_entry = Column(
        Numeric(20, 8), nullable=True, comment="Entry notional in quote currency"
    )
    notional_exit = Column(
        Numeric(20, 8), nullable=True, comment="Exit notional in quote currency"
    )
    fee_cost = Column(
        Numeric(20, 8), nullable=True, comment="Total fees charged in quote currency"
    )

    # Timing
    holding_ms = Column(
        Integer, nullable=True, comment="Holding duration in milliseconds"
    )
    entry_time = Column(
        DateTime(timezone=True), nullable=True, comment="Entry time (UTC)"
    )
    exit_time = Column(
        DateTime(timezone=True), nullable=True, comment="Exit time (UTC)"
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
            "compose_id": self.compose_id,
            "instruction_id": self.instruction_id,
            "entry_price": float(self.entry_price)
            if self.entry_price is not None
            else None,
            "exit_price": float(self.exit_price)
            if self.exit_price is not None
            else None,
            "avg_exec_price": float(self.avg_exec_price)
            if self.avg_exec_price is not None
            else None,
            "unrealized_pnl": float(self.unrealized_pnl)
            if self.unrealized_pnl is not None
            else None,
            "realized_pnl": float(self.realized_pnl)
            if self.realized_pnl is not None
            else None,
            "realized_pnl_pct": float(self.realized_pnl_pct)
            if self.realized_pnl_pct is not None
            else None,
            "notional_entry": float(self.notional_entry)
            if self.notional_entry is not None
            else None,
            "notional_exit": float(self.notional_exit)
            if self.notional_exit is not None
            else None,
            "fee_cost": float(self.fee_cost) if self.fee_cost is not None else None,
            "holding_ms": int(self.holding_ms) if self.holding_ms is not None else None,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
