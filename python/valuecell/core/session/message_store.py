import sqlite3
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any

from .models import Message, Role


class MessageStore(ABC):
    """Abstract base class for message storage"""

    @abstractmethod
    async def save_message(self, message: Message) -> None:
        """Save a single message"""

    @abstractmethod
    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        role: Optional[Role] = None,
    ) -> List[Message]:
        """Get messages for a session with optional filtering and pagination"""

    @abstractmethod
    async def get_message(self, message_id: str) -> Optional[Message]:
        """Get a specific message by ID"""

    @abstractmethod
    async def get_latest_message(self, session_id: str) -> Optional[Message]:
        """Get the latest message in a session"""

    @abstractmethod
    async def get_message_count(self, session_id: str) -> int:
        """Get total message count for a session"""

    @abstractmethod
    async def delete_session_messages(self, session_id: str) -> int:
        """Delete all messages for a session, returns count of deleted messages"""

    @abstractmethod
    async def delete_message(self, message_id: str) -> bool:
        """Delete a specific message"""


class InMemoryMessageStore(MessageStore):
    """In-memory message store implementation for testing and development"""

    def __init__(self):
        self._messages: Dict[str, Message] = {}
        self._session_messages: Dict[str, List[str]] = {}

    async def save_message(self, message: Message) -> None:
        """Save message to memory"""
        self._messages[message.message_id] = message

        # Maintain session index
        if message.session_id not in self._session_messages:
            self._session_messages[message.session_id] = []
        self._session_messages[message.session_id].append(message.message_id)

    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        role: Optional[Role] = None,
    ) -> List[Message]:
        """Get messages for a session"""
        message_ids = self._session_messages.get(session_id, [])
        messages = [self._messages[msg_id] for msg_id in message_ids]

        # Filter by role if specified
        if role:
            messages = [msg for msg in messages if msg.role == role]

        # Sort by timestamp
        messages.sort(key=lambda m: m.timestamp)

        # Apply pagination
        if offset > 0:
            messages = messages[offset:]
        if limit is not None:
            messages = messages[:limit]

        return messages

    async def get_message(self, message_id: str) -> Optional[Message]:
        """Get a specific message"""
        return self._messages.get(message_id)

    async def get_latest_message(self, session_id: str) -> Optional[Message]:
        """Get the latest message in a session"""
        messages = await self.get_messages(session_id)
        return messages[-1] if messages else None

    async def get_message_count(self, session_id: str) -> int:
        """Get message count for a session"""
        return len(self._session_messages.get(session_id, []))

    async def delete_session_messages(self, session_id: str) -> int:
        """Delete all messages for a session"""
        message_ids = self._session_messages.get(session_id, [])
        count = len(message_ids)

        # Remove from messages dict
        for msg_id in message_ids:
            self._messages.pop(msg_id, None)

        # Remove session index
        self._session_messages.pop(session_id, None)

        return count

    async def delete_message(self, message_id: str) -> bool:
        """Delete a specific message"""
        message = self._messages.pop(message_id, None)
        if not message:
            return False

        # Remove from session index
        session_id = message.session_id
        if session_id in self._session_messages:
            try:
                self._session_messages[session_id].remove(message_id)
            except ValueError:
                pass  # Already removed

        return True

    def clear_all(self) -> None:
        """Clear all messages (for testing)"""
        self._messages.clear()
        self._session_messages.clear()


class SQLiteMessageStore(MessageStore):
    """SQLite-based message store implementation"""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize SQLite message store

        Args:
            db_path: Path to SQLite database file. If None, uses in-memory database.
        """
        self.db_path = db_path or ":memory:"
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    agent_name TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    task_id TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_id 
                ON messages(session_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON messages(session_id, timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_role 
                ON messages(session_id, role)
            """)

    def _message_to_dict(self, message: Message) -> Dict[str, Any]:
        """Convert Message object to database record"""
        return {
            "message_id": message.message_id,
            "session_id": message.session_id,
            "user_id": message.user_id,
            "agent_name": message.agent_name,
            "role": message.role.value,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "task_id": message.task_id,
            "metadata": json.dumps(message.metadata) if message.metadata else None,
        }

    def _dict_to_message(self, row: Dict[str, Any]) -> Message:
        """Convert database record to Message object"""
        return Message(
            message_id=row["message_id"],
            session_id=row["session_id"],
            user_id=row["user_id"],
            agent_name=row["agent_name"],
            role=Role(row["role"]),
            content=row["content"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            task_id=row["task_id"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    async def save_message(self, message: Message) -> None:
        """Save message to SQLite database"""
        data = self._message_to_dict(message)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO messages 
                (message_id, session_id, user_id, agent_name, role, content, 
                 timestamp, task_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data["message_id"],
                    data["session_id"],
                    data["user_id"],
                    data["agent_name"],
                    data["role"],
                    data["content"],
                    data["timestamp"],
                    data["task_id"],
                    data["metadata"],
                ),
            )

    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        role: Optional[Role] = None,
    ) -> List[Message]:
        """Get messages for a session"""
        query = """
            SELECT message_id, session_id, user_id, agent_name, role, content, 
                   timestamp, task_id, metadata
            FROM messages 
            WHERE session_id = ?
        """
        params = [session_id]

        # Add role filter if specified
        if role:
            query += " AND role = ?"
            params.append(role.value)

        # Order by timestamp
        query += " ORDER BY timestamp ASC"

        # Add pagination
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            return [self._dict_to_message(dict(row)) for row in rows]

    async def get_message(self, message_id: str) -> Optional[Message]:
        """Get a specific message by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT message_id, session_id, user_id, agent_name, role, content, 
                       timestamp, task_id, metadata
                FROM messages 
                WHERE message_id = ?
            """,
                (message_id,),
            )

            row = cursor.fetchone()
            return self._dict_to_message(dict(row)) if row else None

    async def get_latest_message(self, session_id: str) -> Optional[Message]:
        """Get the latest message in a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT message_id, session_id, user_id, agent_name, role, content, 
                       timestamp, task_id, metadata
                FROM messages 
                WHERE session_id = ?
                ORDER BY timestamp DESC 
                LIMIT 1
            """,
                (session_id,),
            )

            row = cursor.fetchone()
            return self._dict_to_message(dict(row)) if row else None

    async def get_message_count(self, session_id: str) -> int:
        """Get message count for a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM messages WHERE session_id = ?
            """,
                (session_id,),
            )

            return cursor.fetchone()[0]

    async def delete_session_messages(self, session_id: str) -> int:
        """Delete all messages for a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM messages WHERE session_id = ?
            """,
                (session_id,),
            )

            return cursor.rowcount

    async def delete_message(self, message_id: str) -> bool:
        """Delete a specific message"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM messages WHERE message_id = ?
            """,
                (message_id,),
            )

            return cursor.rowcount > 0
