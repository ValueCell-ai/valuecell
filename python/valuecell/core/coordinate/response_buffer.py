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
    UnifiedResponseData,
)
from valuecell.utils.uuid import generate_item_id


@dataclass
class SaveItem:
    item_id: str
    event: object  # ConversationItemEvent union; keep generic to avoid circular typing
    conversation_id: str
    thread_id: Optional[str]
    task_id: Optional[str]
    payload: Optional[BaseModel]
    role: Role = Role.AGENT


# conversation_id, thread_id, task_id, event
BufferKey = Tuple[str, Optional[str], Optional[str], object]


class BufferEntry:
    def __init__(self, item_id: Optional[str] = None, role: Optional[Role] = None):
        self.parts: List[str] = []
        self.last_updated: float = time.monotonic()
        # Stable paragraph id for this buffer entry. Reused across streamed chunks
        # until this entry is flushed (debounce/boundary). On size-based flush,
        # we rotate to a new paragraph id for subsequent chunks.
        self.item_id: str = item_id or generate_item_id()
        self.role: Optional[Role] = role

    def append(self, text: str):
        if text:
            self.parts.append(text)
            self.last_updated = time.monotonic()

    def snapshot_payload(self) -> Optional[BaseResponseDataPayload]:
        """Return current aggregate content without clearing the buffer."""
        if not self.parts:
            return None
        content = "".join(self.parts)
        return BaseResponseDataPayload(content=content)


class ResponseBuffer:
    """Buffers streaming responses and emits SaveMessage at suitable boundaries.

    Simplified rules (no debounce, no size-based rotation):
    - Immediate write-through: tool_call_completed, component_generator, message, plan_require_user_input
    - Buffered: message_chunk, reasoning
        - Maintain a stable paragraph item_id per (conversation, thread, task, event)
        - On every chunk, update the aggregate and return a SaveItem for upsert
    - Buffer key = (conversation_id, thread_id, task_id, event)
    """

    def __init__(self):
        self._buffers: Dict[BufferKey, BufferEntry] = {}

        self._immediate_events = {
            StreamResponseEvent.TOOL_CALL_COMPLETED,
            CommonResponseEvent.COMPONENT_GENERATOR,
            NotifyResponseEvent.MESSAGE,
            SystemResponseEvent.PLAN_REQUIRE_USER_INPUT,
            SystemResponseEvent.THREAD_STARTED,
        }
        self._buffered_events = {
            StreamResponseEvent.MESSAGE_CHUNK,
            StreamResponseEvent.REASONING,
        }

    def annotate(self, resp: BaseResponse) -> BaseResponse:
        """Ensure buffered events carry a stable paragraph item_id on the response.

        For buffered events (message_chunk, reasoning), we assign a stable
        paragraph id per (conversation, thread, task, event) key and stamp it
        into resp.data.item_id so the frontend can correlate chunks and the
        final persisted SaveItem. Immediate and boundary events are left as-is.
        """
        data: UnifiedResponseData = resp.data
        ev = resp.event
        if ev in self._buffered_events:
            key: BufferKey = (
                data.conversation_id,
                data.thread_id,
                data.task_id,
                ev,
            )
            entry = self._buffers.get(key)
            if not entry:
                # Start a new paragraph buffer with a fresh paragraph item_id
                entry = BufferEntry(role=data.role)
                self._buffers[key] = entry
            # Stamp the response with the stable paragraph id
            data.item_id = entry.item_id
            resp.data = data
        return resp

    def ingest(self, resp: BaseResponse) -> List[SaveItem]:
        data: UnifiedResponseData = resp.data
        ev = resp.event

        ctx = (
            data.conversation_id,
            data.thread_id,
            data.task_id,
        )
        out: List[SaveItem] = []

        # Immediate: write-through, but treat as paragraph boundary for buffered keys
        if ev in self._immediate_events:
            # Flush buffered aggregates for this context before the immediate item
            conv_id, th_id, tk_id = ctx
            keys_to_flush = self._collect_task_keys(conv_id, th_id, tk_id)
            out.extend(self._finalize_keys(keys_to_flush))
            # Now write the immediate item
            out.append(self._make_save_item_from_response(resp))
            return out

        # Buffered: accumulate by (ctx + event)
        if ev in self._buffered_events:
            key: BufferKey = (*ctx, ev)
            entry = self._buffers.get(key)
            if not entry:
                # If annotate() wasn't called, create an entry now.
                entry = BufferEntry(role=data.role)
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
                # Always upsert current aggregate (no size-based rotation)
                snap = entry.snapshot_payload()
                if snap is not None:
                    out.append(
                        self._make_save_item(
                            event=ev,
                            data=data,
                            payload=snap,
                            item_id=entry.item_id,
                        )
                    )
            return out

        # Other events: ignore for storage by default
        return out

    # No flush API: paragraph boundaries are triggered by immediate events only

    def _collect_task_keys(
        self,
        conversation_id: str,
        thread_id: Optional[str],
        task_id: Optional[str],
    ) -> List[BufferKey]:
        keys: List[BufferKey] = []
        for key in list(self._buffers.keys()):
            k_conv, k_thread, k_task, k_event = key
            if (
                k_conv == conversation_id
                and (thread_id is None or k_thread == thread_id)
                and (task_id is None or k_task == task_id)
                and k_event in self._buffered_events
            ):
                keys.append(key)
        return keys

    def _finalize_keys(self, keys: List[BufferKey]) -> List[SaveItem]:
        out: List[SaveItem] = []
        for key in keys:
            entry = self._buffers.get(key)
            if not entry:
                continue
            payload = entry.snapshot_payload()
            if payload is not None:
                out.append(
                    SaveItem(
                        item_id=entry.item_id,
                        event=key[3],
                        conversation_id=key[0],
                        thread_id=key[1],
                        task_id=key[2],
                        payload=payload,
                        role=entry.role or Role.AGENT,
                    )
                )
            if key in self._buffers:
                del self._buffers[key]
        return out

    def flush_task(
        self,
        conversation_id: str,
        thread_id: Optional[str],
        task_id: Optional[str],
    ) -> List[SaveItem]:
        """Finalize and emit all buffered aggregates for a given task context.

        This writes current aggregates (using their stable paragraph item_id)
        and clears the corresponding buffers. Use at task end (success or fail).
        """
        keys_to_flush = self._collect_task_keys(conversation_id, thread_id, task_id)
        return self._finalize_keys(keys_to_flush)

    def _make_save_item_from_response(self, resp: BaseResponse) -> SaveItem:
        data: UnifiedResponseData = resp.data
        payload = data.payload

        # Ensure payload is BaseModel
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

        return SaveItem(
            item_id=data.item_id,
            event=resp.event,
            conversation_id=data.conversation_id,
            thread_id=data.thread_id,
            task_id=data.task_id,
            payload=bm,
            role=data.role,
        )

    def _make_save_item(
        self,
        event: object,
        data: UnifiedResponseData,
        payload: BaseModel,
        item_id: str | None = None,
    ) -> SaveItem:
        return SaveItem(
            item_id=item_id or generate_item_id(),
            event=event,
            conversation_id=data.conversation_id,
            thread_id=data.thread_id,
            task_id=data.task_id,
            payload=payload,
            role=data.role,
        )
