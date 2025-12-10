from __future__ import annotations

import os
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger

from ..state import AgentState


async def summarizer_node(state: AgentState) -> dict[str, Any]:
    """
    Generate a polished final report using LangChain native model for streaming.

    Uses natural language current_intent to understand user's goal.
    """
    current_intent = state.get("current_intent") or "General financial analysis"
    execution_history = state.get("execution_history") or []
    completed_tasks = state.get("completed_tasks") or {}

    logger.info(
        "Summarizer start: intent='{i}', history_len={h}, tasks={t}",
        i=current_intent,
        h=len(execution_history),
        t=len(completed_tasks),
    )

    # 1. Extract context
    data_summary = _extract_key_results(completed_tasks)

    # 2. Build prompt with current_intent
    system_template = """
You are a concise Financial Assistant for beginner investors.
Your goal is to synthesize the execution results into a short, actionable insight card.

**User's Goal**:
{current_intent}

**Key Data extracted from tools**:
{data_summary}

**Strict Constraints**:
1. **Length Limit**: Keep the total response under 400 words. Be ruthless with cutting fluff.
2. **Relevance Check**: Ensure you address the user's stated goal.
3. **Completeness Check**: You MUST surface data errors explicitly.
   - If data is missing or mismatched (e.g. "content seems to be AMD" when user asked for "AAPL"), 
     you MUST write: "⚠️ Data Retrieval Issue: [Details]"
4. **No Generic Intros**: Start directly with the answer.
5. **Structure**: Use the format below.

**Required Structure**:
(1-2 sentences direct answer to user's question)

## Key Findings
- **[Metric Name]**: Value (Interpretation)
(List top 3 metrics. If data is missing/error, state it here)

## Analysis
(One short paragraph synthesizing the "Why". Connect the dots.)

## Risk Note
(One specific risk factor found in the data)
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
    """Extract results with Error Highlighting."""
    if not completed_tasks:
        return "(No results available)"

    lines = []
    for task_id, task_data in completed_tasks.items():
        if not isinstance(task_data, dict):
            continue

        result = task_data.get("result")

        # Handle errors reported by Executor
        if task_data.get("error"):
            lines.append(f"- Task {task_id} [FAILED]: {task_data['error']}")
            continue

        if not result:
            continue

        preview = str(result)
        if len(preview) > 500:
            preview = preview[:500] + "... (truncated)"

        lines.append(f"- Task {task_id}: {preview}")

    return "\n".join(lines)
