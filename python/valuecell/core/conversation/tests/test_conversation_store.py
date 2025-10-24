"""
Unit tests for valuecell.core.conversation.conversation_store module
"""

from datetime import datetime

import pytest

from valuecell.core.conversation.conversation_store import (
    ConversationStore,
    InMemoryConversationStore,
    SQLiteConversationStore,
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
    async def test_list_conversations_all_users(self):
        """Test listing all conversations when user_id is None."""
        store = InMemoryConversationStore()

        # Create conversations for different users
        conv1 = Conversation(
            conversation_id="conv-1",
            user_id="user-123",
            created_at=datetime(2023, 1, 1, 10, 0, 0),
        )
        conv2 = Conversation(
            conversation_id="conv-2",
            user_id="user-456",
            created_at=datetime(2023, 1, 1, 11, 0, 0),
        )
        conv3 = Conversation(
            conversation_id="conv-3",
            user_id="user-789",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
        )

        store._conversations = {
            "conv-1": conv1,
            "conv-2": conv2,
            "conv-3": conv3,
        }

        # Test with user_id=None to get all conversations
        result = await store.list_conversations(user_id=None)

        assert len(result) == 3
        # Should be sorted by creation time descending
        assert result[0].conversation_id == "conv-3"  # Newest first
        assert result[1].conversation_id == "conv-2"
        assert result[2].conversation_id == "conv-1"  # Oldest last

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


class TestSQLiteConversationStore:
    """Test SQLiteConversationStore implementation."""

    @pytest.fixture
    def temp_db_store(self, tmp_path):
        """Create a temporary SQLite store for testing."""
        db_path = str(tmp_path / "test_conversations.db")
        store = SQLiteConversationStore(db_path)
        return store

    @pytest.mark.asyncio
    async def test_init(self, tmp_path):
        """Test SQLiteConversationStore initialization."""
        db_path = str(tmp_path / "test.db")
        store = SQLiteConversationStore(db_path)
        assert store.db_path == db_path
        assert not store._initialized
        assert store._init_lock is None

    @pytest.mark.asyncio
    async def test_ensure_initialized(self, temp_db_store):
        """Test database initialization."""
        store = temp_db_store
        assert not store._initialized

        await store._ensure_initialized()

        assert store._initialized
        assert store._init_lock is not None

    @pytest.mark.asyncio
    async def test_ensure_initialized_multiple_calls(self, temp_db_store):
        """Test that multiple initialization calls are safe."""
        store = temp_db_store

        # Call multiple times
        await store._ensure_initialized()
        await store._ensure_initialized()
        await store._ensure_initialized()

        assert store._initialized

    @pytest.mark.asyncio
    async def test_save_conversation(self, temp_db_store):
        """Test saving a conversation."""
        store = temp_db_store
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            title="Test Conversation",
        )

        await store.save_conversation(conversation)

        # Verify it was saved
        loaded = await store.load_conversation("conv-123")
        assert loaded is not None
        assert loaded.conversation_id == "conv-123"
        assert loaded.user_id == "user-123"
        assert loaded.title == "Test Conversation"

    @pytest.mark.asyncio
    async def test_save_conversation_update(self, temp_db_store):
        """Test updating an existing conversation."""
        store = temp_db_store
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            title="Original Title",
        )

        await store.save_conversation(conversation)

        # Update the conversation
        conversation.title = "Updated Title"
        await store.save_conversation(conversation)

        # Verify the update
        loaded = await store.load_conversation("conv-123")
        assert loaded.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_load_conversation_existing(self, temp_db_store):
        """Test loading an existing conversation."""
        store = temp_db_store
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            title="Test Conversation",
        )
        await store.save_conversation(conversation)

        result = await store.load_conversation("conv-123")

        assert result is not None
        assert result.conversation_id == "conv-123"
        assert result.user_id == "user-123"
        assert result.title == "Test Conversation"

    @pytest.mark.asyncio
    async def test_load_conversation_nonexistent(self, temp_db_store):
        """Test loading a nonexistent conversation."""
        store = temp_db_store

        result = await store.load_conversation("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_conversation_existing(self, temp_db_store):
        """Test deleting an existing conversation."""
        store = temp_db_store
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            title="Test Conversation",
        )
        await store.save_conversation(conversation)

        result = await store.delete_conversation("conv-123")

        assert result is True
        # Verify it's deleted
        loaded = await store.load_conversation("conv-123")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_conversation_nonexistent(self, temp_db_store):
        """Test deleting a nonexistent conversation."""
        store = temp_db_store

        result = await store.delete_conversation("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_conversation_exists_true(self, temp_db_store):
        """Test conversation_exists returns True for existing conversation."""
        store = temp_db_store
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            title="Test Conversation",
        )
        await store.save_conversation(conversation)

        result = await store.conversation_exists("conv-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_conversation_exists_false(self, temp_db_store):
        """Test conversation_exists returns False for nonexistent conversation."""
        store = temp_db_store

        result = await store.conversation_exists("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_list_conversations_single_user(self, temp_db_store):
        """Test listing conversations for a single user."""
        store = temp_db_store

        # Create conversations for different users
        conv1 = Conversation(
            conversation_id="conv-1",
            user_id="user-123",
            title="Conversation 1",
        )
        conv2 = Conversation(
            conversation_id="conv-2",
            user_id="user-123",
            title="Conversation 2",
        )
        conv3 = Conversation(
            conversation_id="conv-3",
            user_id="user-456",
            title="Conversation 3",
        )

        await store.save_conversation(conv1)
        await store.save_conversation(conv2)
        await store.save_conversation(conv3)

        result = await store.list_conversations(user_id="user-123")

        assert len(result) == 2
        conv_ids = [conv.conversation_id for conv in result]
        assert "conv-1" in conv_ids
        assert "conv-2" in conv_ids
        assert "conv-3" not in conv_ids

    @pytest.mark.asyncio
    async def test_list_conversations_all_users(self, temp_db_store):
        """Test listing all conversations."""
        store = temp_db_store

        # Create conversations for different users
        conv1 = Conversation(
            conversation_id="conv-1",
            user_id="user-123",
            title="Conversation 1",
        )
        conv2 = Conversation(
            conversation_id="conv-2",
            user_id="user-456",
            title="Conversation 2",
        )

        await store.save_conversation(conv1)
        await store.save_conversation(conv2)

        result = await store.list_conversations()

        assert len(result) == 2
        conv_ids = [conv.conversation_id for conv in result]
        assert "conv-1" in conv_ids
        assert "conv-2" in conv_ids

    @pytest.mark.asyncio
    async def test_list_conversations_empty(self, temp_db_store):
        """Test listing conversations when none exist."""
        store = temp_db_store

        result = await store.list_conversations()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_conversations_pagination(self, temp_db_store):
        """Test conversation listing with pagination."""
        store = temp_db_store

        # Create multiple conversations
        for i in range(5):
            conv = Conversation(
                conversation_id=f"conv-{i}",
                user_id="user-123",
                title=f"Conversation {i}",
            )
            await store.save_conversation(conv)

        # Test pagination
        result_page1 = await store.list_conversations(
            user_id="user-123", limit=2, offset=0
        )
        result_page2 = await store.list_conversations(
            user_id="user-123", limit=2, offset=2
        )

        assert len(result_page1) == 2
        assert len(result_page2) == 2

        # Ensure no overlap
        page1_ids = [conv.conversation_id for conv in result_page1]
        page2_ids = [conv.conversation_id for conv in result_page2]
        assert len(set(page1_ids) & set(page2_ids)) == 0

    @pytest.mark.asyncio
    async def test_row_to_conversation(self, temp_db_store):
        """Test _row_to_conversation static method."""
        from datetime import datetime

        # Create a mock row
        class MockRow:
            def __init__(self, data):
                self._data = data

            def __getitem__(self, key):
                return self._data[key]

        now = datetime.now()
        row = MockRow(
            {
                "conversation_id": "conv-123",
                "user_id": "user-123",
                "title": "Test Title",
                "agent_name": "Agent-1",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "status": "active",
            }
        )

        conversation = SQLiteConversationStore._row_to_conversation(row)

        assert conversation.conversation_id == "conv-123"
        assert conversation.user_id == "user-123"
        assert conversation.agent_name == "Agent-1"
        assert conversation.title == "Test Title"
        assert conversation.status == "active"

    @pytest.mark.asyncio
    async def test_concurrent_initialization(self, temp_db_store):
        """Test that concurrent initialization calls don't cause issues"""
        import asyncio

        # Reset initialization state
        temp_db_store._initialized = False
        temp_db_store._init_lock = None

        # Create multiple concurrent initialization tasks
        async def init_task():
            await temp_db_store._ensure_initialized()
            return temp_db_store._initialized

        # Run multiple initialization tasks concurrently
        tasks = [init_task() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All should succeed and return True
        assert all(results)
        assert temp_db_store._initialized is True
