"""
StrategyAgent router for handling strategy creation via streaming responses.
"""

from fastapi import APIRouter, HTTPException

from valuecell.agents.strategy_agent.models import StrategyStatusContent, UserRequest
from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.core.types import UserInput, UserInputMetadata


def create_strategy_agent_router() -> APIRouter:
    """Create and configure the StrategyAgent router."""

    router = APIRouter(prefix="/agents", tags=["Strategy Agent"])
    orchestrator = AgentOrchestrator()

    @router.post("/create_strategy_agent")
    async def create_strategy_agent(request: UserRequest):
        """
        Create a strategy through StrategyAgent and return final JSON result.

        This endpoint accepts a structured request body, maps it to StrategyAgent's
        UserRequest JSON, and returns an aggregated JSON response (non-SSE).
        """
        try:
            # Ensure we only serialize the core UserRequest fields, excluding conversation_id
            user_request = UserRequest(
                llm_config=request.llm_config,
                exchange_config=request.exchange_config,
                trading_config=request.trading_config,
            )
            query = user_request.model_dump_json()

            agent_name = "StrategyAgent"

            # Build UserInput for orchestrator
            user_input_meta = UserInputMetadata(user_id="default_user")
            user_input = UserInput(
                query=query,
                target_agent_name=agent_name,
                meta=user_input_meta,
            )

            # Directly use process_user_input instead of stream_query_agent
            async for chunk_obj in orchestrator.process_user_input(user_input):
                event = chunk_obj.event
                data = chunk_obj.data

                if event == "component_generator":
                    content = data.payload.content
                    return StrategyStatusContent.model_validate_json(content)

            return StrategyStatusContent(status="error")

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"StrategyAgent create failed: {str(e)}"
            )

    return router
