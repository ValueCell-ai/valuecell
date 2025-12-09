from __future__ import annotations

from typing import Any, Callable

from langchain_core.callbacks import adispatch_custom_event
from loguru import logger
from pydantic import BaseModel

from ..models import ExecutorResult
from ..state import AgentState
from ..tool_registry import registry

_TOOLS_REGISTERED = False


def ensure_default_tools_registered() -> None:
    global _TOOLS_REGISTERED
    if _TOOLS_REGISTERED:
        return

    _register_tool("market_data", _tool_market_data)
    _register_tool("screen", _tool_screen)
    _register_tool("backtest", _tool_backtest)

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


async def executor_node(state: AgentState, task: dict[str, Any]) -> dict[str, Any]:
    """Execute a single task and return execution summary for history.

    Returns:
    - completed_tasks: {task_id: ExecutorResult}
    - execution_history: [concise summary string]
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

        # Generate concise summary for execution history
        summary = _generate_summary(task_id, tool, args, result)
    except Exception as exc:
        logger.warning("Executor error: {err}", err=str(exc))
        exec_res = ExecutorResult(
            task_id=task_id, ok=False, error=str(exc), error_code="ERR_EXEC"
        )
        summary = f"Task {task_id} ({tool}) failed: {str(exc)[:50]}"

    await _emit_progress(95, "Finishing")

    # Return delta for completed_tasks and execution_history
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
    return {
        "completed_tasks": completed_delta,
        "execution_history": [summary],
    }


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


def _generate_summary(task_id: str, tool: str, args: dict, result: Any) -> str:
    """Generate a concise summary for execution_history (token-efficient).

    Example: "Task t1 (market_data): Fetched 3 symbols"
    """
    # Extract key info based on tool type
    if tool == "market_data":
        symbols = args.get("symbols") or result.get("symbols", [])
        return f"Task {task_id} (market_data): Fetched {len(symbols)} symbols"
    elif tool == "screen":
        risk = args.get("risk") or result.get("risk", "Unknown")
        count = len(result.get("table", [])) if isinstance(result, dict) else 0
        return f"Task {task_id} (screen): Risk={risk}, {count} candidates"
    elif tool == "backtest":
        symbols = args.get("symbols") or result.get("symbols", [])
        ret_pct = result.get("return_pct", 0) if isinstance(result, dict) else 0
        return f"Task {task_id} (backtest): {len(symbols)} symbols, return={ret_pct}%"
    else:
        # Generic fallback
        return f"Task {task_id} ({tool}): completed"


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


ensure_default_tools_registered()
