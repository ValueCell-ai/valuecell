"""Task execution context for tool runtime."""

from typing import Any, Optional

from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import RunnableConfig


class TaskContext:
    """Context object passed to tools, encapsulating task metadata and event dispatch.

    This context binds a task_id with the LangGraph config, allowing tools to
    emit progress events and artifacts without polluting their parameter schemas.

    Example:
        ```python
        async def my_tool(symbol: str, context: Optional[TaskContext] = None) -> str:
            if context:
                await context.emit_progress("Fetching data...")
            # ... tool logic ...
            return result
        ```
    """

    def __init__(self, task_id: str, config: RunnableConfig):
        """Initialize task context.

        Args:
            task_id: Unique identifier for the current task
            config: LangGraph RunnableConfig for event dispatch
        """
        self.task_id = task_id
        self._config = config

    async def emit_progress(
        self,
        msg: str,
        step: Optional[str] = None,
    ) -> None:
        """Emit a progress event linked to this specific task.

        Args:
            msg: Human-readable progress message
            percent: Optional completion percentage (0-100)
            step: Optional step identifier (e.g., "fetching_income")
        """
        if not msg.endswith("\n"):
            msg += "\n"

        payload = {
            "type": "progress",
            "task_id": self.task_id,
            "msg": msg,
            "step": step,
        }
        await adispatch_custom_event("tool_event", payload, config=self._config)

    async def emit_artifact(self, artifact_type: str, content: Any) -> None:
        """Emit an intermediate artifact (e.g., a chart or table).

        Args:
            artifact_type: Type identifier for the artifact (e.g., "chart", "table")
            content: Artifact content (JSON-serializable)
        """
        payload = {
            "type": "artifact",
            "task_id": self.task_id,
            "artifact_type": artifact_type,
            "content": content,
        }
        await adispatch_custom_event("tool_event", payload, config=self._config)
