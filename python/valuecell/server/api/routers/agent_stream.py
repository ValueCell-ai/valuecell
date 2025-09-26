"""
Agent stream router for handling streaming agent queries.
"""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from valuecell.server.api.schemas.agent_stream import AgentStreamRequest
from valuecell.server.services.agent_stream_service import AgentStreamService


def create_agent_stream_router() -> APIRouter:
    """Create and configure the agent stream router."""

    router = APIRouter(prefix="/agents", tags=["Agent Stream"])
    agent_service = AgentStreamService()

    @router.post("/stream")
    async def stream_query_agent(request: AgentStreamRequest):
        """
        Stream agent query responses in real-time.

        This endpoint accepts a user query and returns a streaming response
        with agent-generated content in Server-Sent Events (SSE) format.
        """
        try:

            async def generate_stream():
                """Generate SSE formatted stream chunks."""
                async for chunk in agent_service.stream_query_agent(
                    query=request.query, agent_name=request.agent_name
                ):
                    # Format as SSE (Server-Sent Events)
                    yield f"data: {json.dumps(chunk)}\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Agent query failed: {str(e)}")

    return router
