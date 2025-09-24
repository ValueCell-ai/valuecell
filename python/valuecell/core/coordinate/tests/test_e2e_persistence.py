import asyncio

import pytest

from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.core.types import UserInput, UserInputMetadata


@pytest.mark.asyncio
async def test_orchestrator_buffer_store_e2e(tmp_path, monkeypatch):
    # Point default SessionManager to a temp sqlite file
    db_path = tmp_path / "e2e_valuecell.db"
    monkeypatch.setenv("VALUECELL_SQLITE_DB", str(db_path))

    orch = AgentOrchestrator()

    # Prepare a session and a simple query; orchestrator will create the session if missing
    session_id = "e2e-session"
    user_id = "e2e-user"
    ui = UserInput(
        query="hello world",
        desired_agent_name="TestAgent",
        meta=UserInputMetadata(session_id=session_id, user_id=user_id),
    )

    # We don't have a live agent, so we expect planner/agent logic to raise; we just want to ensure
    # that at least conversation_started and done/error go through the buffer->store path without crashing.
    out = []
    try:
        async for resp in orch.process_user_input(ui):
            out.append(resp)
            # allow buffer debounce tick
            await asyncio.sleep(0)
    except Exception:
        # Orchestrator is defensive, should not raise; but in case, we still proceed to check persistence
        pass

    # Verify persistence: at least 1 message exists for session
    msgs = await orch.session_manager.get_session_messages(session_id)
    assert isinstance(msgs, list)
    assert len(msgs) >= 1

    # Also verify we can count and fetch latest
    cnt = await orch.session_manager.get_message_count(session_id)
    assert cnt == len(msgs)
    latest = await orch.session_manager.get_latest_message(session_id)
    assert latest is not None
