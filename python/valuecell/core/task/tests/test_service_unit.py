import pytest
from unittest.mock import AsyncMock

from valuecell.core.task.models import Task
from valuecell.core.task.service import TaskService


@pytest.fixture()
def manager() -> AsyncMock:
    m = AsyncMock()
    m.update_task = AsyncMock()
    m.start_task = AsyncMock(return_value=True)
    m.complete_task = AsyncMock(return_value=True)
    m.fail_task = AsyncMock(return_value=True)
    m.cancel_task = AsyncMock(return_value=True)
    m.cancel_conversation_tasks = AsyncMock(return_value=2)
    return m


def _make_task() -> Task:
    return Task(
        task_id="task",
        query="do something",
        conversation_id="conv",
        user_id="user",
        agent_name="agent",
    )


@pytest.mark.asyncio
async def test_update_task(manager: AsyncMock):
    service = TaskService(manager=manager)
    task = _make_task()

    await service.update_task(task)

    manager.update_task.assert_awaited_once_with(task)


@pytest.mark.asyncio
async def test_start_complete_fail_cancel(manager: AsyncMock):
    service = TaskService(manager=manager)

    assert await service.start_task("task") is True
    assert await service.complete_task("task") is True
    assert await service.fail_task("task", "reason") is True
    assert await service.cancel_task("task") is True

    manager.start_task.assert_awaited_once_with("task")
    manager.complete_task.assert_awaited_once_with("task")
    manager.fail_task.assert_awaited_once_with("task", "reason")
    manager.cancel_task.assert_awaited_once_with("task")


@pytest.mark.asyncio
async def test_cancel_conversation_tasks(manager: AsyncMock):
    service = TaskService(manager=manager)

    result = await service.cancel_conversation_tasks("conv")

    assert result == 2
    manager.cancel_conversation_tasks.assert_awaited_once_with("conv")
