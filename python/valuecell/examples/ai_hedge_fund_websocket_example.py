import json
import logging
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from valuecell.core.coordinate.orchestrator import get_default_orchestrator
from valuecell.core.types import UserInput, UserInputMetadata

logger = logging.getLogger(__name__)

AGENT_ANALYST_MAP = {
    "aswath_damodaran_agent": ("Aswath Damodaran", "aswath_damodaran"),
    "ben_graham_agent": ("Ben Graham", "ben_graham"),
    "bill_ackman_agent": ("Bill Ackman", "bill_ackman"),
    "cathie_wood_agent": ("Cathie Wood", "cathie_wood"),
    "charlie_munger_agent": ("Charlie Munger", "charlie_munger"),
    "michael_burry_agent": ("Michael Burry", "michael_burry"),
    "mohnish_pabrai_agent": ("Mohnish Pabrai", "mohnish_pabrai"),
    "peter_lynch_agent": ("Peter Lynch", "peter_lynch"),
    "phil_fisher_agent": ("Phil Fisher", "phil_fisher"),
    "rakesh_jhunjhunwala_agent": ("Rakesh Jhunjhunwala", "rakesh_jhunjhunwala"),
    "stanley_druckenmiller_agent": ("Stanley Druckenmiller", "stanley_druckenmiller"),
    "warren_buffett_agent": ("Warren Buffett", "warren_buffett"),
    "technical_analyst_agent": ("Technical Analyst", "technical_analyst"),
    "fundamentals_analyst_agent": ("Fundamentals Analyst", "fundamentals_analyst"),
    "sentiment_analyst_agent": ("Sentiment Analyst", "sentiment_analyst"),
    "valuation_analyst_agent": ("Valuation Analyst", "valuation_analyst"),
}


class AnalysisRequest(BaseModel):
    agent_name: str = Field(..., description="The name of the agent to use")
    query: str = Field(..., description="The user's query for the agent")
    session_id: Optional[str] = Field(
        None, description="Session ID, will be auto-generated if not provided"
    )
    user_id: str = Field("default_user", description="User ID")


def _parse_user_input(request: AnalysisRequest) -> UserInput:
    """Parse user input into internal format"""
    session_id = request.session_id or f"{request.agent_name}_session_{request.user_id}"

    meta = UserInputMetadata(
        session_id=session_id,
        user_id=request.user_id,
    )

    query = request.query
    selected_analyst = AGENT_ANALYST_MAP.get(request.agent_name)
    if selected_analyst:
        query += f"\n\n**Hint**: Use {selected_analyst[0]} ({selected_analyst[1]}) in your analysis."

    return UserInput(desired_agent_name="AIHedgeFundAgent", query=query, meta=meta)


app = FastAPI(
    title="AI Hedge Fund WebSocket API",
    description="Real-time stock analysis via WebSocket",
    version="1.0.0",
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "AI Hedge Fund WebSocket API is running",
        "version": "1.0.0",
        "websocket_endpoint": "/ws",
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time stock analysis"""
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
                async for message_chunk in orchestrator.process_user_input(user_input):
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


if __name__ == "__main__":
    import uvicorn

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Start server
    uvicorn.run(
        "ai_hedge_fund_websocket_example:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
