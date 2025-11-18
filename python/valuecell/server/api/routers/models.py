"""Models API router: provide LLM model configuration defaults."""

import os
from pathlib import Path
from typing import List

import yaml
from fastapi import APIRouter, HTTPException, Query

from valuecell.config.constants import CONFIG_DIR, PROJECT_ROOT
from valuecell.config.loader import get_config_loader
from valuecell.config.manager import get_config_manager

from ..schemas import LLMProviderConfigData, SuccessResponse
from ..schemas.model import (
    AddModelRequest,
    ModelItem,
    ModelProviderSummary,
    ProviderDetailData,
    ProviderModelEntry,
    ProviderUpdateRequest,
    SetDefaultModelRequest,
    SetDefaultProviderRequest,
)

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
    """Create models-related router with endpoints for model configs and provider management."""

    router = APIRouter(prefix="/models", tags=["Models"])

    # ---- Utility helpers (local to router) ----
    def _env_path() -> Path:
        return PROJECT_ROOT / ".env"

    def _set_env(key: str, value: str) -> bool:
        os.environ[key] = value
        env_file = _env_path()
        lines: List[str] = []
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        updated = False
        found = False
        new_lines: List[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                found = True
                updated = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key}={value}\n")
            updated = True
        with open(env_file, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return updated

    def _provider_yaml(provider: str) -> Path:
        return CONFIG_DIR / "providers" / f"{provider}.yaml"

    def _load_yaml(path: Path) -> dict:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _write_yaml(path: Path, data: dict) -> None:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    def _refresh_configs() -> None:
        loader = get_config_loader()
        loader.clear_cache()
        manager = get_config_manager()
        manager._config = manager.loader.load_config()

    def _preferred_provider_order(names: List[str]) -> List[str]:
        """Return providers ordered with preferred defaults first.

        Ensures 'openrouter' is first and 'siliconflow' is second when present,
        followed by the remaining providers in their original order.
        """
        preferred = ["openrouter", "siliconflow"]
        seen = set()
        ordered: List[str] = []

        # Add preferred providers in order if they exist
        for p in preferred:
            if p in names and p not in seen:
                ordered.append(p)
                seen.add(p)

        # Append the rest while preserving original order
        for name in names:
            if name not in seen:
                ordered.append(name)
                seen.add(name)

        return ordered

    def _api_key_url_for(provider: str) -> str | None:
        """Return the URL for obtaining an API key for the given provider."""
        mapping = {
            "google": "https://aistudio.google.com/app/api-keys",
            "openrouter": "https://openrouter.ai/settings/keys",
            "openai": "https://platform.openai.com/api-keys",
            "azure": "https://azure.microsoft.com/en-us/products/ai-foundry/models/openai/",
            "siliconflow": "https://cloud.siliconflow.cn/account/ak",
            "deepseek": "https://platform.deepseek.com/api_keys",
        }
        return mapping.get(provider)

    # ---- Existing: LLM config list ----
    @router.get(
        "/llm/config",
        response_model=SuccessResponse[List[LLMProviderConfigData]],
        summary="Get available LLMModelConfigs",
        description=(
            "Return a list of LLM model configurations for the primary provider "
            "and any enabled fallback providers. API keys may be omitted if not configured."
        ),
    )
    async def get_llm_model_config() -> SuccessResponse[List[LLMProviderConfigData]]:
        try:
            manager = get_config_manager()

            providers = [manager.primary_provider] + manager.fallback_providers
            seen = set()
            ordered = [p for p in providers if not (p in seen or seen.add(p))]

            configs: List[LLMProviderConfigData] = []
            for provider in ordered:
                provider_cfg = manager.get_provider_config(provider)
                if provider_cfg is None:
                    configs.append(
                        LLMProviderConfigData(
                            provider=DEFAULT_MODEL_PROVIDER, api_key=None
                        )
                    )
                else:
                    configs.append(
                        LLMProviderConfigData(
                            provider=provider_cfg.name,
                            api_key=provider_cfg.api_key,
                        )
                    )

            if not configs:
                configs.append(
                    LLMProviderConfigData(provider=DEFAULT_MODEL_PROVIDER, api_key=None)
                )

            return SuccessResponse.create(
                data=configs, msg=f"Retrieved {len(configs)} LLM provider configs"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get LLM config list: {str(e)}"
            )

    @router.get(
        "/providers",
        response_model=SuccessResponse[List[ModelProviderSummary]],
        summary="List model providers",
        description="List available providers with status and basics.",
    )
    async def list_providers() -> SuccessResponse[List[ModelProviderSummary]]:
        try:
            manager = get_config_manager()
            loader = get_config_loader()
            # Prefer default ordering: openrouter first, siliconflow second
            names = _preferred_provider_order(loader.list_providers())
            items: List[ModelProviderSummary] = []
            for name in names:
                cfg = manager.get_provider_config(name)
                if not cfg:
                    continue
                items.append(
                    ModelProviderSummary(
                        provider=cfg.name,
                    )
                )
            return SuccessResponse.create(
                data=items, msg=f"Retrieved {len(items)} providers"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to list providers: {e}"
            )

    @router.get(
        "/providers/{provider}",
        response_model=SuccessResponse[ProviderDetailData],
        summary="Get provider details",
        description="Get configuration and models for a provider.",
    )
    async def get_provider_detail(provider: str) -> SuccessResponse[ProviderDetailData]:
        try:
            manager = get_config_manager()
            cfg = manager.get_provider_config(provider)
            if cfg is None:
                raise HTTPException(
                    status_code=404, detail=f"Provider '{provider}' not found"
                )
            models_entries: List[ProviderModelEntry] = []
            for m in cfg.models or []:
                if isinstance(m, dict):
                    mid = m.get("id")
                    name = m.get("name")
                    if mid:
                        models_entries.append(
                            ProviderModelEntry(model_id=mid, model_name=name)
                        )
            detail = ProviderDetailData(
                api_key=cfg.api_key,
                base_url=cfg.base_url,
                is_default=(cfg.name == manager.primary_provider),
                default_model_id=cfg.default_model,
                api_key_url=_api_key_url_for(cfg.name),
                models=models_entries,
            )
            return SuccessResponse.create(
                data=detail, msg=f"Provider '{provider}' details"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get provider: {e}")

    @router.put(
        "/providers/{provider}/config",
        response_model=SuccessResponse[ProviderDetailData],
        summary="Update provider config",
        description="Update provider API key and host, then refresh configs.",
    )
    async def update_provider_config(
        provider: str, payload: ProviderUpdateRequest
    ) -> SuccessResponse[ProviderDetailData]:
        try:
            loader = get_config_loader()
            provider_raw = loader.load_provider_config(provider)
            if not provider_raw:
                raise HTTPException(
                    status_code=404, detail=f"Provider '{provider}' not found"
                )

            connection = provider_raw.get("connection", {})
            api_key_env = connection.get("api_key_env")
            endpoint_env = connection.get("endpoint_env")

            # Update API key via env var
            if payload.api_key and api_key_env:
                _set_env(api_key_env, payload.api_key)

            # Update base_url via env when endpoint_env exists (Azure), otherwise YAML
            if payload.base_url:
                if endpoint_env:
                    _set_env(endpoint_env, payload.base_url)
                else:
                    path = _provider_yaml(provider)
                    data = _load_yaml(path)
                    data.setdefault("connection", {})
                    data["connection"]["base_url"] = payload.base_url
                    _write_yaml(path, data)

            _refresh_configs()

            # Return updated detail
            manager = get_config_manager()
            cfg = manager.get_provider_config(provider)
            if not cfg:
                raise HTTPException(
                    status_code=500, detail="Provider not found after update"
                )
            models_items = [
                ProviderModelEntry(model_id=m.get("id", ""), model_name=m.get("name"))
                for m in (cfg.models or [])
                if isinstance(m, dict)
            ]

            detail = ProviderDetailData(
                api_key=cfg.api_key,
                base_url=cfg.base_url,
                is_default=(cfg.name == manager.primary_provider),
                default_model_id=cfg.default_model,
                models=models_items,
            )
            return SuccessResponse.create(
                data=detail, msg=f"Provider '{provider}' config updated"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update provider config: {e}"
            )

    @router.post(
        "/providers/{provider}/models",
        response_model=SuccessResponse[ModelItem],
        summary="Add provider model",
        description="Add a model id to provider YAML.",
    )
    async def add_provider_model(
        provider: str, payload: AddModelRequest
    ) -> SuccessResponse[ModelItem]:
        try:
            path = _provider_yaml(provider)
            data = _load_yaml(path)
            if not data:
                raise HTTPException(
                    status_code=404, detail=f"Provider '{provider}' not found"
                )
            models = data.get("models") or []
            for m in models:
                if isinstance(m, dict) and m.get("id") == payload.model_id:
                    if payload.model_name:
                        m["name"] = payload.model_name
                    _write_yaml(path, data)
                    _refresh_configs()
                    return SuccessResponse.create(
                        data=ModelItem(
                            model_id=payload.model_id, model_name=m.get("name")
                        ),
                        msg="Model already exists; updated model_name if provided",
                    )
            models.append(
                {"id": payload.model_id, "name": payload.model_name or payload.model_id}
            )
            data["models"] = models
            _write_yaml(path, data)
            _refresh_configs()
            return SuccessResponse.create(
                data=ModelItem(
                    model_id=payload.model_id,
                    model_name=payload.model_name or payload.model_id,
                ),
                msg="Model added",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to add model: {e}")

    @router.delete(
        "/providers/{provider}/models",
        response_model=SuccessResponse[dict],
        summary="Remove provider model",
        description="Remove a model id from provider YAML.",
    )
    async def remove_provider_model(
        provider: str,
        model_id: str = Query(..., description="Model identifier to remove"),
    ) -> SuccessResponse[dict]:
        try:
            path = _provider_yaml(provider)
            data = _load_yaml(path)
            if not data:
                raise HTTPException(
                    status_code=500, detail=f"Provider '{provider}' not found"
                )
            models = data.get("models") or []
            before = len(models)
            models = [
                m
                for m in models
                if not (isinstance(m, dict) and m.get("id") == model_id)
            ]
            after = len(models)
            data["models"] = models
            _write_yaml(path, data)
            _refresh_configs()
            removed = before != after
            return SuccessResponse.create(
                data={"removed": removed, "remaining": after},
                msg="Model removed" if removed else "Model not found",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to remove model: {e}")

    @router.put(
        "/providers/default",
        response_model=SuccessResponse[dict],
        summary="Set default provider",
        description="Set PRIMARY_PROVIDER via env and refresh configs.",
    )
    async def set_default_provider(
        payload: SetDefaultProviderRequest,
    ) -> SuccessResponse[dict]:
        try:
            _set_env("PRIMARY_PROVIDER", payload.provider)
            _refresh_configs()
            manager = get_config_manager()
            return SuccessResponse.create(
                data={"primary_provider": manager.primary_provider},
                msg=f"Primary provider set to '{payload.provider}'",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to set default provider: {e}"
            )

    @router.put(
        "/providers/{provider}/default-model",
        response_model=SuccessResponse[ProviderDetailData],
        summary="Set provider default model",
        description="Update provider default_model in YAML and refresh configs.",
    )
    async def set_provider_default_model(
        provider: str, payload: SetDefaultModelRequest
    ) -> SuccessResponse[ProviderDetailData]:
        try:
            path = _provider_yaml(provider)
            data = _load_yaml(path)
            if not data:
                raise HTTPException(
                    status_code=404, detail=f"Provider '{provider}' not found"
                )

            # Ensure the model exists in the list and optionally update name
            models = data.get("models") or []
            found = False
            for m in models:
                if isinstance(m, dict) and m.get("id") == payload.model_id:
                    if payload.model_name:
                        m["name"] = payload.model_name
                    found = True
                    break
            if not found:
                models.append(
                    {
                        "id": payload.model_id,
                        "name": payload.model_name or payload.model_id,
                    }
                )
            data["models"] = models

            # Set default model
            data["default_model"] = payload.model_id
            _write_yaml(path, data)
            _refresh_configs()

            # Build response from refreshed config
            manager = get_config_manager()
            cfg = manager.get_provider_config(provider)
            if not cfg:
                raise HTTPException(
                    status_code=500, detail="Provider not found after update"
                )
            models_items = [
                ProviderModelEntry(model_id=m.get("id", ""), model_name=m.get("name"))
                for m in (cfg.models or [])
                if isinstance(m, dict)
            ]
            detail = ProviderDetailData(
                api_key=cfg.api_key,
                base_url=cfg.base_url,
                is_default=(cfg.name == manager.primary_provider),
                default_model_id=cfg.default_model,
                models=models_items,
            )
            return SuccessResponse.create(
                data=detail,
                msg=(f"Default model for '{provider}' set to '{payload.model_id}'"),
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to set default model: {e}"
            )

    return router
