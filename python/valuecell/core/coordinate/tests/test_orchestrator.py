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

from valuecell.core.agent.connect import RemoteConnections
from valuecell.core.conversation import ConversationStatus
from valuecell.core.conversation.service import ConversationService
from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.core.event.service import EventResponseService
from valuecell.core.plan.models import ExecutionPlan
from valuecell.core.plan.service import PlanService
from valuecell.core.super_agent import (
    SuperAgentDecision,
    SuperAgentOutcome,
    SuperAgentService,
)
from valuecell.core.task import TaskStatus as CoreTaskStatus
from valuecell.core.task.executor import TaskExecutor
from valuecell.core.task.models import Task
from valuecell.core.task.service import TaskService
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
    mock_conversation_manager: Mock,
    mock_task_manager: Mock,
    mock_planner: Mock,
    monkeypatch: pytest.MonkeyPatch,
) -> AgentOrchestrator:
    # Mock create_model at factory level to avoid API key validation in CI
    import valuecell.adapters.models.factory as factory_mod

    monkeypatch.setattr(
        factory_mod, "create_model", lambda *args, **kwargs: "stub-model"
    )
    monkeypatch.setattr(
        factory_mod, "create_embedder", lambda *args, **kwargs: "stub-embedder"
    )

    agent_connections = Mock(spec=RemoteConnections)
    agent_connections.get_client = AsyncMock()
    agent_connections.start_agent = AsyncMock()

    conversation_service = ConversationService(manager=mock_conversation_manager)
    event_service = EventResponseService(conversation_service=conversation_service)
    task_service = TaskService(manager=mock_task_manager)
    plan_service = PlanService(
        agent_connections=agent_connections, execution_planner=mock_planner
    )

    # Create mock SuperAgent to avoid real model initialization
    mock_super_agent = Mock()
    mock_super_agent.name = "ValueCellAgent"
    mock_super_agent.run = AsyncMock()
    super_agent_service = SuperAgentService(super_agent=mock_super_agent)

    task_executor = TaskExecutor(
        agent_connections=agent_connections,
        task_service=task_service,
        event_service=event_service,
        conversation_service=conversation_service,
    )

    bundle = SimpleNamespace(
        agent_connections=agent_connections,
        conversation_service=conversation_service,
        event_service=event_service,
        task_service=task_service,
        plan_service=plan_service,
        super_agent_service=super_agent_service,
        task_executor=task_executor,
    )

    monkeypatch.setattr(
        "valuecell.core.coordinate.orchestrator.AgentServiceBundle.compose",
        Mock(return_value=bundle),
    )

    orchestrator = AgentOrchestrator()
    orchestrator._testing_bundle = bundle  # type: ignore[attr-defined]
    return orchestrator


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
    mock_task_manager: Mock,
):
    bundle = orchestrator._testing_bundle  # type: ignore[attr-defined]
    bundle.agent_connections.start_agent.return_value = mock_agent_card_streaming
    bundle.agent_connections.get_client.return_value = mock_agent_client
    bundle.agent_connections.stop_all = AsyncMock()

    mock_agent_client.send_message.return_value = _make_streaming_response(
        ["Hello", " World"]
    )

    # Execute
    out = []
    async for chunk in orchestrator.process_user_input(sample_user_input):
        out.append(chunk)

    # Minimal assertions
    mock_task_manager.update_task.assert_called_once()
    mock_task_manager.start_task.assert_called_once()
    bundle.agent_connections.get_client.assert_awaited_once_with("TestAgent")
    mock_agent_client.send_message.assert_called_once()
    # Should at least yield something (content or final)
    assert len(out) >= 1


@pytest.mark.asyncio
async def test_happy_path_non_streaming(
    orchestrator: AgentOrchestrator,
    mock_agent_client: Mock,
    mock_agent_card_non_streaming: AgentCard,
    sample_user_input: UserInput,
    mock_task_manager: Mock,
):
    bundle = orchestrator._testing_bundle  # type: ignore[attr-defined]
    bundle.agent_connections.start_agent.return_value = mock_agent_card_non_streaming
    bundle.agent_connections.get_client.return_value = mock_agent_client
    bundle.agent_connections.stop_all = AsyncMock()

    mock_agent_client.send_message.return_value = _make_non_streaming_response()

    out = []
    async for chunk in orchestrator.process_user_input(sample_user_input):
        out.append(chunk)

    mock_task_manager.start_task.assert_called_once()
    mock_task_manager.complete_task.assert_called_once()
    bundle.agent_connections.get_client.assert_awaited_once_with("TestAgent")
    assert len(out) >= 1


@pytest.mark.asyncio
async def test_planner_error(
    orchestrator: AgentOrchestrator, sample_user_input: UserInput
):
    orchestrator.plan_service.planner.create_plan.side_effect = RuntimeError(
        "Planning failed"
    )

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
    bundle = orchestrator._testing_bundle  # type: ignore[attr-defined]
    bundle.agent_connections.start_agent.return_value = mock_agent_card_streaming
    bundle.agent_connections.get_client.return_value = (
        None  # Simulate connection failure
    )

    out = []
    async for chunk in orchestrator.process_user_input(sample_user_input):
        out.append(chunk)

    assert any("(Error)" in c.data.payload.content for c in out if c.data.payload)


@pytest.mark.asyncio
async def test_super_agent_answer_short_circuits_planner(
    orchestrator: AgentOrchestrator,
):
    outcome = SuperAgentOutcome(
        decision=SuperAgentDecision.ANSWER,
        answer_content="Concise reply",
        enriched_query=None,
        reason="Handled directly",
    )
    orchestrator.super_agent_service = SimpleNamespace(
        name="ValueCellAgent",
        run=AsyncMock(return_value=outcome),
    )

    user_input = UserInput(
        query="What is 2+2?",
        target_agent_name=orchestrator.super_agent_service.name,
        meta=UserInputMetadata(conversation_id="conv-answer", user_id="user-answer"),
    )

    responses = []
    async for resp in orchestrator.process_user_input(user_input):
        responses.append(resp)

    orchestrator.plan_service.planner.create_plan.assert_not_called()
    payload_contents = [
        getattr(resp.data.payload, "content", "")
        for resp in responses
        if getattr(resp, "data", None) and getattr(resp.data, "payload", None)
    ]
    assert any("Concise reply" in content for content in payload_contents)
