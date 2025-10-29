"""Model utility functions using centralized configuration system.

This module provides convenient functions to create model instances using
the three-tier configuration system (YAML + .env + environment variables).

Migration Notes:
- Old behavior: Hardcoded provider selection based on GOOGLE_API_KEY
- New behavior: Uses ConfigManager with automatic provider selection and fallback
- Backward compatible: Environment variables still work for model_id override
"""

import logging
import os
from typing import Optional

from valuecell.adapters.models.factory import (
    create_embedder,
    create_model,
    create_model_for_agent,
)

logger = logging.getLogger(__name__)


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


def create_model_with_provider(provider: str, model_id: Optional[str] = None, **kwargs):
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

    return create_model(
        model_id=model_id,
        provider=provider,
        use_fallback=False,  # Don't fallback when explicitly requesting a provider
        **kwargs,
    )


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
