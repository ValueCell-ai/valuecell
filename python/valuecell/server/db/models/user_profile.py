"""User profile model for ValueCell application."""

import enum

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.sql import func

from .base import Base


class ProfileCategory(str, enum.Enum):
    """User profile memory category."""

    # User profile categories
    PRODUCT_BEHAVIOR = "product_behavior"  # User's behavior on products
    RISK_PREFERENCE = "risk_preference"  # User's risk preference
    READING_PREFERENCE = "reading_preference"  # User's reading preference


class UserProfile(Base):
    """User profile model storing user preferences and memories."""

    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True, comment="User ID")
    category = Column(
        Enum(ProfileCategory),
        nullable=False,
        index=True,
        comment="Memory category",
    )
    content = Column(Text, nullable=False, comment="Profile content in string format")
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="Creation timestamp",
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<UserProfile(id={self.id}, user_id={self.user_id}, category={self.category}, content={self.content[:50]}...)>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category": self.category.value if self.category else None,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
