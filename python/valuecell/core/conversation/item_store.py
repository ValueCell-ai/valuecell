from __future__ import annotations

import asyncio
import sqlite3
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import aiosqlite

from valuecell.core.types import ConversationItem, ConversationItemEvent, Role


class ItemStore(ABC):
    """Abstract storage interface for conversation items.

    Implementations must provide async methods for saving and querying
    ConversationItem instances.
    """

    @abstractmethod
    async def save_item(self, item: ConversationItem) -> None: ...

    @abstractmethod
    async def get_items(
        self,
        conversation_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        role: Optional[Role] = None,
        **kwargs,
    ) -> List[ConversationItem]: ...

    @abstractmethod
    async def get_latest_item(
        self, conversation_id: str
    ) -> Optional[ConversationItem]: ...

    @abstractmethod
    async def get_item(self, item_id: str) -> Optional[ConversationItem]: ...

    @abstractmethod
    async def get_item_count(self, conversation_id: str) -> int: ...

    @abstractmethod
    async def delete_conversation_items(self, conversation_id: str) -> None: ...


class InMemoryItemStore(ItemStore):
    """In-memory store for conversation items.

    Useful for tests and lightweight usage where persistence is not required.
    """

    def __init__(self):
        # conversation_id -> list[ConversationItem]
        self._items: Dict[str, List[ConversationItem]] = {}

    async def save_item(self, item: ConversationItem) -> None:
        arr = self._items.setdefault(item.conversation_id, [])
        arr.append(item)

    async def get_items(
        self,
        conversation_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        role: Optional[Role] = None,
        **kwargs,
    ) -> List[ConversationItem]:
        if conversation_id is not None:
            items = list(self._items.get(conversation_id, []))
        else:
            # Collect all items from all conversations
            items = []
            for conv_items in self._items.values():
                items.extend(conv_items)
        if role is not None:
            items = [m for m in items if m.role == role]
        if offset:
            items = items[offset:]
        if limit is not None:
            items = items[:limit]
        return items

    async def get_latest_item(self, conversation_id: str) -> Optional[ConversationItem]:
        items = self._items.get(conversation_id, [])
        return items[-1] if items else None

    async def get_item(self, item_id: str) -> Optional[ConversationItem]:
        for arr in self._items.values():
            for m in arr:
                if m.item_id == item_id:
                    return m
        return None

    async def get_item_count(self, conversation_id: str) -> int:
        return len(self._items.get(conversation_id, []))

    async def delete_conversation_items(self, conversation_id: str) -> None:
        self._items.pop(conversation_id, None)


class SQLiteItemStore(ItemStore):
    """SQLite-backed item store using aiosqlite for true async I/O.

    Lazily initializes the database schema on first use. Uses aiosqlite to
    perform non-blocking DB operations and converts rows to ConversationItem
    instances.
    """

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
                    CREATE TABLE IF NOT EXISTS conversation_items (
                      item_id TEXT PRIMARY KEY,
                      role TEXT NOT NULL,
                      event TEXT NOT NULL,
                      conversation_id TEXT NOT NULL,
                      thread_id TEXT,
                      task_id TEXT,
                      payload TEXT,
                      agent_name TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_item_conv_time
                    ON conversation_items (conversation_id, created_at);
                    """
                )
                await db.commit()
            self._initialized = True

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> ConversationItem:
        return ConversationItem(
            item_id=row["item_id"],
            role=row["role"],
            event=row["event"],
            conversation_id=row["conversation_id"],
            thread_id=row["thread_id"],
            task_id=row["task_id"],
            payload=row["payload"],
            agent_name=row["agent_name"],
        )

    async def save_item(self, item: ConversationItem) -> None:
        await self._ensure_initialized()
        role_val = getattr(item.role, "value", str(item.role))
        event_val = getattr(item.event, "value", str(item.event))
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO conversation_items (
                    item_id, role, event, conversation_id, thread_id, task_id, payload, agent_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.item_id,
                    role_val,
                    event_val,
                    item.conversation_id,
                    item.thread_id,
                    item.task_id,
                    item.payload,
                    item.agent_name,
                ),
            )
            await db.commit()

    async def get_items(
        self,
        conversation_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        role: Optional[Role] = None,
        event: Optional[ConversationItemEvent] = None,
        component_type: Optional[str] = None,
        **kwargs,
    ) -> List[ConversationItem]:
        await self._ensure_initialized()
        params = []
        where_clauses = []
        if conversation_id is not None:
            where_clauses.append("conversation_id = ?")
            params.append(conversation_id)
        if role is not None:
            where_clauses.append("role = ?")
            params.append(getattr(role, "value", str(role)))
        if event is not None:
            where_clauses.append("event = ?")
            params.append(getattr(event, "value", str(event)))
        if component_type is not None:
            where_clauses.append("json_extract(payload, '$.component_type') = ?")
            params.append(component_type)

        where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        sql = f"SELECT * FROM conversation_items {where} ORDER BY datetime(created_at) ASC"
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
            return [self._row_to_item(r) for r in rows]

    async def get_latest_item(self, conversation_id: str) -> Optional[ConversationItem]:
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute(
                "SELECT * FROM conversation_items WHERE conversation_id = ? ORDER BY datetime(created_at) DESC LIMIT 1",
                (conversation_id,),
            )
            row = await cur.fetchone()
            return self._row_to_item(row) if row else None

    async def get_item(self, item_id: str) -> Optional[ConversationItem]:
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute(
                "SELECT * FROM conversation_items WHERE item_id = ?",
                (item_id,),
            )
            row = await cur.fetchone()
            return self._row_to_item(row) if row else None

    async def get_item_count(self, conversation_id: str) -> int:
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT COUNT(1) FROM conversation_items WHERE conversation_id = ?",
                (conversation_id,),
            )
            row = await cur.fetchone()
            return int(row[0] if row else 0)

    async def delete_conversation_items(self, conversation_id: str) -> None:
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM conversation_items WHERE conversation_id = ?",
                (conversation_id,),
            )
            await db.commit()
