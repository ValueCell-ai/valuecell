from __future__ import annotations

import json
import os
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger

from valuecell.utils import i18n_utils

from ..state import AgentState


async def summarizer_node(state: AgentState) -> dict[str, Any]:
    """
    Generate a polished final report using LangChain native model for streaming.

    Uses natural language current_intent to understand user's goal.
    """
    current_intent = state.get("current_intent") or "General financial analysis"
    completed_tasks = state.get("completed_tasks") or {}
    user_context = state.get("user_context") or {}
    current_datetime = i18n_utils.format_utc_datetime(i18n_utils.get_utc_now())

    logger.info(
        "Summarizer start: intent='{i}', tasks={t}",
        i=current_intent,
        t=len(completed_tasks),
    )

    # 1. Extract context
    data_summary = _extract_key_results(completed_tasks)

    # 2. Build prompt with current_intent and adaptive formatting
    # Note: intent analysis (is_comparison, is_question) can be used in future
    # to select conditional structure; for now provide flexible formatting guidelines
    system_template = """
You are a concise Financial Assistant for beginner investors.
Your goal is to synthesize execution results to answer the user's specific goal.

**User's Current Goal**:
{current_intent}

**User Context**:
{user_context}

**Current Date and Time**: {current_datetime}

**Available Data** (Execution Results):
{data_summary}

**Strict Constraints**:
1. **Source of Truth**: Use the data provided in "Available Data" above as your single source.
2. **Length Limit**: Keep the total response under 400 words. Be ruthless with cutting fluff.
3. **Relevance Check**: Ensure you address the user's stated goal completely.
4. **Completeness Check**: You MUST surface data errors explicitly.
   - If data is missing or mismatched (e.g. "content seems to be AMD" when user asked for "AAPL"), 
     you MUST write: "⚠️ Data Retrieval Issue: [Details]"
5. **No Generic Intros**: Start directly with the answer.
6. **Adaptive Structure**:
   - **General Analysis**: Use "Key Findings → Analysis → Risk Note" structure.
   - **Comparison**: Use "Side-by-Side" approach. Highlight key differences and similarities.
   - **Specific Question**: Answer DIRECTLY. No forced headers if not relevant.
7. **Markdown**: Always use Markdown. Bold key metrics or information.
8. **Truthfulness**: If data is missing, state it explicitly: "Data not available for [X]".
"""

    prompt = ChatPromptTemplate.from_messages(
        [("system", system_template), ("human", "Please generate the final report.")]
    )

    # 3. Initialize LangChain Model (Native Streaming Support)
    # Using ChatOpenAI to connect to OpenRouter (compatible API)
    llm = ChatOpenAI(
        model="google/gemini-2.5-flash",
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),  # Ensure ENV is set
        temperature=0,
        streaming=True,  # Crucial for astream_events
    )

    chain = prompt | llm

    try:
        # 4. Invoke Chain
        # LangGraph automatically captures 'on_chat_model_stream' events here
        response = await chain.ainvoke(
            {
                "current_intent": current_intent,
                "data_summary": data_summary,
                "user_context": user_context,
                "current_datetime": current_datetime,
            }
        )

        report_content = response.content
        logger.info("Summarizer completed: len={l}", l=len(report_content))

        return {
            "messages": [AIMessage(content=report_content)],
            "is_final": True,
            "_summarizer_complete": True,
        }

    except Exception as exc:
        logger.exception("Summarizer error: {err}", err=str(exc))
        return {
            "messages": [
                AIMessage(
                    content="I encountered an error generating the report. Please check the execution logs."
                )
            ],
            "is_final": True,
        }


def _extract_key_results(completed_tasks: dict[str, Any]) -> str:
    """Extract results with JSON formatting and error highlighting.

    Prefers JSON for structured data (dicts/lists) for better LLM comprehension.
    Falls back to string representation for simple values.
    """
    if not completed_tasks:
        return "(No results available)"

    lines = []
    for task_id, task_data in completed_tasks.items():
        if not isinstance(task_data, dict):
            continue

        result = task_data.get("result")
        desc = task_data.get("description") or ""

        # Handle errors reported by Executor
        if task_data.get("error"):
            error_msg = task_data["error"]
            error_code = task_data.get("error_code", "")
            error_info = f"**Error**: {error_msg}"
            if error_code:
                error_info += f" (Code: {error_code})"
            lines.append(f"### Task {task_id} [FAILED]\n{error_info}")
            continue

        if not result:
            continue

        # Prefer JSON formatting for structured data; fallback to str() for simple values
        if isinstance(result, (dict, list)):
            try:
                preview = json.dumps(result, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                preview = str(result)
        else:
            preview = str(result)

        # Slightly higher truncation limit to preserve structured data context
        if len(preview) > 1000:
            preview = preview[:1000] + "\n... (truncated)"

        # Build header with description (critical for Summarizer to understand task purpose)
        header = f"### Task {task_id}"
        if desc:
            header += f": {desc}"

        lines.append(f"{header}\n{preview}")

    return "\n\n".join(lines)
