# ruff: noqa: F811
import time

import pytest
from valuecell.core.coordinate.response import ResponseFactory
from valuecell.core.coordinate.response_buffer import ResponseBuffer
from valuecell.core.types import (
    CommonResponseEvent,
    NotifyResponseEvent,
    StreamResponseEvent,
)


@pytest.fixture(name="ids")
def _ids_fixture():
    return {
        "conversation_id": "conv-1",
        "thread_id": "th-1",
        "task_id": "tsk-1",
        "subtask_id": "sub-1",
    }


@pytest.fixture(name="factory")
def _factory_fixture():
    return ResponseFactory()


def test_buffer_accumulate_and_flush_due(ids, factory):
    buf = ResponseBuffer(debounce_ms=0, max_chars=1024)

    # two message chunks buffered
    r1 = factory.message_response_general(
        event=StreamResponseEvent.MESSAGE_CHUNK,
        conversation_id=ids["conversation_id"],
        thread_id=ids["thread_id"],
        task_id=ids["task_id"],
        subtask_id=ids["subtask_id"],
        content="Hello ",
    )
    r2 = factory.message_response_general(
        event=StreamResponseEvent.MESSAGE_CHUNK,
        conversation_id=ids["conversation_id"],
        thread_id=ids["thread_id"],
        task_id=ids["task_id"],
        subtask_id=ids["subtask_id"],
        content="World",
    )

    assert buf.ingest(r1) == []
    assert buf.ingest(r2) == []

    # flush_due (debounce_ms=0) should emit one aggregated SaveMessage
    out = buf.flush_due()
    assert len(out) == 1
    sm = out[0]
    assert sm.event == StreamResponseEvent.MESSAGE_CHUNK
    assert sm.payload.content == "Hello World"
    # aggregated output should have its own generated item_id
    assert sm.item_id is not None and isinstance(sm.item_id, str)


def test_immediate_component_splits_chunks(ids, factory):
    buf = ResponseBuffer(debounce_ms=1e5, max_chars=1024)  # prevent auto flush

    # buffer one chunk
    r_chunk = factory.message_response_general(
        event=StreamResponseEvent.MESSAGE_CHUNK,
        conversation_id=ids["conversation_id"],
        thread_id=ids["thread_id"],
        task_id=ids["task_id"],
        subtask_id=ids["subtask_id"],
        content="Part A",
    )
    assert buf.ingest(r_chunk) == []

    # immediate component should flush prior chunk, then write itself
    r_comp = factory.component_generator(
        conversation_id=ids["conversation_id"],
        thread_id=ids["thread_id"],
        task_id=ids["task_id"],
        subtask_id=ids["subtask_id"],
        content="<div></div>",
        component_type="html",
    )
    out = buf.ingest(r_comp)
    assert len(out) == 2
    assert out[0].event == StreamResponseEvent.MESSAGE_CHUNK
    assert out[0].payload.content == "Part A"
    assert out[1].event == CommonResponseEvent.COMPONENT_GENERATOR
    assert out[1].payload.component_type == "html"

    # new chunk after component becomes a new segment
    r_chunk2 = factory.message_response_general(
        event=StreamResponseEvent.MESSAGE_CHUNK,
        conversation_id=ids["conversation_id"],
        thread_id=ids["thread_id"],
        task_id=ids["task_id"],
        subtask_id=ids["subtask_id"],
        content="Part B",
    )
    assert buf.ingest(r_chunk2) == []
    out2 = buf.flush_due(now=time.monotonic() + 1e6)  # force flush
    assert len(out2) == 1
    assert out2[0].payload.content == "Part B"


def test_boundary_done_flushes_reasoning(ids, factory):
    buf = ResponseBuffer(debounce_ms=99999, max_chars=1024)

    r1 = factory.reasoning(
        conversation_id=ids["conversation_id"],
        thread_id=ids["thread_id"],
        task_id=ids["task_id"],
        subtask_id=ids["subtask_id"],
        event=StreamResponseEvent.REASONING,
        content="think1",
    )
    r2 = factory.reasoning(
        conversation_id=ids["conversation_id"],
        thread_id=ids["thread_id"],
        task_id=ids["task_id"],
        subtask_id=ids["subtask_id"],
        event=StreamResponseEvent.REASONING,
        content="think2",
    )
    assert buf.ingest(r1) == []
    assert buf.ingest(r2) == []

    # boundary: done -> should flush reasoning, but boundary itself is not stored
    r_done = factory.done(ids["conversation_id"], ids["thread_id"])
    out = buf.ingest(r_done)
    assert len(out) == 1
    assert out[0].event == StreamResponseEvent.REASONING
    assert out[0].payload.content == "think1think2"


def test_size_based_flush(ids, factory):
    buf = ResponseBuffer(debounce_ms=99999, max_chars=5)
    # total length reaches 5, should flush immediately on third ingest
    for part in ["12", "34", "5"]:
        r = factory.message_response_general(
            event=StreamResponseEvent.MESSAGE_CHUNK,
            conversation_id=ids["conversation_id"],
            thread_id=ids["thread_id"],
            task_id=ids["task_id"],
            subtask_id=ids["subtask_id"],
            content=part,
        )
        out = buf.ingest(r)
    # last ingest should have triggered immediate flush
    assert len(out) == 1
    assert out[0].event == StreamResponseEvent.MESSAGE_CHUNK
    assert out[0].payload.content == "12345"


def test_immediate_message(ids, factory):
    buf = ResponseBuffer()
    r = factory.message_response_general(
        event=NotifyResponseEvent.MESSAGE,
        conversation_id=ids["conversation_id"],
        thread_id=ids["thread_id"],
        task_id=ids["task_id"],
        subtask_id=ids["subtask_id"],
        content="hi",
    )
    out = buf.ingest(r)
    assert len(out) == 1
    assert out[0].event == NotifyResponseEvent.MESSAGE
    assert out[0].payload.content == "hi"
    # immediate output should carry the BaseResponse item_id
    assert out[0].item_id == r.item_id
