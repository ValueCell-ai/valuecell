"""
Comprehensive pytest tests for AgentOrchestrator.

This test suite covers the 2x2 matrix of agent capabilities:
- streaming: True/False
- push_notifications: True/False

Test coverage includes:
- Core flow processing with different agent capabilities
- Session management and message handling
- Task lifecycle management
- Error handling and edge cases
- Metadata propagation
- Resource management
"""

from unittest.mock import AsyncMock, Mock
from typing import AsyncGenerator, Any

import pytest
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    TaskState,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    TaskStatus,
    Part,
    TextPart,
    Artifact,
)

from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.core.coordinate.models import ExecutionPlan
from valuecell.core.session import Role
from valuecell.core.task import Task, TaskStatus as CoreTaskStatus
from valuecell.core.types import (
    UserInput,
    UserInputMetadata,
    MessageChunk,
    MessageDataKind,
)


@pytest.fixture
def session_id() -> str:
    """Sample session ID for testing."""
    return "test-session-123"


@pytest.fixture
def user_id() -> str:
    """Sample user ID for testing."""
    return "test-user-456"


@pytest.fixture
def sample_query() -> str:
    """Sample user query for testing."""
    return "What is the latest stock price for AAPL?"


@pytest.fixture
def user_input_metadata(session_id: str, user_id: str) -> UserInputMetadata:
    """Sample user input metadata."""
    return UserInputMetadata(session_id=session_id, user_id=user_id)


@pytest.fixture
def sample_user_input(
    sample_query: str, user_input_metadata: UserInputMetadata
) -> UserInput:
    """Sample user input for testing."""
    return UserInput(
        query=sample_query, desired_agent_name="TestAgent", meta=user_input_metadata
    )


@pytest.fixture
def sample_task(session_id: str, user_id: str) -> Task:
    """Sample task for testing."""
    return Task(
        task_id="test-task-789",
        session_id=session_id,
        user_id=user_id,
        agent_name="TestAgent",
        status=CoreTaskStatus.PENDING,
        remote_task_ids=[],
    )


@pytest.fixture(
    params=[
        (True, True),  # streaming + push_notifications
        (True, False),  # streaming only
        (False, True),  # push_notifications only
        (False, False),  # basic agent
    ]
)
def agent_capabilities(request) -> AgentCapabilities:
    """Parametrized fixture for different agent capability combinations."""
    streaming, push_notifications = request.param
    return AgentCapabilities(streaming=streaming, push_notifications=push_notifications)


@pytest.fixture
def mock_agent_card(agent_capabilities: AgentCapabilities) -> AgentCard:
    """Mock agent card with different capabilities."""
    return AgentCard(
        name="TestAgent",
        description="Test agent for unit testing",
        url="http://localhost:8000/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=agent_capabilities,
        skills=[
            AgentSkill(
                id="test_skill_1",
                name="test_skill",
                description="Test skill",
                tags=["test", "demo"],
            )
        ],
        supports_authenticated_extended_card=False,
    )


@pytest.fixture
def sample_execution_plan(
    session_id: str, user_id: str, sample_query: str, sample_task: Task
) -> ExecutionPlan:
    """Sample execution plan with one task."""
    return ExecutionPlan(
        plan_id="test-plan-123",
        session_id=session_id,
        user_id=user_id,
        query=sample_query,
        tasks=[sample_task],
        created_at="2025-09-16T10:00:00",
    )


@pytest.fixture
def mock_session_manager() -> Mock:
    """Mock session manager."""
    mock = Mock()
    mock.add_message = AsyncMock()
    mock.create_session = AsyncMock(return_value="new-session-id")
    mock.get_session_messages = AsyncMock(return_value=[])
    mock.list_user_sessions = AsyncMock(return_value=[])
    mock.session_exists = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_task_manager() -> Mock:
    """Mock task manager."""
    mock = Mock()
    mock.store = Mock()
    mock.store.save_task = AsyncMock()
    mock.start_task = AsyncMock()
    mock.complete_task = AsyncMock()
    mock.fail_task = AsyncMock()
    mock.cancel_session_tasks = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def mock_agent_client() -> Mock:
    """Mock agent client for different response types."""
    mock = Mock()
    mock.send_message = AsyncMock()
    return mock


@pytest.fixture
def mock_agent_connections(mock_agent_card: AgentCard, mock_agent_client: Mock) -> Mock:
    """Mock agent connections."""
    mock = Mock()
    mock.start_agent = AsyncMock(return_value=mock_agent_card)
    mock.get_client = AsyncMock(return_value=mock_agent_client)
    mock.list_available_agents = Mock(return_value=["TestAgent"])
    mock.stop_all = AsyncMock()
    return mock


@pytest.fixture
def mock_planner(sample_execution_plan: ExecutionPlan) -> Mock:
    """Mock execution planner."""
    mock = Mock()
    mock.create_plan = AsyncMock(return_value=sample_execution_plan)
    return mock


@pytest.fixture
def orchestrator(
    mock_session_manager: Mock,
    mock_task_manager: Mock,
    mock_agent_connections: Mock,
    mock_planner: Mock,
) -> AgentOrchestrator:
    """AgentOrchestrator instance with mocked dependencies."""
    orchestrator = AgentOrchestrator()
    orchestrator.session_manager = mock_session_manager
    orchestrator.task_manager = mock_task_manager
    orchestrator.agent_connections = mock_agent_connections
    orchestrator.planner = mock_planner
    return orchestrator


def create_mock_remote_task(task_id: str = "remote-task-123") -> Mock:
    """Create a mock remote task."""
    remote_task = Mock()
    remote_task.id = task_id
    remote_task.status = Mock()
    remote_task.status.state = TaskState.submitted
    return remote_task


async def create_streaming_response(
    content_chunks: list[str], remote_task_id: str = "remote-task-123"
) -> AsyncGenerator[tuple[Mock, Any], None]:
    """Create a mock streaming response."""
    remote_task = create_mock_remote_task(remote_task_id)

    # First yield the task submission with None event (matching new logic)
    yield remote_task, None

    # Then yield content chunks
    for i, chunk in enumerate(content_chunks):
        # Create proper Artifact with Part and TextPart
        text_part = TextPart(text=chunk)
        part = Part(root=text_part)
        artifact = Artifact(artifactId=f"test-artifact-{i}", parts=[part])

        artifact_event = TaskArtifactUpdateEvent(
            artifact=artifact,
            contextId="test-context",
            taskId=remote_task_id,
            final=False,
        )
        yield remote_task, artifact_event


async def create_non_streaming_response(
    content: str, remote_task_id: str = "remote-task-123"
) -> AsyncGenerator[tuple[Mock, Any], None]:
    """Create a mock non-streaming response."""
    remote_task = create_mock_remote_task(remote_task_id)

    # First yield the task submission with None event
    yield remote_task, None

    # For non-streaming, just yield a final status update
    yield (
        remote_task,
        TaskStatusUpdateEvent(
            status=TaskStatus(state=TaskState.completed),
            contextId="test-context",
            taskId=remote_task_id,
            final=True,
        ),
    )


async def create_failed_response(
    error_message: str, remote_task_id: str = "remote-task-123"
) -> AsyncGenerator[tuple[Mock, Any], None]:
    """Create a mock failed response."""
    remote_task = create_mock_remote_task(remote_task_id)

    # First yield the task submission with None event
    yield remote_task, None

    # Then yield a failed status update
    yield (
        remote_task,
        TaskStatusUpdateEvent(
            status=TaskStatus(state=TaskState.failed, message=error_message),
            contextId="test-context",
            taskId=remote_task_id,
            final=True,
        ),
    )


class TestCoreFlow:
    """Test core orchestrator flow with different agent capabilities."""

    @pytest.mark.asyncio
    async def test_process_user_input_success(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_client: Mock,
        mock_agent_card: AgentCard,
        session_id: str,
        user_id: str,
        sample_query: str,
    ):
        """Test successful user input processing with different agent capabilities."""
        # Setup mock responses based on agent capabilities
        if mock_agent_card.capabilities.streaming:
            mock_response = create_streaming_response(["Hello", " World", "!"])
        else:
            mock_response = create_non_streaming_response("Hello World!")

        mock_agent_client.send_message.return_value = mock_response

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # Verify session messages
        orchestrator.session_manager.add_message.assert_any_call(
            session_id, Role.USER, sample_query
        )

        # Verify task operations
        orchestrator.task_manager.store.save_task.assert_called_once()
        orchestrator.task_manager.start_task.assert_called_once()

        # Verify agent interactions
        orchestrator.agent_connections.start_agent.assert_called_once()
        orchestrator.agent_connections.get_client.assert_called_once_with("TestAgent")

        # Verify send_message call with correct streaming parameter
        expected_streaming = mock_agent_card.capabilities.streaming
        mock_agent_client.send_message.assert_called_once()
        call_args = mock_agent_client.send_message.call_args
        assert call_args.kwargs["streaming"] == expected_streaming

        # Verify chunks based on agent capabilities
        if mock_agent_card.capabilities.streaming:
            # Streaming agents should produce content chunks plus a final empty chunk
            assert len(chunks) >= 1
            for chunk in chunks:
                assert isinstance(chunk, MessageChunk)
                assert chunk.kind == MessageDataKind.TEXT
                assert chunk.meta.session_id == session_id
                assert chunk.meta.user_id == user_id

            # The last chunk should be final and empty (task completion marker)
            final_chunk = chunks[-1]
            assert final_chunk.is_final is True
            assert final_chunk.content == ""
        else:
            # Non-streaming agents should still produce a final completion chunk
            assert len(chunks) >= 1
            final_chunk = chunks[-1]
            assert final_chunk.is_final is True
            assert final_chunk.content == ""

    @pytest.mark.asyncio
    async def test_streaming_agent_chunk_processing(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_client: Mock,
        mock_agent_card: AgentCard,
        session_id: str,
        user_id: str,
    ):
        """Test streaming agent chunk processing specifically."""
        # Skip test for non-streaming agents or push notification agents
        if (
            not mock_agent_card.capabilities.streaming
            or mock_agent_card.capabilities.push_notifications
        ):
            pytest.skip("Test only for streaming agents without push notifications")

        # Setup streaming response
        content_chunks = ["Hello", " from", " streaming", " agent!"]
        mock_agent_client.send_message.return_value = create_streaming_response(
            content_chunks
        )

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # Verify we got chunks (content chunks + final empty chunk)
        assert len(chunks) >= len(content_chunks) + 1

        # Verify chunk content and metadata
        content_received = []
        for chunk in chunks[:-1]:  # Exclude the final empty chunk
            assert isinstance(chunk, MessageChunk)
            assert chunk.kind == MessageDataKind.TEXT
            assert chunk.meta.session_id == session_id
            assert chunk.meta.user_id == user_id
            content_received.append(chunk.content)

        # Verify final chunk is empty and marked as final
        final_chunk = chunks[-1]
        assert final_chunk.is_final is True
        assert final_chunk.content == ""

        # Verify all content was received
        full_content = "".join(content_received)
        assert "Hello from streaming agent!" in full_content

    @pytest.mark.asyncio
    async def test_non_push_notification_agent_processing(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_client: Mock,
        mock_agent_card: AgentCard,
    ):
        """Test that non-push notification agents continue with normal processing."""
        # Skip test for push notification agents
        if mock_agent_card.capabilities.push_notifications:
            pytest.skip("Test only for non-push notification agents")

        # Setup response based on streaming capability
        if mock_agent_card.capabilities.streaming:
            mock_agent_client.send_message.return_value = create_streaming_response(
                ["Processing", " normally"]
            )
        else:
            mock_agent_client.send_message.return_value = create_non_streaming_response(
                "Processing normally"
            )

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # Verify normal processing continues for non-push notification agents
        # All agents should now produce at least one final chunk
        assert len(chunks) >= 1

        # The final chunk should be empty and marked as final
        final_chunk = chunks[-1]
        assert final_chunk.is_final is True
        assert final_chunk.content == ""

        # Task should be completed
        orchestrator.task_manager.complete_task.assert_called_once()

        if mock_agent_card.capabilities.streaming:
            # Streaming agents should produce content chunks + final chunk
            assert len(chunks) >= 2  # At least content chunks + final chunk

    @pytest.mark.asyncio
    async def test_push_notifications_early_return(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_client: Mock,
        mock_agent_card: AgentCard,
    ):
        """Test that push notification agents return early."""
        # Skip test for non-push notification agents
        if not mock_agent_card.capabilities.push_notifications:
            pytest.skip("Test only for push notification agents")

        # Setup response
        mock_agent_client.send_message.return_value = create_streaming_response(
            ["Should not be processed"]
        )

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # For push notification agents, no chunks should be yielded from streaming
        # since they return early and rely on notifications
        # The only chunks should be final session messages

        # Verify agent is started with notification callback
        orchestrator.agent_connections.start_agent.assert_called_once()
        call_args = orchestrator.agent_connections.start_agent.call_args
        assert "notification_callback" in call_args.kwargs


class TestSessionManagement:
    """Test session management functionality."""

    @pytest.mark.asyncio
    async def test_create_session(self, orchestrator: AgentOrchestrator, user_id: str):
        """Test session creation."""
        session_id = await orchestrator.create_session(user_id, "Test Session")

        orchestrator.session_manager.create_session.assert_called_once_with(
            user_id, "Test Session"
        )
        assert session_id == "new-session-id"

    @pytest.mark.asyncio
    async def test_close_session(
        self, orchestrator: AgentOrchestrator, session_id: str
    ):
        """Test session closure with task cancellation."""
        orchestrator.task_manager.cancel_session_tasks.return_value = 2

        await orchestrator.close_session(session_id)

        orchestrator.task_manager.cancel_session_tasks.assert_called_once_with(
            session_id
        )
        orchestrator.session_manager.add_message.assert_called_once()

        # Verify system message was added
        call_args = orchestrator.session_manager.add_message.call_args
        assert call_args[0][1] == Role.SYSTEM  # Role
        assert "2 tasks were cancelled" in call_args[0][2]  # Message content

    @pytest.mark.asyncio
    async def test_get_session_history(
        self, orchestrator: AgentOrchestrator, session_id: str
    ):
        """Test getting session history."""
        await orchestrator.get_session_history(session_id)

        orchestrator.session_manager.get_session_messages.assert_called_once_with(
            session_id
        )

    @pytest.mark.asyncio
    async def test_get_user_sessions(
        self, orchestrator: AgentOrchestrator, user_id: str
    ):
        """Test getting user sessions with pagination."""
        await orchestrator.get_user_sessions(user_id, limit=50, offset=10)

        orchestrator.session_manager.list_user_sessions.assert_called_once_with(
            user_id, 50, 10
        )

    @pytest.mark.asyncio
    async def test_session_message_lifecycle(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_client: Mock,
        session_id: str,
        sample_query: str,
    ):
        """Test that user and agent messages are properly added to session."""
        # Setup mock response
        mock_agent_client.send_message.return_value = create_streaming_response(
            ["Response"]
        )

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # Verify user message was added first
        calls = orchestrator.session_manager.add_message.call_args_list
        assert len(calls) >= 2

        # First call should be user message
        user_call = calls[0]
        assert user_call[0][0] == session_id
        assert user_call[0][1] == Role.USER
        assert user_call[0][2] == sample_query

        # Last call should be agent response
        agent_call = calls[-1]
        assert agent_call[0][0] == session_id
        assert agent_call[0][1] == Role.AGENT


class TestTaskManagement:
    """Test task lifecycle management."""

    @pytest.mark.asyncio
    async def test_task_lifecycle_success(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_client: Mock,
        mock_agent_card: AgentCard,
        sample_task: Task,
    ):
        """Test successful task lifecycle: register -> start -> complete."""
        # Setup response based on agent capabilities
        if mock_agent_card.capabilities.streaming:
            mock_agent_client.send_message.return_value = create_streaming_response(
                ["Done"]
            )
        else:
            mock_agent_client.send_message.return_value = create_non_streaming_response(
                "Done"
            )

        # Execute
        async for _ in orchestrator.process_user_input(sample_user_input):
            pass

        # Verify task lifecycle calls
        orchestrator.task_manager.store.save_task.assert_called_once()
        orchestrator.task_manager.start_task.assert_called_once()
        orchestrator.task_manager.complete_task.assert_called_once()

        # Verify agent connections
        orchestrator.agent_connections.start_agent.assert_called_once()
        start_agent_call = orchestrator.agent_connections.start_agent.call_args
        assert start_agent_call.kwargs["with_listener"] is False
        assert "notification_callback" in start_agent_call.kwargs

    @pytest.mark.asyncio
    async def test_task_failure_handling(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_client: Mock,
    ):
        """Test task failure handling with proper cleanup."""
        # Setup a failed response
        error_message = "Task processing failed"
        mock_agent_client.send_message.return_value = create_failed_response(
            error_message
        )

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # Verify task failure was handled
        orchestrator.task_manager.start_task.assert_called_once()
        orchestrator.task_manager.fail_task.assert_called_once()

        # Verify error message was yielded
        error_chunks = [chunk for chunk in chunks if error_message in chunk.content]
        assert len(error_chunks) >= 1
        assert error_chunks[0].is_final is True

    @pytest.mark.asyncio
    async def test_remote_task_id_tracking(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_client: Mock,
        sample_task: Task,
    ):
        """Test that remote task IDs are properly tracked."""
        remote_task_id = "test-remote-task-456"
        mock_agent_client.send_message.return_value = create_streaming_response(
            ["Content"], remote_task_id
        )

        # Execute
        async for _ in orchestrator.process_user_input(sample_user_input):
            pass

        # Verify remote task ID was tracked
        # Note: In the actual test, we'd need to inspect the task object
        # This is more of an integration test aspect
        orchestrator.task_manager.store.save_task.assert_called_once()
        orchestrator.task_manager.start_task.assert_called_once()
        orchestrator.task_manager.complete_task.assert_called_once()

        # Verify task was started before completion
        start_call = orchestrator.task_manager.start_task.call_args
        complete_call = orchestrator.task_manager.complete_task.call_args
        assert start_call[0][0] == complete_call[0][0]  # Same task_id


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_planner_error(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        session_id: str,
    ):
        """Test error handling when planner fails."""
        # Setup planner to fail
        orchestrator.planner.create_plan.side_effect = ValueError("Planning failed")

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # Verify error handling
        assert len(chunks) == 1
        assert "(Error)" in chunks[0].content
        assert "Planning failed" in chunks[0].content

        # Verify error message added to session
        orchestrator.session_manager.add_message.assert_any_call(
            session_id, Role.SYSTEM, "Error processing request: Planning failed"
        )

    @pytest.mark.asyncio
    async def test_agent_connection_error(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_connections: Mock,
    ):
        """Test error handling when agent connection fails."""
        # Setup agent connections to fail
        mock_agent_connections.get_client.return_value = None

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # Verify error was yielded
        error_chunks = [c for c in chunks if "(Error)" in c.content]
        assert len(error_chunks) >= 1
        assert "Could not connect to agent" in error_chunks[0].content

    @pytest.mark.asyncio
    async def test_empty_execution_plan(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        session_id: str,
        user_id: str,
    ):
        """Test handling of empty execution plan."""
        # Setup empty execution plan
        from valuecell.core.coordinate.models import ExecutionPlan

        empty_plan = ExecutionPlan(
            plan_id="empty-plan",
            session_id=session_id,
            user_id=user_id,
            query=sample_user_input.query,
            tasks=[],
            created_at="2025-09-16T10:00:00",
        )
        orchestrator.planner.create_plan.return_value = empty_plan

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # Verify appropriate message was yielded
        assert len(chunks) >= 1
        assert "No tasks found for this request" in chunks[0].content


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_metadata_propagation(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_client: Mock,
        session_id: str,
        user_id: str,
    ):
        """Test that metadata is properly propagated through the system."""
        mock_agent_client.send_message.return_value = create_streaming_response(
            ["Test"]
        )

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # Verify metadata in all chunks
        for chunk in chunks:
            assert chunk.meta.session_id == session_id
            assert chunk.meta.user_id == user_id

        # Verify metadata passed to agent
        mock_agent_client.send_message.assert_called_once()
        call_args = mock_agent_client.send_message.call_args
        metadata = call_args.kwargs["metadata"]
        assert metadata["session_id"] == session_id
        assert metadata["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_cleanup_resources(self, orchestrator: AgentOrchestrator):
        """Test resource cleanup."""
        await orchestrator.cleanup()

        # Verify agent connections are stopped
        orchestrator.agent_connections.stop_all.assert_called_once()


class TestIntegration:
    """Integration tests that test component interactions."""

    @pytest.mark.asyncio
    async def test_full_flow_integration(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_client: Mock,
        mock_agent_card: AgentCard,
        session_id: str,
        user_id: str,
        sample_query: str,
    ):
        """Test the complete flow from user input to response."""
        # Setup streaming response
        content_chunks = ["Integration", " test", " response"]
        mock_agent_client.send_message.return_value = create_streaming_response(
            content_chunks
        )

        # Execute the full flow
        all_chunks = []
        full_response = ""
        async for chunk in orchestrator.process_user_input(sample_user_input):
            all_chunks.append(chunk)
            full_response += chunk.content

        # Verify the complete flow
        # 1. User message added to session
        orchestrator.session_manager.add_message.assert_any_call(
            session_id, Role.USER, sample_query
        )

        # 2. Plan created
        orchestrator.planner.create_plan.assert_called_once_with(sample_user_input)

        # 3. Task saved and started
        orchestrator.task_manager.store.save_task.assert_called_once()
        orchestrator.task_manager.start_task.assert_called_once()

        # 4. Agent started and message sent
        orchestrator.agent_connections.start_agent.assert_called_once()
        mock_agent_client.send_message.assert_called_once()

        # 5. Task completed
        if not mock_agent_card.capabilities.push_notifications:
            orchestrator.task_manager.complete_task.assert_called_once()

        # 6. Final response added to session
        orchestrator.session_manager.add_message.assert_any_call(
            session_id, Role.AGENT, full_response
        )

        # 7. Verify response content
        if mock_agent_card.capabilities.streaming:
            content_received = "".join(
                [chunk.content for chunk in all_chunks[:-1]]
            )  # Exclude final empty chunk
            assert "Integration test response" in content_received

    @pytest.mark.asyncio
    async def test_task_failed_status_handling(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_client: Mock,
    ):
        """Test handling of TaskState.failed status updates."""
        error_message = "Remote task failed"
        mock_agent_client.send_message.return_value = create_failed_response(
            error_message
        )

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # Verify task was marked as failed
        orchestrator.task_manager.fail_task.assert_called_once()
        fail_call_args = orchestrator.task_manager.fail_task.call_args
        assert (
            error_message in fail_call_args[0][1]
        )  # Error message passed to fail_task

        # Verify error message was yielded to user
        error_chunks = [c for c in chunks if error_message in c.content and c.is_final]
        assert len(error_chunks) >= 1

    @pytest.mark.asyncio
    async def test_agent_start_with_correct_parameters(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_client: Mock,
    ):
        """Test that agent is started with correct parameters."""
        mock_agent_client.send_message.return_value = create_streaming_response(
            ["Test"]
        )

        # Execute
        async for _ in orchestrator.process_user_input(sample_user_input):
            pass

        # Verify agent started with correct parameters
        orchestrator.agent_connections.start_agent.assert_called_once()
        call_args = orchestrator.agent_connections.start_agent.call_args

        # Check the new parameters
        assert call_args.kwargs["with_listener"] is False
        assert "notification_callback" in call_args.kwargs
        assert call_args.kwargs["notification_callback"] is not None

    @pytest.mark.asyncio
    async def test_agent_connection_error(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        mock_agent_connections: Mock,
    ):
        """Test error handling when agent connection fails."""
        # Setup agent connection to fail
        orchestrator.agent_connections.get_client.return_value = None

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # Verify error was handled
        error_chunks = [c for c in chunks if "(Error)" in c.content]
        assert len(error_chunks) >= 1
        assert "Could not connect to agent" in error_chunks[0].content

    @pytest.mark.asyncio
    async def test_empty_execution_plan(
        self,
        orchestrator: AgentOrchestrator,
        sample_user_input: UserInput,
        session_id: str,
        user_id: str,
    ):
        """Test handling of empty execution plan."""
        # Setup empty plan
        empty_plan = ExecutionPlan(
            plan_id="empty-plan",
            session_id=session_id,
            user_id=user_id,
            query=sample_user_input.query,
            tasks=[],
            created_at="2025-09-16T10:00:00",
        )
        orchestrator.planner.create_plan.return_value = empty_plan

        # Execute
        chunks = []
        async for chunk in orchestrator.process_user_input(sample_user_input):
            chunks.append(chunk)

        # Verify appropriate message
        assert len(chunks) == 1
        assert "No tasks found for this request" in chunks[0].content


class TestConcurrency:
    """Test concurrent access scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_agent(
        self,
        orchestrator: AgentOrchestrator,
        mock_agent_client: Mock,
        mock_agent_card: AgentCard,
        session_id: str,
        user_id: str,
    ):
        """Comprehensive test for concurrent process_user_input calls with same agent_name."""
        import asyncio

        # Create two different user inputs but with same agent_name
        user_input_1 = UserInput(
            query="First request to TestAgent",
            desired_agent_name="TestAgent",
            meta=UserInputMetadata(
                session_id=f"{session_id}_1", user_id=f"{user_id}_1"
            ),
        )

        user_input_2 = UserInput(
            query="Second request to TestAgent",
            desired_agent_name="TestAgent",
            meta=UserInputMetadata(
                session_id=f"{session_id}_2", user_id=f"{user_id}_2"
            ),
        )

        # Setup mock responses for both requests
        response_1 = create_streaming_response(
            ["Response from request 1"], "remote-task-1"
        )
        response_2 = create_streaming_response(
            ["Response from request 2"], "remote-task-2"
        )

        # Use side_effect to return different responses for each call
        mock_agent_client.send_message.side_effect = [response_1, response_2]

        # Track agent start calls to verify concurrent handling
        start_agent_call_count = 0
        original_start_agent = orchestrator.agent_connections.start_agent

        async def track_start_agent(*args, **kwargs):
            nonlocal start_agent_call_count
            start_agent_call_count += 1
            # Remove the artificial delay - use asyncio.sleep(0) to yield control
            await asyncio.sleep(0)  # Just yield control, no actual delay
            return await original_start_agent(*args, **kwargs)

        orchestrator.agent_connections.start_agent.side_effect = track_start_agent

        # Execute both requests concurrently
        async def process_request_1():
            chunks_1 = []
            async for chunk in orchestrator.process_user_input(user_input_1):
                chunks_1.append(chunk)
            return chunks_1

        async def process_request_2():
            chunks_2 = []
            async for chunk in orchestrator.process_user_input(user_input_2):
                chunks_2.append(chunk)
            return chunks_2

        # Run both requests concurrently
        results = await asyncio.gather(
            process_request_1(), process_request_2(), return_exceptions=True
        )

        chunks_1, chunks_2 = results

        # Verify both requests completed successfully
        assert not isinstance(chunks_1, Exception), f"Request 1 failed: {chunks_1}"
        assert not isinstance(chunks_2, Exception), f"Request 2 failed: {chunks_2}"
        assert len(chunks_1) > 0, "Request 1 should have produced chunks"
        assert len(chunks_2) > 0, "Request 2 should have produced chunks"

        # Verify agent was started (possibly multiple times due to concurrent access)
        # The exact number depends on the locking mechanism in RemoteConnections
        assert start_agent_call_count >= 1, "Agent should be started at least once"

        # Verify both requests got different session contexts
        session_1_chunks = [
            c for c in chunks_1 if c.meta.session_id == f"{session_id}_1"
        ]
        session_2_chunks = [
            c for c in chunks_2 if c.meta.session_id == f"{session_id}_2"
        ]

        assert len(session_1_chunks) > 0, (
            "Request 1 should have chunks with correct session_id"
        )
        assert len(session_2_chunks) > 0, (
            "Request 2 should have chunks with correct session_id"
        )

        # Verify both requests called the task manager
        assert orchestrator.task_manager.store.save_task.call_count >= 2
        assert orchestrator.task_manager.start_task.call_count >= 2

        # Verify session messages were added for both sessions
        session_add_calls = orchestrator.session_manager.add_message.call_args_list
        session_1_calls = [
            call for call in session_add_calls if call[0][0] == f"{session_id}_1"
        ]
        session_2_calls = [
            call for call in session_add_calls if call[0][0] == f"{session_id}_2"
        ]

        assert len(session_1_calls) >= 2, (
            "Session 1 should have user and agent messages"
        )
        assert len(session_2_calls) >= 2, (
            "Session 2 should have user and agent messages"
        )

    @pytest.mark.asyncio
    async def test_concurrent_requests_different_agents(
        self,
        orchestrator: AgentOrchestrator,
        mock_agent_client: Mock,
        session_id: str,
        user_id: str,
    ):
        """Test concurrent requests to different agents work independently."""
        import asyncio

        # Create user inputs for different agents
        user_input_agent_1 = UserInput(
            query="Request to Agent1",
            desired_agent_name="Agent1",
            meta=UserInputMetadata(
                session_id=f"{session_id}_a1", user_id=f"{user_id}_a1"
            ),
        )

        user_input_agent_2 = UserInput(
            query="Request to Agent2",
            desired_agent_name="Agent2",
            meta=UserInputMetadata(
                session_id=f"{session_id}_a2", user_id=f"{user_id}_a2"
            ),
        )

        # Setup different execution plans for different agents
        from valuecell.core.task import Task, TaskStatus as CoreTaskStatus

        task_1 = Task(
            task_id="task-agent1",
            session_id=f"{session_id}_a1",
            user_id=f"{user_id}_a1",
            agent_name="Agent1",
            status=CoreTaskStatus.PENDING,
            remote_task_ids=[],
        )

        task_2 = Task(
            task_id="task-agent2",
            session_id=f"{session_id}_a2",
            user_id=f"{user_id}_a2",
            agent_name="Agent2",
            status=CoreTaskStatus.PENDING,
            remote_task_ids=[],
        )

        plan_1 = ExecutionPlan(
            plan_id="plan-agent1",
            session_id=f"{session_id}_a1",
            user_id=f"{user_id}_a1",
            query="Request to Agent1",
            tasks=[task_1],
            created_at="2025-09-16T10:00:00",
        )

        plan_2 = ExecutionPlan(
            plan_id="plan-agent2",
            session_id=f"{session_id}_a2",
            user_id=f"{user_id}_a2",
            query="Request to Agent2",
            tasks=[task_2],
            created_at="2025-09-16T10:00:00",
        )

        # Setup planner to return different plans
        orchestrator.planner.create_plan.side_effect = [plan_1, plan_2]

        # Setup agent responses
        response_1 = create_streaming_response(["Agent1 response"], "remote-task-a1")
        response_2 = create_streaming_response(["Agent2 response"], "remote-task-a2")
        mock_agent_client.send_message.side_effect = [response_1, response_2]

        # Execute both requests concurrently
        async def process_agent_1():
            chunks = []
            async for chunk in orchestrator.process_user_input(user_input_agent_1):
                chunks.append(chunk)
            return chunks

        async def process_agent_2():
            chunks = []
            async for chunk in orchestrator.process_user_input(user_input_agent_2):
                chunks.append(chunk)
            return chunks

        results = await asyncio.gather(
            process_agent_1(), process_agent_2(), return_exceptions=True
        )

        chunks_1, chunks_2 = results

        # Verify both requests completed successfully
        assert not isinstance(chunks_1, Exception), f"Agent1 request failed: {chunks_1}"
        assert not isinstance(chunks_2, Exception), f"Agent2 request failed: {chunks_2}"
        assert len(chunks_1) > 0, "Agent1 request should produce chunks"
        assert len(chunks_2) > 0, "Agent2 request should produce chunks"

        # Verify different agents were started
        assert orchestrator.agent_connections.start_agent.call_count == 2
        start_calls = orchestrator.agent_connections.start_agent.call_args_list
        agent_names = [call[0][0] for call in start_calls]
        assert "Agent1" in agent_names
        assert "Agent2" in agent_names

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_session(
        self,
        orchestrator: AgentOrchestrator,
        mock_agent_client: Mock,
        session_id: str,
        user_id: str,
    ):
        """Test concurrent requests in the same session."""
        import asyncio

        # Create two requests for the same session but different queries
        user_input_1 = UserInput(
            query="First query in session",
            desired_agent_name="TestAgent",
            meta=UserInputMetadata(session_id=session_id, user_id=user_id),
        )

        user_input_2 = UserInput(
            query="Second query in session",
            desired_agent_name="TestAgent",
            meta=UserInputMetadata(session_id=session_id, user_id=user_id),
        )

        # Setup responses
        response_1 = create_streaming_response(["First response"], "remote-task-1")
        response_2 = create_streaming_response(["Second response"], "remote-task-2")
        mock_agent_client.send_message.side_effect = [response_1, response_2]

        # Execute concurrently
        async def process_1():
            chunks = []
            async for chunk in orchestrator.process_user_input(user_input_1):
                chunks.append(chunk)
            return chunks

        async def process_2():
            chunks = []
            async for chunk in orchestrator.process_user_input(user_input_2):
                chunks.append(chunk)
            return chunks

        results = await asyncio.gather(process_1(), process_2(), return_exceptions=True)

        chunks_1, chunks_2 = results

        # Verify both completed successfully
        assert not isinstance(chunks_1, Exception)
        assert not isinstance(chunks_2, Exception)
        assert len(chunks_1) > 0
        assert len(chunks_2) > 0

        # Verify session messages were added for both queries
        session_calls = orchestrator.session_manager.add_message.call_args_list
        user_calls = [call for call in session_calls if call[0][1] == Role.USER]
        assert len(user_calls) >= 2, "Both user queries should be added to session"
