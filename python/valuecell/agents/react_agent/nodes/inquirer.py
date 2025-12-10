from __future__ import annotations

from typing import Any

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from langchain_core.messages import AIMessage, SystemMessage
from loguru import logger

from ..models import FinancialIntent, InquirerDecision


def _trim_messages(messages: list, max_messages: int = 10) -> list:
    """Keep only the last N messages to prevent token overflow.

    Always preserves system messages.
    """
    if len(messages) <= max_messages:
        return messages

    # Separate system messages from others
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

    # Keep last N-len(system_msgs) of other messages
    trimmed_others = other_msgs[-(max_messages - len(system_msgs)) :]

    return system_msgs + trimmed_others


async def inquirer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Smart Inquirer: Extracts intent, detects context switches, handles follow-ups.

    Multi-turn conversation logic:
    1. **New Task**: User changes target (e.g., "Check MSFT") -> Clear history
    2. **Follow-up**: User asks about results (e.g., "Why risk high?") -> Keep history
    3. **Chat**: User casual talk (e.g., "Thanks") -> Direct response, no planning

    Inputs: state["messages"], state["user_profile"], state["execution_history"].
    Outputs: Updated state with user_profile, history reset if needed, or chat response.
    """
    messages = state.get("messages") or []
    current_profile = state.get("user_profile")
    execution_history = state.get("execution_history") or []
    turns = int(state.get("inquirer_turns") or 0)

    # Trim messages to prevent token overflow
    trimmed_messages = _trim_messages(messages, max_messages=10)

    logger.info(
        "Inquirer start: turns={t}, current_profile={p}, history_len={h}",
        t=turns,
        p=current_profile,
        h=len(execution_history),
    )

    is_final_turn = turns >= 2

    # Build context-aware system prompt
    system_prompt = (
        "You are a Financial Advisor Assistant's State Manager.\n\n"
        "# YOUR ROLE:\n"
        "Analyze the user's latest message in the context of previous conversation and execution state.\n"
        "Decide what to do with the agent's state.\n\n"
        f"# CURRENT CONTEXT:\n"
        f"- Known Profile: {current_profile or 'None (First interaction)'}\n"
        f"- Completed Tasks: {len(execution_history)} execution steps\n"
        f"- Interaction Turn: {turns} (Max: 2)\n\n"
        "# DECISION LOGIC:\n"
        "1. **CHAT**: If user is just chatting (e.g., 'Thanks', 'OK', casual reply), "
        "set status='CHAT' and provide a polite response in `response_to_user`. Set intent=None.\n\n"
        "2. **NEW TASK**: If user is starting a NEW analysis (e.g., 'Analyze MSFT', 'Switch to Gold'), "
        "set status='COMPLETE', extract the new intent, and set `should_clear_history=True` to reset old data.\n\n"
        "3. **FOLLOW-UP**: If user is asking about EXISTING results (e.g., 'Why is the return low?', 'Tell me about iPhone 17 sales'), "
        "set status='COMPLETE', keep the current intent (or update if refined), set `should_clear_history=False`, "
        "and **CRITICALLY**: extract the specific `focus_topic` the user is asking about (e.g., 'iPhone 17 sales forecasts', 'dividend policy', 'ESG rating'). "
        "This helps the Planner determine if new research is needed for that specific topic.\n\n"
        "4. **INCOMPLETE**: If essential info (risk preference) is MISSING on a NEW task, "
        "set status='INCOMPLETE' and ask a follow-up question in `response_to_user`.\n\n"
        "# REQUIRED INFO FOR COMPLETE:\n"
        "- Asset/Target: What to analyze (stock, sector, etc.)\n"
        "- Risk Tolerance: Low, Medium, or High (can infer from keywords)\n\n"
        "# INFERENCE RULES:\n"
        "- 'safe', 'stable', 'conservative' -> Risk='Low'\n"
        "- 'growth', 'aggressive', 'dynamic' -> Risk='High'\n"
        "- 'balanced', unspecified -> Risk='Medium'\n\n"
    )

    if is_final_turn:
        system_prompt += (
            "# CRITICAL: MAX TURNS REACHED\n"
            "Do NOT set status='INCOMPLETE'. Infer reasonable defaults (Risk='Medium') and proceed.\n"
        )

    # Build user message from conversation history
    message_strs = []
    for m in trimmed_messages:
        role = getattr(m, "type", "unknown")
        content = getattr(m, "content", str(m))
        message_strs.append(f"[{role}]: {content}")

    user_msg = "# Conversation History:\n" + "\n".join(message_strs)

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
            "Inquirer decision: status={s}, clear_history={c}, reason={r}",
            s=decision.status,
            c=decision.should_clear_history,
            r=decision.reasoning,
        )

        # --- State Update Logic (Core Context Switching) ---

        updates: dict[str, Any] = {}

        # CASE 1: CHAT - Direct response, no planning
        if decision.status == "CHAT":
            updates["messages"] = [
                AIMessage(content=decision.response_to_user or "Understood.")
            ]
            updates["user_profile"] = None  # Signal to route to END
            updates["inquirer_turns"] = 0
            return updates

        # CASE 2: INCOMPLETE - Ask follow-up question
        if decision.status == "INCOMPLETE" and not is_final_turn:
            updates["inquirer_turns"] = turns + 1
            updates["user_profile"] = None  # Signal to route to END (wait for user)
            updates["messages"] = [
                AIMessage(
                    content=decision.response_to_user
                    or "Could you tell me your risk preference (Low, Medium, High)?"
                )
            ]
            return updates

        # CASE 3: COMPLETE - Ready for planning
        # Update profile (use new intent or keep current)
        if decision.intent:
            updates["user_profile"] = decision.intent.model_dump()
        elif current_profile:
            # Follow-up without changing intent: keep existing profile
            updates["user_profile"] = current_profile
        else:
            # Fallback: no intent provided, default to Medium risk
            updates["user_profile"] = FinancialIntent(risk="Medium").model_dump()

        # Context Switch: Clear history if starting new task
        if decision.should_clear_history:
            logger.info("Inquirer: Clearing history for NEW TASK")
            updates["plan"] = []
            updates["completed_tasks"] = {}
            updates["execution_history"] = []
            updates["is_final"] = False
            updates["critique_feedback"] = None
            updates["focus_topic"] = None  # Clear old focus
            updates["messages"] = [
                SystemMessage(content="User started a new task. Previous context cleared.")
            ]
        else:
            # Follow-up: Keep history but reset is_final and set focus_topic
            # This forces Planner to re-evaluate whether new data is needed
            logger.info(
                "Inquirer: FOLLOW-UP detected, focus_topic={topic}",
                topic=decision.focus_topic,
            )
            updates["is_final"] = False  # Force replanning
            updates["focus_topic"] = decision.focus_topic or None

        updates["inquirer_turns"] = 0  # Reset turn counter after completion
        return updates

    except Exception as exc:
        logger.exception("Inquirer LLM error: {err}", err=str(exc))

        # Graceful fallback
        if is_final_turn or current_profile:
            # If we have a profile, assume user wants to continue
            return {
                "user_profile": current_profile
                or FinancialIntent(risk="Medium").model_dump(),
                "inquirer_turns": 0,
            }
        else:
            # Ask user to retry
            return {
                "inquirer_turns": turns + 1,
                "user_profile": None,
                "messages": [
                    AIMessage(
                        content="I didn't quite understand. Could you tell me what you'd like to analyze?"
                    )
                ],
            }
