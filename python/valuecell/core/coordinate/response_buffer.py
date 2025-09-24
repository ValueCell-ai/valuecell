import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel

from valuecell.core.types import (
    BaseResponse,
    BaseResponseDataPayload,
    CommonResponseEvent,
    NotifyResponseEvent,
    Role,
    StreamResponseEvent,
    SystemResponseEvent,
    TaskStatusEvent,
    UnifiedResponseData,
)
from valuecell.utils.uuid import generate_uuid


def generate_item_id() -> str:
    return generate_uuid("item")


@dataclass
class SaveMessage:
    item_id: str
    role: Role
    event: object  # ConversationItemEvent union; keep generic to avoid circular typing
    conversation_id: str
    thread_id: Optional[str]
    task_id: Optional[str]
    subtask_id: Optional[str]
    payload: Optional[BaseModel]


# conversation_id, thread_id, task_id, subtask_id, event
BufferKey = Tuple[str, Optional[str], Optional[str], Optional[str], object]


class BufferEntry:
    def __init__(self):
        self.parts: List[str] = []
        self.last_updated: float = time.monotonic()

    def append(self, text: str):
        if text:
            self.parts.append(text)
            self.last_updated = time.monotonic()

    def size(self) -> int:
        return sum(len(p) for p in self.parts)

    def flush_to_payload(self) -> Optional[BaseResponseDataPayload]:
        if not self.parts:
            return None
        content = "".join(self.parts)
        self.parts.clear()
        self.last_updated = time.monotonic()
        return BaseResponseDataPayload(content=content)


class ResponseBuffer:
    """Buffers streaming responses and emits SaveMessage at suitable boundaries.

    Rules:
    - Immediate write: tool_call_completed, component_generator, message, plan_require_user_input
    - Buffered: message_chunk, reasoning (debounced or boundary-triggered)
    - Boundary triggers a flush for the same context: task_completed, task_failed, done
    - Buffer key = (conversation_id, thread_id, task_id, subtask_id, event)
    """

    def __init__(
        self,
        debounce_ms: int = 1000,
        max_chars: int = 4096,
    ):
        self._buffers: Dict[BufferKey, BufferEntry] = {}
        self._debounce_sec = debounce_ms / 1000.0
        self._max_chars = max_chars

        self._immediate_events = {
            StreamResponseEvent.TOOL_CALL_COMPLETED,
            CommonResponseEvent.COMPONENT_GENERATOR,
            NotifyResponseEvent.MESSAGE,
            SystemResponseEvent.PLAN_REQUIRE_USER_INPUT,
        }
        self._buffered_events = {
            StreamResponseEvent.MESSAGE_CHUNK,
            StreamResponseEvent.REASONING,
        }
        self._boundary_events = {
            TaskStatusEvent.TASK_COMPLETED,
            SystemResponseEvent.TASK_FAILED,
            SystemResponseEvent.DONE,
        }

    def ingest(self, resp: BaseResponse) -> List[SaveMessage]:
        data: UnifiedResponseData = resp.data
        ev = resp.event

        ctx = (
            data.conversation_id,
            data.thread_id,
            data.task_id,
            data.subtask_id,
        )
        out: List[SaveMessage] = []

        # Boundary-only: flush buffers for this context
        if ev in self._boundary_events:
            out.extend(self._flush_context(*ctx))
            return out

        # Immediate: flush buffers for this context, then write self
        if ev in self._immediate_events:
            out.extend(self._flush_context(*ctx))
            out.append(self._make_save_message_from_response(resp))
            return out

        # Buffered: accumulate by (ctx + event)
        if ev in self._buffered_events:
            key: BufferKey = (*ctx, ev)
            entry = self._buffers.get(key)
            if not entry:
                entry = BufferEntry()
                self._buffers[key] = entry

            # Extract text content from payload
            payload = data.payload
            text = None
            if isinstance(payload, BaseResponseDataPayload):
                text = payload.content or ""
            elif isinstance(payload, BaseModel):
                # Fallback: serialize whole payload
                text = payload.model_dump_json(exclude_none=True)
            elif isinstance(payload, str):
                text = payload
            else:
                text = ""

            if text:
                entry.append(text)
                # If exceed size, flush one segment immediately
                if entry.size() >= self._max_chars:
                    flushed = entry.flush_to_payload()
                    if flushed is not None:
                        out.append(
                            self._make_save_message(
                                role=self._role_for_event(ev),
                                event=ev,
                                data=data,
                                payload=flushed,
                                item_id=generate_item_id(),
                            )
                        )
            return out

        # Other events: ignore for storage by default
        return out

    def flush_due(self, now: Optional[float] = None) -> List[SaveMessage]:
        now = now or time.monotonic()
        out: List[SaveMessage] = []
        to_delete: List[BufferKey] = []
        for key, entry in self._buffers.items():
            if now - entry.last_updated >= self._debounce_sec and entry.parts:
                payload = entry.flush_to_payload()
                if payload is not None:
                    conv_id, thread_id, task_id, subtask_id, ev = key
                    out.append(
                        SaveMessage(
                            item_id=generate_item_id(),
                            role=self._role_for_event(ev),
                            event=ev,
                            conversation_id=conv_id,
                            thread_id=thread_id,
                            task_id=task_id,
                            subtask_id=subtask_id,
                            payload=payload,
                        )
                    )
                # entry remains but is empty; mark for cleanup to prevent leaks
                to_delete.append(key)
        for key in to_delete:
            # drop empty/idle entries
            if key in self._buffers and not self._buffers[key].parts:
                del self._buffers[key]
        return out

    def flush_context(
        self,
        conversation_id: str,
        thread_id: Optional[str] = None,
        task_id: Optional[str] = None,
        subtask_id: Optional[str] = None,
    ) -> List[SaveMessage]:
        return self._flush_context(conversation_id, thread_id, task_id, subtask_id)

    def flush_all(self) -> List[SaveMessage]:
        out: List[SaveMessage] = []
        for key in list(self._buffers.keys()):
            entry = self._buffers.get(key)
            if not entry:
                continue
            payload = entry.flush_to_payload()
            if payload is not None:
                conv_id, thread_id, task_id, subtask_id, ev = key
                out.append(
                    SaveMessage(
                        item_id=generate_item_id(),
                        role=self._role_for_event(ev),
                        event=ev,
                        conversation_id=conv_id,
                        thread_id=thread_id,
                        task_id=task_id,
                        subtask_id=subtask_id,
                        payload=payload,
                    )
                )
            del self._buffers[key]
        return out

    def _flush_context(
        self,
        conversation_id: str,
        thread_id: Optional[str],
        task_id: Optional[str],
        subtask_id: Optional[str],
    ) -> List[SaveMessage]:
        out: List[SaveMessage] = []

        # Collect keys matching the context and buffered events only
        def match(val, want):
            return want is None or val == want

        keys: List[BufferKey] = []
        for key in list(self._buffers.keys()):
            if (
                key[0] == conversation_id
                and match(key[1], thread_id)
                and match(key[2], task_id)
                and match(key[3], subtask_id)
                and key[4] in self._buffered_events
            ):
                keys.append(key)

        for key in keys:
            entry = self._buffers.get(key)
            if not entry:
                continue
            payload = entry.flush_to_payload()
            if payload is not None:
                conv_id, thread_id, task_id, subtask_id, ev = key
                out.append(
                    SaveMessage(
                        item_id=generate_item_id(),
                        role=self._role_for_event(ev),
                        event=ev,
                        conversation_id=conv_id,
                        thread_id=thread_id,
                        task_id=task_id,
                        subtask_id=subtask_id,
                        payload=payload,
                    )
                )
            # Remove emptied buffer
            if key in self._buffers:
                del self._buffers[key]

        return out

    def _make_save_message_from_response(self, resp: BaseResponse) -> SaveMessage:
        data: UnifiedResponseData = resp.data
        payload = data.payload

        # Ensure payload is BaseModel for SessionManager
        if isinstance(payload, BaseModel):
            bm = payload
        elif isinstance(payload, str):
            bm = BaseResponseDataPayload(content=payload)
        elif payload is None:
            bm = BaseResponseDataPayload(content=None)
        else:
            # Fallback to JSON string
            try:
                bm = BaseResponseDataPayload(content=str(payload))
            except Exception:
                bm = BaseResponseDataPayload(content=None)

        return SaveMessage(
            item_id=getattr(resp, "item_id", generate_item_id()),
            role=self._role_for_event(resp.event),
            event=resp.event,
            conversation_id=data.conversation_id,
            thread_id=data.thread_id,
            task_id=data.task_id,
            subtask_id=data.subtask_id,
            payload=bm,
        )

    def _make_save_message(
        self,
        role: Role,
        event: object,
        data: UnifiedResponseData,
        payload: BaseModel,
        item_id: str | None = None,
    ) -> SaveMessage:
        return SaveMessage(
            item_id=item_id,
            role=role,
            event=event,
            conversation_id=data.conversation_id,
            thread_id=data.thread_id,
            task_id=data.task_id,
            subtask_id=data.subtask_id,
            payload=payload,
        )

    def _role_for_event(self, ev: object) -> Role:
        # Agent-originated by default; some system events are SYSTEM
        if ev in {SystemResponseEvent.PLAN_REQUIRE_USER_INPUT}:
            return Role.SYSTEM
        return Role.AGENT
