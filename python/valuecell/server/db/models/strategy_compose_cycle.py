"""
ValueCell Server - Strategy Compose Cycle Model

Represents a compose cycle aggregation for a strategy. Does NOT store prompts.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from .base import Base


class StrategyComposeCycle(Base):
    __tablename__ = "strategy_compose_cycles"

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

    # Compose timestamp
    compose_time = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    cycle_index = Column(
        Integer,
        nullable=True,
        comment="1-based compose cycle index captured from the coordinator",
    )

    # Optional rationale provided by LLM
    rationale = Column(Text, nullable=True, comment="Optional rationale text")

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
        UniqueConstraint("strategy_id", "compose_id", name="uq_strategy_compose_cycle"),
    )

    def __repr__(self) -> str:
        return (
            "<StrategyComposeCycle(id={id}, strategy_id='{strategy_id}', compose_id='{compose_id}', "
            "cycle_index={cycle_index})>"
        ).format(
            id=self.id,
            strategy_id=self.strategy_id,
            compose_id=self.compose_id,
            cycle_index=self.cycle_index,
        )
