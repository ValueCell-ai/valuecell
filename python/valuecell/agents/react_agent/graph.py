from __future__ import annotations

import uuid
from typing import Any

from langchain_core.runnables import RunnableConfig

from .nodes.critic import critic_node
from .nodes.executor import executor_node
from .nodes.inquirer import inquirer_node
from .nodes.planner import planner_node
from .nodes.summarizer import summarizer_node
from .state import AgentState


def _route_after_planner(state: AgentState):
    """Route after planner based on is_final flag.

    - If is_final=True: Route to critic for verification.
    - If plan has tasks: Route to executor via Send.
    - Otherwise: Route to critic as safety fallback.
    """
    try:
        from langgraph.types import Send  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "LangGraph is required for the orchestrator. Install 'langgraph'."
        ) from exc

    is_final = state.get("is_final", False)
    plan = state.get("plan") or []

    # If planner claims done, verify with critic
    if is_final:
        return "critic"

    # If planner produced tasks, execute them in parallel
    if plan:
        return [Send("executor", {"task": t}) for t in plan]

    # Safety fallback: no tasks and not final -> go to critic
    return "critic"


async def _executor_entry(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """Entry adapter for executor: expects a `task` injected via Send().

    Args:
        state: Agent state containing task data
        config: RunnableConfig injected by LangGraph
    """
    task = state.get("task") or {}
    return await executor_node(state, task, config)


def build_app() -> Any:
    """Build and compile the LangGraph StateGraph with memory checkpointer."""
    # Local imports to keep module import safe if langgraph isn't installed yet
    try:
        from langgraph.checkpoint.memory import MemorySaver  # type: ignore
        from langgraph.graph import END, START, StateGraph  # type: ignore
    except Exception as exc:  # pragma: no cover - import-time guard
        raise RuntimeError(
            "LangGraph is required for the orchestrator. Install 'langgraph'."
        ) from exc

    graph = StateGraph(AgentState)

    graph.add_node("inquirer", inquirer_node)
    graph.add_node("planner", planner_node)
    graph.add_node("executor", _executor_entry)
    graph.add_node("critic", critic_node)
    graph.add_node("summarizer", summarizer_node)

    graph.add_edge(START, "inquirer")

    def _route_after_inquirer(st: AgentState) -> str:
        # After refactor: Inquirer now writes `current_intent` (natural language string)
        # Route to planner when an intent is present, otherwise wait/end.
        return "plan" if st.get("current_intent") else "wait"

    graph.add_conditional_edges(
        "inquirer", _route_after_inquirer, {"plan": "planner", "wait": END}
    )

    # After planning, route based on is_final and plan content
    graph.add_conditional_edges("planner", _route_after_planner, {"critic": "critic"})

    # After executor completion, go back to planner for next iteration
    graph.add_edge("executor", "planner")

    def _route_after_critic(st: AgentState) -> str:
        na = st.get("next_action")
        val = getattr(na, "value", na)
        v = str(val).lower() if val is not None else "exit"
        if v == "replan":
            # Clear is_final flag to allow fresh planning cycle
            st["is_final"] = False
            return "replan"
        # Critic approved: route to summarizer for final report
        return "summarize"

    graph.add_conditional_edges(
        "critic", _route_after_critic, {"replan": "planner", "summarize": "summarizer"}
    )

    # Summarizer generates final report, then END
    graph.add_edge("summarizer", END)

    memory = MemorySaver()
    app = graph.compile(checkpointer=memory)
    return app


# Lazy singleton accessor to avoid import-time dependency failures
_APP_SINGLETON: Any | None = None


def get_app() -> Any:
    global _APP_SINGLETON
    if _APP_SINGLETON is None:
        _APP_SINGLETON = build_app()
    return _APP_SINGLETON


# Backwards-compat: expose `app` when available, else None until build
app: Any | None = None


async def astream_events(initial_state: dict[str, Any], config: dict | None = None):
    """Stream LangGraph events (v2) from the compiled app.

    Usage: async for ev in astream_events(state): ...
    """
    application = get_app()
    # Ensure checkpointer receives required configurable keys.
    cfg: dict = dict(config or {})
    cfg.setdefault("thread_id", "main")
    cfg.setdefault("checkpoint_ns", "react_agent")
    cfg.setdefault("checkpoint_id", str(uuid.uuid4()))

    async for ev in application.astream_events(initial_state, config=cfg, version="v2"):
        yield ev
