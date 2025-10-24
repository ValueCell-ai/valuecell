from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConversationStatus(str, Enum):
    """Conversation status enumeration for tracking lifecycle state."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    REQUIRE_USER_INPUT = "require_user_input"


class Conversation(BaseModel):
    """Conversation data model - lightweight metadata only, items stored separately.

    Conversation objects hold metadata about a conversation; message items
    are stored in a separate ItemStore implementation.
    """

    conversation_id: str = Field(..., description="Unique conversation identifier")
    user_id: str = Field(..., description="User ID")
    title: Optional[str] = Field(None, description="Conversation title")
    agent_name: Optional[str] = Field(None, description="Agent name")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update time"
    )
    status: ConversationStatus = Field(
        default=ConversationStatus.ACTIVE, description="Conversation status"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    @property
    def is_active(self) -> bool:
        """Backward compatibility property - returns True if conversation is active"""
        return self.status == ConversationStatus.ACTIVE

    def set_status(self, status: ConversationStatus) -> None:
        """Update conversation status and timestamp"""
        self.status = status
        self.updated_at = datetime.now()

    def activate(self) -> None:
        """Set conversation to active status"""
        self.set_status(ConversationStatus.ACTIVE)

    def deactivate(self) -> None:
        """Set conversation to inactive status"""
        self.set_status(ConversationStatus.INACTIVE)

    def require_user_input(self) -> None:
        """Set conversation to require user input status"""
        self.set_status(ConversationStatus.REQUIRE_USER_INPUT)

    def touch(self) -> None:
        """Update the conversation's last activity timestamp"""
        self.updated_at = datetime.now()
