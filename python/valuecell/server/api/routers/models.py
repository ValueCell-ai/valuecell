"""Models API router: provide LLM model configuration defaults."""

from typing import List

from fastapi import APIRouter, HTTPException

from valuecell.config.manager import get_config_manager

from ..schemas import LLMModelConfigData, SuccessResponse

# Optional fallback constants from StrategyAgent
try:
    from valuecell.agents.strategy_agent.constants import (
        DEFAULT_AGENT_MODEL,
        DEFAULT_MODEL_PROVIDER,
    )
except Exception:  # pragma: no cover - constants may not exist in minimal env
    DEFAULT_MODEL_PROVIDER = "openrouter"
    DEFAULT_AGENT_MODEL = "gpt-4o"


def create_models_router() -> APIRouter:
    """Create models-related router with endpoints for model configs."""

    router = APIRouter(prefix="/models", tags=["Models"])

    @router.get(
        "/llm/config",
        response_model=SuccessResponse[List[LLMModelConfigData]],
        summary="Get available LLMModelConfigs",
        description=(
            "Return a list of LLM model configurations for the primary provider "
            "and any enabled fallback providers. API keys may be omitted if not configured."
        ),
    )
    async def get_llm_model_config() -> SuccessResponse[List[LLMModelConfigData]]:
        try:
            manager = get_config_manager()

            # Build ordered provider list: primary first, then fallbacks
            providers = [manager.primary_provider] + manager.fallback_providers
            # Deduplicate while preserving order
            seen = set()
            ordered = [p for p in providers if not (p in seen or seen.add(p))]

            configs: List[LLMModelConfigData] = []
            for provider in ordered:
                provider_cfg = manager.get_provider_config(provider)
                if provider_cfg is None:
                    configs.append(
                        LLMModelConfigData(
                            provider=DEFAULT_MODEL_PROVIDER,
                            model_id=DEFAULT_AGENT_MODEL,
                            api_key=None,
                        )
                    )
                else:
                    model_id = provider_cfg.default_model or DEFAULT_AGENT_MODEL
                    configs.append(
                        LLMModelConfigData(
                            provider=provider_cfg.name,
                            model_id=model_id,
                            api_key=provider_cfg.api_key,
                        )
                    )

            # If no providers were detected, return a single default entry
            if not configs:
                configs.append(
                    LLMModelConfigData(
                        provider=DEFAULT_MODEL_PROVIDER,
                        model_id=DEFAULT_AGENT_MODEL,
                        api_key=None,
                    )
                )

            return SuccessResponse.create(
                data=configs, msg=f"Retrieved {len(configs)} LLMModelConfigs"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get LLM config list: {str(e)}"
            )

    return router
