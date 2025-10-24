import asyncio
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

import aiosqlite

from .models import Conversation


class ConversationStore(ABC):
    """Conversation storage abstract base class - handles conversation metadata only.

    Implementations should provide async methods to save, load, delete and
    list conversation metadata. Conversation items themselves are managed
    separately by ItemStore implementations.
    """

    @abstractmethod
    async def save_conversation(self, conversation: Conversation) -> None:
        """Save conversation"""

    @abstractmethod
    async def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Load conversation"""

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation"""

    @abstractmethod
    async def list_conversations(
        self, user_id: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Conversation]:
        """List conversations. If user_id is None, return all conversations."""

    @abstractmethod
    async def conversation_exists(self, conversation_id: str) -> bool:
        """Check if conversation exists"""


class InMemoryConversationStore(ConversationStore):
    """In-memory ConversationStore implementation used for testing and simple scenarios.

    Stores conversations in a dict keyed by conversation_id.
    """

    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}

    async def save_conversation(self, conversation: Conversation) -> None:
        """Save conversation to memory"""
        self._conversations[conversation.conversation_id] = conversation

    async def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Load conversation from memory"""
        return self._conversations.get(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation from memory"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False

    async def list_conversations(
        self, user_id: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Conversation]:
        """List conversations. If user_id is None, return all conversations."""
        if user_id is None:
            # Return all conversations
            conversations = list(self._conversations.values())
        else:
            # Filter by user_id
            conversations = [
                conversation
                for conversation in self._conversations.values()
                if conversation.user_id == user_id
            ]

        # Sort by creation time descending
        conversations.sort(key=lambda c: c.created_at, reverse=True)

        # Apply pagination
        start = offset
        end = offset + limit
        return conversations[start:end]

    async def conversation_exists(self, conversation_id: str) -> bool:
        """Check if conversation exists"""
        return conversation_id in self._conversations

    def clear_all(self) -> None:
        """Clear all conversations (for testing)"""
        self._conversations.clear()

    def get_conversation_count(self) -> int:
        """Get total conversation count (for debugging)"""
        return len(self._conversations)


class SQLiteConversationStore(ConversationStore):
    """SQLite-backed conversation store using aiosqlite for true async I/O.

    Lazily initializes the database schema on first use. Uses aiosqlite to
    perform non-blocking DB operations and converts rows to Conversation
    instances.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialized = False
        self._init_lock = None  # lazy to avoid loop-binding in __init__

    async def _ensure_initialized(self):
        """Ensure database is initialized with proper schema."""
        if self._initialized:
            return

        if self._init_lock is None:
            self._init_lock = asyncio.Lock()

        async with self._init_lock:
            if self._initialized:
                return

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        conversation_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        title TEXT,
                        agent_name TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'active'
                    )
                    """
                )
                await db.commit()

            self._initialized = True

    @staticmethod
    def _row_to_conversation(row: sqlite3.Row) -> Conversation:
        """Convert database row to Conversation object."""
        return Conversation(
            conversation_id=row["conversation_id"],
            user_id=row["user_id"],
            title=row["title"],
            agent_name=row["agent_name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            status=row["status"],
        )

    async def save_conversation(self, conversation: Conversation) -> None:
        """Save conversation to SQLite database."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO conversations (
                    conversation_id, user_id, title, agent_name, created_at, updated_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation.conversation_id,
                    conversation.user_id,
                    conversation.title,
                    conversation.agent_name,
                    conversation.created_at.isoformat(),
                    conversation.updated_at.isoformat(),
                    conversation.status.value
                    if hasattr(conversation.status, "value")
                    else str(conversation.status),
                ),
            )
            await db.commit()

    async def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Load conversation from SQLite database."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute(
                "SELECT * FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            row = await cur.fetchone()
            return self._row_to_conversation(row) if row else None

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation from SQLite database."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "DELETE FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            await db.commit()
            return cur.rowcount > 0

    async def list_conversations(
        self, user_id: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Conversation]:
        """List conversations from SQLite database."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row

            if user_id is None:
                # Return all conversations
                cur = await db.execute(
                    "SELECT * FROM conversations ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            else:
                # Filter by user_id
                cur = await db.execute(
                    "SELECT * FROM conversations WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (user_id, limit, offset),
                )

            rows = await cur.fetchall()
            return [self._row_to_conversation(row) for row in rows]

    async def conversation_exists(self, conversation_id: str) -> bool:
        """Check if conversation exists in SQLite database."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT 1 FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            row = await cur.fetchone()
            return row is not None
