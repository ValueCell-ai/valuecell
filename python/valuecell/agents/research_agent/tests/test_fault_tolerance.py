import pytest


def _raise_unavailable(*args, **kwargs):
    raise ValueError("No embedding provider configured")


def test_get_vector_db_returns_none_when_embedder_unavailable(monkeypatch):
    # Cause embedder creation to fail
    import valuecell.agents.research_agent.vdb as vdb

    monkeypatch.setattr(
        vdb.model_utils_mod, "get_embedder_for_agent", _raise_unavailable
    )

    assert vdb.get_vector_db() is None


def test_get_knowledge_returns_none_without_embeddings(monkeypatch):
    # Cause embedder creation to fail
    import valuecell.agents.research_agent.vdb as vdb

    monkeypatch.setattr(
        vdb.model_utils_mod, "get_embedder_for_agent", _raise_unavailable
    )

    from valuecell.agents.research_agent.knowledge import get_knowledge

    assert get_knowledge() is None


def test_research_agent_initializes_without_knowledge_when_embeddings_missing(
    monkeypatch,
):
    # Cause embedder creation to fail
    import valuecell.agents.research_agent.vdb as vdb

    monkeypatch.setattr(
        vdb.model_utils_mod, "get_embedder_for_agent", _raise_unavailable
    )

    # Stub model creation to avoid provider requirements
    import valuecell.utils.model as model_utils_mod

    monkeypatch.setattr(model_utils_mod, "get_model_for_agent", lambda name: object())

    # Replace Agent with a dummy capturing params
    import valuecell.agents.research_agent.core as core_mod

    class DummyAgent:
        def __init__(
            self,
            *,
            model,
            instructions,
            expected_output,
            tools,
            knowledge,
            db,
            search_knowledge,
            **kwargs,
        ):
            self.model = model
            self.instructions = instructions
            self.expected_output = expected_output
            self.tools = tools
            self.knowledge = knowledge
            self.db = db
            self.search_knowledge = search_knowledge

    monkeypatch.setattr(core_mod, "Agent", DummyAgent)

    from valuecell.agents.research_agent.core import ResearchAgent

    ra = ResearchAgent()
    assert ra.knowledge_research_agent.knowledge is None
    assert ra.knowledge_research_agent.search_knowledge is False


def test_get_vector_db_success_path(monkeypatch):
    import valuecell.agents.research_agent.vdb as vdb

    # Provide a fake embedder and LanceDb to exercise success path
    monkeypatch.setattr(
        vdb.model_utils_mod, "get_embedder_for_agent", lambda name: object()
    )

    class DummyLanceDb:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(vdb, "LanceDb", DummyLanceDb)

    db = vdb.get_vector_db()
    assert isinstance(db, DummyLanceDb)

    # Exercise failure path in LanceDb constructor to cover exception branch
    class RaisingLanceDb:
        def __init__(self, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(vdb, "LanceDb", RaisingLanceDb)
    assert vdb.get_vector_db() is None


@pytest.mark.asyncio
async def test_insert_functions_noop_when_disabled(monkeypatch, tmp_path):
    # Cause embedder creation to fail
    import valuecell.agents.research_agent.vdb as vdb

    monkeypatch.setattr(
        vdb.model_utils_mod, "get_embedder_for_agent", _raise_unavailable
    )

    from valuecell.agents.research_agent.knowledge import (
        insert_md_file_to_knowledge,
        insert_pdf_file_to_knowledge,
    )

    md_file = tmp_path / "doc.md"
    md_file.write_text("# Title\nBody")

    # Should not raise even though knowledge is disabled
    await insert_md_file_to_knowledge("doc", md_file)
    await insert_pdf_file_to_knowledge("https://example.com/doc.pdf")


@pytest.mark.asyncio
async def test_insert_functions_invoke_add_content_when_enabled(monkeypatch, tmp_path):
    # Patch get_knowledge to return a dummy knowledge object
    from valuecell.agents.research_agent import knowledge as knowledge_mod

    class DummyKnowledge:
        def __init__(self):
            self.calls = []

        async def add_content_async(self, **kwargs):
            self.calls.append(kwargs)

    dummy = DummyKnowledge()
    monkeypatch.setattr(knowledge_mod, "_knowledge_cache", None)
    monkeypatch.setattr(knowledge_mod, "get_knowledge", lambda: dummy)

    from valuecell.agents.research_agent.knowledge import (
        insert_md_file_to_knowledge,
        insert_pdf_file_to_knowledge,
    )

    md_file = tmp_path / "doc2.md"
    md_file.write_text("# Title\nBody")

    await insert_md_file_to_knowledge("doc2", md_file, metadata={"k": "v"})
    await insert_pdf_file_to_knowledge("https://example.com/doc2.pdf")

    # Verify that add_content_async was called for both inserts
    assert len(dummy.calls) == 2
    assert any("path" in c for c in dummy.calls)
    assert any("url" in c for c in dummy.calls)


def test_get_knowledge_success_path_creates_and_caches(monkeypatch):
    from valuecell.agents.research_agent import knowledge as knowledge_mod

    # Use a dummy Knowledge to avoid external dependency behavior
    class DummyKnowledge:
        def __init__(self, *, vector_db, max_results):
            self.vector_db = vector_db
            self.max_results = max_results

    monkeypatch.setattr(knowledge_mod, "Knowledge", DummyKnowledge)
    monkeypatch.setattr(knowledge_mod, "_knowledge_cache", None)
    monkeypatch.setattr(knowledge_mod, "get_vector_db", lambda: object())

    from valuecell.agents.research_agent.knowledge import get_knowledge

    k1 = get_knowledge()
    k2 = get_knowledge()
    assert isinstance(k1, DummyKnowledge)
    assert k1 is k2  # cached


@pytest.mark.asyncio
async def test_stream_yields_events_without_knowledge(monkeypatch):
    # Cause embedder creation to fail and stub model creation
    import valuecell.agents.research_agent.vdb as vdb

    monkeypatch.setattr(
        vdb.model_utils_mod, "get_embedder_for_agent", _raise_unavailable
    )

    import valuecell.utils.model as model_utils_mod

    monkeypatch.setattr(model_utils_mod, "get_model_for_agent", lambda name: object())

    import types as _types
    import valuecell.agents.research_agent.core as core_mod

    class DummyAgent:
        def __init__(self, **kwargs):
            pass

        async def arun(self, *args, **kwargs):
            # Yield three events to exercise stream handling
            yield _types.SimpleNamespace(event="RunContent", content="hello")
            yield _types.SimpleNamespace(
                event="ToolCallStarted",
                tool=_types.SimpleNamespace(tool_call_id="id1", tool_name="foo"),
            )
            yield _types.SimpleNamespace(
                event="ToolCallCompleted",
                tool=_types.SimpleNamespace(
                    result="ok", tool_call_id="id1", tool_name="foo"
                ),
            )

    monkeypatch.setattr(core_mod, "Agent", DummyAgent)
    from valuecell.agents.research_agent.core import ResearchAgent

    ra = ResearchAgent()
    # Iterate the stream to ensure branches are executed
    events = []
    async for ev in ra.stream(
        query="q",
        conversation_id="c",
        task_id="t",
        dependencies={"a": 1},
    ):
        events.append(ev)
    # Should have yielded message chunk, tool start, tool complete, and done
    assert len(events) == 4
