import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from valuecell.core.conversation.models import ConversationStatus
from valuecell.core.conversation.service import ConversationService
from valuecell.core.types import NotifyResponseEvent, Role


class _ConversationStub(SimpleNamespace):
    def activate(self) -> None:
        self.status = ConversationStatus.ACTIVE

    def require_user_input(self) -> None:
        self.status = ConversationStatus.REQUIRE_USER_INPUT

    def set_status(self, status: ConversationStatus) -> None:
        self.status = status


@pytest.fixture()
def manager() -> AsyncMock:
    mgr = AsyncMock()
    mgr.update_conversation = AsyncMock()
    mgr.create_conversation = AsyncMock()
    mgr.get_conversation = AsyncMock()
    mgr.add_item = AsyncMock()
    mgr.get_conversation_items = AsyncMock()
    return mgr


@pytest.mark.asyncio
async def test_ensure_conversation_returns_existing(manager: AsyncMock):
    existing = _ConversationStub(conversation_id="conv-existing")
    manager.get_conversation.return_value = existing

    service = ConversationService(manager=manager)

    conversation, created = await service.ensure_conversation(
        user_id="user-1", conversation_id="conv-existing"
    )

    assert conversation is existing
    assert created is False
    manager.create_conversation.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_conversation_creates_when_missing(manager: AsyncMock):
    manager.get_conversation.return_value = None
    created_conv = _ConversationStub(conversation_id="conv-new")
    manager.create_conversation.return_value = created_conv

    service = ConversationService(manager=manager)

    conversation, created = await service.ensure_conversation(
        user_id="user-1",
        conversation_id="conv-new",
        title="Sample",
        agent_name="assistant",
    )

    assert conversation is created_conv
    assert created is True
    manager.create_conversation.assert_awaited_once_with(
        user_id="user-1",
        title="Sample",
        conversation_id="conv-new",
        agent_name="assistant",
    )


@pytest.mark.asyncio
async def test_activate_updates_conversation(manager: AsyncMock):
    conversation = _ConversationStub(status=ConversationStatus.INACTIVE)
    manager.get_conversation.return_value = conversation

    service = ConversationService(manager=manager)

    result = await service.activate("conv-1")

    assert result is True
    assert conversation.status == ConversationStatus.ACTIVE
    manager.update_conversation.assert_awaited_once_with(conversation)


@pytest.mark.asyncio
async def test_activate_returns_false_when_missing(manager: AsyncMock):
    manager.get_conversation.return_value = None
    service = ConversationService(manager=manager)

    assert await service.activate("missing") is False
    manager.update_conversation.assert_not_awaited()


@pytest.mark.asyncio
async def test_require_user_input_updates_status(manager: AsyncMock):
    conversation = _ConversationStub(status=ConversationStatus.ACTIVE)
    manager.get_conversation.return_value = conversation

    service = ConversationService(manager=manager)

    assert await service.require_user_input("conv") is True
    assert conversation.status == ConversationStatus.REQUIRE_USER_INPUT
    manager.update_conversation.assert_awaited_once_with(conversation)


@pytest.mark.asyncio
async def test_set_status_handles_missing_conversation(manager: AsyncMock):
    manager.get_conversation.return_value = None
    service = ConversationService(manager=manager)

    assert await service.set_status("conv", ConversationStatus.INACTIVE) is False


@pytest.mark.asyncio
async def test_set_status_updates_conversation(manager: AsyncMock):
    conversation = _ConversationStub(status=ConversationStatus.ACTIVE)
    manager.get_conversation.return_value = conversation

    service = ConversationService(manager=manager)

    assert await service.set_status("conv", ConversationStatus.INACTIVE) is True
    assert conversation.status == ConversationStatus.INACTIVE
    manager.update_conversation.assert_awaited_once_with(conversation)


@pytest.mark.asyncio
async def test_add_item_delegates_to_manager(manager: AsyncMock):
    service = ConversationService(manager=manager)

    await service.add_item(
        role=Role.USER,
        event=NotifyResponseEvent.MESSAGE,
        conversation_id="conv",
        item_id="item",
        payload=None,
    )

    manager.add_item.assert_awaited_once_with(
        role=Role.USER,
        event=NotifyResponseEvent.MESSAGE,
        conversation_id="conv",
        thread_id=None,
        task_id=None,
        payload=None,
        item_id="item",
        agent_name=None,
        metadata=None,
    )


@pytest.mark.asyncio
async def test_get_conversation_items_pass_through(manager: AsyncMock):
    service = ConversationService(manager=manager)
    manager.get_conversation_items.return_value = ["item"]

    items = await service.get_conversation_items(
        conversation_id="conv",
        limit=1,
        offset=2,
    )

    assert items == ["item"]
    manager.get_conversation_items.assert_awaited_once_with(
        conversation_id="conv",
        event=None,
        component_type=None,
        limit=1,
        offset=2,
    )
