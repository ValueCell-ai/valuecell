from __future__ import annotations

from typing import Any

from loguru import logger


def scheduler_node(state: dict[str, Any]) -> dict[str, Any]:
    """Compute runnable tasks and detect completion/deadlock.

    Returns state with `_runnable` list of task dicts, `_schedule_status`, and
    marks newly runnable tasks as `_dispatched` to prevent duplicate scheduling.
    """
    plan: list[dict] = state.get("plan") or []
    completed: dict = state.get("completed_tasks") or {}
    dispatched: dict = state.get("_dispatched") or {}

    logger.info(
        "Scheduler start: plan={p_len} completed={c_len} dispatched={d_len}",
        p_len=len(plan),
        c_len=len(completed),
        d_len=len(dispatched),
    )

    remaining = [t for t in plan if t.get("id") not in completed]
    if not remaining:
        state["_schedule_status"] = "complete"
        logger.info("Scheduler: plan complete")
        return state

    runnable: list[dict] = []
    completed_ids = set(completed.keys())
    dispatched_ids = set(dispatched.keys())

    for t in remaining:
        task_id = t.get("id")
        # Skip if already dispatched (prevents duplicate scheduling)
        if task_id in dispatched_ids:
            continue
        deps = set(t.get("dependencies") or [])
        if deps.issubset(completed_ids):
            runnable.append(t)

    if runnable:
        # Mark newly runnable tasks as dispatched
        new_dispatched = {t.get("id"): True for t in runnable if t.get("id")}
        state["_runnable"] = runnable
        state["_schedule_status"] = "runnable"
        state["_dispatched"] = {**dispatched, **new_dispatched}
        logger.info("Scheduler: {n} tasks runnable (newly dispatched)", n=len(runnable))
        return state

    # Deadlock or waiting: remaining tasks but none runnable (all may be dispatched)
    if any(t.get("id") in dispatched_ids for t in remaining):
        # Some tasks are dispatched but not yet completed - wait
        state["_schedule_status"] = "waiting"
        logger.info("Scheduler: waiting for dispatched tasks to complete")
    else:
        # True deadlock: tasks exist but can't be dispatched
        state["_schedule_status"] = "deadlock"
        state["_deadlock_reason"] = "No tasks runnable; unmet dependencies"
        logger.warning("Scheduler: deadlock detected")
    return state
