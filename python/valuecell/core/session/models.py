from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Message role enumeration"""

    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class Message(BaseModel):
    """Message data model"""

    message_id: str = Field(..., description="Unique message identifier")
    session_id: str = Field(..., description="Session ID this message belongs to")
    role: Role = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Message timestamp"
    )
    task_id: Optional[str] = Field(None, description="Associated task ID")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Message metadata"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Session(BaseModel):
    """Session data model"""

    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User ID")
    title: Optional[str] = Field(None, description="Session title")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update time"
    )
    messages: List[Message] = Field(
        default_factory=list, description="Session message list"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Session context data"
    )
    is_active: bool = Field(True, description="Whether session is active")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def add_message(self, message: Message) -> None:
        """Add message to session"""
        messages = list(self.messages)
        messages.append(message)
        self.messages = messages
        self.updated_at = datetime.now()

    def get_messages_by_role(self, role: Role) -> List[Message]:
        """Get messages by role"""
        return [msg for msg in self.messages if msg.role == role]

    def get_latest_message(self) -> Optional[Message]:
        """Get latest message"""
        return self.messages[-1] if self.messages else None

    def get_message_count(self) -> int:
        """Get message count"""
        return len(self.messages)

    def update_context(self, key: str, value: Any) -> None:
        """Update session context"""
        context = dict(self.context)
        context[key] = value
        self.context = context
        self.updated_at = datetime.now()

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get session context value"""
        return dict(self.context).get(key, default)
