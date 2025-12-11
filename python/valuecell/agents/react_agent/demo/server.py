"""
FastAPI server for React Agent with SSE (Server-Sent Events) streaming.
Fixed for: Pydantic serialization, Router filtering, and Node observability.
"""

from __future__ import annotations

import json
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from loguru import logger
from pydantic import BaseModel

from valuecell.agents.react_agent.graph import get_app

app = FastAPI(title="React Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str


def format_sse(event_type: str, data: Any) -> str:
    """Format SSE message with proper JSON serialization for Pydantic objects."""
    # jsonable_encoder converts Pydantic models to dicts automatically
    clean_data = jsonable_encoder(data)
    return f"data: {json.dumps({'type': event_type, 'data': clean_data})}\n\n"


async def event_stream_generator(user_input: str, thread_id: str):
    """
    Convert LangGraph v2 event stream to frontend UI protocol.
    """
    try:
        graph = get_app()
        inputs = {"messages": [HumanMessage(content=user_input)]}
        config = {"configurable": {"thread_id": thread_id}}

        logger.info(f"Stream start: {thread_id}")
        last_emitted_text: str | None = None

        async for event in graph.astream_events(inputs, config=config, version="v2"):
            kind = event.get("event", "")
            node = event.get("metadata", {}).get("langgraph_node", "")
            data = event.get("data") or {}

            # --- Helper: Check if this is a valid node output (not a router string) ---
            def is_real_node_output(d):
                output = d.get("output")
                # Routers return strings like "wait", "plan". Nodes return dicts or Messages.
                if isinstance(output, str):
                    return False
                return True

            # =================================================================
            # 1. OBSERVABILITY EVENTS (Planner, Executor, Critic)
            # =================================================================

            # PLANNER: Emit the task list
            if kind == "on_chain_end" and node == "planner":
                if is_real_node_output(data):
                    output = data.get("output", {})
                    # Ensure we have a plan
                    if isinstance(output, dict) and "plan" in output:
                        yield format_sse(
                            "planner_update",
                            {
                                "plan": output.get("plan"),
                                "reasoning": output.get("strategy_update"),
                            },
                        )

            # EXECUTOR: Emit specific task results (text/data)
            elif kind == "on_chain_end" and node == "executor":
                if is_real_node_output(data):
                    output = data.get("output", {})
                    if isinstance(output, dict) and "completed_tasks" in output:
                        for task_id, res in output["completed_tasks"].items():
                            # res structure: {'task_id': 't1', 'ok': True, 'result': '...'}
                            yield format_sse(
                                "task_result",
                                {
                                    "task_id": task_id,
                                    "status": "success" if res.get("ok") else "error",
                                    "result": res.get(
                                        "result"
                                    ),  # This is the markdown text
                                },
                            )

            # CRITIC: Emit approval/rejection logic
            elif kind == "on_chain_end" and node == "critic":
                if is_real_node_output(data):
                    output = data.get("output", {})
                    if isinstance(output, dict):
                        summary = output.get("_critic_summary")
                        if summary:
                            yield format_sse("critic_decision", summary)

            # AGNO/TOOL LOGS: Intermediate progress
            elif kind == "on_custom_event" and event.get("name") == "agno_event":
                yield format_sse(
                    "tool_progress", {"node": node or "executor", "details": data}
                )

            # =================================================================
            # 2. CHAT CONTENT EVENTS (Inquirer, Summarizer)
            # =================================================================

            # STREAMING CONTENT (Summarizer)
            if kind == "on_chat_model_stream" and node == "summarizer":
                chunk = data.get("chunk")
                text = chunk.content if chunk else None
                if text:
                    yield format_sse("content_token", {"delta": text})

            # STATIC CONTENT (Inquirer / Fallback)
            # Inquirer returns a full AIMessage at the end, not streamed
            elif kind == "on_chain_end" and node == "inquirer":
                if is_real_node_output(data):
                    output = data.get("output", {})
                    msgs = output.get("messages", [])
                    if msgs and isinstance(msgs, list):
                        last_msg = msgs[-1]
                        # Verify it's an AI message meant for the user
                        if isinstance(last_msg, AIMessage) and last_msg.content:
                            # Only emit if we haven't streamed this content already
                            # (Inquirer doesn't stream, so this is safe)
                            yield format_sse(
                                "content_token", {"delta": last_msg.content}
                            )

            # =================================================================
            # 3. UI STATE EVENTS
            # =================================================================

            elif kind == "on_chain_start" and node:
                yield format_sse("step_change", {"step": node, "status": "started"})

            elif kind == "on_chain_end" and node:
                # Filter out routers for UI cleanliness
                if is_real_node_output(data):
                    yield format_sse(
                        "step_change", {"step": node, "status": "completed"}
                    )

        # End of stream
        yield format_sse("done", {})
        logger.info(f"Stream done: {thread_id}")

    except Exception as exc:
        logger.exception(f"Stream error: {exc}")
        yield format_sse("error", {"message": str(exc)})


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        event_stream_generator(request.message, request.thread_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8009)
