from __future__ import annotations

from typing import Any

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from loguru import logger

from ..models import FinancialIntent, InquirerDecision


async def inquirer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Use LLM-driven structured output to extract financial intent from conversation.

    Inputs: state["messages"], state["inquirer_turns"].
    Outputs: updated state with user_profile (if COMPLETE) or follow-up question (if INCOMPLETE).
    """
    messages = state.get("messages") or []
    turns = int(state.get("inquirer_turns") or 0)

    logger.info("Inquirer node start: turns={turns}", turns=turns)

    is_final_turn = turns >= 2

    system_prompt = (
        "You are a professional Financial Advisor Assistant. "
        "Your goal is to extract structured investment requirements from the conversation.\n\n"
        "# REQUIRED INFORMATION:\n"
        "1. **Asset/Target**: What does the user want to buy? (e.g., AAPL, Tech Stocks, Gold)\n"
        "2. **Risk Tolerance**: Low, Medium, or High.\n\n"
        "# INFERENCE RULES:\n"
        "- If user says 'safe', 'stable', 'conservative': infer Risk='Low'.\n"
        "- If user says 'growth', 'aggressive', 'dynamic': infer Risk='High'.\n"
        "- If user says 'balanced': infer Risk='Medium'.\n"
        "- Analyze conversation history to infer intent.\n\n"
        f"# CURRENT STATUS:\n"
        f"- Interaction Turn: {turns}\n"
        f"- Max Turns Allowed: 2\n\n"
    )

    if not is_final_turn:
        system_prompt += (
            "# INSTRUCTION:\n"
            "If essential information (risk preference) is MISSING, set status='INCOMPLETE' "
            "and ask a natural, concise follow-up question. "
            "Do NOT assume or infer defaults yet."
        )
    else:
        system_prompt += (
            "# CRITICAL INSTRUCTION (MAX TURNS REACHED):\n"
            "You have reached the maximum interaction limit. "
            "Do NOT ask more questions. Instead: "
            "Set status='COMPLETE' and infer reasonable defaults for any missing fields. "
            "(e.g., Risk='Medium' if unspecified). "
            "The response_to_user should confirm the inferred values."
        )

    # Build user message from conversation history
    message_strs = []
    for m in messages:
        if hasattr(m, "content"):
            message_strs.append(m.content)
        else:
            message_strs.append(str(m))
    user_msg = "Conversation history:\n" + "\n".join(message_strs)

    try:
        agent = Agent(
            model=OpenRouter(id="google/gemini-2.5-flash"),
            instructions=[system_prompt],
            markdown=False,
            output_schema=InquirerDecision,
            debug_mode=True,
        )
        response = await agent.arun(user_msg)
        decision: InquirerDecision = response.content

        logger.info(
            "Inquirer decision: status={s} reason={r}",
            s=decision.status,
            r=decision.reasoning,
        )

        if decision.status == "INCOMPLETE":
            # Increment turns and ask the follow-up question
            new_turns = turns + 1
            state["inquirer_turns"] = new_turns
            state["user_profile"] = None
            state["_inquirer_question"] = decision.response_to_user
            state.setdefault("completed_tasks", {})
            return state
        else:  # COMPLETE
            # Store profile and reset turns for next session
            state["user_profile"] = decision.intent.model_dump()
            state["inquirer_turns"] = 0
            logger.info(
                "Inquirer completed: profile={p} reason={r}",
                p=state["user_profile"],
                r=decision.reasoning,
            )
            return state

    except Exception as exc:
        logger.warning("Inquirer LLM error: {err}", err=str(exc))
        # Graceful fallback: if error on final turn, default to Medium risk
        if is_final_turn:
            state["user_profile"] = FinancialIntent(
                asset_symbols=None, risk="Medium"
            ).model_dump()
            state["inquirer_turns"] = 0
            logger.info("Inquirer fallback: defaulting to Medium risk due to LLM error")
            return state
        else:
            # On error and not final turn, ask the user to repeat
            state["inquirer_turns"] = turns + 1
            state["user_profile"] = None
            state["_inquirer_question"] = (
                "I didn't quite understand. Could you tell me your risk preference (Low, Medium, or High)?"
            )
            state.setdefault("completed_tasks", {})
            return state
