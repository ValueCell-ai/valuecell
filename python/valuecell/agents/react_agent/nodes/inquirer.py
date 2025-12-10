from __future__ import annotations

from typing import Any

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from langchain_core.messages import AIMessage, SystemMessage
from loguru import logger

from ..models import FinancialIntent, InquirerDecision


def _merge_profiles(old: dict | None, delta: dict | None) -> dict:
    """Merge new intent delta into existing profile (set union for assets).

    Args:
        old: Existing user_profile dict or None
        delta: New intent delta dict from LLM or None

    Returns:
        Merged profile dict

    Examples:
        old={'asset_symbols': ['AAPL']}, delta={'asset_symbols': ['MSFT']}
        -> {'asset_symbols': ['AAPL', 'MSFT']}
    """
    if not old:
        return delta or {}
    if not delta:
        return old

    merged = old.copy()

    # 1. Merge asset lists (Set union for deduplication)
    old_assets = set(old.get("asset_symbols") or [])
    new_assets = set(delta.get("asset_symbols") or [])
    if new_assets:
        merged["asset_symbols"] = list(old_assets | new_assets)

    return merged


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

    is_final_turn = turns >= 2

    # Extract recent execution history for context (last 3 items)
    recent_history = execution_history[-3:] if execution_history else []
    history_context = (
        "\n".join(recent_history) if recent_history else "(No execution history yet)"
    )

    system_prompt = (
        "You are the **State Manager** for a Financial Advisor Assistant.\n"
        "Your PRIMARY GOAL is to extract **only the new information (delta)** from the user's latest message.\n\n"
        f"# CURRENT STATE (Context):\n"
        f"- **Active Profile**: {current_profile or 'None (Empty)'}\n"
        f"- **Recent Execution Summary**:\n{history_context}\n\n"
        "# OUTPUT INSTRUCTIONS:\n"
        "1. **intent_delta**: Return ONLY the new fields found in the latest message. Do NOT repeat old info.\n"
        "2. **HARD RESET (System Command)**\n"
        "   - Trigger ONLY if user says: 'Start over', 'Reset', 'Clear history', 'New session'.\n"
        "   - Output: status='COMPLETE', is_hard_switch=True.\n"
        "3. **Implicit Reference**: If user refers to a previous asset or topic (e.g., 'Why did it drop?'), assume they refer to the Active Profile. Use the Recent Execution Summary to understand context.\n\n"
        "# EXAMPLES (Few-Shot):\n\n"
        "**Scenario 1: Incremental Addition**\n"
        "Context: {assets: ['AAPL']}\n"
        "User: 'Compare with MSFT'\n"
        "Output: {intent_delta: {asset_symbols: ['MSFT']}, status: 'COMPLETE', is_hard_switch: False}\n"
        "(Note: Only output MSFT. The system will merge it to get [AAPL, MSFT])\n\n"
        "**Scenario 2: Parameter Refinement**\n"
        "Context: {assets: ['AAPL'], risk: 'Medium'}\n"
        "User: 'Actually, I want low risk'\n"
        "Output: {intent_delta: {risk: 'Low'}, status: 'COMPLETE', is_hard_switch: False}\n\n"
        "**Scenario 3: Implicit Follow-up**\n"
        "Context: {assets: ['AAPL']}\n"
        "Execution: Task result shows 'Sales down 10% YoY'\n"
        "User: 'Why are sales down?'\n"
        "Output: {intent_delta: null, status: 'COMPLETE', is_hard_switch: false}\n"
        "(Note: Context has assets and execution history shows sales trend. Inquirer extracts the topic implicitly; Planner generates deep-dive tasks.)\n\n"
        "**Scenario 4: Hard Switch**\n"
        "Context: {assets: ['AAPL']}\n"
        "User: 'Forget that. Let's look at Bitcoin.'\n"
        "Output: {intent_delta: {asset_symbols: ['BTC']}, status: 'COMPLETE', is_hard_switch: True}\n\n"
        "**Scenario 5: Incomplete Start**\n"
        "Context: None\n"
        "User: 'I want to invest'\n"
        "Output: {status: 'INCOMPLETE', response: 'What assets are you interested in?'}\n\n"
        "# INFERENCE RULES:\n"
        "- Risk: 'Safe/Retirement' -> Low | 'Aggressive/Growth' -> High\n"
        "- Default behavior: Assume the user is building on the previous conversation."
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
            "Inquirer decision: status={s}, hard_switch={h}, reason={r}",
            s=decision.status,
            h=decision.is_hard_switch,
            r=decision.reasoning,
        )

        # --- State Update Logic: Append-Only with Explicit Resets ---

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
                    or "Could you tell me your preference?"
                )
            ]
            return updates

        # CASE 3: COMPLETE - Ready for planning (with state accumulation)

        # Branch A: HARD RESET (rare - explicit user command)
        if decision.is_hard_switch:
            logger.info(
                "Inquirer: HARD RESET - User explicitly requested context clear"
            )
            # Extract fresh intent from delta
            new_profile = (
                decision.intent_delta.model_dump()
                if decision.intent_delta
                else FinancialIntent().model_dump()
            )
            updates["user_profile"] = new_profile
            # Clear all accumulated state
            updates["plan"] = []
            updates["completed_tasks"] = {}
            updates["execution_history"] = []
            updates["is_final"] = False
            updates["critique_feedback"] = None
            updates["messages"] = [
                AIMessage(content="Context reset. Starting fresh analysis.")
            ]

        # Branch B: DEFAULT ACCUMULATION (90% of cases)
        else:
            # Merge delta into existing profile
            if decision.intent_delta:
                merged_profile = _merge_profiles(
                    current_profile, decision.intent_delta.model_dump()
                )
                updates["user_profile"] = merged_profile
                logger.info(
                    "Inquirer: DELTA MERGE - Old: {old}, Delta: {delta}, Merged: {merged}",
                    old=current_profile,
                    delta=decision.intent_delta.model_dump(),
                    merged=merged_profile,
                )
            elif current_profile:
                # Follow-up without new intent: keep existing profile
                updates["user_profile"] = current_profile
                logger.info("Inquirer: FOLLOW-UP - No delta, preserving profile")
            else:
                # Fallback: no delta and no existing profile
                updates["user_profile"] = FinancialIntent().model_dump()
                logger.info(
                    "Inquirer: DEFAULT PROFILE - No context, using default profile"
                )

            # Always reset is_final to trigger replanning (Planner decides what to reuse)
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
        if is_final_turn or current_profile:
            # If we have a profile, assume user wants to continue
            return {
                "user_profile": current_profile or FinancialIntent().model_dump(),
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
