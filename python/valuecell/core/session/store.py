from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from .models import Session


class SessionStore(ABC):
    """Session storage abstract base class - handles session metadata only.

    Messages are stored separately using MessageStore implementations.
    """

    @abstractmethod
    async def save_session(self, session: Session) -> None:
        """Save session"""

    @abstractmethod
    async def load_session(self, session_id: str) -> Optional[Session]:
        """Load session"""

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""

    @abstractmethod
    async def list_sessions(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Session]:
        """List user sessions"""

    @abstractmethod
    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""


class InMemorySessionStore(SessionStore):
    """In-memory session storage implementation"""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    async def save_session(self, session: Session) -> None:
        """Save session to memory"""
        self._sessions[session.session_id] = session

    async def load_session(self, session_id: str) -> Optional[Session]:
        """Load session from memory"""
        return self._sessions.get(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete session from memory"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def list_sessions(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Session]:
        """List user sessions"""
        user_sessions = [
            session for session in self._sessions.values() if session.user_id == user_id
        ]
        # Sort by creation time descending
        user_sessions.sort(key=lambda s: s.created_at, reverse=True)

        # Apply pagination
        start = offset
        end = offset + limit
        return user_sessions[start:end]

    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        return session_id in self._sessions

    def clear_all(self) -> None:
        """Clear all sessions (for testing)"""
        self._sessions.clear()

    def get_session_count(self) -> int:
        """Get total session count (for debugging)"""
        return len(self._sessions)
