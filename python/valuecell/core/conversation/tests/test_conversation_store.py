"""
Unit tests for valuecell.core.conversation.conversation_store module
"""

from datetime import datetime

import pytest

from valuecell.core.conversation.conversation_store import (
    ConversationStore,
    InMemoryConversationStore,
)
from valuecell.core.conversation.models import Conversation


class TestConversationStore:
    """Test ConversationStore abstract base class."""

    def test_abstract_methods(self):
        """Test that ConversationStore defines required abstract methods."""
        # This is more of a documentation test - the ABC will prevent instantiation
        expected_methods = [
            "save_conversation",
            "load_conversation",
            "delete_conversation",
            "list_conversations",
            "conversation_exists",
        ]

        for method in expected_methods:
            assert hasattr(ConversationStore, method), (
                f"Missing abstract method: {method}"
            )


class TestInMemoryConversationStore:
    """Test InMemoryConversationStore implementation."""

    def test_init(self):
        """Test InMemoryConversationStore initialization."""
        store = InMemoryConversationStore()
        assert store._conversations == {}

    @pytest.mark.asyncio
    async def test_save_conversation(self):
        """Test saving a conversation."""
        store = InMemoryConversationStore()
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            title="Test Conversation",
        )

        await store.save_conversation(conversation)

        assert "conv-123" in store._conversations
        assert store._conversations["conv-123"] == conversation

    @pytest.mark.asyncio
    async def test_save_conversation_update(self):
        """Test updating an existing conversation."""
        store = InMemoryConversationStore()
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            title="Original Title",
        )

        await store.save_conversation(conversation)

        # Update the conversation
        conversation.title = "Updated Title"
        await store.save_conversation(conversation)

        assert store._conversations["conv-123"].title == "Updated Title"

    @pytest.mark.asyncio
    async def test_load_conversation_existing(self):
        """Test loading an existing conversation."""
        store = InMemoryConversationStore()
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            title="Test Conversation",
        )
        store._conversations["conv-123"] = conversation

        result = await store.load_conversation("conv-123")

        assert result == conversation

    @pytest.mark.asyncio
    async def test_load_conversation_nonexistent(self):
        """Test loading a nonexistent conversation."""
        store = InMemoryConversationStore()

        result = await store.load_conversation("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_conversation_existing(self):
        """Test deleting an existing conversation."""
        store = InMemoryConversationStore()
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
        )
        store._conversations["conv-123"] = conversation

        result = await store.delete_conversation("conv-123")

        assert result is True
        assert "conv-123" not in store._conversations

    @pytest.mark.asyncio
    async def test_delete_conversation_nonexistent(self):
        """Test deleting a nonexistent conversation."""
        store = InMemoryConversationStore()

        result = await store.delete_conversation("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_conversation_exists_true(self):
        """Test conversation_exists returns True for existing conversation."""
        store = InMemoryConversationStore()
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
        )
        store._conversations["conv-123"] = conversation

        result = await store.conversation_exists("conv-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_conversation_exists_false(self):
        """Test conversation_exists returns False for nonexistent conversation."""
        store = InMemoryConversationStore()

        result = await store.conversation_exists("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_list_conversations_single_user(self):
        """Test listing conversations for a single user."""
        store = InMemoryConversationStore()

        # Create conversations for user-123
        conv1 = Conversation(
            conversation_id="conv-1",
            user_id="user-123",
            created_at=datetime(2023, 1, 1, 10, 0, 0),
        )
        conv2 = Conversation(
            conversation_id="conv-2",
            user_id="user-123",
            created_at=datetime(2023, 1, 1, 11, 0, 0),
        )
        conv3 = Conversation(
            conversation_id="conv-3",
            user_id="user-456",  # Different user
            created_at=datetime(2023, 1, 1, 12, 0, 0),
        )

        store._conversations = {
            "conv-1": conv1,
            "conv-2": conv2,
            "conv-3": conv3,
        }

        result = await store.list_conversations("user-123")

        assert len(result) == 2
        # Should be sorted by creation time descending
        assert result[0].conversation_id == "conv-2"  # Newer first
        assert result[1].conversation_id == "conv-1"  # Older second

    @pytest.mark.asyncio
    async def test_list_conversations_empty(self):
        """Test listing conversations for user with no conversations."""
        store = InMemoryConversationStore()

        result = await store.list_conversations("user-123")

        assert result == []

    @pytest.mark.asyncio
    async def test_list_conversations_pagination(self):
        """Test listing conversations with pagination."""
        store = InMemoryConversationStore()

        # Create multiple conversations
        conversations = []
        for i in range(5):
            conv = Conversation(
                conversation_id=f"conv-{i}",
                user_id="user-123",
                created_at=datetime(2023, 1, 1, 10 + i, 0, 0),
            )
            conversations.append(conv)
            store._conversations[f"conv-{i}"] = conv

        # Test limit
        result = await store.list_conversations("user-123", limit=3)
        assert len(result) == 3
        # Should be sorted by creation time descending
        assert result[0].conversation_id == "conv-4"
        assert result[1].conversation_id == "conv-3"
        assert result[2].conversation_id == "conv-2"

        # Test offset
        result = await store.list_conversations("user-123", limit=2, offset=1)
        assert len(result) == 2
        assert result[0].conversation_id == "conv-3"
        assert result[1].conversation_id == "conv-2"

    def test_clear_all(self):
        """Test clear_all method."""
        store = InMemoryConversationStore()
        store._conversations = {
            "conv-1": Conversation(conversation_id="conv-1", user_id="user-1"),
            "conv-2": Conversation(conversation_id="conv-2", user_id="user-1"),
        }

        store.clear_all()

        assert store._conversations == {}

    def test_get_conversation_count(self):
        """Test get_conversation_count method."""
        store = InMemoryConversationStore()
        store._conversations = {
            "conv-1": Conversation(conversation_id="conv-1", user_id="user-1"),
            "conv-2": Conversation(conversation_id="conv-2", user_id="user-1"),
            "conv-3": Conversation(conversation_id="conv-3", user_id="user-2"),
        }

        count = store.get_conversation_count()

        assert count == 3
