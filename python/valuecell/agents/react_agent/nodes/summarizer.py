from __future__ import annotations

import json
from typing import Any

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from langchain_core.messages import AIMessage
from loguru import logger

from ..state import AgentState


async def summarizer_node(state: AgentState) -> dict[str, Any]:
    """
    Generate a polished final report from raw execution history.

    This node is the final step in the workflow. It transforms the technical
    execution log into a user-friendly financial analysis report suitable for
    beginner investors.

    Takes:
    - user_profile: Original user request
    - execution_history: Raw task completion summaries
    - completed_tasks: Actual data results

    Returns:
    - messages: Final AIMessage with formatted report
    - is_final: True (confirm completion)
    """
    user_profile = state.get("user_profile") or {}
    execution_history = state.get("execution_history") or []
    completed_tasks = state.get("completed_tasks") or {}

    logger.info(
        "Summarizer start: history_len={h}, tasks={t}",
        h=len(execution_history),
        t=len(completed_tasks),
    )

    # Build context for the summarizer
    # Extract key data points from completed_tasks for evidence
    data_summary = _extract_key_results(completed_tasks)

    system_prompt = (
        "You are a concise Financial Assistant for beginner investors.\n"
        "Your goal is to synthesize the execution results into a short, actionable insight card.\n\n"
        "**User Request**:\n"
        f"{json.dumps(user_profile, ensure_ascii=False)}\n\n"
        "**Key Data**:\n"
        f"{data_summary}\n\n"
        "**Strict Constraints**:\n"
        "1. **Length Limit**: Keep the total response under 400 words. Be ruthless with cutting fluff.\n"
        "2. **No Generic Intros**: DELETE sections like 'Company Overview' or 'What they do'.\n"
        "3. **Focus on NOW**: Only mention historical data if it directly explains a current trend.\n\n"
        "**Required Structure**:\n"
        "(1-2 sentences direct answer to user's question)\n\n"
        "## Key Findings\n"
        "- **Metric 1**: Value (Interpretation)\n"
        "- **Metric 2**: Value (Interpretation)\n"
        "(Only include the top 3 most relevant numbers)\n\n"
        "## Analysis\n"
        "(One short paragraph explaining WHY. Use the 'Recent Developments' here)\n\n"
        "## Risk Note\n"
        "(One sentence on the specific risk found in the data, e.g., 'High volatility detected.')"
    )

    user_msg = "Please generate the final financial analysis report."

    try:
        agent = Agent(
            model=OpenRouter(id="google/gemini-2.5-flash"),
            instructions=[system_prompt],
            markdown=True,  # Enable markdown in response
            debug_mode=True,
        )
        response = await agent.arun(user_msg)
        report_content = response.content

        logger.info("Summarizer completed: report_len={l}", l=len(report_content))

        # Return as AIMessage for conversation history
        return {
            "messages": [AIMessage(content=report_content)],
            "is_final": True,
            "_summarizer_complete": True,
        }
    except Exception as exc:
        logger.exception("Summarizer error: {err}", err=str(exc))
        # Fallback: return a basic summary
        fallback = (
            "## Analysis Complete\n\n"
            f"Completed {len(completed_tasks)} tasks based on your request. "
            "Please review the execution history for details."
        )
        return {
            "messages": [AIMessage(content=fallback)],
            "is_final": True,
            "_summarizer_error": str(exc),
        }


def _extract_key_results(completed_tasks: dict[str, Any]) -> str:
    """Extract and format key data points from completed tasks for LLM context.

    This reduces token usage by summarizing only the most important results
    instead of dumping entire task outputs.
    """
    if not completed_tasks:
        return "(No results available)"

    lines = []
    for task_id, task_data in completed_tasks.items():
        if not isinstance(task_data, dict):
            continue

        result = task_data.get("result")
        if not result:
            continue

        # Extract different types of results
        if isinstance(result, dict):
            # Market data
            if "symbols" in result:
                symbols = result.get("symbols", [])
                lines.append(
                    f"- Task {task_id}: Market data for {len(symbols)} symbols"
                )

            # Screen results
            if "table" in result:
                count = len(result.get("table", []))
                risk = result.get("risk", "Unknown")
                lines.append(
                    f"- Task {task_id}: Screened {count} candidates (Risk: {risk})"
                )

            # Backtest results
            if "return_pct" in result:
                ret = result.get("return_pct", 0)
                sharpe = result.get("sharpe_ratio", 0)
                lines.append(
                    f"- Task {task_id}: Backtest return={ret:.2f}%, Sharpe={sharpe:.2f}"
                )

        elif isinstance(result, str):
            # Research/text results - truncate to avoid token overflow
            # preview = result[:150] + "..." if len(result) > 150 else result
            preview = result
            lines.append(f"- Task {task_id}: {preview}")

    return "\n".join(lines) if lines else "(No extractable data)"
