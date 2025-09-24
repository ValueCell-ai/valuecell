from __future__ import annotations

import asyncio
import sqlite3
import aiosqlite
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from valuecell.core.types import ConversationItem, Role


class MessageStore(ABC):
    @abstractmethod
    async def save_message(self, message: ConversationItem) -> None: ...

    @abstractmethod
    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        role: Optional[Role] = None,
    ) -> List[ConversationItem]: ...

    @abstractmethod
    async def get_latest_message(
        self, session_id: str
    ) -> Optional[ConversationItem]: ...

    @abstractmethod
    async def get_message(self, message_id: str) -> Optional[ConversationItem]: ...

    @abstractmethod
    async def get_message_count(self, session_id: str) -> int: ...

    @abstractmethod
    async def delete_session_messages(self, session_id: str) -> None: ...


class InMemoryMessageStore(MessageStore):
    def __init__(self):
        # session_id -> list[ConversationItem]
        self._messages: Dict[str, List[ConversationItem]] = {}

    async def save_message(self, message: ConversationItem) -> None:
        arr = self._messages.setdefault(message.conversation_id, [])
        arr.append(message)

    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        role: Optional[Role] = None,
    ) -> List[ConversationItem]:
        items = list(self._messages.get(session_id, []))
        if role is not None:
            items = [m for m in items if m.role == role]
        if offset:
            items = items[offset:]
        if limit is not None:
            items = items[:limit]
        return items

    async def get_latest_message(self, session_id: str) -> Optional[ConversationItem]:
        items = self._messages.get(session_id, [])
        return items[-1] if items else None

    async def get_message(self, message_id: str) -> Optional[ConversationItem]:
        for arr in self._messages.values():
            for m in arr:
                if m.item_id == message_id:
                    return m
        return None

    async def get_message_count(self, session_id: str) -> int:
        return len(self._messages.get(session_id, []))

    async def delete_session_messages(self, session_id: str) -> None:
        self._messages.pop(session_id, None)


class SQLiteMessageStore(MessageStore):
    """SQLite-backed message store using aiosqlite for true async I/O."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialized = False
        self._init_lock = None  # lazy to avoid loop-binding in __init__

    async def _ensure_initialized(self) -> None:
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
                    CREATE TABLE IF NOT EXISTS messages (
                      item_id TEXT PRIMARY KEY,
                      role TEXT NOT NULL,
                      event TEXT NOT NULL,
                      conversation_id TEXT NOT NULL,
                      thread_id TEXT,
                      task_id TEXT,
                      payload TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_messages_conv_time
                    ON messages (conversation_id, created_at);
                    """
                )
                await db.commit()
            self._initialized = True

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> ConversationItem:
        return ConversationItem(
            item_id=row["item_id"],
            role=row["role"],
            event=row["event"],
            conversation_id=row["conversation_id"],
            thread_id=row["thread_id"],
            task_id=row["task_id"],
            payload=row["payload"],
        )

    async def save_message(self, message: ConversationItem) -> None:
        await self._ensure_initialized()
        role_val = getattr(message.role, "value", str(message.role))
        event_val = getattr(message.event, "value", str(message.event))
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO messages (
                    item_id, role, event, conversation_id, thread_id, task_id, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.item_id,
                    role_val,
                    event_val,
                    message.conversation_id,
                    message.thread_id,
                    message.task_id,
                    message.payload,
                ),
            )
            await db.commit()

    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        role: Optional[Role] = None,
    ) -> List[ConversationItem]:
        await self._ensure_initialized()
        params = [session_id]
        where = "WHERE conversation_id = ?"
        if role is not None:
            where += " AND role = ?"
            params.append(getattr(role, "value", str(role)))
        sql = f"SELECT * FROM messages {where} ORDER BY datetime(created_at) ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        if offset:
            if limit is None:
                sql += " LIMIT -1"
            sql += " OFFSET ?"
            params.append(int(offset))
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute(sql, params)
            rows = await cur.fetchall()
            return [self._row_to_message(r) for r in rows]

    async def get_latest_message(self, session_id: str) -> Optional[ConversationItem]:
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY datetime(created_at) DESC LIMIT 1",
                (session_id,),
            )
            row = await cur.fetchone()
            return self._row_to_message(row) if row else None

    async def get_message(self, message_id: str) -> Optional[ConversationItem]:
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute(
                "SELECT * FROM messages WHERE item_id = ?",
                (message_id,),
            )
            row = await cur.fetchone()
            return self._row_to_message(row) if row else None

    async def get_message_count(self, session_id: str) -> int:
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT COUNT(1) FROM messages WHERE conversation_id = ?",
                (session_id,),
            )
            row = await cur.fetchone()
            return int(row[0] if row else 0)

    async def delete_session_messages(self, session_id: str) -> None:
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (session_id,),
            )
            await db.commit()
