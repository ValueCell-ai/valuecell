"""
Unit tests for valuecell.core.agent.listener module
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from valuecell.core.agent.listener import NotificationListener


class TestNotificationListener:
    """Test NotificationListener class."""

    def test_init(self):
        """Test NotificationListener initialization."""
        listener = NotificationListener("localhost", 5000)

        assert listener.host == "localhost"
        assert listener.port == 5000
        assert listener.notification_callback is None
        assert listener.app is not None

    def test_init_with_callback(self):
        """Test NotificationListener initialization with callback."""

        def callback(task):
            pass

        listener = NotificationListener("localhost", 5000, callback)

        assert listener.notification_callback == callback

    def test_create_app(self):
        """Test that _create_app creates a Starlette app with routes."""
        listener = NotificationListener()

        app = listener._create_app()

        # Check that the app has the notify route
        routes = [route.path for route in app.routes]
        assert "/notify" in routes

    @pytest.mark.asyncio
    async def test_handle_notification_success(self):
        """Test successful notification handling."""
        callback_called = False
        received_task = None

        async def callback(task):
            nonlocal callback_called, received_task
            callback_called = True
            received_task = task

        listener = NotificationListener(notification_callback=callback)

        # Create a test task
        task_data = {
            "id": "test-task-id",
            "context_id": "test-context-id",
            "status": {"state": "completed"},
        }

        # Create a mock request
        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value=task_data)

        # Call the handler
        response = await listener.handle_notification(mock_request)

        # Verify response
        assert response.status_code == 200
        assert response.body == b'{"status":"ok"}'

        # Verify callback was called
        assert callback_called
        assert received_task is not None
        assert received_task.id == "test-task-id"

    @pytest.mark.asyncio
    async def test_handle_notification_sync_callback(self):
        """Test notification handling with synchronous callback."""
        callback_called = False
        received_task = None

        def callback(task):
            nonlocal callback_called, received_task
            callback_called = True
            received_task = task

        listener = NotificationListener(notification_callback=callback)

        task_data = {
            "id": "test-task-id",
            "context_id": "test-context-id",
            "status": {"state": "completed"},
        }

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value=task_data)

        response = await listener.handle_notification(mock_request)

        assert response.status_code == 200
        assert callback_called
        assert received_task.id == "test-task-id"

    @pytest.mark.asyncio
    async def test_handle_notification_no_callback(self):
        """Test notification handling without callback."""
        listener = NotificationListener()

        task_data = {
            "id": "test-task-id",
            "context_id": "test-context-id",
            "status": {"state": "completed"},
        }

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value=task_data)

        response = await listener.handle_notification(mock_request)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_handle_notification_error(self):
        """Test notification handling with error."""
        listener = NotificationListener()

        # Mock request that raises an exception
        mock_request = MagicMock()
        mock_request.json = AsyncMock(side_effect=Exception("Parse error"))

        response = await listener.handle_notification(mock_request)

        assert response.status_code == 500
        response_data = response.body.decode()
        assert "Parse error" in response_data

    @pytest.mark.asyncio
    async def test_handle_notification_invalid_task_data(self):
        """Test notification handling with invalid task data."""

        def callback(task):
            pass

        listener = NotificationListener(notification_callback=callback)

        # Invalid task data that will fail validation
        invalid_task_data = {"invalid_field": "value"}

        mock_request = MagicMock()
        mock_request.json = AsyncMock(return_value=invalid_task_data)

        response = await listener.handle_notification(mock_request)

        # Should return 500 when task validation fails
        assert response.status_code == 500

    def test_integration_with_test_client(self):
        """Integration test using Starlette TestClient."""
        callback_called = False
        received_task = None

        def callback(task):
            nonlocal callback_called, received_task
            callback_called = True
            received_task = task

        listener = NotificationListener(notification_callback=callback)

        client = TestClient(listener.app)

        task_data = {
            "id": "integration-test-task",
            "context_id": "integration-context-id",
            "status": {"state": "completed"},
        }

        response = client.post("/notify", json=task_data)

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert callback_called
        assert received_task.id == "integration-test-task"
