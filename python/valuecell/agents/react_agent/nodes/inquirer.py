from __future__ import annotations

from typing import Any

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from langchain_core.messages import AIMessage, SystemMessage
from loguru import logger

from ..models import FinancialIntent, InquirerDecision


# TODO: summarize with LLM
def _compress_history(history: list[str]) -> str:
    """Compress long execution history to prevent token explosion.

    Args:
        history: List of execution history strings

    Returns:
        Single compressed summary string
    """
    # Simple compression: Keep first 3 and last 3 entries
    if len(history) <= 6:
        return "\n".join(history)

    compressed = [
        "[Execution History - Compressed]",
        *history[:3],
        f"... ({len(history) - 6} steps omitted) ...",
        *history[-3:],
    ]
    return "\n".join(compressed)


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
    """Smart Inquirer: Extracts natural language intent from conversation.

    Produces a single comprehensive sentence describing user's immediate goal.
    Resolves pronouns and context using conversation and execution history.

    Multi-turn conversation logic:
    1. **New Task**: User starts new analysis -> Generate clear intent
    2. **Follow-up**: User asks about prior results -> Resolve references and generate focused intent
    3. **Chat**: User casual talk (e.g., "Thanks") -> Direct response, no planning

    Inputs: state["messages"], state["current_intent"], state["execution_history"].
    Outputs: Updated state with current_intent (natural language string) or chat response.
    """
    messages = state.get("messages") or []
    current_intent = state.get("current_intent")
    execution_history = state.get("execution_history") or []
    turns = int(state.get("inquirer_turns") or 0)

    # Trim messages to prevent token overflow
    trimmed_messages = _trim_messages(messages, max_messages=10)

    logger.info(
        "Inquirer start: turns={t}, current_intent={i}, history_len={h}",
        t=turns,
        i=current_intent or "None",
        h=len(execution_history),
    )

    # Extract recent execution history for context (last 3 items)
    recent_history = execution_history[-3:] if execution_history else []
    history_context = (
        "\n".join(recent_history) if recent_history else "(No execution history yet)"
    )

    system_prompt = (
        "You are the **Intent Interpreter** for a Financial Advisor Assistant.\n"
        "Your job is to produce a single, comprehensive natural language sentence describing the user's IMMEDIATE goal.\n\n"
        f"# CURRENT CONTEXT:\n"
        f"- **Active Intent**: {current_intent or 'None (Empty)'}\n"
        f"- **Recent Execution Summary**:\n{history_context}\n\n"
        "# YOUR TASK: Output the user's current goal as a natural language instruction\n\n"
        "# DECISION LOGIC:\n\n"
        "## 1. CHAT (Greeting/Acknowledgement)\n"
        "- Pattern: 'Thanks', 'Hello', 'Got it'\n"
        "- Output: status='CHAT', response_to_user=[polite reply]\n\n"
        "## 2. RESET (Explicit Command)\n"
        "- Pattern: 'Start over', 'Reset', 'Clear everything', 'Forget that'\n"
        "- Output: status='RESET', current_intent=None\n\n"
        "## 3. PLAN (Task Execution Needed)\n"
        "### 3a. New Analysis Request\n"
        "- Pattern: 'Analyze Apple'\n"
        "- Output: status='PLAN', current_intent='Analyze Apple stock price and fundamentals'\n\n"
        "### 3b. Comparison Request\n"
        "- Pattern: 'Compare Apple and Tesla'\n"
        "- Output: status='PLAN', current_intent='Compare Apple and Tesla 2024 financial performance'\n\n"
        "### 3c. Adding to Comparison (Context-Aware)\n"
        "- Current Intent: 'Analyze Apple stock'\n"
        "- User: 'Compare with Microsoft'\n"
        "- Output: status='PLAN', current_intent='Compare Apple and Microsoft stock performance'\n"
        "- **CRITICAL**: Merge context! Don't just output 'Microsoft'.\n\n"
        "### 3d. Follow-up Questions (Reference Resolution)\n"
        "- Current Intent: 'Analyze Apple stock'\n"
        "- Recent Execution: 'AAPL price $150, down 5%'\n"
        "- User: 'Why did it drop?'\n"
        "- Output: status='PLAN', current_intent='Find reasons for Apple stock price drop'\n"
        "- **CRITICAL**: Resolve pronouns using context! 'it' → 'Apple stock'.\n\n"
        "### 3e. Specific Follow-up (Drill-Down)\n"
        "- Current Intent: 'Analyze Apple stock'\n"
        "- Assistant mentioned: 'consistent revenue growth'\n"
        "- User: 'Tell me more about the revenue growth'\n"
        "- Output: status='PLAN', current_intent='Analyze Apple revenue growth trends and details'\n"
        "- **CRITICAL**: Extract the specific phrase and make it explicit!\n\n"
        "### 3f. Switching Assets\n"
        "- Current Intent: 'Analyze Apple stock'\n"
        "- User: 'Forget Apple, look at Tesla'\n"
        "- Output: status='RESET', current_intent='Analyze Tesla stock'\n\n"
        "# EXAMPLES:\n\n"
        "**Example 1: Adding Asset**\n"
        "Current: 'Analyze Apple stock'\n"
        "User: 'Compare with Microsoft'\n"
        "→ {status: 'PLAN', current_intent: 'Compare Apple and Microsoft stock performance'}\n\n"
        "**Example 2: Reference Resolution**\n"
        "Current: 'Analyze Apple stock'\n"
        "Recent: 'AAPL down 5%'\n"
        "User: 'Why did it drop?'\n"
        "→ {status: 'PLAN', current_intent: 'Find reasons for Apple stock price drop'}\n\n"
        "**Example 3: Drill-Down**\n"
        "Current: 'Analyze Apple stock'\n"
        "Assistant: 'strong revenue growth'\n"
        "User: 'Tell me more about revenue growth'\n"
        "→ {status: 'PLAN', current_intent: 'Analyze Apple revenue growth details'}\n\n"
        "**Example 4: Greeting**\n"
        "User: 'Thanks!'\n"
        "→ {status: 'CHAT', response_to_user: 'You're welcome!'}\n"
    )

    # Build user message from conversation history
    message_strs = []
    for m in trimmed_messages:
        role = getattr(m, "type", "unknown")
        content = getattr(m, "content", str(m))
        message_strs.append(f"[{role}]: {content}")

    conversation_text = (
        "\n".join(message_strs) if message_strs else "(No conversation yet)"
    )
    user_msg = (
        "# Conversation History:\n"
        f"{conversation_text}\n\n"
        "# Execution Context:\n"
        f"Recent execution summary is already injected in CURRENT STATE above. "
        f"Use it to understand what data/analysis has already been completed."
    )

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
            "Inquirer decision: status={s}, intent={i}, reason={r}",
            s=decision.status,
            i=decision.current_intent,
            r=decision.reasoning,
        )

        # --- Simplified State Update Logic: Direct Application ---
        updates: dict[str, Any] = {}

        # CASE 1: CHAT - Direct response, no planning
        if decision.status == "CHAT":
            return {
                "messages": [
                    AIMessage(content=decision.response_to_user or "Understood.")
                ],
                "current_intent": None,  # Signal to route to END
                "inquirer_turns": 0,
            }

        # CASE 2: RESET - Clear everything and start fresh
        if decision.status == "RESET":
            logger.info("Inquirer: RESET - Clearing all context")
            return {
                "current_intent": decision.current_intent,
                "plan": [],
                "completed_tasks": {},
                "execution_history": [],
                "is_final": False,
                "critique_feedback": None,
                "messages": [
                    AIMessage(
                        content="Starting fresh session. What would you like to analyze?"
                    )
                ],
                "inquirer_turns": 0,
            }

        # CASE 3: PLAN - Apply the current intent directly
        if decision.current_intent:
            updates["current_intent"] = decision.current_intent
            logger.info(
                "Inquirer: PLAN - Intent set to: {i}",
                i=decision.current_intent,
            )
        elif current_intent:
            # Fallback: LLM didn't return intent but we have existing context
            updates["current_intent"] = current_intent
            logger.info("Inquirer: PLAN - Preserving existing intent")
        else:
            # No intent at all - shouldn't happen in PLAN status
            logger.warning("Inquirer: PLAN with no intent - asking for clarification")
            return {
                "current_intent": None,
                "inquirer_turns": 0,
                "messages": [
                    AIMessage(
                        content="I didn't quite understand. What would you like to analyze?"
                    )
                ],
            }

        # Force replanning
        updates["is_final"] = False

        # History Compression (Garbage Collection)
        current_history = state.get("execution_history") or []
        if len(current_history) > 20:
            logger.warning(
                "Execution history too long ({n} entries), compressing...",
                n=len(current_history),
            )
            compressed = _compress_history(current_history)
            updates["execution_history"] = [compressed]

        updates["inquirer_turns"] = 0  # Reset turn counter
        return updates

    except Exception as exc:
        logger.exception("Inquirer LLM error: {err}", err=str(exc))

        # Graceful fallback
        if current_intent:
            # If we have an intent, assume user wants to continue
            return {
                "current_intent": current_intent,
                "inquirer_turns": 0,
                "is_final": False,
            }
        else:
            # Ask user to retry
            return {
                "inquirer_turns": 0,
                "current_intent": None,
                "messages": [
                    AIMessage(
                        content="I didn't quite understand. Could you tell me what you'd like to analyze?"
                    )
                ],
            }
