from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from a2a.types import TaskState, TaskStatusUpdateEvent
from a2a.utils import get_message_text
from loguru import logger

from valuecell.core.agent.responses import EventPredicates
from valuecell.core.event.factory import ResponseFactory
from valuecell.core.task.models import Task
from valuecell.core.types import (
    BaseResponse,
    CommonResponseEvent,
)


class SideEffectKind(Enum):
    """Kinds of side-effects that routing logic can request.

    Side effects are actions that the orchestrator should take in response to
    routed events (for example, failing a task when the agent reports an
    unrecoverable error).
    """

    FAIL_TASK = "fail_task"


@dataclass
class SideEffect:
    """Represents a side-effect produced by event routing.

    Attributes:
        kind: The kind of side effect to apply (see SideEffectKind).
        reason: Optional human-readable reason for the side-effect.
    """

    kind: SideEffectKind
    reason: Optional[str] = None


@dataclass
class RouteResult:
    """Result of routing a single incoming event.

    Contains zero or more `BaseResponse` objects to emit to the orchestrator,
    a `done` flag that signals task-level completion (stop processing), and an
    optional list of `SideEffect` objects describing actions the orchestrator
    should apply (for example, failing a task).
    """

    responses: List[BaseResponse]
    done: bool = False
    side_effects: List[SideEffect] = None

    def __post_init__(self):
        if self.side_effects is None:
            self.side_effects = []


async def handle_status_update(
    response_factory: ResponseFactory,
    task: Task,
    thread_id: str,
    event: TaskStatusUpdateEvent,
) -> RouteResult:
    responses: List[BaseResponse] = []
    state = event.status.state
    logger.info(f"Task {task.task_id} status update: {state}")

    # No messaging for submitted/completed states by default
    if state in {TaskState.submitted, TaskState.completed}:
        return RouteResult(responses)

    if state == TaskState.failed:
        # Produce a task_failed response and request the task be marked failed
        err_msg = get_message_text(event.status.message)
        responses.append(
            response_factory.task_failed(
                conversation_id=task.conversation_id,
                thread_id=thread_id,
                task_id=task.task_id,
                content=err_msg,
                agent_name=task.agent_name,
            )
        )
        return RouteResult(
            responses=responses,
            done=True,
            side_effects=[SideEffect(kind=SideEffectKind.FAIL_TASK, reason=err_msg)],
        )

    if not event.metadata:
        return RouteResult(responses)

    response_event = event.metadata.get("response_event")

    # Tool call events
    if state == TaskState.working and EventPredicates.is_tool_call(response_event):
        tool_call_id = event.metadata.get("tool_call_id", "unknown_tool_call_id")
        tool_name = event.metadata.get("tool_name", "unknown_tool_name")

        tool_result = None
        if "tool_result" in event.metadata and event.metadata["tool_result"]:
            tool_result = event.metadata.get("tool_result")
        responses.append(
            response_factory.tool_call(
                conversation_id=task.conversation_id,
                thread_id=thread_id,
                task_id=task.task_id,
                event=response_event,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_result=tool_result,
                agent_name=task.agent_name,
            )
        )
        return RouteResult(responses)

    # Reasoning messages
    content = get_message_text(event.status.message, "")
    if state == TaskState.working and EventPredicates.is_reasoning(response_event):
        responses.append(
            response_factory.reasoning(
                conversation_id=task.conversation_id,
                thread_id=thread_id,
                task_id=task.task_id,
                event=response_event,
                content=content,
                agent_name=task.agent_name,
            )
        )
        return RouteResult(responses)

    # component generator
    if (
        state == TaskState.working
        and response_event == CommonResponseEvent.COMPONENT_GENERATOR
    ):
        component_type = event.metadata.get("component_type", "unknown")
        component_id = event.metadata.get("component_id")
        responses.append(
            response_factory.component_generator(
                conversation_id=task.conversation_id,
                thread_id=thread_id,
                task_id=task.task_id,
                content=content,
                component_type=component_type,
                component_id=component_id,
                agent_name=task.agent_name,
            )
        )
        return RouteResult(responses)

    # general messages
    if state == TaskState.working and EventPredicates.is_message(response_event):
        responses.append(
            response_factory.message_response_general(
                event=response_event,
                conversation_id=task.conversation_id,
                thread_id=thread_id,
                task_id=task.task_id,
                content=content,
                agent_name=task.agent_name,
            )
        )
        return RouteResult(responses)

    return RouteResult(responses)
