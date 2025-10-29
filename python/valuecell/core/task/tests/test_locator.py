"""
Tests for process-local TaskService singleton locator.
"""

from unittest.mock import AsyncMock

from valuecell.core.task.locator import (
    get_task_service,
    reset_task_service,
    set_task_service,
)
from valuecell.core.task.service import TaskService


def test_singleton_returns_same_instance():
    reset_task_service()
    s1 = get_task_service()
    s2 = get_task_service()
    assert isinstance(s1, TaskService)
    assert s1 is s2


def test_set_and_reset_task_service():
    reset_task_service()
    custom_manager = AsyncMock()
    custom_service = TaskService(manager=custom_manager)

    set_task_service(custom_service)
    got = get_task_service()
    assert got is custom_service

    reset_task_service()
    new_service = get_task_service()
    assert isinstance(new_service, TaskService)
    assert new_service is not custom_service
