import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel

from valuecell.core.types import (
    BaseResponse,
    BaseResponseDataPayload,
    CommonResponseEvent,
    NotifyResponseEvent,
    ResponseMetadata,
    ResponsePayload,
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
    payload: Optional[ResponsePayload]
    role: Role = Role.AGENT
    agent_name: Optional[str] = None
    metadata: Optional[ResponseMetadata] = None


# conversation_id, thread_id, task_id, event
BufferKey = Tuple[str, Optional[str], Optional[str], object]


class BufferEntry:
    """Represents an in-memory paragraph buffer for streamed chunks.

    A BufferEntry collects sequential message chunks belonging to the same
    logical paragraph. It maintains a stable `item_id` so streamed chunks can
    be correlated with the final persisted ConversationItem.
    """

    def __init__(
        self,
        item_id: Optional[str] = None,
        role: Optional[Role] = None,
        agent_name: Optional[str] = None,
    ):
        self.parts: List[str] = []
        self.last_updated: float = time.monotonic()
        # Stable paragraph id for this buffer entry. Reused across streamed chunks
        # until this entry is flushed (debounce/boundary). On size-based flush,
        # we rotate to a new paragraph id for subsequent chunks.
        self.item_id: str = item_id or generate_item_id()
        self.role: Optional[Role] = role
        self.agent_name: Optional[str] = agent_name

    def append(self, text: str):
        """Append a chunk of text to this buffer and update the timestamp."""
        if text:
            self.parts.append(text)
            self.last_updated = time.monotonic()

    def snapshot_payload(self) -> Optional[BaseResponseDataPayload]:
        """Return the current aggregate content as a payload without clearing.

        Returns None when there is no content buffered.
        """
        if not self.parts:
            return None
        content = "".join(self.parts)
        return BaseResponseDataPayload(content=content)


class ResponseBuffer:
    """Buffer streaming responses and produce persistence-ready SaveItem objects.

    The ResponseBuffer implements a simple buffering strategy:
    - Some events are "immediate" and should be persisted as-is (tool results,
        component generator events, notify messages, system-level events).
    - Other events (message chunks, reasoning) are buffered and aggregated
        into paragraph-level items which are upserted as streaming progress
        is received. This preserves a stable paragraph `item_id` across chunks.

    The buffer key is a tuple (conversation_id, thread_id, task_id, event).
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
        """Stamp buffered responses with a stable paragraph `item_id`.

        For events that are buffered (e.g. message chunks, reasoning), assign a
        stable paragraph `item_id` to resp.data.item_id so the frontend and
        storage layer can correlate incremental chunks with the final saved
        conversation item.

        For REASONING events, if the caller has already set an item_id, it is
        preserved to allow correlation of reasoning_started/reasoning/reasoning_completed.
        MESSAGE_CHUNK events always use the buffer to get a stable paragraph item_id.
        """
        data: UnifiedResponseData = resp.data
        ev = resp.event
        if ev in self._buffered_events:
            # For REASONING events, trust the caller's item_id (set by orchestrator)
            # and skip buffer-based id assignment. MESSAGE_CHUNK always uses buffer.
            # TODO: consider when no item_id is set for REASONING, especially in remote agent calls
            if ev == StreamResponseEvent.REASONING and data.item_id:
                return resp
            key: BufferKey = (
                data.conversation_id,
                data.thread_id,
                data.task_id,
                ev,
            )
            entry = self._buffers.get(key)
            if not entry:
                # Start a new paragraph buffer with a fresh paragraph item_id
                entry = BufferEntry(role=data.role, agent_name=data.agent_name)
                self._buffers[key] = entry
            if entry.agent_name is None and data.agent_name:
                entry.agent_name = data.agent_name
            # Stamp the response with the stable paragraph id
            data.item_id = entry.item_id
            resp.data = data
        return resp

    def ingest(self, resp: BaseResponse) -> List[SaveItem]:
        """Ingest a response and return a list of SaveItem objects to persist.

        Depending on the event type this will either:
        - Flush and emit an immediate item (for immediate events), or
        - Accumulate buffered chunks and emit an upsert SaveItem with the
          current aggregated payload for the paragraph entry.

        Returns:
            A list of SaveItem objects that should be persisted by the caller.
        """
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
                entry = BufferEntry(role=data.role, agent_name=data.agent_name)
                self._buffers[key] = entry
            elif entry.agent_name is None and data.agent_name:
                entry.agent_name = data.agent_name

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
                        agent_name=entry.agent_name,
                        metadata=None,  # Buffered entries don't have metadata
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
            agent_name=data.agent_name,
            metadata=data.metadata,
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
            agent_name=data.agent_name,
            metadata=data.metadata,
        )
