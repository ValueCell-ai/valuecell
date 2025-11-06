"""
StrategyAgent router for handling strategy creation via streaming responses.
"""

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from valuecell.agents.strategy_agent.models import StrategyStatusContent, UserRequest
from valuecell.config.loader import get_config_loader
from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.core.types import CommonResponseEvent, UserInput, UserInputMetadata
from valuecell.server.db.connection import get_db
from valuecell.server.db.models.strategy import Strategy
from valuecell.utils.uuid import generate_conversation_id


def create_strategy_agent_router() -> APIRouter:
    """Create and configure the StrategyAgent router."""

    router = APIRouter(prefix="/agents", tags=["Strategy Agent"])
    orchestrator = AgentOrchestrator()

    @router.post("/create_strategy_agent")
    async def create_strategy_agent(
        request: UserRequest, db: Session = Depends(get_db)
    ):
        """
        Create a strategy through StrategyAgent and return final JSON result.

        This endpoint accepts a structured request body, maps it to StrategyAgent's
        UserRequest JSON, and returns an aggregated JSON response (non-SSE).
        """
        try:
            # Ensure we only serialize the core UserRequest fields, excluding conversation_id
            user_request = UserRequest(
                llm_model_config=request.llm_model_config,
                exchange_config=request.exchange_config,
                trading_config=request.trading_config,
            )

            # If same provider + model_id comes with a new api_key, override previous key
            try:
                provider = user_request.llm_model_config.provider
                model_id = user_request.llm_model_config.model_id
                new_api_key = user_request.llm_model_config.api_key
                if provider and model_id and new_api_key:
                    loader = get_config_loader()
                    provider_cfg_raw = loader.load_provider_config(provider) or {}
                    api_key_env = provider_cfg_raw.get("connection", {}).get(
                        "api_key_env"
                    )
                    # Update environment and clear loader cache so subsequent reads use new key
                    if api_key_env:
                        os.environ[api_key_env] = new_api_key
                        loader.clear_cache()
            except Exception:
                # Best-effort override; continue even if config update fails
                pass

            query = user_request.model_dump_json()

            agent_name = "StrategyAgent"

            # Build UserInput for orchestrator
            user_input_meta = UserInputMetadata(
                user_id="default_user",
                conversation_id=generate_conversation_id(),
            )
            user_input = UserInput(
                query=query,
                target_agent_name=agent_name,
                meta=user_input_meta,
            )

            # Directly use process_user_input instead of stream_query_agent
            async for chunk_obj in orchestrator.process_user_input(user_input):
                event = chunk_obj.event
                data = chunk_obj.data

                if event == CommonResponseEvent.COMPONENT_GENERATOR:
                    content = data.payload.content
                    status_content = StrategyStatusContent.model_validate_json(content)

                    # Persist strategy to database (best-effort)
                    try:
                        db.add(
                            Strategy(
                                strategy_id=status_content.strategy_id,
                                name=(
                                    request.trading_config.strategy_name
                                    or f"Strategy-{status_content.strategy_id[:8]}"
                                ),
                                user_id=user_input_meta.user_id,
                                status=(
                                    status_content.status.value
                                    if hasattr(status_content.status, "value")
                                    else str(status_content.status)
                                ),
                                config=request.model_dump(),
                                strategy_metadata={
                                    "agent_name": agent_name,
                                    "model_provider": request.llm_model_config.provider,
                                    "model_id": request.llm_model_config.model_id,
                                    "exchange_id": request.exchange_config.exchange_id,
                                    "trading_mode": (
                                        request.exchange_config.trading_mode.value
                                        if hasattr(
                                            request.exchange_config.trading_mode,
                                            "value",
                                        )
                                        else str(request.exchange_config.trading_mode)
                                    ),
                                },
                            )
                        )
                        db.commit()
                    except Exception:
                        db.rollback()
                        # Do not fail the API due to persistence error

                    return status_content

            return StrategyStatusContent(strategy_id="unknown", status="error")

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"StrategyAgent create failed: {str(e)}"
            )

    return router
