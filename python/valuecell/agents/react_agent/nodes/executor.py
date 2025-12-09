from __future__ import annotations

from typing import Any, Callable

from langchain_core.callbacks import adispatch_custom_event
from loguru import logger
from pydantic import BaseModel

from ..models import ExecutorResult
from ..tool_registry import registry


_TOOLS_REGISTERED = False


def ensure_default_tools_registered() -> None:
    global _TOOLS_REGISTERED
    if _TOOLS_REGISTERED:
        return

    _register_tool("market_data", _tool_market_data)
    _register_tool("screen", _tool_screen)
    _register_tool("backtest", _tool_backtest)
    _register_tool("summary", _tool_summary)

    _TOOLS_REGISTERED = True


def _register_tool(
    tool_id: str,
    func: Callable[..., Any],
    description: str | None = None,
    *,
    args_schema: type[BaseModel] | None = None,
) -> None:
    try:
        registry.register(
            tool_id,
            func,
            description,
            args_schema=args_schema,
        )
    except ValueError:
        # Already registered; ignore to keep idempotent
        pass


async def executor_node(state: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    """Execute a single task in a stateless manner.

    Selects the tool by `task["tool_name"]` and returns updated state with
    `completed_tasks[task_id]`. Artifacts are not persisted in state at this layer.
    """
    task_id = task.get("id") or ""
    tool = task.get("tool_name") or ""
    args = task.get("tool_args") or {}

    logger.info("Executor start: task_id={tid} tool={tool}", tid=task_id, tool=tool)

    # Idempotency guard: if this task is already completed, no-op
    completed_snapshot = (state.get("completed_tasks") or {}).keys()
    if task_id and task_id in completed_snapshot:
        logger.info("Executor skip (already completed): task_id={tid}", tid=task_id)
        return {}
    await _emit_progress(5, "Starting")

    try:
        runtime_args = {"state": state}
        result = await registry.execute(tool, args, runtime_args=runtime_args)
        exec_res = ExecutorResult(task_id=task_id, ok=True, result=result)
    except Exception as exc:
        logger.warning("Executor error: {err}", err=str(exc))
        exec_res = ExecutorResult(
            task_id=task_id, ok=False, error=str(exc), error_code="ERR_EXEC"
        )

    await _emit_progress(95, "Finishing")

    # Return only the delta for completed_tasks to enable safe parallel merging
    completed_delta = {task_id: exec_res.model_dump()}

    # Emit a task-done event so the LangGraph event stream clearly shows completion
    try:
        await adispatch_custom_event(
            "agno_event",
            {"type": "task_done", "task_id": task_id, "ok": exec_res.ok},
        )
    except Exception:
        pass

    await _emit_progress(100, "Done")
    return {"completed_tasks": completed_delta}


async def _emit_progress(percent: int, msg: str) -> None:
    try:
        payload = {
            "type": "progress",
            "payload": {"percent": percent, "msg": msg},
            "node": "executor",
        }
        await adispatch_custom_event("agno_event", payload)
    except Exception:
        # progress emission is non-critical
        pass


async def _tool_market_data(symbols: list[str] | None = None) -> dict[str, Any]:
    await _emit_progress(15, "Fetching market data")
    symbols = symbols or ["AAPL", "MSFT", "GOOGL"]
    # Placeholder: return mock stats; real integration later
    data = {"symbols": symbols, "stats": {"count": len(symbols)}}
    await _emit_progress(40, "Market data fetched")
    return data


async def _tool_screen(risk: str | None = None) -> dict[str, Any]:
    await _emit_progress(50, "Screening candidates")
    risk = risk or "Medium"
    table = (
        [{"symbol": "AAPL", "score": 0.8}, {"symbol": "MSFT", "score": 0.78}]
        if risk != "High"
        else [{"symbol": "TSLA", "score": 0.82}]
    )
    await _emit_progress(70, "Screening done")
    return {"risk": risk, "table": table}


async def _tool_backtest(
    symbols: list[str] | None = None, horizon_days: int = 90
) -> dict[str, Any]:
    await _emit_progress(75, "Backtesting")
    horizon = int(horizon_days or 90)
    # Placeholder: simple buy-hold mock result
    result = {
        "symbols": symbols or [],
        "horizon_days": horizon,
        "return_pct": 5.2,
    }
    await _emit_progress(85, "Backtest done")
    return result


async def _tool_summary(*, state: dict[str, Any]) -> dict[str, Any]:
    await _emit_progress(88, "Summarizing")
    completed = state.get("completed_tasks") or {}
    summary = {
        "tasks": list(completed.keys()),
        "ok_count": sum(1 for v in completed.values() if v.get("ok")),
    }
    await _emit_progress(92, "Summary done")
    return summary


ensure_default_tools_registered()
