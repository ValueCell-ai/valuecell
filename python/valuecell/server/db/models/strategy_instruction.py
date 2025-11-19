"""
ValueCell Server - Strategy Instruction Model

Represents an instruction produced in a compose cycle. Includes NOOP.
"""

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


class StrategyInstruction(Base):
    __tablename__ = "strategy_instructions"

    id = Column(Integer, primary_key=True, index=True)

    strategy_id = Column(
        String(100),
        ForeignKey("strategies.strategy_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Runtime strategy identifier",
    )

    compose_id = Column(
        String(200), nullable=False, index=True, comment="Compose cycle identifier"
    )

    instruction_id = Column(
        String(200), nullable=False, index=True, comment="Deterministic instruction id"
    )

    # Minimal instruction payload for aggregation
    symbol = Column(String(50), nullable=False, index=True, comment="Instrument symbol")
    action = Column(String(50), nullable=True, comment="LLM action (open/close/noop)")
    side = Column(String(20), nullable=True, comment="Derived execution side BUY/SELL")
    quantity = Column(Numeric(20, 8), nullable=True, comment="Order quantity")
    leverage = Column(Numeric(10, 4), nullable=True, comment="Leverage multiple")

    note = Column(Text, nullable=True, comment="Optional instruction note")

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
            "instruction_id",
            name="uq_strategy_instruction_id",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<StrategyInstruction(id={self.id}, strategy_id='{self.strategy_id}', compose_id='{self.compose_id}',"
            f" instruction_id='{self.instruction_id}', symbol='{self.symbol}', action='{self.action}')>"
        )
