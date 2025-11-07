"""Model-related API schemas."""

from typing import Optional

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


class LLMProviderConfigData(BaseModel):
    """LLM provider configuration without model_id for /models/llm/config endpoint."""

    provider: str = Field(
        ..., description="Model provider, e.g. 'openrouter', 'google', 'openai'"
    )
    api_key: Optional[str] = Field(
        default=None, description="API key for the model provider (may be omitted)"
    )
