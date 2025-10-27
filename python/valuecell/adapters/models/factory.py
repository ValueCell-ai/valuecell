"""
Model Factory - Creates model instances using the three-tier configuration system

This factory:
1. Loads configuration from YAML + .env + environment variables
2. Validates provider credentials
3. Creates appropriate model instances with correct parameters
4. Supports fallback providers for reliability
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from valuecell.config.manager import ConfigManager, ProviderConfig, get_config_manager

logger = logging.getLogger(__name__)


class ModelProvider(ABC):
    """Abstract base class for model providers"""

    def __init__(self, config: ProviderConfig):
        """
        Initialize provider

        Args:
            config: Provider configuration
        """
        self.config = config

    @abstractmethod
    def create_model(self, model_id: Optional[str] = None, **kwargs):
        """
        Create a model instance

        Args:
            model_id: Model identifier (uses default if None)
            **kwargs: Additional model parameters

        Returns:
            Model instance
        """
        pass

    def is_available(self) -> bool:
        """
        Check if provider credentials are available

        Returns:
            True if provider can be used
        """
        # Default implementation: check API key
        return bool(self.config.api_key)


class OpenRouterProvider(ModelProvider):
    """OpenRouter model provider"""

    def create_model(self, model_id: Optional[str] = None, **kwargs):
        """Create OpenRouter model via agno"""
        try:
            from agno.models.openrouter import OpenRouter
        except ImportError:
            raise ImportError(
                "agno package not installed. Install with: pip install agno"
            )

        # Use provided model_id or default
        model_id = model_id or self.config.default_model

        # Merge parameters: provider defaults < kwargs
        params = {**self.config.parameters, **kwargs}

        # Get extra headers from config
        extra_headers = self.config.extra_config.get("extra_headers", {})

        logger.info(f"Creating OpenRouter model: {model_id}")

        return OpenRouter(
            id=model_id,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            extra_headers=extra_headers if extra_headers else None,
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
            top_p=params.get("top_p"),
            frequency_penalty=params.get("frequency_penalty"),
            presence_penalty=params.get("presence_penalty"),
        )


class GoogleProvider(ModelProvider):
    """Google Gemini model provider"""

    def create_model(self, model_id: Optional[str] = None, **kwargs):
        """Create Google Gemini model via agno"""
        try:
            from agno.models.google import Gemini
        except ImportError:
            raise ImportError(
                "agno package not installed. Install with: pip install agno"
            )

        model_id = model_id or self.config.default_model
        params = {**self.config.parameters, **kwargs}

        logger.info(f"Creating Google Gemini model: {model_id}")

        return Gemini(
            id=model_id,
            api_key=self.config.api_key,
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
        )


class AzureProvider(ModelProvider):
    """Azure OpenAI model provider"""

    def create_model(self, model_id: Optional[str] = None, **kwargs):
        """Create Azure OpenAI model"""
        try:
            # Try to import from agno first
            from agno.models.azure import AzureOpenAI
        except ImportError:
            try:
                # Fallback to langchain
                from langchain_openai import AzureChatOpenAI as AzureOpenAI
            except ImportError:
                raise ImportError("No Azure OpenAI library found")

        model_id = model_id or self.config.default_model
        params = {**self.config.parameters, **kwargs}

        api_version = self.config.extra_config.get("api_version", "2024-10-21")

        logger.info(f"Creating Azure OpenAI model: {model_id}")

        return AzureOpenAI(
            deployment_name=model_id,
            api_key=self.config.api_key,
            azure_endpoint=self.config.base_url,
            api_version=api_version,
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
        )

    def is_available(self) -> bool:
        """Azure needs both API key and endpoint"""
        return bool(self.config.api_key and self.config.base_url)


class AnthropicProvider(ModelProvider):
    """Anthropic Claude model provider"""

    def create_model(self, model_id: Optional[str] = None, **kwargs):
        """Create Anthropic Claude model"""
        try:
            from agno.models.anthropic import Claude
        except ImportError:
            raise ImportError("agno package not installed")

        model_id = model_id or self.config.default_model
        params = {**self.config.parameters, **kwargs}

        logger.info(f"Creating Anthropic Claude model: {model_id}")

        return Claude(
            id=model_id,
            api_key=self.config.api_key,
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
        )


class DeepSeekProvider(ModelProvider):
    """DeepSeek model provider (via OpenAI-compatible API)"""

    def create_model(self, model_id: Optional[str] = None, **kwargs):
        """Create DeepSeek model"""
        try:
            from agno.models.openrouter import OpenRouter
        except ImportError:
            raise ImportError("agno package not installed")

        model_id = model_id or self.config.default_model
        params = {**self.config.parameters, **kwargs}

        logger.info(f"Creating DeepSeek model: {model_id}")

        # DeepSeek uses OpenAI-compatible API
        return OpenRouter(
            id=model_id,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
        )


class ModelFactory:
    """
    Factory for creating model instances with provider abstraction

    Features:
    - Three-tier configuration (YAML + .env + env vars)
    - Provider validation
    - Fallback provider support
    - Parameter merging
    """

    # Registry of provider classes
    _providers: Dict[str, type[ModelProvider]] = {
        "openrouter": OpenRouterProvider,
        "google": GoogleProvider,
        "azure": AzureProvider,
        "anthropic": AnthropicProvider,
        "deepseek": DeepSeekProvider,
    }

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize model factory

        Args:
            config_manager: ConfigManager instance (auto-created if None)
        """
        self.config_manager = config_manager or get_config_manager()

    def register_provider(self, name: str, provider_class: type[ModelProvider]):
        """
        Register a custom provider

        Args:
            name: Provider name
            provider_class: Provider class
        """
        self._providers[name] = provider_class
        logger.info(f"Registered custom provider: {name}")

    def create_model(
        self,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        use_fallback: bool = True,
        **kwargs,
    ):
        """
        Create a model instance with automatic provider selection

        Priority:
        1. Specified provider parameter
        2. PRIMARY_PROVIDER env var
        3. Primary provider from config.yaml

        Args:
            model_id: Specific model ID (optional, uses provider default)
            provider: Provider name (optional, uses primary_provider)
            use_fallback: Try fallback providers if primary fails
            **kwargs: Additional arguments for model creation

        Returns:
            Model instance

        Raises:
            ValueError: If provider is not available or not supported

        Examples:
            >>> factory = ModelFactory()
            >>> model = factory.create_model()  # Uses primary provider + default model
            >>> model = factory.create_model(provider="google")  # Specific provider
            >>> model = factory.create_model(model_id="gpt-4", provider="openrouter")
        """
        provider = provider or self.config_manager.primary_provider

        # Try primary provider
        try:
            return self._create_model_internal(model_id, provider, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to create model with provider {provider}: {e}")

            if not use_fallback:
                raise

            # Try fallback providers
            for fallback_provider in self.config_manager.fallback_providers:
                if fallback_provider == provider:
                    continue  # Skip already tried provider

                try:
                    logger.info(f"Trying fallback provider: {fallback_provider}")
                    return self._create_model_internal(
                        model_id, fallback_provider, **kwargs
                    )
                except Exception as fallback_error:
                    logger.warning(
                        f"Fallback provider {fallback_provider} also failed: {fallback_error}"
                    )
                    continue

            # All providers failed
            raise ValueError(
                f"Failed to create model. Primary provider ({provider}) "
                f"and all fallback providers failed. Original error: {e}"
            )

    def _create_model_internal(self, model_id: Optional[str], provider: str, **kwargs):
        """
        Internal method to create model without fallback logic

        Args:
            model_id: Model ID
            provider: Provider name
            **kwargs: Model parameters

        Returns:
            Model instance
        """
        # Check if provider is registered
        if provider not in self._providers:
            raise ValueError(f"Unsupported provider: {provider}")

        # Get provider configuration
        provider_config = self.config_manager.get_provider_config(provider)
        if not provider_config:
            raise ValueError(f"Provider configuration not found: {provider}")

        # Validate provider
        is_valid, error_msg = self.config_manager.validate_provider(provider)
        if not is_valid:
            raise ValueError(f"Provider validation failed: {error_msg}")

        # Create provider instance
        provider_class = self._providers[provider]
        provider_instance = provider_class(provider_config)

        # Create model
        return provider_instance.create_model(model_id, **kwargs)

    def create_model_for_agent(
        self, agent_name: str, use_fallback: bool = True, **kwargs
    ):
        """
        Create model for a specific agent using its configuration

        This method:
        1. Loads agent config (with all three-tier overrides)
        2. Gets model_id and provider from agent config
        3. Merges agent parameters with kwargs
        4. Creates model instance

        Args:
            agent_name: Agent name
            use_fallback: Try fallback providers if primary fails
            **kwargs: Override parameters

        Returns:
            Model instance configured for the agent

        Example:
            >>> factory = ModelFactory()
            >>> model = factory.create_model_for_agent("research_agent")
            >>> # Uses model_id and provider from research_agent.yaml + overrides
        """
        # Get agent configuration
        agent_config = self.config_manager.get_agent_config(agent_name)

        if not agent_config:
            raise ValueError(f"Agent configuration not found: {agent_name}")

        if not agent_config.enabled:
            raise ValueError(f"Agent is disabled: {agent_name}")

        # Get model config from agent
        model_config = agent_config.primary_model

        # Merge parameters: agent config < kwargs
        merged_params = {**model_config.parameters, **kwargs}

        logger.info(
            f"Creating model for agent '{agent_name}': "
            f"model_id={model_config.model_id}, provider={model_config.provider}"
        )

        # Create model
        return self.create_model(
            model_id=model_config.model_id,
            provider=model_config.provider,
            use_fallback=use_fallback,
            **merged_params,
        )

    def get_available_providers(self) -> list[str]:
        """
        Get list of available providers (with valid credentials)

        Returns:
            List of provider names
        """
        return self.config_manager.get_enabled_providers()

    def get_available_models(
        self, provider: Optional[str] = None
    ) -> list[Dict[str, Any]]:
        """
        Get list of available models for a provider

        Args:
            provider: Provider name (uses primary if None)

        Returns:
            List of model dictionaries
        """
        return self.config_manager.get_available_models(provider)


# ============================================
# Singleton and Convenience Functions
# ============================================

_factory: Optional[ModelFactory] = None


def get_model_factory() -> ModelFactory:
    """
    Get singleton model factory instance

    Returns:
        ModelFactory instance
    """
    global _factory
    if _factory is None:
        _factory = ModelFactory()
    return _factory


def create_model(
    model_id: Optional[str] = None, provider: Optional[str] = None, **kwargs
):
    """
    Convenience function to create a model instance

    Args:
        model_id: Model identifier
        provider: Provider name
        **kwargs: Model parameters

    Returns:
        Model instance

    Examples:
        >>> # Use default provider and model
        >>> model = create_model()

        >>> # Use specific provider
        >>> model = create_model(provider="google")

        >>> # Use specific model and provider
        >>> model = create_model(model_id="gpt-4", provider="openrouter")

        >>> # Override parameters
        >>> model = create_model(temperature=0.9, max_tokens=8192)
    """
    factory = get_model_factory()
    return factory.create_model(model_id, provider, **kwargs)


def create_model_for_agent(agent_name: str, **kwargs):
    """
    Convenience function to create model for an agent

    Args:
        agent_name: Agent name
        **kwargs: Override parameters

    Returns:
        Model instance

    Example:
        >>> model = create_model_for_agent("research_agent")
        >>> # Uses configuration from agents/research_agent.yaml + overrides
    """
    factory = get_model_factory()
    return factory.create_model_for_agent(agent_name, **kwargs)
