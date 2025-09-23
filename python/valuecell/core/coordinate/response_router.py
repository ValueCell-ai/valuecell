import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from a2a.types import TaskArtifactUpdateEvent, TaskState, TaskStatusUpdateEvent
from a2a.utils import get_message_text
from valuecell.core.agent.responses import EventPredicates
from valuecell.core.coordinate.response import ResponseFactory
from valuecell.core.task import Task
from valuecell.core.types import BaseResponse, StreamResponseEvent

logger = logging.getLogger(__name__)


class SideEffectKind(Enum):
    FAIL_TASK = "fail_task"


@dataclass
class SideEffect:
    kind: SideEffectKind
    reason: Optional[str] = None


@dataclass
class RouteResult:
    responses: List[BaseResponse]
    done: bool = False
    side_effects: List[SideEffect] = None

    def __post_init__(self):
        if self.side_effects is None:
            self.side_effects = []


def _default_subtask_id(task_id: str) -> str:
    return f"{task_id}_default-subtask"


async def handle_status_update(
    response_factory: ResponseFactory,
    task: Task,
    thread_id: str,
    event: TaskStatusUpdateEvent,
) -> RouteResult:
    responses: List[BaseResponse] = []
    state = event.status.state
    logger.info(f"Task {task.task_id} status update: {state}")

    if state in {TaskState.submitted, TaskState.completed}:
        return RouteResult(responses)

    if state == TaskState.failed:
        err_msg = get_message_text(event.status.message)
        responses.append(
            response_factory.task_failed(
                conversation_id=task.session_id,
                thread_id=thread_id,
                task_id=task.task_id,
                subtask_id=_default_subtask_id(task.task_id),
                content=err_msg,
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
    subtask_id = event.metadata.get("subtask_id")
    if not subtask_id:
        subtask_id = _default_subtask_id(task.task_id)

    # Tool call events
    if state == TaskState.working and EventPredicates.is_tool_call(response_event):
        tool_call_id = event.metadata.get("tool_call_id", "unknown_tool_call_id")
        tool_name = event.metadata.get("tool_name", "unknown_tool_name")

        tool_result = None
        if "tool_result" in event.metadata:
            tool_result = get_message_text(event.metadata.get("tool_result", ""))
        responses.append(
            response_factory.tool_call(
                conversation_id=task.session_id,
                thread_id=thread_id,
                task_id=task.task_id,
                subtask_id=subtask_id,
                event=response_event,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_result=tool_result,
            )
        )
        return RouteResult(responses)

    # Reasoning messages
    if state == TaskState.working and EventPredicates.is_reasoning(response_event):
        responses.append(
            response_factory.reasoning(
                conversation_id=task.session_id,
                thread_id=thread_id,
                task_id=task.task_id,
                subtask_id=subtask_id,
                event=response_event,
                content=get_message_text(event.status.message, ""),
            )
        )
        return RouteResult(responses)

    return RouteResult(responses)


async def handle_artifact_update(
    response_factory: ResponseFactory,
    task: Task,
    thread_id: str,
    event: TaskArtifactUpdateEvent,
) -> List[BaseResponse]:
    responses: List[BaseResponse] = []
    artifact = event.artifact
    subtask_id = artifact.metadata.get("subtask_id") if artifact.metadata else None
    if not subtask_id:
        subtask_id = _default_subtask_id(task.task_id)
    response_event = artifact.metadata.get("response_event")
    content = get_message_text(artifact, "")

    if response_event == StreamResponseEvent.COMPONENT_GENERATOR:
        component_type = artifact.metadata.get("component_type", "unknown")
        responses.append(
            response_factory.component_generator(
                conversation_id=task.session_id,
                thread_id=thread_id,
                task_id=task.task_id,
                subtask_id=subtask_id,
                content=content,
                component_type=component_type,
            )
        )
        return responses

    responses.append(
        response_factory.message_response_general(
            event=response_event,
            conversation_id=task.session_id,
            thread_id=thread_id,
            task_id=task.task_id,
            subtask_id=subtask_id,
            content=content,
        )
    )
    return responses
