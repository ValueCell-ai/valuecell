"""Model-related API schemas."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LLMModelConfigData(BaseModel):
    """LLM model configuration used by frontend to prefill UserRequest.

    This is a relaxed version of agents.strategy_agent.models.LLMModelConfig,
    allowing `api_key` to be optional so the API can return defaults
    even when user credentials are not provided.
    """

    provider: str = Field(
        ..., description="Model provider, e.g. 'openrouter', 'google', 'openai'"
    )
    model_id: str = Field(
        ...,
        description="Model identifier, e.g. 'gpt-4o' or 'deepseek-ai/deepseek-v3.1'",
    )
    api_key: Optional[str] = Field(
        default=None, description="API key for the model provider (may be omitted)"
    )


# Extended provider and model management schemas
class ModelItem(BaseModel):
    model_id: str = Field(..., description="Model identifier")
    model_name: Optional[str] = Field(None, description="Display name of the model")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Optional metadata for the model"
    )


class ModelProviderSummary(BaseModel):
    provider: str = Field(..., description="Provider key, e.g. 'openrouter'")


class ProviderModelEntry(BaseModel):
    model_id: str = Field(..., description="Model identifier")
    model_name: Optional[str] = Field(None, description="Display name of the model")


class ProviderDetailData(BaseModel):
    api_key: Optional[str] = Field(None, description="API key if available")
    base_url: Optional[str] = Field(None, description="API base URL")
    is_default: bool = Field(..., description="Whether this is the primary provider")
    default_model_id: Optional[str] = Field(None, description="Default model id")
    api_key_url: Optional[str] = Field(
        None, description="URL to obtain/apply for the provider's API key"
    )
    models: List[ProviderModelEntry] = Field(
        default_factory=list, description="Available provider models"
    )


class ProviderUpdateRequest(BaseModel):
    api_key: Optional[str] = Field(None, description="New API key to set for provider")
    base_url: Optional[str] = Field(
        None, description="New API base URL to set for provider"
    )


class AddModelRequest(BaseModel):
    model_id: str = Field(..., description="Model identifier to add")
    model_name: Optional[str] = Field(None, description="Optional display name")


class ProviderValidateResponse(BaseModel):
    is_valid: bool = Field(..., description="Validation result")
    error: Optional[str] = Field(None, description="Error message if invalid")


class SetDefaultProviderRequest(BaseModel):
    provider: str = Field(..., description="Provider key to set as default")


class SetDefaultModelRequest(BaseModel):
    model_id: str = Field(..., description="Model identifier to set as default")
    model_name: Optional[str] = Field(
        None,
        description="Optional display name; added/updated in models list if provided",
    )
