from __future__ import annotations

from typing import Any
import json

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from loguru import logger
from pydantic import BaseModel, Field
from enum import Enum


class NextAction(str, Enum):
    EXIT = "exit"
    REPLAN = "replan"


class CriticDecision(BaseModel):
    next_action: NextAction = Field(description="Either 'exit' or 'replan'")
    reason: str = Field(description="Short rationale for the decision")


async def critic_node(state: dict[str, Any]) -> dict[str, Any]:
    """Use an Agno agent to decide whether to exit or trigger replanning."""
    completed = state.get("completed_tasks") or {}

    # Prepare concise context for the agent
    ok = {tid: res.get("result") for tid, res in completed.items() if res.get("ok")}
    errors = {
        tid: {"error": res.get("error"), "code": res.get("error_code")}
        for tid, res in completed.items()
        if not res.get("ok")
    }

    context = {
        "plan_logic": state.get("plan_logic"),
        "plan": state.get("plan"),
        "ok_results": ok,
        "errors": errors,
    }

    # If nothing ran, default to replan to let planner try again
    if not completed:
        logger.warning("Critic: no completed tasks; defaulting to replan")
        state["_critic_summary"] = {"status": "empty"}
        state["next_action"] = "replan"
        state["next_action_reason"] = (
            "No tasks executed; require planner to produce a plan."
        )
        return state

    system_prompt = (
        "You are a critical reviewer for an execution graph in a financial agent. "
        "Review the completed tasks and errors. Decide whether the current results "
        "are sufficient to exit, or whether the planner should continue with additional "
        "planning to achieve the user's goal. Respond strictly in JSON per the schema."
    )
    user_msg = json.dumps(context, ensure_ascii=False)

    try:
        agent = Agent(
            model=OpenRouter(id="google/gemini-2.5-flash"),
            instructions=[system_prompt],
            markdown=False,
            output_schema=CriticDecision,
            debug_mode=True,
        )
        response = await agent.arun(user_msg)
        decision: CriticDecision = response.content
        state["_critic_summary"] = {
            "ok_count": len(ok),
            "error_count": len(errors),
            "errors": errors,
        }
        action = decision.next_action
        state["next_action"] = action
        state["next_action_reason"] = decision.reason
        logger.info("Critic decided: {a} - {r}", a=action.value, r=decision.reason)
        return state
    except Exception as exc:
        logger.warning("Critic agent error: {err}", err=str(exc))
        # On error, default to replan to allow recovery
        state["_critic_summary"] = {
            "ok_count": len(ok),
            "error_count": len(errors),
            "errors": errors,
        }
        state["next_action"] = NextAction.REPLAN
        state["next_action_reason"] = "Critic error; safe default is to replan."
        return state
