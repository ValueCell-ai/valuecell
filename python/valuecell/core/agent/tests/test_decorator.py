"""
Unit tests for valuecell.core.agent.decorator module
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from a2a.server.events import EventQueue
from a2a.types import AgentCapabilities, AgentCard
from valuecell.core.agent.decorator import (
    GenericAgentExecutor,
    _create_agent_executor,
    _serve,
    create_wrapped_agent,
)
from valuecell.core.types import (
    BaseAgent,
    StreamResponse,
    StreamResponseEvent,
    NotifyResponse,
    NotifyResponseEvent,
)


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    def __init__(self):
        self.stream_called = False
        self.notify_called = False

    async def stream(self, query, context_id, task_id, dependencies):
        self.stream_called = True
        yield StreamResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK, content="Hello world"
        )

    async def notify(self, query, context_id, task_id, dependencies):
        self.notify_called = True
        yield NotifyResponse(
            event=NotifyResponseEvent.MESSAGE, content="Notification sent"
        )


class MockToolCallAgent(BaseAgent):
    """Mock agent that returns tool call responses."""

    def __init__(self):
        self.stream_called = False

    async def stream(self, query, context_id, task_id, dependencies):
        self.stream_called = True
        yield StreamResponse(
            event=StreamResponseEvent.TOOL_CALL_STARTED,
            content="Tool call started",
            metadata={
                "tool_call_id": "call-123",
                "tool_name": "test_tool",
                "tool_result": "Tool result data",
            },
        )


class TestGenericAgentExecutor:
    """Test GenericAgentExecutor class."""

    @pytest.mark.asyncio
    async def test_execute_with_existing_task(self):
        """Test execute method with existing task."""
        agent = MockAgent()
        executor = GenericAgentExecutor(agent)

        # Mock request context
        context = MagicMock()
        context.get_user_input.return_value = "test query"
        context.current_task = MagicMock()
        context.current_task.id = "task-123"
        context.current_task.context_id = "context-456"
        context.metadata = {}
        context.message = MagicMock()
        context.message.metadata = {}

        # Mock event queue
        event_queue = MagicMock(spec=EventQueue)
        event_queue.enqueue_event = AsyncMock()

        # Mock task updater
        with patch("valuecell.core.agent.decorator.TaskUpdater") as mock_updater_class:
            mock_updater = MagicMock()
            mock_updater.update_status = AsyncMock()
            mock_updater.complete = AsyncMock()
            mock_updater_class.return_value = mock_updater

            await executor.execute(context, event_queue)

            # Verify agent.stream was called
            assert agent.stream_called

            # Verify task updater was used
            mock_updater_class.assert_called_once_with(
                event_queue, "task-123", "context-456"
            )
            assert (
                mock_updater.update_status.call_count >= 2
            )  # At least start and complete
            mock_updater.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_creates_new_task(self):
        """Test execute method creating new task when none exists."""
        agent = MockAgent()
        executor = GenericAgentExecutor(agent)

        context = MagicMock()
        context.get_user_input.return_value = "test query"
        context.current_task = None
        context.metadata = {}
        context.message = MagicMock()
        context.message.metadata = {}

        event_queue = MagicMock(spec=EventQueue)
        event_queue.enqueue_event = AsyncMock()

        with (
            patch("valuecell.core.agent.decorator.new_task") as mock_new_task,
            patch("valuecell.core.agent.decorator.TaskUpdater") as mock_updater_class,
        ):
            mock_task = MagicMock()
            mock_task.id = "new-task-123"
            mock_task.context_id = "new-context-456"
            mock_new_task.return_value = mock_task

            mock_updater = MagicMock()
            mock_updater.update_status = AsyncMock()
            mock_updater.complete = AsyncMock()
            mock_updater_class.return_value = mock_updater

            await executor.execute(context, event_queue)

            # Verify new task was created and enqueued
            mock_new_task.assert_called_once_with(context.message)
            event_queue.enqueue_event.assert_called_once_with(mock_task)
            assert mock_task.metadata == {}

    @pytest.mark.asyncio
    async def test_execute_with_notify_metadata(self):
        """Test execute method with notify metadata."""
        agent = MockAgent()
        executor = GenericAgentExecutor(agent)

        context = MagicMock()
        context.get_user_input.return_value = "test query"
        context.current_task = MagicMock()
        context.current_task.id = "task-123"
        context.current_task.context_id = "context-456"
        context.metadata = {"notify": True}
        context.message = MagicMock()
        context.message.metadata = {"notify": True}

        event_queue = MagicMock(spec=EventQueue)
        event_queue.enqueue_event = AsyncMock()

        with patch("valuecell.core.agent.decorator.TaskUpdater") as mock_updater_class:
            mock_updater = MagicMock()
            mock_updater.update_status = AsyncMock()
            mock_updater.complete = AsyncMock()
            mock_updater_class.return_value = mock_updater

            await executor.execute(context, event_queue)

            # Verify agent.notify was called instead of stream
            assert agent.notify_called
            assert not agent.stream_called

    @pytest.mark.asyncio
    async def test_execute_handles_exceptions(self):
        """Test execute method handles exceptions properly."""
        agent = MockAgent()

        # Make agent.stream raise an exception
        async def failing_stream(*args):
            raise RuntimeError("Agent failed")

        agent.stream = failing_stream
        executor = GenericAgentExecutor(agent)

        context = MagicMock()
        context.get_user_input.return_value = "test query"
        context.current_task = MagicMock()
        context.current_task.id = "task-123"
        context.current_task.context_id = "context-456"
        context.metadata = {}
        context.message = MagicMock()
        context.message.metadata = {}

        event_queue = MagicMock(spec=EventQueue)

        with patch("valuecell.core.agent.decorator.TaskUpdater") as mock_updater_class:
            mock_updater = MagicMock()
            mock_updater.update_status = AsyncMock()
            mock_updater.complete = AsyncMock()
            mock_updater_class.return_value = mock_updater

            await executor.execute(context, event_queue)

            # Verify error was handled
            error_calls = [
                call
                for call in mock_updater.update_status.call_args_list
                if "Error during" in str(call)
            ]
            assert len(error_calls) > 0
            mock_updater.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_handles_tool_call_response(self):
        """Test execute method handles tool call responses properly."""
        agent = MockToolCallAgent()
        executor = GenericAgentExecutor(agent)

        # Mock request context
        context = MagicMock()
        context.get_user_input.return_value = "test query"
        context.current_task = MagicMock()
        context.current_task.id = "task-123"
        context.current_task.context_id = "context-456"
        context.metadata = {}
        context.message = MagicMock()
        context.message.metadata = {}

        # Mock event queue
        event_queue = MagicMock(spec=EventQueue)
        event_queue.enqueue_event = AsyncMock()

        # Mock task updater
        with patch("valuecell.core.agent.decorator.TaskUpdater") as mock_updater_class:
            mock_updater = MagicMock()
            mock_updater.update_status = AsyncMock()
            mock_updater.complete = AsyncMock()
            mock_updater_class.return_value = mock_updater

            await executor.execute(context, event_queue)

            # Verify agent.stream was called
            assert agent.stream_called

            # Verify task updater was used
            mock_updater_class.assert_called_once_with(
                event_queue, "task-123", "context-456"
            )

            # Verify tool call metadata was passed correctly
            tool_call_calls = [
                call
                for call in mock_updater.update_status.call_args_list
                if len(call[1]) > 1
                and call[1].get("metadata", {}).get("tool_call_id") == "call-123"
            ]
            assert len(tool_call_calls) == 1

            # Check that metadata contains tool_result (line 182 coverage)
            metadata = tool_call_calls[0][1]["metadata"]
            assert "tool_result" in metadata
            assert metadata["tool_result"] == "Tool result data"
            assert metadata["tool_call_id"] == "call-123"
            assert metadata["tool_name"] == "test_tool"

            mock_updater.complete.assert_called_once()


class TestCreateAgentExecutor:
    """Test _create_agent_executor function."""

    def test_create_agent_executor(self):
        """Test _create_agent_executor creates GenericAgentExecutor."""
        agent = MockAgent()

        executor = _create_agent_executor(agent)

        assert isinstance(executor, GenericAgentExecutor)
        assert executor.agent == agent


class TestServeDecorator:
    """Test _serve decorator function."""

    @patch("valuecell.core.agent.decorator.find_local_agent_card_by_agent_name")
    def test_serve_decorator(self, mock_find_card):
        """Test _serve decorator creates decorated class."""
        # Mock agent card
        mock_card = AgentCard(
            name="TestAgent",
            url="http://localhost:8000",
            description="Test agent",
            capabilities=AgentCapabilities(streaming=True, push_notifications=False),
            default_input_modes=["text"],
            default_output_modes=["text"],
            version="1.0.0",
            skills=[
                {
                    "id": "test_skill",
                    "name": "Test Skill",
                    "description": "A test skill",
                    "tags": ["test"],
                }
            ],
        )
        mock_find_card.return_value = mock_card

        # Create decorator
        decorator = _serve(mock_card)

        # Apply to mock class
        @decorator
        class TestAgent:
            def __init__(self):
                pass

        # Verify decorated class has expected attributes
        assert hasattr(TestAgent, "serve")

        # Create instance
        instance = TestAgent()
        assert hasattr(instance, "agent_card")
        assert instance.agent_card == mock_card

    @patch("valuecell.core.agent.decorator.find_local_agent_card_by_agent_name")
    @patch("uvicorn.Server")
    @patch("httpx.AsyncClient")
    @patch("valuecell.core.agent.decorator.A2AStarletteApplication")
    @patch("valuecell.core.agent.decorator.DefaultRequestHandler")
    @patch("valuecell.core.agent.decorator.InMemoryTaskStore")
    @patch("valuecell.core.agent.decorator.InMemoryPushNotificationConfigStore")
    @patch("valuecell.core.agent.decorator.BasePushNotificationSender")
    @pytest.mark.asyncio
    async def test_serve_method(
        self,
        mock_sender,
        mock_config_store,
        mock_task_store,
        mock_handler,
        mock_app,
        mock_client,
        mock_server,
        mock_find_card,
    ):
        """Test serve method starts server."""
        # Mock agent card
        mock_card = AgentCard(
            name="TestAgent",
            url="http://localhost:8000",
            description="Test agent",
            capabilities=AgentCapabilities(streaming=True, push_notifications=False),
            default_input_modes=["text"],
            default_output_modes=["text"],
            version="1.0.0",
            skills=[
                {
                    "id": "test_skill",
                    "name": "Test Skill",
                    "description": "A test skill",
                    "tags": ["test"],
                }
            ],
        )
        mock_find_card.return_value = mock_card

        # Create decorated agent
        decorator = _serve(mock_card)

        @decorator
        class TestAgent:
            def __init__(self):
                self._host = "localhost"
                self._port = 8000

        instance = TestAgent()

        # Mock server
        mock_server_instance = MagicMock()
        mock_server_instance.serve = AsyncMock()
        mock_server.return_value = mock_server_instance

        # Mock app
        mock_app_instance = MagicMock()
        mock_app_instance.build.return_value = MagicMock()
        mock_app.return_value = mock_app_instance

        # Mock other dependencies
        mock_httpx_client = MagicMock()
        mock_httpx_client.aclose = AsyncMock()
        mock_client.return_value = mock_httpx_client
        mock_config_store.return_value = MagicMock()
        mock_task_store.return_value = MagicMock()
        mock_sender.return_value = MagicMock()
        mock_handler.return_value = MagicMock()

        # This would normally run forever, so we patch to avoid it
        with patch(
            "valuecell.core.agent.decorator._create_agent_executor",
            return_value=MagicMock(),
        ):
            # Mock the server to not actually serve
            mock_server_instance.serve = AsyncMock(side_effect=asyncio.CancelledError())
            with pytest.raises(asyncio.CancelledError):
                await instance.serve()

    @pytest.mark.asyncio
    async def test_shutdown_sets_should_exit(self):
        """Test shutdown flips server should_exit flag."""
        mock_card = AgentCard(
            name="TestAgent",
            url="http://localhost:8000",
            description="Test agent",
            capabilities=AgentCapabilities(streaming=True, push_notifications=False),
            default_input_modes=["text"],
            default_output_modes=["text"],
            version="1.0.0",
            skills=[
                {
                    "id": "test_skill",
                    "name": "Test Skill",
                    "description": "A test skill",
                    "tags": ["test"],
                }
            ],
        )

        decorator = _serve(mock_card)

        @decorator
        class TestAgent2:
            def __init__(self):
                self._host = "localhost"
                self._port = 8000

        instance = TestAgent2()

        # Simulate a running uvicorn.Server stored on the instance
        server = MagicMock()
        server.should_exit = False
        instance._server = server

        await instance.shutdown()
        assert instance._server.should_exit is True


class TestCreateWrappedAgent:
    """Test create_wrapped_agent function."""

    @patch("valuecell.core.agent.decorator.find_local_agent_card_by_agent_name")
    def test_create_wrapped_agent_success(self, mock_find_card):
        """Test create_wrapped_agent with valid agent card."""
        mock_card = AgentCard(
            name="TestAgent",
            url="http://localhost:8000",
            description="Test agent",
            capabilities=AgentCapabilities(streaming=True, push_notifications=False),
            default_input_modes=["text"],
            default_output_modes=["text"],
            version="1.0.0",
            skills=[
                {
                    "id": "test_skill",
                    "name": "Test Skill",
                    "description": "A test skill",
                    "tags": ["test"],
                }
            ],
        )
        mock_find_card.return_value = mock_card

        class TestAgent(BaseAgent):
            async def stream(self, query, context_id, task_id, dependencies):
                # Mock implementation
                pass

        result = create_wrapped_agent(TestAgent)

        assert result is not None
        assert hasattr(result, "agent_card")
        assert result.agent_card == mock_card

    @patch("valuecell.core.agent.decorator.find_local_agent_card_by_agent_name")
    def test_create_wrapped_agent_no_card(self, mock_find_card):
        """Test create_wrapped_agent with no agent card found."""
        mock_find_card.return_value = None

        class TestAgent(BaseAgent):
            async def stream(self, query, context_id, task_id, dependencies):
                # Mock implementation
                pass

        with pytest.raises(ValueError, match="No agent configuration found"):
            create_wrapped_agent(TestAgent)
