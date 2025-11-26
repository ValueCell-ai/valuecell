import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator, Awaitable, Callable, Iterable, Optional

from a2a.types import TaskArtifactUpdateEvent, TaskState, TaskStatusUpdateEvent
from loguru import logger

from valuecell.core.agent.connect import RemoteConnections
from valuecell.core.agent.responses import EventPredicates
from valuecell.core.constants import (
    CURRENT_CONTEXT,
    DEPENDENCIES,
    LANGUAGE,
    METADATA,
    TIMEZONE,
    USER_PROFILE,
)
from valuecell.core.conversation.service import ConversationService
from valuecell.core.event.factory import ResponseFactory
from valuecell.core.event.router import RouteResult, SideEffectKind
from valuecell.core.event.service import EventResponseService
from valuecell.core.plan.models import ExecutionPlan
from valuecell.core.task.models import Task, TaskStatus
from valuecell.core.task.service import DEFAULT_EXECUTION_POLL_INTERVAL, TaskService
from valuecell.core.task.temporal import calculate_next_execution_delay
from valuecell.core.types import (
    BaseResponse,
    ComponentType,
    ScheduledTaskComponentContent,
    StreamResponseEvent,
    SubagentConversationPhase,
)
from valuecell.utils.i18n_utils import get_current_language, get_current_timezone
from valuecell.utils.user_profile_utils import get_user_profile_metadata
from valuecell.utils.uuid import generate_item_id, generate_task_id


class ScheduledTaskResultAccumulator:
    """Collect streaming output for a scheduled task run."""

    def __init__(self, task: Task) -> None:
        self._task = task
        self._buffer: list[str] = []

    @property
    def enabled(self) -> bool:
        return self._task.is_scheduled()

    def consume(self, responses: Iterable[BaseResponse]) -> list[BaseResponse]:
        if not self.enabled:
            return list(responses)

        passthrough: list[BaseResponse] = []
        for resp in responses:
            event = resp.event

            if EventPredicates.is_message(event):
                payload = resp.data.payload
                content = payload.content if payload else None
                if content:
                    self._buffer.append(content)
                continue

            if EventPredicates.is_reasoning(event):
                continue

            if EventPredicates.is_tool_call(event):
                continue

            passthrough.append(resp)

        return passthrough

    def finalize(self, response_factory: ResponseFactory) -> Optional[BaseResponse]:
        if not self.enabled:
            return None

        content = "".join(self._buffer).strip()
        if not content:
            content = "Task completed without output."

        component_payload = ScheduledTaskComponentContent(
            result=content,
            create_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        )
        component_payload_json = component_payload.model_dump_json(exclude_none=True)

        return response_factory.schedule_task_result_component(
            task=self._task,
            content=component_payload_json,
        )


class TaskExecutor:
    """Execute tasks and plans while persisting streamed output."""

    def __init__(
        self,
        agent_connections: RemoteConnections,
        task_service: TaskService,
        event_service: EventResponseService,
        conversation_service: ConversationService,
        poll_interval: float = DEFAULT_EXECUTION_POLL_INTERVAL,
    ) -> None:
        self._agent_connections = agent_connections
        self._task_service = task_service
        self._event_service = event_service
        self._conversation_service = conversation_service
        self._poll_interval = poll_interval

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        thread_id: str,
        metadata: Optional[dict] = None,
    ) -> AsyncGenerator[BaseResponse, None]:
        if plan.guidance_message:
            response = self._event_service.factory.message_response_general(
                event=StreamResponseEvent.MESSAGE_CHUNK,
                conversation_id=plan.conversation_id,
                thread_id=thread_id,
                task_id=generate_task_id(),
                content=plan.guidance_message,
                agent_name="Planner",
            )
            yield await self._event_service.emit(response)
            return

        for task in plan.tasks:
            subagent_component_id = generate_item_id()
            # Define a one-time emitter for subagent END component (used in two places)
            end_component_emitted = False

            async def emit_subagent_end_once() -> Optional[BaseResponse]:
                nonlocal end_component_emitted
                if not task.handoff_from_super_agent:
                    return None
                if end_component_emitted:
                    return None
                end_component_emitted = True
                return await self._emit_subagent_conversation_component(
                    plan.conversation_id,
                    thread_id,
                    task,
                    subagent_component_id,
                    SubagentConversationPhase.END,
                )

            if task.handoff_from_super_agent:
                await self._conversation_service.ensure_conversation(
                    user_id=plan.user_id,
                    conversation_id=task.conversation_id,
                    agent_name=task.agent_name,
                    title=task.title,
                )

                # Emit subagent conversation start component
                yield await self._emit_subagent_conversation_component(
                    plan.conversation_id,
                    thread_id,
                    task,
                    subagent_component_id,
                    SubagentConversationPhase.START,
                )

                thread_started = self._event_service.factory.thread_started(
                    conversation_id=task.conversation_id,
                    thread_id=thread_id,
                    user_query=task.query,
                )
                yield await self._event_service.emit(thread_started)

            try:
                await self._task_service.update_task(task)
                async for response in self.execute_task(
                    task,
                    thread_id,
                    metadata,
                    on_before_done=(
                        emit_subagent_end_once
                        if task.handoff_from_super_agent
                        else None
                    ),
                ):
                    yield response
            except Exception as exc:  # pragma: no cover - defensive logging
                error_msg = f"(Error) Error executing {task.task_id}: {exc}"
                logger.exception(error_msg)
                failure = self._event_service.factory.task_failed(
                    conversation_id=plan.conversation_id,
                    thread_id=thread_id,
                    task_id=task.task_id,
                    content=error_msg,
                    agent_name=task.agent_name,
                )
                yield await self._event_service.emit(failure)
            finally:
                if task.handoff_from_super_agent:
                    # Emit subagent conversation end component (only if not already emitted)
                    end_resp = await emit_subagent_end_once()
                    if end_resp is not None:
                        yield end_resp

    async def _emit_subagent_conversation_component(
        self,
        super_agent_conversation_id: str,
        thread_id: str,
        subagent_task: Task,
        component_id: str,
        phase: SubagentConversationPhase,
    ) -> BaseResponse:
        """Emit a subagent conversation component with the specified phase."""
        component_payload = json.dumps(
            {
                "conversation_id": subagent_task.conversation_id,
                "agent_name": subagent_task.agent_name,
                "phase": phase.value,
            }
        )
        component = self._event_service.factory.component_generator(
            conversation_id=super_agent_conversation_id,
            thread_id=thread_id,
            task_id=subagent_task.task_id,
            content=component_payload,
            component_type=ComponentType.SUBAGENT_CONVERSATION.value,
            component_id=component_id,
            agent_name=subagent_task.agent_name,
        )
        return await self._event_service.emit(component)

    async def execute_task(
        self,
        task: Task,
        thread_id: str,
        metadata: Optional[dict] = None,
        *,
        on_before_done: Optional[
            Callable[[], Awaitable[Optional[BaseResponse]]]
        ] = None,
        resumed: bool = False,
    ) -> AsyncGenerator[BaseResponse, None]:
        task_id = task.task_id
        conversation_id = task.conversation_id

        await self._task_service.start_task(task_id)

        exec_metadata = dict(metadata or {})
        exec_metadata.setdefault(METADATA, {})
        exec_metadata.setdefault(
            DEPENDENCIES,
            {
                USER_PROFILE: get_user_profile_metadata(task.user_id),
                CURRENT_CONTEXT: {},
                LANGUAGE: get_current_language(),
                TIMEZONE: get_current_timezone(),
            },
        )

        if task.is_scheduled() and not resumed:
            yield await self._event_service.emit(
                self._event_service.factory.schedule_task_controller_component(
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                    task=task,
                )
            )
            # Optionally emit a one-time subagent END before sending done
            if on_before_done is not None:
                maybe_resp = await on_before_done()
                if maybe_resp is not None:
                    yield maybe_resp
            yield await self._event_service.emit(
                self._event_service.factory.done(
                    conversation_id=conversation_id,
                    thread_id=thread_id,
                )
            )

        try:
            while True:
                async for response in self._execute_single_task_run(
                    task,
                    thread_id,
                    exec_metadata,
                ):
                    yield response

                if not task.is_scheduled():
                    break

                delay = calculate_next_execution_delay(task.schedule_config)
                if not delay:
                    break
                logger.info(
                    f"Scheduled task `{task.title}` ({task_id}) will re-execute in {delay} seconds."
                )

                await self._sleep_with_cancellation(task, delay)

                task = await self._task_service.get_task(task.task_id)
                if task.is_finished():
                    logger.info(f"Task `{task.title}` ({task_id}) is finished.")
                    break

            await self._task_service.complete_task(task_id)
            completed = self._event_service.factory.task_completed(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
                agent_name=task.agent_name,
            )
            yield await self._event_service.emit(completed)
        except Exception as exc:
            await self._task_service.fail_task(task_id, str(exc))
            raise
        finally:
            await self._event_service.flush_task_response(
                conversation_id=conversation_id,
                thread_id=thread_id,
                task_id=task_id,
            )

    async def _execute_single_task_run(
        self,
        task: Task,
        thread_id: str,
        metadata: dict,
    ) -> AsyncGenerator[BaseResponse, None]:
        agent_name = task.agent_name
        client = await self._agent_connections.get_client(agent_name)
        if not client:
            raise RuntimeError(f"Could not connect to agent {agent_name}")

        remote_response = await client.send_message(
            task.query,
            conversation_id=task.conversation_id,
            metadata=metadata,
        )

        accumulator = ScheduledTaskResultAccumulator(task)
        async for remote_task, event in remote_response:
            if event is None and remote_task.status.state == TaskState.submitted:
                task.remote_task_ids.append(remote_task.id)
                started = self._event_service.factory.task_started(
                    conversation_id=task.conversation_id,
                    thread_id=thread_id,
                    task_id=task.task_id,
                    agent_name=agent_name,
                )
                yield await self._event_service.emit(started)
                continue

            if isinstance(event, TaskStatusUpdateEvent):
                route_result: RouteResult = await self._event_service.route_task_status(
                    task, thread_id, event
                )
                responses = accumulator.consume(route_result.responses)
                for resp in responses:
                    yield await self._event_service.emit(resp)
                for side_effect in route_result.side_effects:
                    if side_effect.kind == SideEffectKind.FAIL_TASK:
                        await self._task_service.fail_task(
                            task.task_id, side_effect.reason or ""
                        )
                        # Sync the failure back to persisted conversation items
                        await self._conversation_service.manager.update_task_component_status(
                            task_id=task.task_id,
                            status=TaskStatus.FAILED.value,
                            error_reason=side_effect.reason,
                        )
                if route_result.done:
                    return
                continue

            if isinstance(event, TaskArtifactUpdateEvent):
                logger.info(
                    "Received unexpected artifact update for task %s: %s",
                    task.task_id,
                    event,
                )
                continue

        final_component = accumulator.finalize(self._event_service.factory)
        if final_component is not None:
            yield await self._event_service.emit(final_component)

        return

    async def _sleep_with_cancellation(self, task: Task, delay: float) -> None:
        remaining = delay
        while remaining > 0:
            task = await self._task_service.get_task(task.task_id)
            if task.is_finished():
                return
            sleep_for = min(self._poll_interval, remaining)
            await asyncio.sleep(sleep_for)
            remaining -= sleep_for
