from datetime import datetime
from typing import List, Optional

from valuecell.utils import generate_uuid

from .models import Message, Role, Session, SessionStatus
from .store import InMemorySessionStore, SessionStore
from .message_store import MessageStore, InMemoryMessageStore


class SessionManager:
    """Session manager - handles both session metadata and messages through separate stores"""

    def __init__(
        self,
        session_store: Optional[SessionStore] = None,
        message_store: Optional[MessageStore] = None,
    ):
        self.session_store = session_store or InMemorySessionStore()
        self.message_store = message_store or InMemoryMessageStore()

    async def create_session(
        self,
        user_id: str,
        title: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        """Create new session"""
        session = Session(
            session_id=session_id or generate_uuid("session"),
            user_id=user_id,
            title=title,
        )
        await self.session_store.save_session(session)
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session metadata"""
        return await self.session_store.load_session(session_id)

    async def update_session(self, session: Session) -> None:
        """Update session metadata"""
        session.updated_at = datetime.now()
        await self.session_store.save_session(session)

    async def delete_session(self, session_id: str) -> bool:
        """Delete session and all its messages"""
        # First delete all messages for this session
        await self.message_store.delete_session_messages(session_id)

        # Then delete the session metadata
        return await self.session_store.delete_session(session_id)

    async def list_user_sessions(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Session]:
        """List user sessions"""
        return await self.session_store.list_sessions(user_id, limit, offset)

    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        return await self.session_store.session_exists(session_id)

    async def add_message(
        self,
        session_id: str,
        role: Role,
        content: str,
        user_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Optional[Message]:
        """Add message to session

        Args:
            session_id: Session ID to add message to
            role: Message role (USER, AGENT, SYSTEM)
            content: Message content
            user_id: User ID (will be fetched from session if not provided)
            agent_name: Agent name (optional)
            task_id: Associated task ID (optional)
        """
        # Verify session exists
        session = await self.get_session(session_id)
        if not session:
            return None

        # Use provided user_id or get from session
        if user_id is None:
            user_id = session.user_id

        # Create message
        message = Message(
            message_id=generate_uuid("msg"),
            session_id=session_id,
            user_id=user_id,
            agent_name=agent_name,
            role=role,
            content=content,
            task_id=task_id,
        )

        # Save message directly to message store
        await self.message_store.save_message(message)

        # Update session timestamp
        session.touch()
        await self.session_store.save_session(session)

        return message

    async def get_session_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        role: Optional[Role] = None,
    ) -> List[Message]:
        """Get messages for a session with optional filtering and pagination

        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            role: Filter by specific role (optional)
        """
        return await self.message_store.get_messages(session_id, limit, offset, role)

    async def get_latest_message(self, session_id: str) -> Optional[Message]:
        """Get latest message in a session"""
        return await self.message_store.get_latest_message(session_id)

    async def get_message(self, message_id: str) -> Optional[Message]:
        """Get a specific message by ID"""
        return await self.message_store.get_message(message_id)

    async def get_message_count(self, session_id: str) -> int:
        """Get total message count for a session"""
        return await self.message_store.get_message_count(session_id)

    async def get_messages_by_role(self, session_id: str, role: Role) -> List[Message]:
        """Get messages filtered by role"""
        return await self.message_store.get_messages(session_id, role=role)

    async def deactivate_session(self, session_id: str) -> bool:
        """Deactivate session"""
        session = await self.get_session(session_id)
        if not session:
            return False

        session.deactivate()
        await self.session_store.save_session(session)
        return True

    async def activate_session(self, session_id: str) -> bool:
        """Activate session"""
        session = await self.get_session(session_id)
        if not session:
            return False

        session.activate()
        await self.session_store.save_session(session)
        return True

    async def set_session_status(self, session_id: str, status: SessionStatus) -> bool:
        """Set session status"""
        session = await self.get_session(session_id)
        if not session:
            return False

        session.set_status(status)
        await self.session_store.save_session(session)
        return True

    async def require_user_input(self, session_id: str) -> bool:
        """Mark session as requiring user input"""
        return await self.set_session_status(
            session_id, SessionStatus.REQUIRE_USER_INPUT
        )

    async def get_sessions_by_status(
        self, user_id: str, status: SessionStatus, limit: int = 100, offset: int = 0
    ) -> List[Session]:
        """Get user sessions filtered by status"""
        # Get all user sessions and filter by status
        # Note: This could be optimized by adding status filtering to the store interface
        all_sessions = await self.session_store.list_sessions(
            user_id, limit * 2, offset
        )
        return [session for session in all_sessions if session.status == status][:limit]


# Default session manager instance
_session_manager = SessionManager()


def get_default_session_manager() -> SessionManager:
    """Get the default session manager instance"""
    return _session_manager
