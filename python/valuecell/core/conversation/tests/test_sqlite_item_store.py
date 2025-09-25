import os
import tempfile

import pytest
from valuecell.core.conversation.item_store import SQLiteItemStore
from valuecell.core.types import ConversationItem, Role, SystemResponseEvent


@pytest.mark.asyncio
async def test_sqlite_item_store_basic_crud():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        store = SQLiteItemStore(path)

        # create and save two items
        i1 = ConversationItem(
            item_id="i1",
            role=Role.SYSTEM,
            event=SystemResponseEvent.THREAD_STARTED,
            conversation_id="s1",
            thread_id="t1",
            task_id=None,
            payload='{"a":1}',
        )
        i2 = ConversationItem(
            item_id="i2",
            role=Role.SYSTEM,
            event=SystemResponseEvent.DONE,
            conversation_id="s1",
            thread_id="t1",
            task_id=None,
            payload='{"a":1}',
        )
        await store.save_item(i1)
        await store.save_item(i2)

        # count
        cnt = await store.get_item_count("s1")
        assert cnt == 2

        # get latest
        latest = await store.get_latest_item("s1")
        assert latest is not None
        assert latest.item_id in {"i1", "i2"}

        # list
        items = await store.get_items("s1")
        assert len(items) == 2
        ids = {i.item_id for i in items}
        assert ids == {"i1", "i2"}

        # get one
        one = await store.get_item("i1")
        assert one is not None
        assert one.item_id == "i1"

        # delete
        await store.delete_conversation_items("s1")
        cnt2 = await store.get_item_count("s1")
        assert cnt2 == 0
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.asyncio
async def test_sqlite_item_store_filters_and_pagination():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        store = SQLiteItemStore(path)

        # create several items with varying roles, events and payloads
        items = [
            ConversationItem(
                item_id="a1",
                role=Role.SYSTEM,
                event=SystemResponseEvent.THREAD_STARTED,
                conversation_id="s2",
                thread_id="t1",
                task_id=None,
                payload='{"a":1}',
            ),
            ConversationItem(
                item_id="a2",
                role=Role.AGENT,
                event=SystemResponseEvent.DONE,
                conversation_id="s2",
                thread_id="t1",
                task_id=None,
                payload='{"component_type":"card","a":2}',
            ),
            ConversationItem(
                item_id="a3",
                role=Role.AGENT,
                event=SystemResponseEvent.THREAD_STARTED,
                conversation_id="s2",
                thread_id="t2",
                task_id=None,
                payload='{"component_type":"chart","a":3}',
            ),
        ]

        # save in order
        for it in items:
            await store.save_item(it)

        # filter by role
        agent_items = await store.get_items("s2", role=Role.AGENT)
        assert {i.item_id for i in agent_items} == {"a2", "a3"}

        # filter by event
        thread_started = await store.get_items(
            "s2", event=SystemResponseEvent.THREAD_STARTED
        )
        assert {i.item_id for i in thread_started} == {"a1", "a3"}

        # filter by component_type (json_extract on payload)
        cards = await store.get_items("s2", component_type="card")
        assert [i.item_id for i in cards] == ["a2"]

        # limit & offset: get first item only, then skip first
        first = await store.get_items("s2", limit=1)
        assert len(first) == 1
        second_page = await store.get_items("s2", limit=1, offset=1)
        assert len(second_page) == 1

    finally:
        if os.path.exists(path):
            os.remove(path)
