from __future__ import annotations

import json
from typing import Any

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from loguru import logger

from ..models import ExecutionPlan, FinancialIntent, PlannedTask, Task
from ..tool_registry import registry


async def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    """Iterative batch planner: generates the IMMEDIATE next batch of tasks.

    Looks at execution_history to understand what has been done,
    critique_feedback to fix any issues, and focus_topic to prioritize research focus.

    Two Modes:
    - General Scan: Profile fully explored (focus_topic=None) -> Research all assets
    - Surgical: Specific question (focus_topic=set) -> Research only relevant topics, ignore unrelated assets
    """
    profile_dict = state.get("user_profile") or {}
    profile = (
        FinancialIntent.model_validate(profile_dict)
        if profile_dict
        else FinancialIntent()
    )

    execution_history = state.get("execution_history") or []
    critique_feedback = state.get("critique_feedback")
    focus_topic = state.get("focus_topic")

    logger.info(
        "Planner start: profile={p}, history_len={h}, focus={f}",
        p=profile.model_dump(),
        h=len(execution_history),
        f=focus_topic or "General",
    )

    # Build iterative planning prompt
    tool_context = registry.get_prompt_context()

    history_text = (
        "\n\n".join(execution_history) if execution_history else "(No history yet)"
    )
    feedback_text = (
        f"\n\n**Critic Feedback**: {critique_feedback}" if critique_feedback else ""
    )

    # Dynamic mode instruction based on focus_topic
    if focus_topic:
        mode_instruction = (
            f"🎯 **SURGICAL MODE** 🎯\n"
            f'**Current User Question**: "{focus_topic}"\n'
            "**Strategy**:\n"
            "1. **FOCUS ONLY**: Research ONLY what's needed to answer this question.\n"
            "2. **IGNORE IRRELEVANT ASSETS**: If the user has [AAPL, MSFT] but asks 'Tell me about MSFT earnings', "
            "do NOT also fetch AAPL data.\n"
            "3. **VERIFY FRESHNESS**: Check if the Execution History has *recent, specific* data for this question. "
            "If the history only has generic data or is from a previous turn, GENERATE NEW TASKS.\n"
            "4. **Be Surgical**: Don't over-fetch. Narrow your scope to the exact question.\n"
        )
    else:
        mode_instruction = (
            "🌍 **GENERAL SCAN MODE** 🌍\n"
            "**Strategy**:\n"
            "1. **COMPREHENSIVE**: Ensure ALL assets in the User Profile are researched.\n"
            "2. **BALANCED**: Generate tasks that cover all dimensions (price, news, fundamentals) for each asset.\n"
        )

    system_prompt_text = (
        "You are an iterative financial planning agent.\n\n"
        f"{mode_instruction}\n\n"
        "**Your Role**: Decide the **IMMEDIATE next batch** of tasks.\n\n"
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
        f"**Execution History**:\n{history_text}{feedback_text}\n"
    )

    user_profile_json = json.dumps(profile.model_dump(), ensure_ascii=False)
    user_msg = f"User Request Context: {user_profile_json}"

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
            )
        )

    _validate_plan(tasks)

    # Clear critique_feedback after consuming it
    return {
        "plan": [t.model_dump() for t in tasks],
        "plan_logic": strategy_update,  # For backwards compatibility
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
