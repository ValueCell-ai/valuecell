from __future__ import annotations

import json
from typing import Any, Dict, List

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from loguru import logger
from pydantic import BaseModel, Field

from ..models import FinancialIntent, Task
from ..tool_registry import registry

ARG_VAL_TYPES = str | float | int


class PlannedTask(BaseModel):
    id: str = Field(description="Unique task identifier, e.g., 't1'")
    tool_id: str = Field(description="The EXACT tool_id from the available tool list")
    tool_args: Dict[str, ARG_VAL_TYPES | list[ARG_VAL_TYPES]] = Field(
        default_factory=dict,
        description="The arguments to pass to the tool. "
        "MUST strictly match the 'Arguments' list in the tool definition. "
        "DO NOT leave empty if the tool requires parameters. "
        "Example: {'symbol': 'AAPL', 'period': '1y'}",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Task IDs that must complete BEFORE this task starts",
    )
    description: str = Field(description="Short description for logs")


class ExecutionPlan(BaseModel):
    logic: str = Field(description="Reasoning behind the plan")
    tasks: List[PlannedTask] = Field(description="Directed acyclic graph of tasks")


async def planner_node(state: dict[str, Any]) -> dict[str, Any]:
    profile_dict = state.get("user_profile") or {}
    profile = (
        FinancialIntent.model_validate(profile_dict)
        if profile_dict
        else FinancialIntent()
    )

    logger.info("Planner start: profile={p}", p=profile.model_dump())

    # Build prompt for Agno Agent planning
    tool_context = registry.get_prompt_context()
    system_prompt_text = (
        "You are a Financial Systems Architect. Break down the user's financial request into a specific execution plan.\n\n"
        "Use ONLY these available tools:\n" + tool_context + "\n\n"
        "Planning Rules:\n"
        "1. Dependency Management:\n"
        "   - If a task needs data from a previous task, add the previous task's ID to dependencies.\n"
        "   - If tasks are independent, keep dependencies empty for parallel execution.\n"
        "2. Argument Precision:\n"
        "   - Ensure tool_args strictly match in the tool list.\n"
        "   - Do not invent arguments.\n"
        "3. Logical Flow:\n"
        "   - Typically: Fetch Data -> Analyze -> Summarize.\n"
        "4. Output Constraint:\n"
        "   - tool_args must contain only literal values or values from the user profile.\n"
        "   - Do not reference other task outputs (e.g., 't2.output...') inside tool_args.\n"
        "   - Use dependencies to express ordering; do not encode dataflow by string placeholders.\n"
    )

    user_profile_json = json.dumps(profile.model_dump(), ensure_ascii=False)
    user_msg = f"User Request Context: {user_profile_json}"

    planned_tasks = []
    plan_logic = ""

    # TODO: add retry with backoff
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
        plan_logic = plan_obj.logic
        logger.info(
            "Planner Agno produced {} tasks, reason: `{}`, all: {}",
            len(planned_tasks),
            plan_logic,
            planned_tasks,
        )
    except Exception as exc:
        logger.warning("Planner Agno error: {err}", err=str(exc))
        # Do not fall back to a deterministic plan here; return an empty plan
        # so higher-level orchestration can decide how to proceed.
        planned_tasks = []
        plan_logic = "No plan produced due to Agno/LLM error."

    # Validate tool registration and convert to internal Task models
    tasks: list[Task] = []
    available = {tool.tool_id for tool in registry.list_tools()}
    for pt in planned_tasks:
        if pt.tool_id not in available:
            raise ValueError(f"Planner produced unknown tool_id: {pt.tool_id}")

        tasks.append(
            Task(
                id=pt.id,
                tool_name=pt.tool_id,  # our Task's tool_name equals registry tool_id
                tool_args=pt.tool_args,
                dependencies=pt.dependencies,
            )
        )

    _validate_plan(tasks)

    state["plan"] = [t.model_dump() for t in tasks]
    state["plan_logic"] = plan_logic
    logger.info("Planner completed: {n} tasks", n=len(tasks))
    return state


def _validate_plan(tasks: list[Task]) -> None:
    ids = set()
    for t in tasks:
        if t.id in ids:
            raise ValueError(f"Duplicate task id: {t.id}")
        ids.add(t.id)
    valid_ids = ids.copy()
    for t in tasks:
        for dep in t.dependencies:
            if dep not in valid_ids:
                raise ValueError(f"Missing dependency '{dep}' for task '{t.id}'")
