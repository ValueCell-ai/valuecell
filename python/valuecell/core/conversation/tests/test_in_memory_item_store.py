"""
Unit tests for valuecell.core.conversation.item_store module - InMemoryItemStore
"""

import pytest

from valuecell.core.conversation.item_store import InMemoryItemStore
from valuecell.core.types import ConversationItem, Role, NotifyResponseEvent


class TestInMemoryItemStore:
    """Test InMemoryItemStore implementation."""

    def test_init(self):
        """Test InMemoryItemStore initialization."""
        store = InMemoryItemStore()
        assert store._items == {}

    @pytest.mark.asyncio
    async def test_save_item(self):
        """Test saving an item."""
        store = InMemoryItemStore()
        item = ConversationItem(
            item_id="item-123",
            role=Role.USER,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-123",
            thread_id="thread-123",
            task_id="task-123",
            payload='{"message": "Hello"}',
        )

        await store.save_item(item)

        assert "conv-123" in store._items
        assert len(store._items["conv-123"]) == 1
        assert store._items["conv-123"][0] == item

    @pytest.mark.asyncio
    async def test_save_multiple_items_same_conversation(self):
        """Test saving multiple items to the same conversation."""
        store = InMemoryItemStore()

        item1 = ConversationItem(
            item_id="item-1",
            role=Role.USER,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-123",
            payload="Message 1",
        )
        item2 = ConversationItem(
            item_id="item-2",
            role=Role.AGENT,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-123",
            payload="Response 1",
        )

        await store.save_item(item1)
        await store.save_item(item2)

        assert len(store._items["conv-123"]) == 2
        assert store._items["conv-123"][0] == item1
        assert store._items["conv-123"][1] == item2

    @pytest.mark.asyncio
    async def test_save_items_different_conversations(self):
        """Test saving items to different conversations."""
        store = InMemoryItemStore()

        item1 = ConversationItem(
            item_id="item-1",
            role=Role.USER,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-1",
            payload="Message 1",
        )
        item2 = ConversationItem(
            item_id="item-2",
            role=Role.USER,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-2",
            payload="Message 2",
        )

        await store.save_item(item1)
        await store.save_item(item2)

        assert "conv-1" in store._items
        assert "conv-2" in store._items
        assert len(store._items["conv-1"]) == 1
        assert len(store._items["conv-2"]) == 1

    @pytest.mark.asyncio
    async def test_get_items_no_filters(self):
        """Test getting all items for a conversation."""
        store = InMemoryItemStore()

        items = [
            ConversationItem(
                item_id=f"item-{i}",
                role=Role.USER if i % 2 == 0 else Role.AGENT,
                event="message",
                conversation_id="conv-123",
                payload=f"Message {i}",
            )
            for i in range(3)
        ]

        for item in items:
            await store.save_item(item)

        result = await store.get_items("conv-123")

        assert len(result) == 3
        assert result == items

    @pytest.mark.asyncio
    async def test_get_items_with_limit(self):
        """Test getting items with limit."""
        store = InMemoryItemStore()

        items = [
            ConversationItem(
                item_id=f"item-{i}",
                role=Role.USER,
                event="message",
                conversation_id="conv-123",
                payload=f"Message {i}",
            )
            for i in range(5)
        ]

        for item in items:
            await store.save_item(item)

        result = await store.get_items("conv-123", limit=3)

        assert len(result) == 3
        assert result == items[:3]

    @pytest.mark.asyncio
    async def test_get_items_with_offset(self):
        """Test getting items with offset."""
        store = InMemoryItemStore()

        items = [
            ConversationItem(
                item_id=f"item-{i}",
                role=Role.USER,
                event="message",
                conversation_id="conv-123",
                payload=f"Message {i}",
            )
            for i in range(5)
        ]

        for item in items:
            await store.save_item(item)

        result = await store.get_items("conv-123", offset=2)

        assert len(result) == 3
        assert result == items[2:]

    @pytest.mark.asyncio
    async def test_get_items_with_role_filter(self):
        """Test getting items filtered by role."""
        store = InMemoryItemStore()

        user_item = ConversationItem(
            item_id="user-1",
            role=Role.USER,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-123",
            payload="User message",
        )
        agent_item1 = ConversationItem(
            item_id="agent-1",
            role=Role.AGENT,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-123",
            payload="Agent response 1",
        )
        agent_item2 = ConversationItem(
            item_id="agent-2",
            role=Role.AGENT,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-123",
            payload="Agent response 2",
        )

        await store.save_item(user_item)
        await store.save_item(agent_item1)
        await store.save_item(agent_item2)

        # Filter by USER role
        result = await store.get_items("conv-123", role=Role.USER)
        assert len(result) == 1
        assert result[0] == user_item

        # Filter by AGENT role
        result = await store.get_items("conv-123", role=Role.AGENT)
        assert len(result) == 2
        assert result == [agent_item1, agent_item2]

    @pytest.mark.asyncio
    async def test_get_items_empty_conversation(self):
        """Test getting items for empty conversation."""
        store = InMemoryItemStore()

        result = await store.get_items("empty-conv")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_latest_item_existing(self):
        """Test getting latest item from conversation with items."""
        store = InMemoryItemStore()

        items = [
            ConversationItem(
                item_id=f"item-{i}",
                role=Role.USER,
                event="message",
                conversation_id="conv-123",
                payload=f"Message {i}",
            )
            for i in range(3)
        ]

        for item in items:
            await store.save_item(item)

        result = await store.get_latest_item("conv-123")

        assert result == items[-1]  # Last item added
        assert result.item_id == "item-2"

    @pytest.mark.asyncio
    async def test_get_latest_item_empty_conversation(self):
        """Test getting latest item from empty conversation."""
        store = InMemoryItemStore()

        result = await store.get_latest_item("empty-conv")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_item_existing(self):
        """Test getting a specific item by ID."""
        store = InMemoryItemStore()

        item = ConversationItem(
            item_id="target-item",
            role=Role.USER,
            event="message",
            conversation_id="conv-123",
            payload="Target message",
        )
        await store.save_item(item)

        # Add another item to make sure we find the right one
        other_item = ConversationItem(
            item_id="other-item",
            role=Role.USER,
            event="message",
            conversation_id="conv-456",
            payload="Other message",
        )
        await store.save_item(other_item)

        result = await store.get_item("target-item")

        assert result == item

    @pytest.mark.asyncio
    async def test_get_item_nonexistent(self):
        """Test getting a nonexistent item."""
        store = InMemoryItemStore()

        result = await store.get_item("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_item_count(self):
        """Test getting item count for a conversation."""
        store = InMemoryItemStore()

        # Add items to conv-123
        for i in range(3):
            item = ConversationItem(
                item_id=f"item-{i}",
                role=Role.USER,
                event="message",
                conversation_id="conv-123",
                payload=f"Message {i}",
            )
            await store.save_item(item)

        # Add items to another conversation
        item = ConversationItem(
            item_id="other-item",
            role=Role.USER,
            event="message",
            conversation_id="conv-456",
            payload="Other message",
        )
        await store.save_item(item)

        count = await store.get_item_count("conv-123")
        assert count == 3

        count_empty = await store.get_item_count("empty-conv")
        assert count_empty == 0

    @pytest.mark.asyncio
    async def test_delete_conversation_items_existing(self):
        """Test deleting all items for an existing conversation."""
        store = InMemoryItemStore()

        # Add items to conv-123
        for i in range(3):
            item = ConversationItem(
                item_id=f"item-{i}",
                role=Role.USER,
                event="message",
                conversation_id="conv-123",
                payload=f"Message {i}",
            )
            await store.save_item(item)

        # Add items to another conversation
        item = ConversationItem(
            item_id="other-item",
            role=Role.USER,
            event="message",
            conversation_id="conv-456",
            payload="Other message",
        )
        await store.save_item(item)

        await store.delete_conversation_items("conv-123")

        # conv-123 should be empty
        count = await store.get_item_count("conv-123")
        assert count == 0
        assert "conv-123" not in store._items

        # conv-456 should still have items
        count_other = await store.get_item_count("conv-456")
        assert count_other == 1

    @pytest.mark.asyncio
    async def test_delete_conversation_items_nonexistent(self):
        """Test deleting items for a nonexistent conversation."""
        store = InMemoryItemStore()

        # Should not raise an error
        await store.delete_conversation_items("nonexistent")

        assert "nonexistent" not in store._items
