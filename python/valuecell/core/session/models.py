from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Session status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    REQUIRE_USER_INPUT = "require_user_input"


class Session(BaseModel):
    """Session data model - lightweight metadata only, messages stored separately"""

    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User ID")
    title: Optional[str] = Field(None, description="Session title")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update time"
    )
    status: SessionStatus = Field(
        default=SessionStatus.ACTIVE, description="Session status"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    @property
    def is_active(self) -> bool:
        """Backward compatibility property - returns True if session is active"""
        return self.status == SessionStatus.ACTIVE

    def set_status(self, status: SessionStatus) -> None:
        """Update session status and timestamp"""
        self.status = status
        self.updated_at = datetime.now()

    def activate(self) -> None:
        """Set session to active status"""
        self.set_status(SessionStatus.ACTIVE)

    def deactivate(self) -> None:
        """Set session to inactive status"""
        self.set_status(SessionStatus.INACTIVE)

    def require_user_input(self) -> None:
        """Set session to require user input status"""
        self.set_status(SessionStatus.REQUIRE_USER_INPUT)

    def touch(self) -> None:
        """Update the session's last activity timestamp"""
        self.updated_at = datetime.now()
