from __future__ import annotations

from typing import Any
import uuid

from .nodes.critic import critic_node
from .nodes.executor import executor_node
from .nodes.inquirer import inquirer_node
from .nodes.planner import planner_node
from .nodes.scheduler import scheduler_node
from .state import AgentState


def _route_after_scheduler(state: dict[str, Any]):
    """Route after scheduler node based on _schedule_status.

    - Returns list[Send("executor", {"task": t})] when runnable tasks exist.
    - Returns "critic" when plan is complete or deadlocked.
    - Returns END when waiting for dispatched tasks.
    """
    try:
        from langgraph.types import Send  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "LangGraph is required for the orchestrator. Install 'langgraph'."
        ) from exc

    status = state.get("_schedule_status")
    if status == "runnable":
        runnable = state.get("_runnable") or []
        if runnable:
            return [Send("executor", {"task": t}) for t in runnable]
    if status == "waiting":
        # Tasks are dispatched but not completed; return empty to no-op
        return []
    if status in {"complete", "deadlock"}:
        return "critic"
    return "critic"


async def _executor_entry(state: dict[str, Any]) -> dict[str, Any]:
    """Entry adapter for executor: expects a `task` injected via Send()."""
    task = state.get("task") or {}
    return await executor_node(state, task)


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
    graph.add_node("scheduler", scheduler_node)
    graph.add_node("executor", _executor_entry)
    graph.add_node("critic", critic_node)

    graph.add_edge(START, "inquirer")

    def _route_after_inquirer(st: dict[str, Any]) -> str:
        return "plan" if st.get("user_profile") else "wait"

    graph.add_conditional_edges(
        "inquirer", _route_after_inquirer, {"plan": "planner", "wait": END}
    )
    
    # After planning, go to scheduler
    graph.add_edge("planner", "scheduler")
    
    # After executor completion, go back to scheduler to check for next wave
    graph.add_edge("executor", "scheduler")
    
    # After scheduler node, route based on status
    graph.add_conditional_edges("scheduler", _route_after_scheduler, {"critic": "critic"})

    def _route_after_critic(st: dict[str, Any]) -> str:
        na = st.get("next_action")
        val = getattr(na, "value", na)
        v = str(val).lower() if val is not None else "exit"
        if v == "replan":
            # Clear plan/schedule to allow fresh planning cycle
            st.pop("plan", None)
            st.pop("_schedule_status", None)
            st.pop("_runnable", None)
            st.pop("_dispatched", None)  # Clear dispatch tracking for fresh plan
            return "replan"
        return "end"

    graph.add_conditional_edges(
        "critic", _route_after_critic, {"replan": "planner", "end": END}
    )

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
