"""
ValueCell Server - Strategy Portfolio View Model

Aggregated portfolio snapshot storing cash, equity, and unrealized PnL per
strategy at a specific timestamp. This complements StrategyHolding, which
captures per-symbol details.
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


class StrategyPortfolioView(Base):
    """Aggregated portfolio snapshot for a strategy."""

    __tablename__ = "strategy_portfolio_views"

    id = Column(Integer, primary_key=True, index=True)

    strategy_id = Column(
        String(100),
        ForeignKey("strategies.strategy_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Runtime strategy identifier",
    )

    cash = Column(Numeric(20, 8), nullable=False, comment="Cash balance at snapshot")
    total_value = Column(
        Numeric(20, 8), nullable=False, comment="Total portfolio value (equity)"
    )
    total_unrealized_pnl = Column(
        Numeric(20, 8), nullable=True, comment="Total unrealized PnL"
    )
    total_realized_pnl = Column(
        Numeric(20, 8), nullable=True, comment="Total realized PnL"
    )
    gross_exposure = Column(
        Numeric(20, 8), nullable=True, comment="Aggregate gross exposure at snapshot"
    )
    net_exposure = Column(
        Numeric(20, 8), nullable=True, comment="Aggregate net exposure at snapshot"
    )

    snapshot_ts = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Snapshot timestamp (UTC)",
    )

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "strategy_id",
            "snapshot_ts",
            name="uq_strategy_portfolio_snapshot",
        ),
    )

    def __repr__(self) -> str:
        return (
            "<StrategyPortfolioView(id={}, strategy_id='{}', cash={}, total_value={}, "
            "total_unrealized_pnl={}, total_realized_pnl={}, gross_exposure={}, net_exposure={}, snapshot_ts={})>"
        ).format(
            self.id,
            self.strategy_id,
            self.cash,
            self.total_value,
            self.total_unrealized_pnl,
            self.total_realized_pnl,
            self.gross_exposure,
            self.net_exposure,
            self.snapshot_ts,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "cash": float(self.cash) if self.cash is not None else None,
            "total_value": float(self.total_value)
            if self.total_value is not None
            else None,
            "total_unrealized_pnl": float(self.total_unrealized_pnl)
            if self.total_unrealized_pnl is not None
            else None,
            "total_realized_pnl": float(self.total_realized_pnl)
            if self.total_realized_pnl is not None
            else None,
            "gross_exposure": float(self.gross_exposure)
            if self.gross_exposure is not None
            else None,
            "net_exposure": float(self.net_exposure)
            if self.net_exposure is not None
            else None,
            "snapshot_ts": self.snapshot_ts.isoformat() if self.snapshot_ts else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
