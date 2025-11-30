"""
StrategyAgent router for handling strategy creation via streaming responses.
"""

import os

# New imports for delete endpoint
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.orm import Session

from valuecell.agents.common.trading.models import (
    ExchangeConfig,
    StrategyStatus,
    StrategyStatusContent,
    StrategyType,
    UserRequest,
)
from valuecell.config.loader import get_config_loader
from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.core.types import CommonResponseEvent, UserInput, UserInputMetadata
from valuecell.server.api.schemas.base import SuccessResponse

# Note: Strategy type is now part of TradingConfig in the request body.
from valuecell.server.db.connection import get_db
from valuecell.server.db.repositories import get_strategy_repository
from valuecell.server.services.strategy_autoresume import auto_resume_strategies
from valuecell.utils.uuid import generate_conversation_id, generate_uuid


def create_strategy_agent_router() -> APIRouter:
    """Create and configure the StrategyAgent router."""

    router = APIRouter(prefix="/strategies", tags=["strategies"])
    orchestrator = AgentOrchestrator()

    @router.on_event("startup")
    async def _startup_auto_resume() -> None:
        """Schedule strategy auto-resume on FastAPI startup."""
        try:
            await auto_resume_strategies(orchestrator)
        except Exception:
            logger.warning("Failed to schedule strategy auto-resume startup task")

    @router.post("/create")
    async def create_strategy_agent(
        request: UserRequest,
        db: Session = Depends(get_db),
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

            # Prepare repository with injected session (used below and for prompt resolution)
            repo = get_strategy_repository(db_session=db)

            # If a prompt_id (previously template_id) is provided but prompt_text is empty,
            # attempt to resolve it from the prompts table and populate trading_config.prompt_text.
            try:
                prompt_id = user_request.trading_config.template_id
                if prompt_id and not user_request.trading_config.prompt_text:
                    try:
                        prompt_item = repo.get_prompt_by_id(prompt_id)
                        if prompt_item is not None:
                            # prompt_item may be an ORM object or dict-like; use attribute or key access
                            content = prompt_item.content
                            if content:
                                user_request.trading_config.prompt_text = content
                                logger.info(
                                    "Resolved prompt_id={} to prompt_text for strategy creation",
                                    prompt_id,
                                )
                    except Exception:
                        logger.exception(
                            "Failed to load prompt for prompt_id={}; continuing without resolved prompt",
                            prompt_id,
                        )
            except Exception:
                # Defensive: any unexpected error here should not block strategy creation
                logger.exception(
                    "Unexpected error while resolving prompt_id before strategy creation"
                )

            query = user_request.model_dump_json()

            # Use enum directly for comparison; derive human-readable label for metadata
            strategy_type_enum = (
                user_request.trading_config.strategy_type or StrategyType.PROMPT
            )

            if strategy_type_enum == StrategyType.PROMPT:
                agent_name = "PromptBasedStrategyAgent"
            elif strategy_type_enum == StrategyType.GRID:
                agent_name = "GridStrategyAgent"
            else:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unsupported strategy_type: '{strategy_type_enum}'. "
                        "Use 'PromptBasedStrategy' or 'GridStrategy'"
                    ),
                )

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

            # Prepare repository with injected session
            repo = get_strategy_repository(db_session=db)

            # Directly use process_user_input instead of stream_query_agent
            try:
                async for chunk_obj in orchestrator.process_user_input(user_input):
                    event = chunk_obj.event
                    data = chunk_obj.data

                    if event == CommonResponseEvent.COMPONENT_GENERATOR:
                        content = data.payload.content
                        status_content = StrategyStatusContent.model_validate_json(
                            content
                        )

                        # Persist strategy to database via repository (best-effort)
                        try:
                            name = (
                                request.trading_config.strategy_name
                                or f"Strategy-{status_content.strategy_id[:8]}"
                            )
                            metadata = {
                                "agent_name": agent_name,
                                "strategy_type": strategy_type_enum,
                                "model_provider": request.llm_model_config.provider,
                                "model_id": request.llm_model_config.model_id,
                                "exchange_id": request.exchange_config.exchange_id,
                                "trading_mode": request.exchange_config.trading_mode.value,
                            }
                            status = status_content.status
                            if status == StrategyStatus.STOPPED:
                                metadata["stop_reason"] = (
                                    status_content.stop_reason.value
                                )
                                metadata["stop_reason_detail"] = (
                                    status_content.stop_reason_detail
                                )
                            repo.upsert_strategy(
                                strategy_id=status_content.strategy_id,
                                name=name,
                                description=None,
                                user_id=user_input_meta.user_id,
                                status=status.value,
                                config=request.model_dump(),
                                metadata=metadata,
                            )
                        except Exception:
                            # Do not fail the API due to persistence error
                            pass

                        return status_content

                # If no status event received, fallback to DB-only creation
                fallback_strategy_id = generate_uuid("strategy")
                try:
                    name = (
                        request.trading_config.strategy_name
                        or f"Strategy-{fallback_strategy_id.split('-')[-1][:8]}"
                    )
                    metadata = {
                        "agent_name": agent_name,
                        "strategy_type": strategy_type_enum,
                        "model_provider": request.llm_model_config.provider,
                        "model_id": request.llm_model_config.model_id,
                        "exchange_id": request.exchange_config.exchange_id,
                        "trading_mode": (
                            request.exchange_config.trading_mode.value
                            if hasattr(request.exchange_config.trading_mode, "value")
                            else str(request.exchange_config.trading_mode)
                        ),
                        "fallback": True,
                        "stop_reason": "error",
                        "stop_reason_detail": "No status event from orchestrator",
                    }
                    repo.upsert_strategy(
                        strategy_id=fallback_strategy_id,
                        name=name,
                        description=None,
                        user_id=user_input_meta.user_id,
                        status="stopped",
                        config=request.model_dump(),
                        metadata=metadata,
                    )
                except Exception:
                    pass

                return StrategyStatusContent(
                    strategy_id=fallback_strategy_id, status="stopped"
                )
            except Exception as exc:
                # Orchestrator failed; fallback to direct DB creation
                fallback_strategy_id = generate_uuid("strategy")
                try:
                    name = (
                        request.trading_config.strategy_name
                        or f"Strategy-{fallback_strategy_id.split('-')[-1][:8]}"
                    )
                    metadata = {
                        "agent_name": agent_name,
                        "strategy_type": strategy_type_enum,
                        "model_provider": request.llm_model_config.provider,
                        "model_id": request.llm_model_config.model_id,
                        "exchange_id": request.exchange_config.exchange_id,
                        "trading_mode": (
                            request.exchange_config.trading_mode.value
                            if hasattr(request.exchange_config.trading_mode, "value")
                            else str(request.exchange_config.trading_mode)
                        ),
                        "fallback": True,
                        "stop_reason": "error",
                        "stop_reason_detail": str(exc),
                    }
                    repo.upsert_strategy(
                        strategy_id=fallback_strategy_id,
                        name=name,
                        description=None,
                        user_id=user_input_meta.user_id,
                        status="stopped",
                        config=request.model_dump(),
                        metadata=metadata,
                    )
                except Exception:
                    pass
                return StrategyStatusContent(
                    strategy_id=fallback_strategy_id, status="stopped"
                )

        except Exception as e:
            # As a last resort, log the exception and attempt to create a DB record
            # with "error" status, then return a structured error.
            logger.exception(f"Failed to create strategy in API endpoint: {e}")
            fallback_strategy_id = generate_uuid("strategy")
            try:
                repo = get_strategy_repository(db_session=db)
                name = (
                    request.trading_config.strategy_name
                    or f"Strategy-{fallback_strategy_id.split('-')[-1][:8]}"
                )
                metadata = {
                    "agent_name": agent_name,
                    "strategy_type": strategy_type_enum,
                    "model_provider": request.llm_model_config.provider,
                    "model_id": request.llm_model_config.model_id,
                    "exchange_id": request.exchange_config.exchange_id,
                    "trading_mode": (
                        request.exchange_config.trading_mode.value
                        if hasattr(request.exchange_config.trading_mode, "value")
                        else str(request.exchange_config.trading_mode)
                    ),
                    "fallback": True,
                    "stop_reason": "error",
                    "stop_reason_detail": str(e),
                }
                repo.upsert_strategy(
                    strategy_id=fallback_strategy_id,
                    name=name,
                    description=f"Failed to create strategy: {str(e)}",
                    user_id="default_user",  # Assuming a default user
                    status=StrategyStatus.ERROR.value,
                    config=request.model_dump(),
                    metadata=metadata,
                )
            except Exception as db_exc:
                logger.exception(
                    f"Failed to persist error state for strategy: {db_exc}"
                )
                # If DB persistence also fails, return a generic error without a valid ID
                return StrategyStatusContent(
                    strategy_id="unknown", status=StrategyStatus.ERROR
                )

            return StrategyStatusContent(
                strategy_id=fallback_strategy_id, status=StrategyStatus.ERROR
            )

    @router.post("/test-connection")
    async def test_exchange_connection(request: ExchangeConfig):
        """Test connection to the exchange with provided credentials."""
        try:
            # If virtual trading, just return success immediately
            if getattr(request, "trading_mode", None) == "virtual":
                return SuccessResponse.create(msg="Success!")

            from valuecell.agents.common.trading.execution.ccxt_trading import (
                create_ccxt_gateway,
            )

            # Map ExchangeConfig fields to gateway args
            # Note: ExchangeConfig might differ slightly from create_ccxt_gateway args
            gateway = await create_ccxt_gateway(
                exchange_id=request.exchange_id,
                api_key=request.api_key or "",
                secret_key=request.secret_key or "",
                passphrase=request.passphrase,
                wallet_address=request.wallet_address,
                private_key=request.private_key,
                # Ensure we pass a safe default for required args if missing in config
                market_type="swap",  # Default to swap/perpetual for testing
            )

            try:
                is_connected = await gateway.test_connection()
                if is_connected:
                    return SuccessResponse.create(msg="Success!")
                else:
                    # Return 200 with error message or 400? User asked for "Failed..." return
                    # We'll throw 400 for UI to catch, or return success=False in body
                    # But SuccessResponse implies 200.
                    # If I raise HTTPException it shows as error.
                    raise HTTPException(
                        status_code=400, detail="Failed, please check your API key"
                    )
            finally:
                await gateway.close()

        except Exception as e:
            # If create_ccxt_gateway fails or other error
            logger.warning(f"Connection test failed: {e}")
            raise HTTPException(
                status_code=400, detail=f"Failed, please check your API key: {str(e)}"
            )

    @router.delete("/delete")
    async def delete_strategy_agent(
        id: str = Query(..., description="Strategy ID"),
        cascade: bool = Query(
            True, description="Delete related records (holdings/details/portfolio)"
        ),
        db: Session = Depends(get_db),
    ):
        """Delete a strategy created by StrategyAgent.

        - Validates the strategy exists.
        - Ensures the strategy is stopped before deletion (idempotent stop).
        - Optionally cascades deletion to holdings, portfolio snapshots, and details.
        - Returns a success response when completed.
        """
        try:
            repo = get_strategy_repository(db_session=db)
            strategy = repo.get_strategy_by_strategy_id(id)
            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")

            # Stop strategy before deletion (best-effort, idempotent)
            try:
                current_status = getattr(strategy, "status", None)
                if current_status != "stopped":
                    repo.upsert_strategy(strategy_id=id, status="stopped")
            except Exception:
                # Do not fail deletion due to stop failure; proceed to deletion
                pass

            ok = repo.delete_strategy(id, cascade=cascade)
            if not ok:
                raise HTTPException(status_code=500, detail="Failed to delete strategy")

            return SuccessResponse.create(
                data={"strategy_id": id},
                msg=f"Strategy '{id}' stopped (if running) and deleted successfully",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error deleting strategy: {str(e)}"
            )

    return router
