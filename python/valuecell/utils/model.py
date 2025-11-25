"""Model utility functions using centralized configuration system.

This module provides convenient functions to create model instances using
the three-tier configuration system (YAML + .env + environment variables).

Migration Notes:
- Old behavior: Hardcoded provider selection based on GOOGLE_API_KEY
- New behavior: Uses ConfigManager with automatic provider selection and fallback
- Backward compatible: Environment variables still work for model_id override
"""

import os
from typing import Optional

from agno.models.base import Model as AgnoModel
from agno.models.google import Gemini as AgnoGeminiModel
from agno.models.openai import OpenAIChat as AgnoOpenAIChatModel
from agno.models.openai import OpenAILike as AgnoOpenAILikeModel
from agno.models.openrouter import OpenRouter as AgnoOpenRouterModel
from agno.models.siliconflow import Siliconflow as AgnoSiliconflowModel
from loguru import logger

from valuecell.adapters.models.factory import (
    create_embedder,
    create_embedder_for_agent,
    create_model,
    create_model_for_agent,
)


def describe_model(model: AgnoModel) -> str:
    try:
        model_description = f"{model.id} (via {model.provider})"
    except Exception:
        model_description = "unknown model/provider"

    return model_description


def model_should_use_json_mode(model: AgnoModel) -> bool:
    """
    Determine if a model should use JSON mode instead of structured outputs.

    JSON mode is required for:
    1. Models that support JSON mode but not OpenAI's structured outputs
    2. OpenAI-compatible APIs that don't support response_format with json_schema

    Returns True for:
    - Google Gemini models
    - OpenAI models (official)
    - DeepSeek models (OpenAI-compatible but no structured outputs support)
    - OpenRouter models (third-party proxy, safer to use JSON mode)
    - SiliconFlow models (OpenAI-compatible but limited structured outputs support)
    - Other OpenAI-compatible APIs (safer default)
    """
    try:
        provider = getattr(model, "provider", None)
        name = getattr(model, "name", None)

        # Google Gemini requires JSON mode
        if provider == AgnoGeminiModel.provider and name == AgnoGeminiModel.name:
            logger.debug("Detected Gemini model - using JSON mode")
            return True

        # Official OpenAI models support both, but JSON mode is more reliable
        if (
            provider == AgnoOpenAIChatModel.provider
            and name == AgnoOpenAIChatModel.name
        ):
            logger.debug("Detected OpenAI model - using JSON mode")
            return True

        # OpenRouter models - third-party proxy supporting many models
        # Use JSON mode for compatibility across different underlying models
        if (
            AgnoOpenRouterModel
            and provider == AgnoOpenRouterModel.provider
            and name == AgnoOpenRouterModel.name
        ):
            logger.debug(
                "Detected OpenRouter model - using JSON mode (third-party proxy)"
            )
            return True

        # SiliconFlow models - OpenAI-compatible but limited structured outputs
        if (
            AgnoSiliconflowModel
            and provider == AgnoSiliconflowModel.provider
            and name == AgnoSiliconflowModel.name
        ):
            logger.debug("Detected SiliconFlow model - using JSON mode")
            return True

        # OpenAI-compatible models (OpenAILike) - check base_url
        if (
            AgnoOpenAILikeModel
            and provider == AgnoOpenAILikeModel.provider
            and name == AgnoOpenAILikeModel.name
        ):
            base_url = getattr(model, "base_url", None)
            if base_url:
                base_url_str = str(base_url).lower()

                # DeepSeek doesn't support structured outputs, only JSON mode
                if "deepseek.com" in base_url_str:
                    logger.debug(
                        "Detected DeepSeek API - forcing JSON mode "
                        "(structured outputs not supported)"
                    )
                    return True

                # For other OpenAI-compatible APIs, use JSON mode as safer default
                # Most OpenAI-compatible APIs support JSON mode but not structured outputs
                logger.debug(
                    f"Detected OpenAI-compatible API ({base_url_str}) - using JSON mode"
                )
                return True

    except Exception as e:
        # Any unexpected condition falls back to JSON mode for safety
        logger.debug(
            f"Exception in model_should_use_json_mode: {e}, defaulting to JSON mode"
        )
        return True

    return False


def get_model(env_key: str, **kwargs):
    """
    Get model instance using configuration system with environment variable override.

    This function replaces the old hardcoded logic with the flexible config system
    while maintaining backward compatibility with existing code.

    Priority for model selection:
    1. Environment variable specified by env_key (e.g., PLANNER_MODEL_ID)
    2. Primary provider's default model from config
    3. Auto-detection based on available API keys

    Args:
        env_key: Environment variable name for model_id override
                 (e.g., "PLANNER_MODEL_ID", "RESEARCH_AGENT_MODEL_ID")
        **kwargs: Additional parameters to pass to model creation
                  (e.g., temperature, max_tokens, search)

    Returns:
        Model instance configured via the config system

    Examples:
        >>> # Use default model from config
        >>> model = get_model("PLANNER_MODEL_ID")

        >>> # Override with environment variable
        >>> # export PLANNER_MODEL_ID="anthropic/claude-3.5-sonnet"
        >>> model = get_model("PLANNER_MODEL_ID")

        >>> # Pass additional parameters
        >>> model = get_model("RESEARCH_AGENT_MODEL_ID", temperature=0.9, max_tokens=8192)

    Raises:
        ValueError: If no provider is available or model creation fails
    """

    # Check if environment variable specifies a model
    model_id = os.getenv(env_key)

    if model_id:
        logger.debug(f"Using model_id from {env_key}: {model_id}")

    # Create model using the factory with proper fallback chain
    try:
        return create_model(
            model_id=model_id,  # Uses provider default if None
            provider=None,  # Auto-detect or use primary provider
            use_fallback=True,  # Enable fallback to other providers
            **kwargs,
        )
    except Exception as e:
        logger.error(f"Failed to create model for {env_key}: {e}")
        # Provide helpful error message
        if "API key" in str(e):
            logger.error(
                "Hint: Make sure to set API keys in .env file. "
                "Check configs/providers/ for required environment variables."
            )
        raise


def get_model_for_agent(agent_name: str, **kwargs):
    """
    Get model configured specifically for an agent.

    This uses the agent's YAML configuration with all three-tier overrides:
    1. Agent YAML file (developer defaults)
    2. .env file (user preferences)
    3. Environment variables (runtime overrides)

    Args:
        agent_name: Agent name matching the config file
                    (e.g., "research_agent" -> configs/agents/research_agent.yaml)
        **kwargs: Override parameters for this specific call

    Returns:
        Model instance configured for the agent

    Examples:
        >>> # Use agent's configured model
        >>> model = get_model_for_agent("research_agent")

        >>> # Override temperature for this call
        >>> model = get_model_for_agent("research_agent", temperature=0.8)

        >>> # Use different model while keeping agent's other configs
        >>> model = get_model_for_agent("research_agent", model_id="gpt-4o")

    Raises:
        ValueError: If agent configuration not found or model creation fails
    """

    try:
        return create_model_for_agent(agent_name, **kwargs)
    except Exception as e:
        logger.error(f"Failed to create model for agent '{agent_name}': {e}")
        raise


def create_model_with_provider(
    provider: str,
    model_id: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs,
):
    """
    Create a model from a specific provider.

    Useful when you need to explicitly use a particular provider
    rather than relying on auto-detection.

    Args:
        provider: Provider name (e.g., "openrouter", "google", "anthropic")
        model_id: Model identifier (uses provider's default if None)
        **kwargs: Additional model parameters

    Returns:
        Model instance from the specified provider

    Examples:
        >>> # Use Google Gemini directly
        >>> model = create_model_with_provider("google", "gemini-2.5-flash")

        >>> # Use OpenRouter with specific model
        >>> model = create_model_with_provider(
        ...     "openrouter",
        ...     "anthropic/claude-3.5-sonnet",
        ...     temperature=0.7
        ... )

    Raises:
        ValueError: If provider not found or not configured
    """

    # If no api_key override is supplied, use the standard factory path.
    if not api_key:
        return create_model(
            model_id=model_id,
            provider=provider,
            use_fallback=False,  # Don't fallback when explicitly requesting a provider
            **kwargs,
        )

    # Minimal override: instantiate the provider class with a copy of its
    # ProviderConfig but using the provided api_key. This avoids changing the
    # global configuration and keeps the change localized to this call.
    try:
        from valuecell.adapters.models.factory import get_model_factory
        from valuecell.config.manager import ProviderConfig, get_config_manager
    except Exception:
        # Fallback to factory convenience if imports fail for some reason
        return create_model(
            model_id=model_id,
            provider=provider,
            use_fallback=False,
            api_key=api_key,
            **kwargs,
        )

    cfg_mgr = get_config_manager()
    existing = cfg_mgr.get_provider_config(provider)
    if not existing:
        raise ValueError(f"Provider configuration not found: {provider}")

    # Build a shallow copy of ProviderConfig overriding api_key
    overridden = ProviderConfig(
        name=existing.name,
        enabled=existing.enabled,
        api_key=api_key,
        base_url=existing.base_url,
        default_model=existing.default_model,
        models=existing.models,
        parameters=existing.parameters,
        default_embedding_model=existing.default_embedding_model,
        embedding_models=existing.embedding_models,
        embedding_parameters=existing.embedding_parameters,
        extra_config=existing.extra_config,
    )

    factory = get_model_factory()
    provider_class = factory._providers.get(provider)
    if not provider_class:
        raise ValueError(f"Unsupported provider: {provider}")

    provider_instance = provider_class(overridden)
    # Delegate to the provider instance directly so the supplied api_key is used
    return provider_instance.create_model(model_id, **kwargs)


# ============================================
# Embedding Functions
# ============================================


def get_embedder(env_key: str = "EMBEDDER_MODEL_ID", **kwargs):
    """
    Get embedder instance using configuration system with environment variable override.

    This function automatically:
    1. Checks if environment variable specifies a model
    2. Selects a provider with embedding support
    3. Falls back to other providers if needed
    4. Uses configuration from YAML + .env + environment variables

    Priority for model selection:
    1. Environment variable specified by env_key (e.g., EMBEDDER_MODEL_ID)
    2. Primary provider's default embedding model from config
    3. Auto-detection based on available providers with embedding support

    Args:
        env_key: Environment variable name for model_id override
                 (e.g., "EMBEDDER_MODEL_ID", "RESEARCH_AGENT_EMBEDDING_MODEL_ID")
        **kwargs: Additional parameters to pass to embedder creation
                  (e.g., dimensions, encoding_format)

    Returns:
        Embedder instance configured via the config system

    Examples:
        >>> # Use default embedding model from config
        >>> embedder = get_embedder()

        >>> # Override with environment variable
        >>> # export EMBEDDER_MODEL_ID="openai/text-embedding-3-large"
        >>> embedder = get_embedder()

        >>> # Use custom env key
        >>> embedder = get_embedder("RESEARCH_AGENT_EMBEDDING_MODEL_ID")

        >>> # Pass additional parameters
        >>> embedder = get_embedder(dimensions=3072, encoding_format="float")

    Raises:
        ValueError: If no provider with embedding support is available
    """
    # Check if environment variable specifies a model
    model_id = os.getenv(env_key)

    if model_id:
        logger.debug(f"Using embedding model from {env_key}: {model_id}")

    # Create embedder using the factory with auto-selection and fallback
    try:
        return create_embedder(
            model_id=model_id,  # Uses provider default if None
            provider=None,  # Auto-detect provider with embedding support
            use_fallback=True,  # Enable fallback to other providers
            **kwargs,
        )
    except Exception as e:
        logger.error(f"Failed to create embedder with {env_key}: {e}")
        # Provide helpful error message
        if "API key" in str(e) or "not found" in str(e):
            logger.error(
                "Hint: Make sure to set API keys in .env file and configure "
                "embedding models in providers/*.yaml files."
            )
        raise


def get_embedder_for_agent(agent_name: str, **kwargs):
    """
    Get an embedder instance configured specifically for an agent.

    This mirrors `get_model_for_agent` but for embedders. It delegates to
    the adapters/models factory which will resolve the agent's embedding
    configuration and provider using the three-tier configuration system.

    Args:
        agent_name: Agent name matching the config file
        **kwargs: Override parameters for this specific call

    Returns:
        Embedder instance configured for the agent

    Raises:
        ValueError: If agent configuration not found or embedder creation fails
    """

    try:
        return create_embedder_for_agent(agent_name, **kwargs)
    except Exception as e:
        logger.error(f"Failed to create embedder for agent '{agent_name}': {e}")
        raise


def create_embedder_with_provider(
    provider: str, model_id: Optional[str] = None, **kwargs
):
    """
    Create an embedder from a specific provider.

    Useful when you need to explicitly use a particular provider
    rather than relying on auto-detection.

    Args:
        provider: Provider name (e.g., "openrouter", "google")
        model_id: Embedding model identifier (uses provider's default if None)
        **kwargs: Additional embedder parameters

    Returns:
        Embedder instance from the specified provider

    Examples:
        >>> # Use OpenRouter for embeddings
        >>> embedder = create_embedder_with_provider("openrouter")

        >>> # Use specific model
        >>> embedder = create_embedder_with_provider(
        ...     "openrouter",
        ...     "openai/text-embedding-3-large",
        ...     dimensions=3072
        ... )

    Raises:
        ValueError: If provider not found or doesn't support embeddings
    """

    return create_embedder(
        model_id=model_id,
        provider=provider,
        use_fallback=False,  # Don't fallback when explicitly requesting a provider
        **kwargs,
    )
