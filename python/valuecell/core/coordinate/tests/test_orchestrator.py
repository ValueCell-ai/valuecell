"""
Lean pytest tests for AgentOrchestrator.

Focus on essential behavior without over-engineering:
- Happy path (streaming and non-streaming)
- Planner error and agent connection error
- Conversation create/close and cleanup
"""

from types import SimpleNamespace
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, Mock

import pytest
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Artifact,
    Part,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)

from valuecell.core.coordinate.models import ExecutionPlan
from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.core.conversation import ConversationStatus
from valuecell.core.task import Task, TaskStatus as CoreTaskStatus
from valuecell.core.types import UserInput, UserInputMetadata


# -------------------------
# Fixtures
# -------------------------


@pytest.fixture(name="conversation_id")
def _conversation_id() -> str:
    return "test-conversation-123"


@pytest.fixture(name="user_id")
def _user_id() -> str:
    return "test-user-456"


@pytest.fixture(name="sample_query")
def _sample_query() -> str:
    return "What is the latest stock price for AAPL?"


@pytest.fixture(name="sample_user_input")
def _sample_user_input(
    conversation_id: str, user_id: str, sample_query: str
) -> UserInput:
    return UserInput(
        query=sample_query,
        target_agent_name="TestAgent",
        meta=UserInputMetadata(conversation_id=conversation_id, user_id=user_id),
    )


@pytest.fixture(name="sample_task")
def _sample_task(conversation_id: str, user_id: str, sample_query: str) -> Task:
    return Task(
        task_id="task-1",
        conversation_id=conversation_id,
        user_id=user_id,
        agent_name="TestAgent",
        query=sample_query,
        status=CoreTaskStatus.PENDING,
        remote_task_ids=[],
    )


@pytest.fixture(name="sample_plan")
def _sample_plan(
    conversation_id: str, user_id: str, sample_query: str, sample_task: Task
) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan-1",
        conversation_id=conversation_id,
        user_id=user_id,
        orig_query=sample_query,
        tasks=[sample_task],
        created_at="2025-09-16T10:00:00",
    )


def _stub_conversation(status: Any = ConversationStatus.ACTIVE):
    # Minimal conversation stub with status and basic methods used by orchestrator
    s = SimpleNamespace(status=status)

    def activate():
        s.status = ConversationStatus.ACTIVE

    def require_user_input():
        s.status = ConversationStatus.REQUIRE_USER_INPUT

    s.activate = activate
    s.require_user_input = require_user_input
    return s


@pytest.fixture(name="mock_conversation_manager")
def _mock_conversation_manager() -> Mock:
    m = Mock()
    m.add_item = AsyncMock()
    m.create_conversation = AsyncMock(return_value="new-conversation-id")
    m.get_conversation_items = AsyncMock(return_value=[])
    m.list_user_conversations = AsyncMock(return_value=[])
    m.get_conversation = AsyncMock(return_value=_stub_conversation())
    m.update_conversation = AsyncMock()
    return m


@pytest.fixture(name="mock_task_manager")
def _mock_task_manager() -> Mock:
    m = Mock()
    m.update_task = AsyncMock()
    m.start_task = AsyncMock()
    m.complete_task = AsyncMock()
    m.fail_task = AsyncMock()
    m.cancel_conversation_tasks = AsyncMock(return_value=0)
    return m


@pytest.fixture(name="mock_agent_card_streaming")
def _mock_agent_card_streaming() -> AgentCard:
    return AgentCard(
        name="TestAgent",
        description="",
        url="http://localhost",
        version="1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        skills=[AgentSkill(id="s1", name="n", description="d", tags=[])],
        supports_authenticated_extended_card=False,
    )


@pytest.fixture(name="mock_agent_card_non_streaming")
def _mock_agent_card_non_streaming() -> AgentCard:
    return AgentCard(
        name="TestAgent",
        description="",
        url="http://localhost",
        version="1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        skills=[AgentSkill(id="s1", name="n", description="d", tags=[])],
        supports_authenticated_extended_card=False,
    )


@pytest.fixture(name="mock_agent_client")
def _mock_agent_client() -> Mock:
    c = Mock()
    c.send_message = AsyncMock()
    return c


@pytest.fixture(name="mock_planner")
def _mock_planner(sample_plan: ExecutionPlan) -> Mock:
    p = Mock()
    p.create_plan = AsyncMock(return_value=sample_plan)
    return p


@pytest.fixture(name="orchestrator")
def _orchestrator(
    mock_conversation_manager: Mock, mock_task_manager: Mock, mock_planner: Mock
) -> AgentOrchestrator:
    o = AgentOrchestrator()
    o.conversation_manager = mock_conversation_manager
    o.task_manager = mock_task_manager
    o.planner = mock_planner
    return o


# -------------------------
# Helpers
# -------------------------


def _make_streaming_response(
    chunks: list[str], remote_task_id: str = "rt-1"
) -> AsyncGenerator[tuple[Mock, Any], None]:
    async def gen():
        rt = Mock()
        rt.id = remote_task_id
        rt.status = Mock(state=TaskState.submitted)
        # First yield submission with None event
        yield rt, None
        for i, text in enumerate(chunks):
            part = Part(root=TextPart(text=text))
            artifact = Artifact(artifactId=f"a-{i}", parts=[part])
            yield (
                rt,
                TaskArtifactUpdateEvent(
                    artifact=artifact,
                    contextId="ctx",
                    taskId=remote_task_id,
                    final=False,
                ),
            )

    return gen()


def _make_non_streaming_response(
    remote_task_id: str = "rt-1",
) -> AsyncGenerator[tuple[Mock, Any], None]:
    async def gen():
        rt = Mock()
        rt.id = remote_task_id
        rt.status = Mock(state=TaskState.submitted)
        yield rt, None
        yield (
            rt,
            TaskStatusUpdateEvent(
                status=TaskStatus(state=TaskState.completed),
                contextId="ctx",
                taskId=remote_task_id,
                final=True,
            ),
        )

    return gen()


# -------------------------
# Tests
# -------------------------


@pytest.mark.asyncio
async def test_happy_path_streaming(
    orchestrator: AgentOrchestrator,
    mock_agent_client: Mock,
    mock_agent_card_streaming: AgentCard,
    sample_user_input: UserInput,
):
    # Inject agent connections mock
    ac = Mock()
    ac.start_agent = AsyncMock(return_value=mock_agent_card_streaming)
    ac.get_client = AsyncMock(return_value=mock_agent_client)
    ac.stop_all = AsyncMock()
    orchestrator.agent_connections = ac

    mock_agent_client.send_message.return_value = _make_streaming_response(
        ["Hello", " World"]
    )

    # Execute
    out = []
    async for chunk in orchestrator.process_user_input(sample_user_input):
        out.append(chunk)

    # Minimal assertions
    orchestrator.task_manager.update_task.assert_called_once()
    orchestrator.task_manager.start_task.assert_called_once()
    ac.start_agent.assert_called_once()
    ac.get_client.assert_called_once_with("TestAgent")
    mock_agent_client.send_message.assert_called_once()
    # Should at least yield something (content or final)
    assert len(out) >= 1


@pytest.mark.asyncio
async def test_happy_path_non_streaming(
    orchestrator: AgentOrchestrator,
    mock_agent_client: Mock,
    mock_agent_card_non_streaming: AgentCard,
    sample_user_input: UserInput,
):
    ac = Mock()
    ac.start_agent = AsyncMock(return_value=mock_agent_card_non_streaming)
    ac.get_client = AsyncMock(return_value=mock_agent_client)
    ac.stop_all = AsyncMock()
    orchestrator.agent_connections = ac

    mock_agent_client.send_message.return_value = _make_non_streaming_response()

    out = []
    async for chunk in orchestrator.process_user_input(sample_user_input):
        out.append(chunk)

    orchestrator.task_manager.start_task.assert_called_once()
    orchestrator.task_manager.complete_task.assert_called_once()
    assert len(out) >= 1


@pytest.mark.asyncio
async def test_planner_error(
    orchestrator: AgentOrchestrator, sample_user_input: UserInput
):
    orchestrator.planner.create_plan.side_effect = RuntimeError("Planning failed")

    # Need agent connections to exist but won't be used
    orchestrator.agent_connections = Mock()

    out = []
    async for chunk in orchestrator.process_user_input(sample_user_input):
        out.append(chunk)

    assert len(out) == 3
    assert "(Error)" in out[1].data.payload.content
    assert "Planning failed" in out[1].data.payload.content


@pytest.mark.asyncio
async def test_agent_connection_error(
    orchestrator: AgentOrchestrator,
    sample_user_input: UserInput,
    mock_agent_card_streaming: AgentCard,
):
    ac = Mock()
    ac.start_agent = AsyncMock(return_value=mock_agent_card_streaming)
    ac.get_client = AsyncMock(return_value=None)  # Simulate connection failure
    orchestrator.agent_connections = ac

    out = []
    async for chunk in orchestrator.process_user_input(sample_user_input):
        out.append(chunk)

    assert any("(Error)" in c.data.payload.content for c in out if c.data.payload)


@pytest.mark.asyncio
async def test_continue_planning_metadata_retrieval(
    orchestrator: AgentOrchestrator, conversation_id: str, sample_user_input: UserInput
):
    """Test that _continue_planning correctly retrieves metadata from context."""
    from valuecell.core.coordinate.orchestrator import ExecutionContext
    from valuecell.core.constants import PLANNING_TASK, ORIGINAL_USER_INPUT

    # Create a real asyncio.Task-like object that can be awaited
    import asyncio

    async def mock_plan_coroutine():
        return Mock()  # Mock ExecutionPlan

    # Create actual task from coroutine, but mark it as done with a result
    mock_planning_task = asyncio.create_task(mock_plan_coroutine())
    # Wait a bit to let it complete
    await asyncio.sleep(0.01)

    # Create execution context with required metadata
    context = ExecutionContext("planning", conversation_id, "thread-1", "user-1")
    context.add_metadata(
        **{PLANNING_TASK: mock_planning_task, ORIGINAL_USER_INPUT: sample_user_input}
    )

    # Set up execution context in orchestrator
    orchestrator._execution_contexts[conversation_id] = context

    # Mock dependencies
    orchestrator._response_factory.plan_failed = Mock()

    async def mock_execute_plan(*args):
        yield Mock()

    # Mock the async generator method directly
    orchestrator._execute_plan_with_input_support = Mock(
        return_value=mock_execute_plan()
    )

    # Call the method to trigger metadata retrieval (lines 507-508)
    results = []
    async for response in orchestrator._continue_planning(
        conversation_id, "thread-1", context
    ):
        results.append(response)

    # Verify that the method executed successfully
    # The fact that we got here without errors means metadata was retrieved correctly
    assert (
        conversation_id not in orchestrator._execution_contexts
    )  # Context should be cleaned up
    assert mock_planning_task.done()  # Task should be completed
    assert len(results) >= 1  # Should have yielded at least one response


@pytest.mark.asyncio
async def test_cancel_execution_with_planning_task(
    orchestrator: AgentOrchestrator, conversation_id: str
):
    """Test that _cancel_execution correctly retrieves planning_task metadata."""
    from valuecell.core.coordinate.orchestrator import ExecutionContext
    from valuecell.core.constants import PLANNING_TASK

    # Create mock planning task
    mock_planning_task = Mock()
    mock_planning_task.done.return_value = False
    mock_planning_task.cancel = Mock()

    # Create execution context with planning task
    context = ExecutionContext("planning", conversation_id, "thread-1", "user-1")
    context.add_metadata(**{PLANNING_TASK: mock_planning_task})

    # Set up execution context in orchestrator
    orchestrator._execution_contexts[conversation_id] = context

    # Mock user input manager
    orchestrator.user_input_manager.clear_request = Mock()

    # Mock conversation manager
    mock_conversation = _stub_conversation()
    orchestrator.conversation_manager.get_conversation.return_value = mock_conversation
    orchestrator.conversation_manager.update_conversation = AsyncMock()

    # Call _cancel_execution to trigger
    await orchestrator._cancel_execution(conversation_id)

    # Verify planning task was retrieved and cancelled
    mock_planning_task.cancel.assert_called_once()

    # Verify context cleanup
    assert conversation_id not in orchestrator._execution_contexts
    orchestrator.user_input_manager.clear_request.assert_called_once_with(
        conversation_id
    )
