import os
import tempfile

import pytest
from valuecell.core.session.message_store import SQLiteMessageStore
from valuecell.core.types import ConversationItem, Role, SystemResponseEvent


@pytest.mark.asyncio
async def test_sqlite_message_store_basic_crud():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        store = SQLiteMessageStore(path)

        # create and save two messages
        m1 = ConversationItem(
            item_id="i1",
            role=Role.SYSTEM,
            event=SystemResponseEvent.THREAD_STARTED,
            conversation_id="s1",
            thread_id="t1",
            task_id=None,
            payload='{"a":1}',
        )
        m2 = ConversationItem(
            item_id="i2",
            role=Role.SYSTEM,
            event=SystemResponseEvent.DONE,
            conversation_id="s1",
            thread_id="t1",
            task_id=None,
            payload='{"a":1}',
        )
        await store.save_message(m1)
        await store.save_message(m2)

        # count
        cnt = await store.get_message_count("s1")
        assert cnt == 2

        # get latest
        latest = await store.get_latest_message("s1")
        assert latest is not None
        assert latest.item_id in {"i1", "i2"}

        # list
        msgs = await store.get_messages("s1")
        assert len(msgs) == 2
        ids = {m.item_id for m in msgs}
        assert ids == {"i1", "i2"}

        # get one
        one = await store.get_message("i1")
        assert one is not None
        assert one.item_id == "i1"

        # delete
        await store.delete_session_messages("s1")
        cnt2 = await store.get_message_count("s1")
        assert cnt2 == 0
    finally:
        if os.path.exists(path):
            os.remove(path)
