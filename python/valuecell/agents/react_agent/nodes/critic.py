from __future__ import annotations

import json
from enum import Enum
from typing import Any

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from loguru import logger
from pydantic import BaseModel, Field


class NextAction(str, Enum):
    EXIT = "exit"
    REPLAN = "replan"


class CriticDecision(BaseModel):
    """Gatekeeper decision for iterative batch planning."""

    approved: bool = Field(
        description="True if goal is fully satisfied, False otherwise"
    )
    reason: str = Field(description="Short rationale for the decision")
    feedback: str | None = Field(
        default=None,
        description="Specific feedback for Planner if rejected (what is missing)",
    )


async def critic_node(state: dict[str, Any]) -> dict[str, Any]:
    """Gatekeeper: Verify if user's goal is fully satisfied.

    Only runs when Planner sets is_final=True.
    - If approved: Return next_action="exit"
    - If rejected: Return critique_feedback and next_action="replan"
    """
    user_profile = state.get("user_profile") or {}
    execution_history = state.get("execution_history") or []
    is_final = state.get("is_final", False)

    # Safety check: Critic should only run when planner claims done
    if not is_final:
        logger.warning("Critic invoked but is_final=False; defaulting to replan")
        return {
            "next_action": NextAction.REPLAN,
            "critique_feedback": "Planner has not completed the workflow.",
        }

    history_text = "\n".join(execution_history) if execution_history else "(Empty)"

    system_prompt = (
        "You are a gatekeeper critic for an iterative financial planning system.\n\n"
        "**Your Role**: Compare the User's Request with the Execution History.\n"
        "- If the goal is fully satisfied, approve (approved=True).\n"
        "- If something is missing or incomplete, reject (approved=False) and provide specific feedback.\n\n"
        "**Decision Criteria**:\n"
        "1. All requested tasks completed successfully.\n"
        "2. No critical errors that prevent goal satisfaction.\n"
        "3. Results align with user's intent.\n"
        "4. **Synthesis Phase**: If sufficient research/data-gathering tasks are complete to answer the user's request, "
        "APPROVE the plan. The system will synthesize the final response from the execution history. "
        "Do NOT demand an explicit 'generate_report' or 'create_plan' task when the necessary data is already available.\n"
    )

    context = {
        "user_request": user_profile,
        "execution_history": history_text,
    }
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

        if decision.approved:
            logger.info("Critic APPROVED: {r}", r=decision.reason)
            return {
                "next_action": NextAction.EXIT,
                "_critic_summary": {"approved": True, "reason": decision.reason},
            }
        else:
            logger.info("Critic REJECTED: {r}", r=decision.reason)
            return {
                "next_action": NextAction.REPLAN,
                "critique_feedback": decision.feedback or decision.reason,
                "is_final": False,  # Reset is_final to allow re-planning
                "_critic_summary": {"approved": False, "reason": decision.reason},
            }
    except Exception as exc:
        logger.warning("Critic agent error: {err}", err=str(exc))
        # On error, default to replan for safety
        return {
            "next_action": NextAction.REPLAN,
            "critique_feedback": f"Critic error: {str(exc)[:100]}",
            "is_final": False,
        }
