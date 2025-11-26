import asyncio

import pytest

from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.core.types import UserInput, UserInputMetadata
import valuecell.adapters.models.factory as factory_mod
import valuecell.utils.model as model_utils_mod


@pytest.mark.asyncio
async def test_orchestrator_buffer_store_e2e(tmp_path, monkeypatch):
    db_path = tmp_path / "e2e_valuecell.db"
    # Use DATABASE_URL for tests; utils resolve_db_path will honor sqlite DSN
    monkeypatch.setenv("VALUECELL_DATABASE_URL", f"sqlite:///{db_path}")

    monkeypatch.setattr(
        factory_mod, "create_model", lambda *args, **kwargs: "stub-model"
    )
    monkeypatch.setattr(
        factory_mod, "create_embedder", lambda *args, **kwargs: "stub-embedder"
    )
    monkeypatch.setattr(
        model_utils_mod, "get_model_for_agent", lambda *args, **kwargs: "stub-model"
    )
    monkeypatch.setattr(
        model_utils_mod, "create_embedder", lambda *args, **kwargs: "stub-embedder"
    )

    orch = AgentOrchestrator()

    # Prepare a conversation and a simple query; orchestrator will create the conversation if missing
    conversation_id = "e2e-conversation"
    user_id = "e2e-user"
    ui = UserInput(
        query="hello world",
        target_agent_name="TestAgent",
        meta=UserInputMetadata(conversation_id=conversation_id, user_id=user_id),
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

    # Verify persistence: at least 1 message exists for conversation
    msgs = await orch.conversation_service.manager.get_conversation_items(
        conversation_id
    )
    assert isinstance(msgs, list)
    assert len(msgs) >= 1

    # Also verify we can count and fetch latest
    cnt = await orch.conversation_service.manager.get_item_count(conversation_id)
    assert cnt == len(msgs)
    latest = await orch.conversation_service.manager.get_latest_item(conversation_id)
    assert latest is not None
