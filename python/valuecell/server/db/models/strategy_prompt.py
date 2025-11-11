"""Strategy Prompt Model

Minimal table to store reusable strategy prompt texts.
No versioning, ownership, or permissions at this stage.
"""

import uuid
from typing import Any, Dict

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.sql import func

from .base import Base


class StrategyPrompt(Base):
    """Reusable prompt text for strategies."""

    __tablename__ = "strategy_prompts"

    id = Column(
        String(100), primary_key=True, default=lambda: "prompt-" + str(uuid.uuid4())
    )
    name = Column(String(200), nullable=False, comment="Prompt name (display)")
    content = Column(Text, nullable=False, comment="Full prompt text")

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<StrategyPrompt(id={self.id}, name='{self.name}')>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
