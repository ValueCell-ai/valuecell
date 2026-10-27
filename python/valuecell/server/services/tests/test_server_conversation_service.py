import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from valuecell.core.conversation.models import Conversation
from valuecell.server.services.conversation_service import ConversationService


@pytest.fixture()
def mock_conversations():
    return [
        Conversation(
            conversation_id=f"conv_{i}",
            user_id="user_1",
            agent_name="GeneralAgent",
            title=f"Chat {i}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        for i in range(15)
    ]


@pytest.mark.asyncio
async def test_get_conversation_list_applies_limit_and_offset(mock_conversations):
    service = ConversationService.__new__(ConversationService)
    service.conversation_manager = AsyncMock()
    service.conversation_manager.list_user_conversations.return_value = (
        mock_conversations
    )

    result = await service.get_conversation_list(user_id="user_1", limit=3, offset=6)

    assert result.total == 15
    assert len(result.conversations) == 3
    assert result.conversations[0].conversation_id == "conv_6"
    assert result.conversations[1].conversation_id == "conv_7"
    assert result.conversations[2].conversation_id == "conv_8"


@pytest.mark.asyncio
async def test_get_conversation_list_offset_beyond_total(mock_conversations):
    service = ConversationService.__new__(ConversationService)
    service.conversation_manager = AsyncMock()
    service.conversation_manager.list_user_conversations.return_value = (
        mock_conversations
    )

    result = await service.get_conversation_list(user_id="user_1", limit=10, offset=20)

    assert result.total == 15
    assert result.conversations == []


@pytest.mark.asyncio
async def test_get_conversation_list_excludes_strategy_agents_before_pagination():
    conversations = [
        Conversation(
            conversation_id="reg_0",
            user_id="user_1",
            agent_name="GeneralAgent",
            title="Regular 0",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Conversation(
            conversation_id="strat_0",
            user_id="user_1",
            agent_name="CustomStrategyAgent",
            title="Strategy 0",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Conversation(
            conversation_id="reg_1",
            user_id="user_1",
            agent_name="GeneralAgent",
            title="Regular 1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        Conversation(
            conversation_id="reg_2",
            user_id="user_1",
            agent_name="GeneralAgent",
            title="Regular 2",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]

    service = ConversationService.__new__(ConversationService)
    service.conversation_manager = AsyncMock()
    service.conversation_manager.list_user_conversations.return_value = conversations

    # Total non-strategy conversations is 3 (reg_0, reg_1, reg_2).
    # Requesting limit=2, offset=1 should return [reg_1, reg_2].
    result = await service.get_conversation_list(user_id="user_1", limit=2, offset=1)

    assert result.total == 3
    assert len(result.conversations) == 2
    assert result.conversations[0].conversation_id == "reg_1"
    assert result.conversations[1].conversation_id == "reg_2"
