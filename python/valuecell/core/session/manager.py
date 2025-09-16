from datetime import datetime
from typing import List, Optional

from valuecell.utils import generate_uuid

from .models import Message, Role, Session
from .store import InMemorySessionStore, SessionStore


class SessionManager:
    """Session manager"""

    def __init__(self, store: Optional[SessionStore] = None):
        self.store = store or InMemorySessionStore()

    async def create_session(
        self, user_id: str, title: Optional[str] = None
    ) -> Session:
        """Create new session"""
        session = Session(
            session_id=generate_uuid("session"), user_id=user_id, title=title
        )
        await self.store.save_session(session)
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session"""
        return await self.store.load_session(session_id)

    async def update_session(self, session: Session) -> None:
        """Update session"""
        session.updated_at = datetime.now()
        await self.store.save_session(session)

    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        return await self.store.delete_session(session_id)

    async def list_user_sessions(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Session]:
        """List user sessions"""
        return await self.store.list_sessions(user_id, limit, offset)

    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        return await self.store.session_exists(session_id)

    async def add_message(
        self, session_id: str, role: Role, content: str, task_id: Optional[str] = None
    ) -> Optional[Message]:
        """Add message to session"""
        session = await self.get_session(session_id)
        if not session:
            return None

        message = Message(
            message_id=generate_uuid("msg"),
            session_id=session_id,
            role=role,
            content=content,
            task_id=task_id,
        )

        session.add_message(message)
        await self.update_session(session)
        return message

    async def get_session_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Message]:
        """Get session messages"""
        session = await self.get_session(session_id)
        if not session:
            return []

        messages = session.messages
        if limit is not None:
            messages = messages[-limit:]  # Get latest limit messages

        return messages

    async def get_latest_message(self, session_id: str) -> Optional[Message]:
        """Get latest session message"""
        session = await self.get_session(session_id)
        if not session:
            return None

        return session.get_latest_message()

    async def update_session_context(self, session_id: str, key: str, value) -> bool:
        """Update session context"""
        session = await self.get_session(session_id)
        if not session:
            return False

        session.update_context(key, value)
        await self.update_session(session)
        return True

    async def get_session_context(self, session_id: str, key: str, default=None):
        """Get session context value"""
        session = await self.get_session(session_id)
        if not session:
            return default

        return session.get_context(key, default)

    async def deactivate_session(self, session_id: str) -> bool:
        """Deactivate session"""
        session = await self.get_session(session_id)
        if not session:
            return False

        session.is_active = False
        await self.update_session(session)
        return True

    async def activate_session(self, session_id: str) -> bool:
        """Activate session"""
        session = await self.get_session(session_id)
        if not session:
            return False

        session.is_active = True
        await self.update_session(session)
        return True


_session_manager = SessionManager()


def get_default_session_manager() -> SessionManager:
    return _session_manager
