"""WebSocket router for real-time stock analysis."""

import json
import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from valuecell.core.coordinate.orchestrator import get_default_orchestrator
from valuecell.core.types import UserInput, UserInputMetadata

logger = logging.getLogger(__name__)

# Agent analyst mapping from the example
AGENT_ANALYST_MAP = {"SecAgent": ("SecAgent")}


class AnalysisRequest(BaseModel):
    """Request model for analysis."""

    agent_name: str = Field(..., description="The name of the agent to use")
    query: str = Field(..., description="The user's query for the agent")
    session_id: Optional[str] = Field(
        None, description="Session ID, will be auto-generated if not provided"
    )
    user_id: str = Field("default_user", description="User ID")


def _parse_user_input(request: AnalysisRequest) -> UserInput:
    """Parse analysis request into UserInput."""
    session_id = request.session_id or str(uuid4())

    return UserInput(
        query=request.query,
        desired_agent_name=request.agent_name,
        meta=UserInputMetadata(
            session_id=session_id,
            user_id=request.user_id,
        ),
    )


def create_websocket_router() -> APIRouter:
    """Create and configure WebSocket router."""
    router = APIRouter()

    @router.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time stock analysis."""
        await websocket.accept()
        logger.info("WebSocket connection established")

        try:
            orchestrator = get_default_orchestrator()

            while True:
                # Receive message from client
                data = await websocket.receive_text()
                logger.info(f"Received message: {data}")

                try:
                    # Parse the incoming message
                    message_data = json.loads(data)

                    # Validate agent name
                    agent_name = message_data.get("agent_name")
                    if agent_name not in AGENT_ANALYST_MAP:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "error",
                                    "message": f"Unsupported agent: {agent_name}. Available agents: {list(AGENT_ANALYST_MAP.keys())}",
                                }
                            )
                        )
                        continue

                    # Create analysis request
                    request = AnalysisRequest(**message_data)
                    user_input = _parse_user_input(request)

                    # Send analysis start notification
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "analysis_started",
                                "agent_name": request.agent_name,
                            }
                        )
                    )

                    # Stream analysis results
                    async for message_chunk in orchestrator.process_user_input(
                        user_input
                    ):
                        response = {
                            "type": "analysis_chunk",
                            "message": str(message_chunk),
                            "agent_name": request.agent_name,
                        }
                        await websocket.send_text(json.dumps(response))
                        logger.info(f"Sent message chunk: {message_chunk}")

                    # Send completion notification
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "analysis_completed",
                                "agent_name": request.agent_name,
                            }
                        )
                    )

                except json.JSONDecodeError:
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": "Invalid JSON format"})
                    )
                except Exception as e:
                    logger.error(f"Error processing request: {e}")
                    await websocket.send_text(
                        json.dumps(
                            {"type": "error", "message": f"Analysis failed: {str(e)}"}
                        )
                    )

        except WebSocketDisconnect:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")

    return router
