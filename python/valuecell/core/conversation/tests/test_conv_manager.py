"""
Unit tests for valuecell.core.conversation.manager module
"""

from datetime import datetime
import json
from unittest.mock import AsyncMock, patch

import pytest

from valuecell.core.conversation.manager import ConversationManager
from valuecell.core.conversation.models import Conversation, ConversationStatus
from valuecell.core.types import ConversationItem, Role, NotifyResponseEvent
from valuecell.core.types import ComponentType


class TestConversationManager:
    """Test ConversationManager class."""

    def test_init_default_stores(self):
        """Test ConversationManager initialization with default stores."""
        manager = ConversationManager()

        assert manager.conversation_store is not None
        assert manager.item_store is not None

    def test_init_custom_stores(self):
        """Test ConversationManager initialization with custom stores."""
        mock_conv_store = AsyncMock()
        mock_item_store = AsyncMock()

        manager = ConversationManager(
            conversation_store=mock_conv_store,
            item_store=mock_item_store,
        )

        assert manager.conversation_store == mock_conv_store
        assert manager.item_store == mock_item_store

    @pytest.mark.asyncio
    async def test_create_conversation_minimal(self):
        """Test creating a conversation with minimal parameters."""
        manager = ConversationManager()
        user_id = "user-123"

        with patch(
            "valuecell.core.conversation.manager.generate_conversation_id"
        ) as mock_uuid:
            mock_uuid.return_value = "conv-generated-123"

            result = await manager.create_conversation(user_id)

            assert isinstance(result, Conversation)
            assert result.user_id == user_id
            assert result.conversation_id == "conv-generated-123"
            assert result.title is None
            assert result.status == ConversationStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_create_conversation_full(self):
        """Test creating a conversation with all parameters."""
        manager = ConversationManager()
        user_id = "user-123"
        title = "Test Conversation"
        conversation_id = "custom-conv-123"

        result = await manager.create_conversation(
            user_id=user_id,
            title=title,
            conversation_id=conversation_id,
        )

        assert isinstance(result, Conversation)
        assert result.user_id == user_id
        assert result.conversation_id == conversation_id
        assert result.title == title
        assert result.status == ConversationStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_conversation_existing(self):
        """Test getting an existing conversation."""
        manager = ConversationManager()
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            title="Test Conversation",
        )

        # Mock the store
        manager.conversation_store.load_conversation = AsyncMock(
            return_value=conversation
        )

        result = await manager.get_conversation("conv-123")

        assert result == conversation
        manager.conversation_store.load_conversation.assert_called_once_with("conv-123")

    @pytest.mark.asyncio
    async def test_get_conversation_nonexistent(self):
        """Test getting a nonexistent conversation."""
        manager = ConversationManager()

        # Mock the store
        manager.conversation_store.load_conversation = AsyncMock(return_value=None)

        result = await manager.get_conversation("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_conversation(self):
        """Test updating a conversation."""
        manager = ConversationManager()
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            title="Original Title",
        )

        with patch("valuecell.core.conversation.manager.datetime") as mock_datetime:
            update_time = datetime(2023, 1, 1, 13, 0, 0)
            mock_datetime.now.return_value = update_time

            # Mock the store
            manager.conversation_store.save_conversation = AsyncMock()

            await manager.update_conversation(conversation)

            assert conversation.updated_at == update_time
            manager.conversation_store.save_conversation.assert_called_once_with(
                conversation
            )

    @pytest.mark.asyncio
    async def test_delete_conversation_success(self):
        """Test successfully deleting a conversation."""
        manager = ConversationManager()

        # Mock the stores
        manager.item_store.delete_conversation_items = AsyncMock()
        manager.conversation_store.delete_conversation = AsyncMock(return_value=True)

        result = await manager.delete_conversation("conv-123")

        assert result is True
        manager.item_store.delete_conversation_items.assert_called_once_with("conv-123")
        manager.conversation_store.delete_conversation.assert_called_once_with(
            "conv-123"
        )

    @pytest.mark.asyncio
    async def test_delete_conversation_failure(self):
        """Test failing to delete a conversation."""
        manager = ConversationManager()

        # Mock the stores
        manager.item_store.delete_conversation_items = AsyncMock()
        manager.conversation_store.delete_conversation = AsyncMock(return_value=False)

        result = await manager.delete_conversation("conv-123")

        assert result is False
        manager.item_store.delete_conversation_items.assert_called_once_with("conv-123")
        manager.conversation_store.delete_conversation.assert_called_once_with(
            "conv-123"
        )

    @pytest.mark.asyncio
    async def test_list_user_conversations(self):
        """Test listing user conversations."""
        manager = ConversationManager()
        user_id = "user-123"

        conversations = [
            Conversation(conversation_id="conv-1", user_id=user_id),
            Conversation(conversation_id="conv-2", user_id=user_id),
        ]

        # Mock the store
        manager.conversation_store.list_conversations = AsyncMock(
            return_value=conversations
        )

        result = await manager.list_user_conversations(user_id, limit=10, offset=5)

        assert result == conversations
        manager.conversation_store.list_conversations.assert_called_once_with(
            user_id, 10, 5
        )

    @pytest.mark.asyncio
    async def test_conversation_exists_true(self):
        """Test conversation_exists returns True."""
        manager = ConversationManager()

        # Mock the store
        manager.conversation_store.conversation_exists = AsyncMock(return_value=True)

        result = await manager.conversation_exists("conv-123")

        assert result is True
        manager.conversation_store.conversation_exists.assert_called_once_with(
            "conv-123"
        )

    @pytest.mark.asyncio
    async def test_conversation_exists_false(self):
        """Test conversation_exists returns False."""
        manager = ConversationManager()

        # Mock the store
        manager.conversation_store.conversation_exists = AsyncMock(return_value=False)

        result = await manager.conversation_exists("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_add_item_success(self):
        """Test successfully adding an item to a conversation."""
        manager = ConversationManager()

        conversation = Conversation(conversation_id="conv-123", user_id="user-123")

        # Mock stores
        manager.conversation_store.load_conversation = AsyncMock(
            return_value=conversation
        )
        manager.item_store.save_item = AsyncMock()
        manager.conversation_store.save_conversation = AsyncMock()

        with patch("valuecell.core.conversation.manager.generate_item_id") as mock_uuid:
            mock_uuid.return_value = "item-generated-123"

            result = await manager.add_item(
                role=Role.USER,
                event=NotifyResponseEvent.MESSAGE,
                conversation_id="conv-123",
                payload='{"message": "Hello"}',
                agent_name="agent-123",
            )

            assert result is not None
            assert result.item_id == "item-generated-123"
            assert result.role == Role.USER
            assert result.event == NotifyResponseEvent.MESSAGE
            assert result.conversation_id == "conv-123"
            assert result.payload == '{"message": "Hello"}'
            assert result.agent_name == "agent-123"

            # Verify stores were called
            manager.conversation_store.load_conversation.assert_called_once_with(
                "conv-123"
            )
            manager.item_store.save_item.assert_called_once()
            saved_item = manager.item_store.save_item.call_args.args[0]
            assert saved_item.agent_name == "agent-123"
            manager.conversation_store.save_conversation.assert_called_once_with(
                conversation
            )

    @pytest.mark.asyncio
    async def test_add_item_conversation_not_exists(self):
        """Test adding item to nonexistent conversation."""
        manager = ConversationManager()

        # Mock store to return None
        manager.conversation_store.load_conversation = AsyncMock(return_value=None)

        result = await manager.add_item(
            role=Role.USER,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="nonexistent",
        )

        assert result is None
        manager.conversation_store.load_conversation.assert_called_once_with(
            "nonexistent"
        )

    @pytest.mark.asyncio
    async def test_add_item_with_pydantic_payload(self):
        """Test adding item with pydantic model payload."""
        manager = ConversationManager()

        conversation = Conversation(conversation_id="conv-123", user_id="user-123")

        # Mock stores
        manager.conversation_store.load_conversation = AsyncMock(
            return_value=conversation
        )
        manager.item_store.save_item = AsyncMock()
        manager.conversation_store.save_conversation = AsyncMock()

        # Create a mock pydantic model
        class MockPayload:
            def __init__(self, message: str):
                self.message = message

            def model_dump_json(self, exclude_none=True):
                return f'{{"message": "{self.message}"}}'

        payload = MockPayload("Hello World")

        result = await manager.add_item(
            role=Role.USER,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-123",
            payload=payload,
        )

        assert result is not None
        assert result.payload == '{"message": "Hello World"}'

    @pytest.mark.asyncio
    async def test_add_item_with_string_payload_fallback(self):
        """Test adding item with payload that falls back to string conversion."""
        manager = ConversationManager()

        conversation = Conversation(conversation_id="conv-123", user_id="user-123")

        # Mock stores
        manager.conversation_store.load_conversation = AsyncMock(
            return_value=conversation
        )
        manager.item_store.save_item = AsyncMock()
        manager.conversation_store.save_conversation = AsyncMock()

        # Payload without model_dump_json method
        class MockPayload:
            def __str__(self):
                return "string payload"

        payload = MockPayload()

        result = await manager.add_item(
            role=Role.USER,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-123",
            payload=payload,
        )

        assert result is not None
        assert result.payload == "string payload"

    @pytest.mark.asyncio
    async def test_add_item_with_metadata_serialization_success(self):
        """Test adding item with serializable metadata produces JSON string."""
        manager = ConversationManager()

        conversation = Conversation(conversation_id="conv-123", user_id="user-123")

        # Mock stores
        manager.conversation_store.load_conversation = AsyncMock(
            return_value=conversation
        )
        manager.item_store.save_item = AsyncMock()
        manager.conversation_store.save_conversation = AsyncMock()

        metadata = {"score": 1, "note": "ok", "ts": 123.4}

        result = await manager.add_item(
            role=Role.USER,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-123",
            payload="hello",
            metadata=metadata,
        )

        assert result is not None
        # Verify metadata is JSON-dumped with default=str
        expected_metadata = json.dumps(metadata, default=str)
        saved_item = manager.item_store.save_item.call_args.args[0]
        assert saved_item.metadata == expected_metadata

    @pytest.mark.asyncio
    async def test_add_item_with_metadata_serialization_exception_fallback(self):
        """Test adding item with circular metadata falls back to empty JSON object."""
        manager = ConversationManager()

        conversation = Conversation(conversation_id="conv-123", user_id="user-123")

        # Mock stores
        manager.conversation_store.load_conversation = AsyncMock(
            return_value=conversation
        )
        manager.item_store.save_item = AsyncMock()
        manager.conversation_store.save_conversation = AsyncMock()

        # Create circular dict to trigger json.dumps exception
        metadata = {}
        metadata["self"] = metadata

        result = await manager.add_item(
            role=Role.USER,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-123",
            payload="hello",
            metadata=metadata,
        )

        assert result is not None
        saved_item = manager.item_store.save_item.call_args.args[0]
        # Fallback path sets metadata to "{}"
        assert saved_item.metadata == "{}"

    @pytest.mark.asyncio
    async def test_get_conversation_items(self):
        """Test getting conversation items."""
        manager = ConversationManager()

        items = [
            ConversationItem(
                item_id="item-1",
                role=Role.USER,
                event=NotifyResponseEvent.MESSAGE,
                conversation_id="conv-123",
                payload="Hello",
            ),
            ConversationItem(
                item_id="item-2",
                role=Role.AGENT,
                event=NotifyResponseEvent.MESSAGE,
                conversation_id="conv-123",
                payload="Hi there!",
            ),
        ]

        # Mock store
        manager.item_store.get_items = AsyncMock(return_value=items)

        result = await manager.get_conversation_items("conv-123")

        assert result == items
        manager.item_store.get_items.assert_called_once_with(
            conversation_id="conv-123",
            event=None,
            component_type=None,
            limit=None,
            offset=0,
        )

    @pytest.mark.asyncio
    async def test_get_latest_item(self):
        """Test getting latest item."""
        manager = ConversationManager()

        latest_item = ConversationItem(
            item_id="latest-item",
            role=Role.AGENT,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-123",
            payload="Latest response",
        )

        # Mock store
        manager.item_store.get_latest_item = AsyncMock(return_value=latest_item)

        result = await manager.get_latest_item("conv-123")

        assert result == latest_item
        manager.item_store.get_latest_item.assert_called_once_with("conv-123")

    @pytest.mark.asyncio
    async def test_get_item(self):
        """Test getting a specific item."""
        manager = ConversationManager()

        item = ConversationItem(
            item_id="target-item",
            role=Role.USER,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-123",
            payload="Target message",
        )

        # Mock store
        manager.item_store.get_item = AsyncMock(return_value=item)

        result = await manager.get_item("target-item")

        assert result == item
        manager.item_store.get_item.assert_called_once_with("target-item")

    @pytest.mark.asyncio
    async def test_get_item_count(self):
        """Test getting item count."""
        manager = ConversationManager()

        # Mock store
        manager.item_store.get_item_count = AsyncMock(return_value=5)

        result = await manager.get_item_count("conv-123")

        assert result == 5
        manager.item_store.get_item_count.assert_called_once_with("conv-123")

    @pytest.mark.asyncio
    async def test_get_items_by_role(self):
        """Test getting items filtered by role."""
        manager = ConversationManager()

        items = [
            ConversationItem(
                item_id="agent-1",
                role=Role.AGENT,
                event=NotifyResponseEvent.MESSAGE,
                conversation_id="conv-123",
                payload="Agent response",
            ),
        ]

        # Mock store
        manager.item_store.get_items = AsyncMock(return_value=items)

        result = await manager.get_items_by_role("conv-123", Role.AGENT)

        assert result == items
        manager.item_store.get_items.assert_called_once_with(
            "conv-123", role=Role.AGENT
        )

    @pytest.mark.asyncio
    async def test_deactivate_conversation_success(self):
        """Test successfully deactivating a conversation."""
        manager = ConversationManager()

        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            status=ConversationStatus.ACTIVE,
        )

        # Mock stores
        manager.conversation_store.load_conversation = AsyncMock(
            return_value=conversation
        )
        manager.conversation_store.save_conversation = AsyncMock()

        result = await manager.deactivate_conversation("conv-123")

        assert result is True
        assert conversation.status == ConversationStatus.INACTIVE
        manager.conversation_store.load_conversation.assert_called_once_with("conv-123")
        manager.conversation_store.save_conversation.assert_called_once_with(
            conversation
        )

    @pytest.mark.asyncio
    async def test_deactivate_conversation_not_exists(self):
        """Test deactivating nonexistent conversation."""
        manager = ConversationManager()

        # Mock store
        manager.conversation_store.load_conversation = AsyncMock(return_value=None)

        result = await manager.deactivate_conversation("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_activate_conversation_success(self):
        """Test successfully activating a conversation."""
        manager = ConversationManager()

        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            status=ConversationStatus.INACTIVE,
        )

        # Mock stores
        manager.conversation_store.load_conversation = AsyncMock(
            return_value=conversation
        )
        manager.conversation_store.save_conversation = AsyncMock()

        result = await manager.activate_conversation("conv-123")

        assert result is True
        assert conversation.status == ConversationStatus.ACTIVE
        manager.conversation_store.load_conversation.assert_called_once_with("conv-123")
        manager.conversation_store.save_conversation.assert_called_once_with(
            conversation
        )

    @pytest.mark.asyncio
    async def test_set_conversation_status_success(self):
        """Test successfully setting conversation status."""
        manager = ConversationManager()

        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            status=ConversationStatus.ACTIVE,
        )

        # Mock stores
        manager.conversation_store.load_conversation = AsyncMock(
            return_value=conversation
        )
        manager.conversation_store.save_conversation = AsyncMock()

        result = await manager.set_conversation_status(
            "conv-123", ConversationStatus.REQUIRE_USER_INPUT
        )

        assert result is True
        assert conversation.status == ConversationStatus.REQUIRE_USER_INPUT
        manager.conversation_store.load_conversation.assert_called_once_with("conv-123")
        manager.conversation_store.save_conversation.assert_called_once_with(
            conversation
        )

    @pytest.mark.asyncio
    async def test_require_user_input_success(self):
        """Test successfully requiring user input."""
        manager = ConversationManager()

        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            status=ConversationStatus.ACTIVE,
        )

        # Mock stores
        manager.conversation_store.load_conversation = AsyncMock(
            return_value=conversation
        )
        manager.conversation_store.save_conversation = AsyncMock()

        result = await manager.require_user_input("conv-123")

        assert result is True
        assert conversation.status == ConversationStatus.REQUIRE_USER_INPUT

    @pytest.mark.asyncio
    async def test_get_conversations_by_status(self):
        """Test getting conversations filtered by status."""
        manager = ConversationManager()
        user_id = "user-123"

        # Create conversations with different statuses
        active_conv = Conversation(
            conversation_id="active-conv",
            user_id=user_id,
            status=ConversationStatus.ACTIVE,
        )
        inactive_conv = Conversation(
            conversation_id="inactive-conv",
            user_id=user_id,
            status=ConversationStatus.INACTIVE,
        )
        require_input_conv = Conversation(
            conversation_id="require-conv",
            user_id=user_id,
            status=ConversationStatus.REQUIRE_USER_INPUT,
        )

        all_conversations = [active_conv, inactive_conv, require_input_conv]

        # Mock store
        manager.conversation_store.list_conversations = AsyncMock(
            return_value=all_conversations
        )

        result = await manager.get_conversations_by_status(
            user_id, ConversationStatus.INACTIVE, limit=10, offset=0
        )

        assert len(result) == 1
        assert result[0] == inactive_conv
        manager.conversation_store.list_conversations.assert_called_once_with(
            user_id, 20, 0
        )

    @pytest.mark.asyncio
    async def test_update_task_component_status_updates_item(self):
        """update_task_component_status should update payload.content.task_status and metadata"""
        manager = ConversationManager()

        # Create a conversation item representing a scheduled_task_controller component
        content_obj = {"task_id": "task-1", "task_title": "T"}
        payload_obj = {
            "component_type": ComponentType.SCHEDULED_TASK_CONTROLLER,
            "content": json.dumps(content_obj),
        }
        item = ConversationItem(
            item_id="item-1",
            role=Role.AGENT,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-1",
            payload=json.dumps(payload_obj),
            metadata="{}",
            task_id="task-1",
        )

        manager.item_store.get_items = AsyncMock(return_value=[item])
        manager.item_store.save_item = AsyncMock()

        await manager.update_task_component_status("task-1", "failed", "boom")

        # save_item called once with updated item
        manager.item_store.save_item.assert_awaited_once()
        saved_item = manager.item_store.save_item.call_args.args[0]

        # payload should be JSON and contain content whose task_status is 'failed'
        parsed = json.loads(saved_item.payload)
        inner = json.loads(parsed.get("content"))
        assert inner.get("task_status") == "failed"

        # metadata should include error_reason
        meta = json.loads(saved_item.metadata)
        assert meta.get("error_reason") == "boom"

    @pytest.mark.asyncio
    async def test_update_task_component_status_skips_non_matching(self):
        """Non-matching component_type should be ignored."""
        manager = ConversationManager()

        payload_obj = {"component_type": "other_component", "content": "{}"}
        item = ConversationItem(
            item_id="item-2",
            role=Role.AGENT,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-1",
            payload=json.dumps(payload_obj),
            metadata="{}",
            task_id="task-2",
        )

        manager.item_store.get_items = AsyncMock(return_value=[item])
        manager.item_store.save_item = AsyncMock()

        await manager.update_task_component_status("task-2", "failed", "boom")

        manager.item_store.save_item.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_task_component_status_skips_invalid_payload(self):
        """Invalid JSON payload should be skipped without raising."""
        manager = ConversationManager()

        item = ConversationItem(
            item_id="item-3",
            role=Role.AGENT,
            event=NotifyResponseEvent.MESSAGE,
            conversation_id="conv-1",
            payload="not-a-json",
            metadata="{}",
            task_id="task-3",
        )

        manager.item_store.get_items = AsyncMock(return_value=[item])
        manager.item_store.save_item = AsyncMock()

        await manager.update_task_component_status("task-3", "failed", "boom")

        manager.item_store.save_item.assert_not_awaited()
