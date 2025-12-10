from __future__ import annotations

from typing import Any, Callable

from langchain_core.callbacks import adispatch_custom_event
from loguru import logger
from pydantic import BaseModel

from ...research_agent.sources import (
    search_crypto_people,
    search_crypto_projects,
    search_crypto_vcs,
    web_search,
)
from ..models import ExecutorResult
from ..state import AgentState
from ..tool_registry import registry
from ..tools.research import research

_TOOLS_REGISTERED = False


def ensure_default_tools_registered() -> None:
    global _TOOLS_REGISTERED
    if _TOOLS_REGISTERED:
        return

    _register_tool("research", research)
    _register_tool("search_crypto_people", search_crypto_people)
    _register_tool("search_crypto_projects", search_crypto_projects)
    _register_tool("search_crypto_vcs", search_crypto_vcs)
    _register_tool("web_search", web_search)

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
    result_preview = str(result)
    if len(result_preview) > 100:
        result_preview = result_preview[:100] + "..."
    return f"Task {task_id} ({tool} with args {args}): completed. Result preview: {result_preview}"


ensure_default_tools_registered()
