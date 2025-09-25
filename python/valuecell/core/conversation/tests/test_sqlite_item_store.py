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
