"""
Unit tests for valuecell.core.response.buffer module
"""

import time

import pytest

from valuecell.core.event.buffer import (
    BufferEntry,
    ResponseBuffer,
    SaveItem,
)
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


class TestBufferEntry:
    """Test BufferEntry class."""

    def test_init_default(self):
        """Test BufferEntry initialization with defaults."""
        entry = BufferEntry()

        assert entry.parts == []
        assert isinstance(entry.last_updated, float)
        assert isinstance(entry.item_id, str)
        assert len(entry.item_id) > 0
        assert entry.role is None
        assert entry.agent_name is None

    def test_init_with_params(self):
        """Test BufferEntry initialization with parameters."""
        item_id = "test-item-123"
        role = Role.USER
        entry = BufferEntry(item_id=item_id, role=role, agent_name="agent-test")

        assert entry.parts == []
        assert isinstance(entry.last_updated, float)
        assert entry.item_id == item_id
        assert entry.role == role
        assert entry.agent_name == "agent-test"

    def test_append_empty_text(self):
        """Test appending empty text."""
        entry = BufferEntry()
        initial_updated = entry.last_updated

        # Small delay to ensure time difference
        time.sleep(0.001)
        entry.append("")

        assert entry.parts == []
        assert entry.last_updated == initial_updated

    def test_append_text(self):
        """Test appending text."""
        entry = BufferEntry()
        initial_updated = entry.last_updated

        # Small delay to ensure time difference
        time.sleep(0.001)
        entry.append("Hello")

        assert entry.parts == ["Hello"]
        assert entry.last_updated > initial_updated

    def test_append_multiple_texts(self):
        """Test appending multiple texts."""
        entry = BufferEntry()

        entry.append("Hello")
        entry.append(" ")
        entry.append("World")

        assert entry.parts == ["Hello", " ", "World"]

    def test_snapshot_payload_empty(self):
        """Test snapshot_payload with no content."""
        entry = BufferEntry()

        result = entry.snapshot_payload()

        assert result is None

    def test_snapshot_payload_with_content(self):
        """Test snapshot_payload with content."""
        entry = BufferEntry()
        entry.append("Hello")
        entry.append(" World")

        result = entry.snapshot_payload()

        assert result is not None
        assert isinstance(result, BaseResponseDataPayload)
        assert result.content == "Hello World"


class TestResponseBuffer:
    """Test ResponseBuffer class."""

    def test_init(self):
        """Test ResponseBuffer initialization."""
        buffer = ResponseBuffer()

        assert buffer._buffers == {}
        assert StreamResponseEvent.TOOL_CALL_COMPLETED in buffer._immediate_events
        assert CommonResponseEvent.COMPONENT_GENERATOR in buffer._immediate_events
        assert NotifyResponseEvent.MESSAGE in buffer._immediate_events
        assert SystemResponseEvent.PLAN_REQUIRE_USER_INPUT in buffer._immediate_events
        assert SystemResponseEvent.THREAD_STARTED in buffer._immediate_events

        assert StreamResponseEvent.MESSAGE_CHUNK in buffer._buffered_events
        assert StreamResponseEvent.REASONING in buffer._buffered_events

    def test_annotate_non_buffered_event(self):
        """Test annotate with non-buffered event."""
        buffer = ResponseBuffer()
        response = BaseResponse(
            event=NotifyResponseEvent.MESSAGE,
            data=UnifiedResponseData(
                conversation_id="conv-123", role=Role.USER, item_id="item-123"
            ),
        )

        result = buffer.annotate(response)

        assert result == response
        assert result.data.item_id == "item-123"  # Should remain unchanged

    def test_annotate_buffered_event_new_buffer(self):
        """Test annotate with buffered event creating new buffer."""
        buffer = ResponseBuffer()
        # MESSAGE_CHUNK without item_id triggers buffer creation
        response = BaseResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            data=UnifiedResponseData(conversation_id="conv-123", role=Role.USER),
        )

        result = buffer.annotate(response)

        # Buffer should assign a stable item_id
        assert result.data.item_id is not None

        # Check buffer was created
        key = ("conv-123", None, None, StreamResponseEvent.MESSAGE_CHUNK)
        assert key in buffer._buffers
        assert buffer._buffers[key].role == Role.USER

    def test_annotate_reasoning_preserves_item_id(self):
        """Test that REASONING events preserve caller-provided item_id."""
        buffer = ResponseBuffer()
        response = BaseResponse(
            event=StreamResponseEvent.REASONING,
            data=UnifiedResponseData(
                conversation_id="conv-123", role=Role.AGENT, item_id="caller-item-id"
            ),
        )

        result = buffer.annotate(response)

        # Caller's item_id should be preserved
        assert result.data.item_id == "caller-item-id"
        # No buffer should be created for REASONING with item_id
        assert len(buffer._buffers) == 0

    def test_annotate_buffered_event_existing_buffer(self):
        """Test annotate with buffered event using existing buffer."""
        buffer = ResponseBuffer()
        response1 = BaseResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            data=UnifiedResponseData(conversation_id="conv-123", role=Role.USER),
        )
        response2 = BaseResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            data=UnifiedResponseData(conversation_id="conv-123", role=Role.USER),
        )

        result1 = buffer.annotate(response1)
        result2 = buffer.annotate(response2)

        # Both should get the same stable item_id from the buffer
        assert result1.data.item_id == result2.data.item_id
        # Only one buffer entry should exist
        assert len(buffer._buffers) == 1

    @pytest.mark.asyncio
    async def test_ingest_immediate_event_message(self):
        """Test ingest with immediate event (message)."""
        buffer = ResponseBuffer()
        response = BaseResponse(
            event=NotifyResponseEvent.MESSAGE,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                role=Role.USER,
                item_id="item-123",
                payload=BaseResponseDataPayload(content="Hello"),
                agent_name="agent-immediate",
            ),
        )

        result = buffer.ingest(response)

        assert len(result) == 1
        assert isinstance(result[0], SaveItem)
        assert result[0].item_id == "item-123"
        assert result[0].event == NotifyResponseEvent.MESSAGE
        assert result[0].conversation_id == "conv-123"
        assert result[0].role == Role.USER
        assert result[0].payload.content == "Hello"
        assert result[0].agent_name == "agent-immediate"

    @pytest.mark.asyncio
    async def test_ingest_buffered_event_message_chunk(self):
        """Test ingest with buffered event (message_chunk)."""
        buffer = ResponseBuffer()
        response = BaseResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                role=Role.AGENT,
                item_id="item-123",
                payload=BaseResponseDataPayload(content="Hello"),
                agent_name="agent-buffer",
            ),
        )

        result = buffer.ingest(response)

        assert len(result) == 1
        assert isinstance(result[0], SaveItem)
        assert result[0].event == StreamResponseEvent.MESSAGE_CHUNK
        assert result[0].conversation_id == "conv-123"
        assert result[0].role == Role.AGENT
        assert result[0].payload.content == "Hello"
        assert result[0].agent_name == "agent-buffer"

    @pytest.mark.asyncio
    async def test_ingest_buffered_event_reasoning(self):
        """Test ingest with buffered event (reasoning)."""
        buffer = ResponseBuffer()
        response = BaseResponse(
            event=StreamResponseEvent.REASONING,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                role=Role.AGENT,
                item_id="item-123",
                payload=BaseResponseDataPayload(content="Thinking..."),
            ),
        )

        result = buffer.ingest(response)

        assert len(result) == 1
        assert isinstance(result[0], SaveItem)
        assert result[0].event == StreamResponseEvent.REASONING
        assert result[0].payload.content == "Thinking..."

    @pytest.mark.asyncio
    async def test_ingest_buffered_event_multiple_chunks(self):
        """Test ingest with multiple buffered chunks."""
        buffer = ResponseBuffer()

        # First chunk
        response1 = BaseResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                role=Role.AGENT,
                payload=BaseResponseDataPayload(content="Hello"),
            ),
        )

        # Second chunk
        response2 = BaseResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                role=Role.AGENT,
                payload=BaseResponseDataPayload(content=" World"),
            ),
        )

        result1 = buffer.ingest(response1)
        result2 = buffer.ingest(response2)

        assert len(result1) == 1
        assert len(result2) == 1
        assert result1[0].payload.content == "Hello"
        assert result2[0].payload.content == "Hello World"

    @pytest.mark.asyncio
    async def test_ingest_unknown_event(self):
        """Test ingest with unknown event type."""
        buffer = ResponseBuffer()
        response = BaseResponse(
            event=SystemResponseEvent.CONVERSATION_STARTED,
            data=UnifiedResponseData(
                conversation_id="conv-123", role=Role.SYSTEM, item_id="item-123"
            ),
        )

        result = buffer.ingest(response)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_ingest_immediate_event_flushes_buffered(self):
        """Test that immediate events flush buffered content."""
        buffer = ResponseBuffer()

        # Add buffered content
        buffered_response = BaseResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                role=Role.AGENT,
                payload=BaseResponseDataPayload(content="Buffered content"),
            ),
        )
        buffer.ingest(buffered_response)

        # Send immediate event
        immediate_response = BaseResponse(
            event=NotifyResponseEvent.MESSAGE,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                role=Role.USER,
                item_id="immediate-item-123",
                payload=BaseResponseDataPayload(content="Immediate message"),
            ),
        )

        result = buffer.ingest(immediate_response)

        # Should have 2 items: flushed buffered + immediate
        assert len(result) == 2
        assert result[0].payload.content == "Buffered content"  # Flushed buffered
        assert result[1].payload.content == "Immediate message"  # Immediate

    @pytest.mark.asyncio
    async def test_flush_task(self):
        """Test flush_task method."""
        buffer = ResponseBuffer()

        # Add some buffered content
        response = BaseResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                thread_id="thread-123",
                task_id="task-123",
                role=Role.AGENT,
                payload=BaseResponseDataPayload(content="Content to flush"),
            ),
        )
        buffer.ingest(response)

        # Flush the task
        result = buffer.flush_task("conv-123", "thread-123", "task-123")

        assert len(result) == 1
        assert result[0].payload.content == "Content to flush"

        # Buffer should be cleared
        key = ("conv-123", "thread-123", "task-123", StreamResponseEvent.MESSAGE_CHUNK)
        assert key not in buffer._buffers

    @pytest.mark.asyncio
    async def test_flush_task_partial_match(self):
        """Test flush_task with partial context matching."""
        buffer = ResponseBuffer()

        # Add content for different tasks
        response1 = BaseResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                thread_id="thread-123",
                task_id="task-1",
                role=Role.AGENT,
                payload=BaseResponseDataPayload(content="Task 1 content"),
            ),
        )
        response2 = BaseResponse(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                thread_id="thread-123",
                task_id="task-2",
                role=Role.AGENT,
                payload=BaseResponseDataPayload(content="Task 2 content"),
            ),
        )

        buffer.ingest(response1)
        buffer.ingest(response2)

        # Flush only task-1
        result = buffer.flush_task("conv-123", "thread-123", "task-1")

        assert len(result) == 1
        assert result[0].payload.content == "Task 1 content"

        # Only task-1 buffer should be cleared
        key1 = ("conv-123", "thread-123", "task-1", StreamResponseEvent.MESSAGE_CHUNK)
        key2 = ("conv-123", "thread-123", "task-2", StreamResponseEvent.MESSAGE_CHUNK)
        assert key1 not in buffer._buffers
        assert key2 in buffer._buffers

    def test_make_save_item_from_response_with_base_payload(self):
        """Test _make_save_item_from_response with BaseResponseDataPayload."""
        buffer = ResponseBuffer()
        response = BaseResponse(
            event=NotifyResponseEvent.MESSAGE,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                role=Role.USER,
                item_id="item-123",
                payload=BaseResponseDataPayload(content="Test content"),
            ),
        )

        result = buffer._make_save_item_from_response(response)

        assert isinstance(result, SaveItem)
        assert result.item_id == "item-123"
        assert result.event == NotifyResponseEvent.MESSAGE
        assert result.conversation_id == "conv-123"
        assert result.role == Role.USER
        assert result.payload.content == "Test content"

    def test_make_save_item_from_response_with_string_payload(self):
        """Test _make_save_item_from_response with string payload."""
        buffer = ResponseBuffer()
        response = BaseResponse(
            event=NotifyResponseEvent.MESSAGE,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                role=Role.USER,
                item_id="item-123",
                payload=BaseResponseDataPayload(content="String content"),
            ),
        )

        result = buffer._make_save_item_from_response(response)

        assert isinstance(result, SaveItem)
        assert result.payload.content == "String content"

    def test_make_save_item_from_response_with_none_payload(self):
        """Test _make_save_item_from_response with None payload."""
        buffer = ResponseBuffer()
        response = BaseResponse(
            event=NotifyResponseEvent.MESSAGE,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                role=Role.USER,
                item_id="item-123",
                payload=None,
            ),
        )

        result = buffer._make_save_item_from_response(response)

        assert isinstance(result, SaveItem)
        assert result.payload.content is None

    def test_make_save_item_from_response_with_unknown_payload(self):
        """Test _make_save_item_from_response with unknown payload type."""
        buffer = ResponseBuffer()
        response = BaseResponse(
            event=NotifyResponseEvent.MESSAGE,
            data=UnifiedResponseData(
                conversation_id="conv-123",
                role=Role.USER,
                item_id="item-123",
                payload=BaseResponseDataPayload(
                    content="123"
                ),  # Use valid payload type
            ),
        )

        result = buffer._make_save_item_from_response(response)

        assert isinstance(result, SaveItem)
        assert result.payload.content == "123"

        assert isinstance(result, SaveItem)
        assert result.payload.content == "123"  # Should be converted to string

    def test_make_save_item(self):
        """Test _make_save_item method."""
        buffer = ResponseBuffer()
        data = UnifiedResponseData(
            conversation_id="conv-123",
            thread_id="thread-123",
            task_id="task-123",
            role=Role.AGENT,
        )
        payload = BaseResponseDataPayload(content="Test content")

        result = buffer._make_save_item(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            data=data,
            payload=payload,
            item_id="custom-item-123",
        )

        assert isinstance(result, SaveItem)
        assert result.item_id == "custom-item-123"
        assert result.event == StreamResponseEvent.MESSAGE_CHUNK
        assert result.conversation_id == "conv-123"
        assert result.thread_id == "thread-123"
        assert result.task_id == "task-123"
        assert result.role == Role.AGENT
        assert result.payload.content == "Test content"

    def test_make_save_item_auto_item_id(self):
        """Test _make_save_item method with auto-generated item_id."""
        buffer = ResponseBuffer()
        data = UnifiedResponseData(conversation_id="conv-123", role=Role.USER)
        payload = BaseResponseDataPayload(content="Test content")

        result = buffer._make_save_item(
            event=NotifyResponseEvent.MESSAGE, data=data, payload=payload
        )

        assert isinstance(result, SaveItem)
        assert isinstance(result.item_id, str)
        assert len(result.item_id) > 0
        assert result.event == NotifyResponseEvent.MESSAGE
        assert result.role == Role.USER
