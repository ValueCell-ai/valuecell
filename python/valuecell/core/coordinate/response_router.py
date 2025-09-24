import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from a2a.types import TaskState, TaskStatusUpdateEvent
from a2a.utils import get_message_text
from valuecell.core.agent.responses import EventPredicates
from valuecell.core.coordinate.response import ResponseFactory
from valuecell.core.task import Task
from valuecell.core.types import (
    BaseResponse,
    CommonResponseEvent,
)

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
                event=response_event,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_result=tool_result,
            )
        )
        return RouteResult(responses)

    # Reasoning messages
    content = get_message_text(event.status.message, "")
    if state == TaskState.working and EventPredicates.is_reasoning(response_event):
        responses.append(
            response_factory.reasoning(
                conversation_id=task.session_id,
                thread_id=thread_id,
                task_id=task.task_id,
                event=response_event,
                content=content,
            )
        )
        return RouteResult(responses)

    # component generator
    if (
        state == TaskState.working
        and response_event == CommonResponseEvent.COMPONENT_GENERATOR
    ):
        component_type = event.metadata.get("component_type", "unknown")
        responses.append(
            response_factory.component_generator(
                conversation_id=task.session_id,
                thread_id=thread_id,
                task_id=task.task_id,
                content=content,
                component_type=component_type,
            )
        )
        return RouteResult(responses)

    # general messages
    if state == TaskState.working and EventPredicates.is_message(response_event):
        responses.append(
            response_factory.message_response_general(
                event=response_event,
                conversation_id=task.session_id,
                thread_id=thread_id,
                task_id=task.task_id,
                content=content,
            )
        )
        return RouteResult(responses)

    return RouteResult(responses)
