from __future__ import annotations

from typing import Any

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from langchain_core.messages import AIMessage, HumanMessage
from loguru import logger

from ..models import ExecutionPlan, PlannedTask, Task
from ..tool_registry import registry


async def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    """Iterative batch planner: generates the IMMEDIATE next batch of tasks.

    Uses natural language current_intent as the primary instruction.
    Looks at execution_history to understand what has been done,
    and critique_feedback to fix any issues.
    """
    current_intent = state.get("current_intent") or "General financial analysis"
    execution_history = state.get("execution_history") or []
    critique_feedback = state.get("critique_feedback")

    logger.info(
        "Planner start: intent='{i}', history_len={h}",
        i=current_intent,
        h=len(execution_history),
    )

    # Build iterative planning prompt
    tool_context = registry.get_prompt_context()

    history_text = (
        "\n\n".join(execution_history) if execution_history else "(No history yet)"
    )
    feedback_text = (
        f"\n\n**Critic Feedback**: {critique_feedback}" if critique_feedback else ""
    )

    # 1. Extract recent conversation (last Assistant + User messages)
    messages_list = state.get("messages", []) or []
    recent_msgs: list[tuple[str, str]] = []
    for m in messages_list:
        # support both Message objects and plain dicts
        if isinstance(m, (HumanMessage, AIMessage)):
            role = "User" if isinstance(m, HumanMessage) else "Assistant"
            recent_msgs.append((role, m.content))

    # Keep only the last 3 relevant messages (AI/User pairs preferred)
    recent_msgs = recent_msgs[-3:]
    if recent_msgs:
        context_str = "\n\n".join(f"{r}: {c}" for r, c in recent_msgs)
        recent_context_text = f"**RECENT CONVERSATION**:\n{context_str}\n(Use this context to resolve references. If user asks about a phrase mentioned by the Assistant, target your research to verify or expand on that claim.)\n\n"
    else:
        recent_context_text = ""

    system_prompt_text = (
        "You are an iterative financial planning agent.\n\n"
        f"**CURRENT GOAL**: {current_intent}\n\n"
        "**Your Role**: Decide the **IMMEDIATE next batch** of tasks to achieve this goal.\n\n"
        f"**Available Tools**:\n{tool_context}\n\n"
        "**Planning Rules**:\n"
        "1. **Iterative Planning**: Plan only the next step(s), not the entire workflow.\n"
        "2. **Context Awareness**: Read the Execution History carefully. Don't repeat completed work.\n"
        "3. **Relevance & Freshness**:\n"
        "   - If user asks 'latest', 'today', or 'recent news' -> Check if history data is fresh (from current turn).\n"
        "   - If history only has old/generic data from previous turns, GENERATE NEW TASKS.\n"
        "   - Be skeptical of old data. When in doubt, fetch fresh data rather than stale data.\n"
        "4. **Concrete Arguments**: tool_args must contain only literal values (no placeholders).\n"
        "5. **Parallel Execution**: Tasks in the same batch run concurrently.\n"
        "6. **Completion Signal**: Return `tasks=[]` and `is_final=True` only when the goal is fully satisfied.\n"
        "7. **Critique Integration**: If Critic Feedback is present, address the issues mentioned.\n\n"
        f"{recent_context_text}**Execution History**:\n{history_text}{feedback_text}\n"
    )

    user_msg = f"Current Goal: {current_intent}"

    is_final = False
    strategy_update = ""
    # TODO: organize plan like a TODO list
    planned_tasks: list[PlannedTask] = []

    try:
        agent = Agent(
            model=OpenRouter(id="google/gemini-2.5-flash"),
            instructions=[system_prompt_text],
            markdown=False,
            output_schema=ExecutionPlan,
            debug_mode=True,
        )
        response = await agent.arun(user_msg)
        plan_obj: ExecutionPlan = response.content

        planned_tasks = plan_obj.tasks
        strategy_update = plan_obj.strategy_update
        is_final = plan_obj.is_final

        logger.info(
            "Planner produced {} tasks, is_final={}, strategy: {}",
            len(planned_tasks),
            is_final,
            strategy_update,
        )
    except Exception as exc:
        logger.warning("Planner Agno error: {err}", err=str(exc))
        planned_tasks = []
        strategy_update = "No plan produced due to Agno/LLM error."
        is_final = False

    # Validate tool registration and convert to internal Task models
    tasks: list[Task] = []
    available = {tool.tool_id for tool in registry.list_tools()}
    for pt in planned_tasks:
        if pt.tool_id not in available:
            raise ValueError(f"Planner produced unknown tool_id: {pt.tool_id}")

        tasks.append(
            Task(
                id=pt.id,
                tool_name=pt.tool_id,
                tool_args=pt.tool_args,
                description=pt.description or "No description provided by planner",
            )
        )

    _validate_plan(tasks)

    # Clear critique_feedback after consuming it
    return {
        "plan": [t.model_dump() for t in tasks],
        "strategy_update": strategy_update,
        "is_final": is_final,
        "critique_feedback": None,  # Clear after consuming
    }


def _validate_plan(tasks: list[Task]) -> None:
    """Basic validation: check for duplicate task IDs."""
    ids = set()
    for t in tasks:
        if t.id in ids:
            raise ValueError(f"Duplicate task id: {t.id}")
        ids.add(t.id)
