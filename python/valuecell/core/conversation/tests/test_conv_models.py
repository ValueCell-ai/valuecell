"""
Unit tests for valuecell.core.conversation.models module
"""

from datetime import datetime
from unittest.mock import patch


from valuecell.core.conversation.models import Conversation, ConversationStatus


class TestConversationStatus:
    """Test ConversationStatus enum."""

    def test_enum_values(self):
        """Test enum values are correct."""
        assert ConversationStatus.ACTIVE == "active"
        assert ConversationStatus.INACTIVE == "inactive"
        assert ConversationStatus.REQUIRE_USER_INPUT == "require_user_input"

    def test_enum_members(self):
        """Test all enum members exist."""
        assert hasattr(ConversationStatus, "ACTIVE")
        assert hasattr(ConversationStatus, "INACTIVE")
        assert hasattr(ConversationStatus, "REQUIRE_USER_INPUT")


class TestConversation:
    """Test Conversation model."""

    def test_init_minimal(self):
        """Test conversation initialization with minimal fields."""
        created_time = datetime(2023, 1, 1, 12, 0, 0)

        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            created_at=created_time,
            updated_at=created_time,
        )

        assert conversation.conversation_id == "conv-123"
        assert conversation.user_id == "user-123"
        assert conversation.title is None
        assert conversation.created_at == created_time
        assert conversation.updated_at == created_time
        assert conversation.status == ConversationStatus.ACTIVE

    def test_init_full(self):
        """Test conversation initialization with all fields."""
        created_time = datetime(2023, 1, 1, 12, 0, 0)

        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            title="Test Conversation",
            status=ConversationStatus.INACTIVE,
            created_at=created_time,
            updated_at=created_time,
        )

        assert conversation.conversation_id == "conv-123"
        assert conversation.user_id == "user-123"
        assert conversation.title == "Test Conversation"
        assert conversation.created_at == created_time
        assert conversation.updated_at == created_time
        assert conversation.status == ConversationStatus.INACTIVE

    def test_is_active_property(self):
        """Test is_active property."""
        # Active conversation
        conv_active = Conversation(
            conversation_id="conv-1",
            user_id="user-1",
            status=ConversationStatus.ACTIVE,
        )
        assert conv_active.is_active is True

        # Inactive conversation
        conv_inactive = Conversation(
            conversation_id="conv-2",
            user_id="user-1",
            status=ConversationStatus.INACTIVE,
        )
        assert conv_inactive.is_active is False

        # Require user input conversation
        conv_require_input = Conversation(
            conversation_id="conv-3",
            user_id="user-1",
            status=ConversationStatus.REQUIRE_USER_INPUT,
        )
        assert conv_require_input.is_active is False

    def test_set_status(self):
        """Test set_status method."""
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
        )

        with patch("valuecell.core.conversation.models.datetime") as mock_datetime:
            update_time = datetime(2023, 1, 1, 13, 0, 0)
            mock_datetime.now.return_value = update_time

            conversation.set_status(ConversationStatus.INACTIVE)

            assert conversation.status == ConversationStatus.INACTIVE
            assert conversation.updated_at == update_time

    def test_activate(self):
        """Test activate method."""
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            status=ConversationStatus.INACTIVE,
        )

        with patch("valuecell.core.conversation.models.datetime") as mock_datetime:
            update_time = datetime(2023, 1, 1, 13, 0, 0)
            mock_datetime.now.return_value = update_time

            conversation.activate()

            assert conversation.status == ConversationStatus.ACTIVE
            assert conversation.updated_at == update_time

    def test_deactivate(self):
        """Test deactivate method."""
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            status=ConversationStatus.ACTIVE,
        )

        with patch("valuecell.core.conversation.models.datetime") as mock_datetime:
            update_time = datetime(2023, 1, 1, 13, 0, 0)
            mock_datetime.now.return_value = update_time

            conversation.deactivate()

            assert conversation.status == ConversationStatus.INACTIVE
            assert conversation.updated_at == update_time

    def test_require_user_input(self):
        """Test require_user_input method."""
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            status=ConversationStatus.ACTIVE,
        )

        with patch("valuecell.core.conversation.models.datetime") as mock_datetime:
            update_time = datetime(2023, 1, 1, 13, 0, 0)
            mock_datetime.now.return_value = update_time

            conversation.require_user_input()

            assert conversation.status == ConversationStatus.REQUIRE_USER_INPUT
            assert conversation.updated_at == update_time

    def test_touch(self):
        """Test touch method."""
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
        )

        with patch("valuecell.core.conversation.models.datetime") as mock_datetime:
            touch_time = datetime(2023, 1, 1, 14, 0, 0)
            mock_datetime.now.return_value = touch_time

            conversation.touch()

            assert conversation.updated_at == touch_time

    def test_json_encoders(self):
        """Test JSON serialization with datetime encoders."""
        conversation = Conversation(
            conversation_id="conv-123",
            user_id="user-123",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 1, 1, 13, 0, 0),
        )

        # Test that model_dump works (pydantic handles the datetime encoding)
        data = conversation.model_dump()
        assert data["conversation_id"] == "conv-123"
        assert data["user_id"] == "user-123"
        assert "created_at" in data
        assert "updated_at" in data
