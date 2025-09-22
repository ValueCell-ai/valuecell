"""
Lean pytest tests for AgentOrchestrator.

Focus on essential behavior without over-engineering:
- Happy path (streaming and non-streaming)
- Planner error and agent connection error
- Session create/close and cleanup
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
from valuecell.core.session import SessionStatus
from valuecell.core.task import Task, TaskStatus as CoreTaskStatus
from valuecell.core.types import UserInput, UserInputMetadata


# -------------------------
# Fixtures
# -------------------------


@pytest.fixture
def session_id() -> str:
    return "test-session-123"


@pytest.fixture
def user_id() -> str:
    return "test-user-456"


@pytest.fixture
def sample_query() -> str:
    return "What is the latest stock price for AAPL?"


@pytest.fixture
def sample_user_input(session_id: str, user_id: str, sample_query: str) -> UserInput:
    return UserInput(
        query=sample_query,
        desired_agent_name="TestAgent",
        meta=UserInputMetadata(session_id=session_id, user_id=user_id),
    )


@pytest.fixture
def sample_task(session_id: str, user_id: str, sample_query: str) -> Task:
    return Task(
        task_id="task-1",
        session_id=session_id,
        user_id=user_id,
        agent_name="TestAgent",
        query=sample_query,
        status=CoreTaskStatus.PENDING,
        remote_task_ids=[],
    )


@pytest.fixture
def sample_plan(
    session_id: str, user_id: str, sample_query: str, sample_task: Task
) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan-1",
        session_id=session_id,
        user_id=user_id,
        orig_query=sample_query,
        tasks=[sample_task],
        created_at="2025-09-16T10:00:00",
    )


def _stub_session(status: Any = SessionStatus.ACTIVE):
    # Minimal session stub with status and basic methods used by orchestrator
    s = SimpleNamespace(status=status)

    def activate():
        s.status = SessionStatus.ACTIVE

    def require_user_input():
        s.status = SessionStatus.REQUIRE_USER_INPUT

    s.activate = activate
    s.require_user_input = require_user_input
    return s


@pytest.fixture
def mock_session_manager() -> Mock:
    m = Mock()
    m.add_message = AsyncMock()
    m.create_session = AsyncMock(return_value="new-session-id")
    m.get_session_messages = AsyncMock(return_value=[])
    m.list_user_sessions = AsyncMock(return_value=[])
    m.get_session = AsyncMock(return_value=_stub_session())
    m.update_session = AsyncMock()
    return m


@pytest.fixture
def mock_task_manager() -> Mock:
    m = Mock()
    m.store = Mock()
    m.store.save_task = AsyncMock()
    m.start_task = AsyncMock()
    m.complete_task = AsyncMock()
    m.fail_task = AsyncMock()
    m.cancel_session_tasks = AsyncMock(return_value=0)
    return m


@pytest.fixture
def mock_agent_card_streaming() -> AgentCard:
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


@pytest.fixture
def mock_agent_card_non_streaming() -> AgentCard:
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


@pytest.fixture
def mock_agent_client() -> Mock:
    c = Mock()
    c.send_message = AsyncMock()
    return c


@pytest.fixture
def mock_planner(sample_plan: ExecutionPlan) -> Mock:
    p = Mock()
    p.create_plan = AsyncMock(return_value=sample_plan)
    return p


@pytest.fixture
def orchestrator(
    mock_session_manager: Mock, mock_task_manager: Mock, mock_planner: Mock
) -> AgentOrchestrator:
    o = AgentOrchestrator()
    o.session_manager = mock_session_manager
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
    orchestrator.task_manager.store.save_task.assert_called_once()
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

    assert len(out) == 1
    assert "(Error)" in out[0].data.content
    assert "Planning failed" in out[0].data.content


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

    assert any("(Error)" in c.data.content for c in out)


@pytest.mark.asyncio
async def test_create_and_close_session(
    orchestrator: AgentOrchestrator, user_id: str, session_id: str
):
    # create
    new_id = await orchestrator.create_session(user_id, "Title")
    orchestrator.session_manager.create_session.assert_called_once_with(
        user_id, "Title"
    )
    assert new_id == "new-session-id"

    # close
    orchestrator.task_manager.cancel_session_tasks.return_value = 1
    await orchestrator.close_session(session_id)
    orchestrator.task_manager.cancel_session_tasks.assert_called_once_with(session_id)
    orchestrator.session_manager.add_message.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup(orchestrator: AgentOrchestrator):
    orchestrator.agent_connections = Mock()
    orchestrator.agent_connections.stop_all = AsyncMock()
    await orchestrator.cleanup()
    orchestrator.agent_connections.stop_all.assert_called_once()
