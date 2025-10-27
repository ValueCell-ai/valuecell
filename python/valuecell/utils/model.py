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
    from valuecell.adapters.models.factory import create_model

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
    from valuecell.adapters.models.factory import create_model_for_agent

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
    from valuecell.adapters.models.factory import create_model

    return create_model(
        model_id=model_id,
        provider=provider,
        use_fallback=False,  # Don't fallback when explicitly requesting a provider
        **kwargs,
    )
