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

    # Extract recent execution history for context (last 3 items)
    recent_history = execution_history[-3:] if execution_history else []
    history_context = (
        "\n".join(recent_history) if recent_history else "(No execution history yet)"
    )

    system_prompt = (
        "You are the **State Manager** for a Financial Advisor Assistant.\n"
        "Your job is to produce the NEXT STATE based on current context and user input.\n\n"
        f"# CURRENT STATE:\n"
        f"- **Active Profile**: {current_profile or 'None (Empty)'}\n"
        f"- **Recent Execution Summary**:\n{history_context}\n\n"
        "# YOUR TASK: Output the COMPLETE, UPDATED state\n\n"
        "# DECISION LOGIC:\n\n"
        "## 1. CHAT (Greeting/Acknowledgement)\n"
        "- Pattern: 'Thanks', 'Hello', 'Got it'\n"
        "- Output: status='CHAT', response_to_user=[polite reply]\n\n"
        "## 2. RESET (Explicit Command)\n"
        "- Pattern: 'Start over', 'Reset', 'Clear everything', 'Forget that'\n"
        "- Output: status='RESET', updated_profile=None\n\n"
        "## 3. PLAN (Task Execution Needed)\n"
        "### 3a. Adding Assets\n"
        "- Pattern: 'Compare with MSFT' (when context has ['AAPL'])\n"
        "- Output: status='PLAN', updated_profile={assets: ['AAPL', 'MSFT']}\n"
        "- **CRITICAL**: Output the MERGED list, not just the new asset!\n\n"
        "### 3b. Switching Assets\n"
        "- Pattern: 'Check TSLA instead' (when context has ['AAPL'])\n"
        "- Output: status='PLAN', updated_profile={assets: ['TSLA']}\n"
        "- **CRITICAL**: Only output the new asset when user explicitly switches!\n\n"
        "### 3c. Follow-up Questions\n"
        "- Pattern: 'Why did it drop?', 'Tell me about iPhone sales'\n"
        "- Output: status='PLAN', updated_profile={assets: ['AAPL']} (same as current), focus_topic='price drop reasons'\n"
        "- **CRITICAL**: Keep profile unchanged, extract the specific question in focus_topic!\n\n"
        "### 3d. New Analysis Request\n"
        "- Pattern: 'Analyze Apple'\n"
        "- Output: status='PLAN', updated_profile={assets: ['AAPL']}\n\n"
        "# EXAMPLES:\n\n"
        "**Example 1: Adding Asset**\n"
        "Current: {assets: ['AAPL']}\n"
        "User: 'Compare with Microsoft'\n"
        "→ {status: 'PLAN', updated_profile: {asset_symbols: ['AAPL', 'MSFT']}, focus_topic: null}\n\n"
        "**Example 2: Follow-up**\n"
        "Current: {assets: ['AAPL']}\n"
        "Recent: 'Task completed: AAPL price $150, down 5%'\n"
        "User: 'Why did it drop?'\n"
        "→ {status: 'PLAN', updated_profile: {asset_symbols: ['AAPL']}, focus_topic: 'price drop reasons'}\n\n"
        "**Example 3: Switch**\n"
        "Current: {assets: ['AAPL']}\n"
        "User: 'Forget Apple, look at Tesla'\n"
        "→ {status: 'RESET', updated_profile: {asset_symbols: ['TSLA']}}\n\n"
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
            "Inquirer decision: status={s}, profile={p}, focus={f}, reason={r}",
            s=decision.status,
            p=decision.updated_profile,
            f=decision.focus_topic,
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
                "user_profile": None,  # Signal to route to END
                "inquirer_turns": 0,
            }

        # CASE 2: RESET - Clear everything and start fresh
        if decision.status == "RESET":
            logger.info("Inquirer: RESET - Clearing all context")
            new_profile = (
                decision.updated_profile.model_dump()
                if decision.updated_profile
                else None
            )
            return {
                "user_profile": new_profile,
                "plan": [],
                "completed_tasks": {},
                "execution_history": [],
                "is_final": False,
                "critique_feedback": None,
                "focus_topic": None,
                "messages": [
                    AIMessage(
                        content="Starting fresh session. What would you like to analyze?"
                    )
                ],
                "inquirer_turns": 0,
            }

        # CASE 3: PLAN - Apply the updated profile directly (trust the LLM)
        if decision.updated_profile:
            updates["user_profile"] = decision.updated_profile.model_dump()
            logger.info(
                "Inquirer: PLAN - Profile updated to {p}",
                p=decision.updated_profile.model_dump(),
            )
        elif current_profile:
            # Fallback: LLM didn't return profile but we have existing context
            updates["user_profile"] = current_profile
            logger.info("Inquirer: PLAN - Preserving existing profile")
        else:
            # No profile at all - shouldn't happen in PLAN status, but handle gracefully
            updates["user_profile"] = FinancialIntent().model_dump()
            logger.warning("Inquirer: PLAN with no profile - using empty default")

        # Update focus topic (critical for follow-up questions)
        updates["focus_topic"] = decision.focus_topic

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
        if current_profile:
            # If we have a profile, assume user wants to continue
            return {
                "user_profile": current_profile,
                "inquirer_turns": 0,
                "is_final": False,
            }
        else:
            # Ask user to retry
            return {
                "inquirer_turns": 0,
                "user_profile": None,
                "messages": [
                    AIMessage(
                        content="I didn't quite understand. Could you tell me what you'd like to analyze?"
                    )
                ],
            }
