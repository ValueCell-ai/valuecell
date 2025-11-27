"""
Model Factory - Creates model instances using the three-tier configuration system

This factory:
1. Loads configuration from YAML + .env + environment variables
2. Validates provider credentials
3. Creates appropriate model instances with correct parameters
4. Supports fallback providers for reliability
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from loguru import logger

from valuecell.config.manager import ConfigManager, ProviderConfig, get_config_manager


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

    def create_embedder(self, model_id: Optional[str] = None, **kwargs):
        """
        Create an embedder instance (optional, not all providers support it)

        Args:
            model_id: Embedding model identifier (uses default if None)
            **kwargs: Additional embedder parameters (dimensions, etc.)

        Returns:
            Embedder instance

        Raises:
            NotImplementedError: If provider doesn't support embeddings
        """
        raise NotImplementedError(
            f"Provider '{self.config.name}' does not support embedding models"
        )

    def is_available(self) -> bool:
        """
        Check if provider credentials are available

        Returns:
            True if provider can be used
        """
        # Default implementation: check API key
        return bool(self.config.api_key)

    def has_embedding_support(self) -> bool:
        """
        Check if provider supports embedding models

        Returns:
            True if provider has embedding configuration
        """
        return bool(self.config.default_embedding_model)


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
        )

    def create_embedder(self, model_id: Optional[str] = None, **kwargs):
        """Create embedder via Google Gemini"""
        try:
            from agno.knowledge.embedder.google import GeminiEmbedder
        except ImportError:
            raise ImportError("agno package not installed")

        # Use provided model_id or default embedding model
        model_id = model_id or self.config.default_embedding_model

        if not model_id:
            raise ValueError(
                f"No embedding model specified for provider '{self.config.name}'"
            )

        # Merge parameters: provider embedding defaults < kwargs
        params = {**self.config.embedding_parameters, **kwargs}

        logger.info(f"Creating Google Gemini embedder: {model_id}")

        return GeminiEmbedder(
            id=model_id,
            api_key=self.config.api_key,
            dimensions=int(params.get("dimensions", 3072)),
            task_type=params.get("task_type", "RETRIEVAL_DOCUMENT"),
        )


class AzureProvider(ModelProvider):
    """Azure OpenAI model provider

    Azure OpenAI is a managed service providing OpenAI models deployed on Azure infrastructure.
    It uses deployment names instead of model IDs, and requires both API key and endpoint.

    Configuration:
    - AZURE_OPENAI_API_KEY: API key from Azure Portal
    - AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL
    - api_version: API version for Azure OpenAI REST API (default: 2024-10-21)
    """

    def create_model(self, model_id: Optional[str] = None, **kwargs):
        """Create Azure OpenAI model

        Args:
            model_id: Deployment name in Azure (uses default if None)
            **kwargs: Additional model parameters

        Returns:
            AzureOpenAI model instance
        """
        try:
            from agno.models.azure import AzureOpenAI
        except ImportError:
            raise ImportError(
                "agno package with Azure support not installed. "
                "Install with: pip install agno[azure]"
            )

        # Use provided model_id or default
        deployment_name = model_id or self.config.default_model

        # Merge parameters: provider defaults < kwargs
        params = {**self.config.parameters, **kwargs}

        # Get API version from config (can be overridden by env var)
        # The api_version field in azure.yaml is handled by env_overrides
        api_version = self.config.extra_config.get("api_version", "2024-10-21")

        logger.info(
            f"Creating Azure OpenAI model: deployment={deployment_name}, "
            f"endpoint={self.config.base_url}, api_version={api_version}"
        )

        return AzureOpenAI(
            deployment_name=deployment_name,
            api_key=self.config.api_key,
            azure_endpoint=self.config.base_url,
            api_version=api_version,
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
            top_p=params.get("top_p"),
            frequency_penalty=params.get("frequency_penalty"),
            presence_penalty=params.get("presence_penalty"),
        )

    def create_embedder(self, model_id: Optional[str] = None, **kwargs):
        """Create embedder via Azure OpenAI (OpenAI-compatible)

        Args:
            model_id: Embedding deployment name in Azure (uses default if None)
            **kwargs: Additional embedder parameters

        Returns:
            OpenAIEmbedder instance configured for Azure
        """
        try:
            from agno.knowledge.embedder.openai import OpenAIEmbedder
        except ImportError:
            raise ImportError("agno package not installed")

        # Use provided model_id or default embedding model
        deployment_name = model_id or self.config.default_embedding_model

        if not deployment_name:
            raise ValueError(
                f"No embedding model specified for provider '{self.config.name}'. "
                "Set 'embedding.default_model' in azure.yaml"
            )

        # Merge parameters: provider embedding defaults < kwargs
        params = {**self.config.embedding_parameters, **kwargs}

        logger.info(
            f"Creating Azure OpenAI embedder: deployment={deployment_name}, "
            f"endpoint={self.config.base_url}"
        )

        return OpenAIEmbedder(
            id=deployment_name,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            dimensions=int(params.get("dimensions", 1536))
            if params.get("dimensions")
            else None,
            encoding_format=params.get("encoding_format", "float"),
        )

    def is_available(self) -> bool:
        """Azure needs both API key and endpoint to be available

        Returns:
            True if both API key and endpoint are configured
        """
        has_key = bool(self.config.api_key)
        has_endpoint = bool(self.config.base_url)

        if not has_key:
            logger.warning(
                "Azure OpenAI API key not configured. "
                "Set AZURE_OPENAI_API_KEY environment variable."
            )

        if not has_endpoint:
            logger.warning(
                "Azure OpenAI endpoint not configured. "
                "Set AZURE_OPENAI_ENDPOINT environment variable."
            )

        return has_key and has_endpoint


class SiliconFlowProvider(ModelProvider):
    """SiliconFlow model provider"""

    def create_model(self, model_id: Optional[str] = None, **kwargs):
        """Create SiliconFlow model"""
        try:
            from agno.models.siliconflow import Siliconflow
        except ImportError:
            raise ImportError("agno package not installed")

        model_id = model_id or self.config.default_model
        params = {**self.config.parameters, **kwargs}

        logger.info(f"Creating SiliconFlow model: {model_id}")

        return Siliconflow(
            id=model_id,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
        )

    def create_embedder(self, model_id: Optional[str] = None, **kwargs):
        """Create embedder via SiliconFlow (OpenAI-compatible)"""
        try:
            from agno.knowledge.embedder.openai import OpenAIEmbedder
        except ImportError:
            raise ImportError("agno package not installed")

        # Use provided model_id or default embedding model
        model_id = model_id or self.config.default_embedding_model

        if not model_id:
            raise ValueError(
                f"No embedding model specified for provider '{self.config.name}'"
            )

        # Merge parameters: provider embedding defaults < kwargs
        params = {**self.config.embedding_parameters, **kwargs}

        logger.info(f"Creating SiliconFlow embedder: {model_id}")

        return OpenAIEmbedder(
            id=model_id,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            dimensions=int(params.get("dimensions", 1024)),
            encoding_format=params.get("encoding_format"),
        )


class OpenAIProvider(ModelProvider):
    """OpenAI model provider"""

    def create_model(self, model_id: Optional[str] = None, **kwargs):
        """Create OpenAI model via agno"""
        try:
            from agno.models.openai import OpenAIChat
        except ImportError:
            raise ImportError(
                "agno package not installed. Install with: pip install agno"
            )

        model_id = model_id or self.config.default_model
        params = {**self.config.parameters, **kwargs}

        logger.info(f"Creating OpenAI model: {model_id}")

        return OpenAIChat(
            id=model_id,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
            top_p=params.get("top_p"),
            frequency_penalty=params.get("frequency_penalty"),
            presence_penalty=params.get("presence_penalty"),
        )

    def create_embedder(self, model_id: Optional[str] = None, **kwargs):
        """Create embedder via OpenAI"""
        try:
            from agno.knowledge.embedder.openai import OpenAIEmbedder
        except ImportError:
            raise ImportError("agno package not installed")

        # Use provided model_id or default embedding model
        model_id = model_id or self.config.default_embedding_model

        if not model_id:
            raise ValueError(
                f"No embedding model specified for provider '{self.config.name}'"
            )

        # Merge parameters: provider embedding defaults < kwargs
        params = {**self.config.embedding_parameters, **kwargs}

        logger.info(f"Creating OpenAI embedder: {model_id}")

        return OpenAIEmbedder(
            id=model_id,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            dimensions=int(params.get("dimensions", 1536))
            if params.get("dimensions")
            else None,
            encoding_format=params.get("encoding_format", "float"),
        )


class OpenAICompatibleProvider(ModelProvider):
    """OpenAI-compatible model provider with role compatibility handling

    This provider handles OpenAI-compatible APIs (like DashScope, vLLM, etc.) that may not
    support newer OpenAI features like the 'developer' role. It wraps the OpenAIChat model
    and converts incompatible roles to compatible ones.
    """

    def create_model(self, model_id: Optional[str] = None, **kwargs):
        """Create OpenAI-compatible model via agno with role compatibility"""
        try:
            from agno.models.openai import OpenAILike
        except ImportError:
            raise ImportError(
                "agno package not installed. Install with: pip install agno"
            )

        model_id = model_id or self.config.default_model
        params = {**self.config.parameters, **kwargs}

        logger.info(
            f"Creating OpenAI-compatible model: {model_id} (base_url: {self.config.base_url})"
        )

        # Create the base OpenAILike model
        return OpenAILike(
            id=model_id,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
            top_p=params.get("top_p"),
            frequency_penalty=params.get("frequency_penalty"),
            presence_penalty=params.get("presence_penalty"),
        )

    def create_embedder(self, model_id: Optional[str] = None, **kwargs):
        """Create embedder via OpenAI-compatible API"""
        try:
            from agno.knowledge.embedder.openai import OpenAIEmbedder
        except ImportError:
            raise ImportError("agno package not installed")

        # Use provided model_id or default embedding model
        model_id = model_id or self.config.default_embedding_model

        if not model_id:
            raise ValueError(
                f"No embedding model specified for provider '{self.config.name}'"
            )

        # Merge parameters: provider embedding defaults < kwargs
        params = {**self.config.embedding_parameters, **kwargs}

        logger.info(f"Creating OpenAI-compatible embedder: {model_id}")

        return OpenAIEmbedder(
            id=model_id,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            dimensions=int(params.get("dimensions", 1024)),
            encoding_format=params.get("encoding_format"),
        )

    def is_available(self) -> bool:
        """Check if provider is available (needs both API key and base URL)"""
        return bool(self.config.api_key and self.config.base_url)


class DeepSeekProvider(ModelProvider):
    """DeepSeek model provider

    DeepSeek provides OpenAI-compatible API endpoints for their models.
    This provider uses the OpenAI-compatible interface to interact with DeepSeek's API.
    """

    def create_model(self, model_id: Optional[str] = None, **kwargs):
        """Create DeepSeek model via agno (OpenAI-compatible)"""
        try:
            from agno.models.openai import OpenAILike
        except ImportError:
            raise ImportError(
                "agno package not installed. Install with: pip install agno"
            )

        model_id = model_id or self.config.default_model
        params = {**self.config.parameters, **kwargs}

        logger.info(f"Creating DeepSeek model: {model_id}")

        return OpenAILike(
            id=model_id,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
            top_p=params.get("top_p"),
            frequency_penalty=params.get("frequency_penalty"),
            presence_penalty=params.get("presence_penalty"),
        )


class DashScopeProvider(ModelProvider):
    """DashScope model provider (native)"""

    def create_model(self, model_id: Optional[str] = None, **kwargs):
        """Create DashScope model via agno"""
        try:
            from agno.models.dashscope import DashScope
        except ImportError:
            raise ImportError(
                "agno package not installed. Install with: pip install agno"
            )

        model_id = model_id or self.config.default_model
        params = {**self.config.parameters, **kwargs}

        # Use configured base_url if present, otherwise let DashScope use its default
        # agno's DashScope class has a default base_url for the compatible-mode endpoint
        base_url = self.config.base_url

        logger.info(f"Creating DashScope model: {model_id}")

        return DashScope(
            id=model_id,
            api_key=self.config.api_key,
            base_url=base_url,
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
            top_p=params.get("top_p"),
        )

    def create_embedder(self, model_id: Optional[str] = None, **kwargs):
        """Create embedder via DashScope (OpenAI-compatible)"""
        try:
            from agno.knowledge.embedder.openai import OpenAIEmbedder
        except ImportError:
            raise ImportError("agno package not installed")

        # Use provided model_id or default embedding model
        model_id = model_id or self.config.default_embedding_model

        if not model_id:
            raise ValueError(
                f"No embedding model specified for provider '{self.config.name}'"
            )

        # Merge parameters: provider embedding defaults < kwargs
        params = {**self.config.embedding_parameters, **kwargs}

        logger.info(f"Creating DashScope embedder: {model_id}")

        return OpenAIEmbedder(
            id=model_id,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            dimensions=int(params.get("dimensions", 2048))
            if params.get("dimensions")
            else None,
            encoding_format=params.get("encoding_format", "float"),
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
        "siliconflow": SiliconFlowProvider,
        "openai": OpenAIProvider,
        "openai-compatible": OpenAICompatibleProvider,
        "deepseek": DeepSeekProvider,
        "dashscope": DashScopeProvider,
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
        provider_models: Optional[dict] = None,
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
            provider_models: Dict mapping provider names to model IDs for fallback
                           e.g., {"siliconflow": "deepseek-ai/DeepSeek-V3.1-Terminus"}
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
            >>> # With provider-specific models
            >>> model = factory.create_model(
            ...     model_id="anthropic/claude-3.5-sonnet",
            ...     provider="openrouter",
            ...     provider_models={"siliconflow": "deepseek-ai/DeepSeek-V3.1-Terminus"}
            ... )
        """
        provider = provider or self.config_manager.primary_provider
        if provider_models is None:
            provider_models = {}

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
                    # Determine model ID for fallback provider
                    fallback_model_id = model_id

                    # Priority: provider_models > default_model
                    if fallback_provider in provider_models:
                        fallback_model_id = provider_models[fallback_provider]
                        logger.info(
                            f"Using provider-specific model for {fallback_provider}: {fallback_model_id}"
                        )
                    else:
                        # Use provider's default model
                        fallback_provider_config = (
                            self.config_manager.get_provider_config(fallback_provider)
                        )
                        if fallback_provider_config:
                            fallback_model_id = fallback_provider_config.default_model
                            logger.info(
                                f"Using default model for {fallback_provider}: {fallback_model_id}"
                            )

                    logger.info(f"Trying fallback provider: {fallback_provider}")
                    return self._create_model_internal(
                        fallback_model_id, fallback_provider, **kwargs
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

        # Support per-call API key override via kwargs
        override_api_key = kwargs.pop("api_key", None)
        if override_api_key is not None:
            # Create a copy of provider_config with overridden api_key
            provider_config = ProviderConfig(
                name=provider_config.name,
                enabled=provider_config.enabled,
                api_key=override_api_key,
                base_url=provider_config.base_url,
                default_model=provider_config.default_model,
                models=provider_config.models,
                parameters=provider_config.parameters,
                default_embedding_model=provider_config.default_embedding_model,
                embedding_models=provider_config.embedding_models,
                embedding_parameters=provider_config.embedding_parameters,
                extra_config=provider_config.extra_config,
            )
            # Inline validation with override applied
            if not provider_config.enabled:
                raise ValueError(f"Provider '{provider}' is disabled in config")
            if provider != "ollama" and not provider_config.api_key:
                raise ValueError(
                    f"API key override missing/empty for provider '{provider}'."
                )
            if provider == "azure" and not provider_config.base_url:
                raise ValueError(
                    "Azure endpoint not configured. Please set AZURE_OPENAI_ENDPOINT"
                )
        else:
            # Validate provider using default manager rules
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

        # Check if specified provider is available (has API key)
        provider = model_config.provider
        model_id = model_config.model_id
        is_valid, error_msg = self.config_manager.validate_provider(provider)

        if not is_valid:
            # If configured provider is not available, use primary provider instead
            fallback_provider = self.config_manager.primary_provider
            logger.warning(
                f"Configured provider '{provider}' for agent '{agent_name}' is not available: {error_msg}. "
                f"Falling back to primary provider: {fallback_provider}"
            )
            provider = fallback_provider

            # Update model_id for the fallback provider
            # Priority: provider_models[fallback_provider] > provider's default_model
            if fallback_provider in model_config.provider_models:
                model_id = model_config.provider_models[fallback_provider]
                logger.info(
                    f"Using provider-specific model for fallback: {fallback_provider} -> {model_id}"
                )
            else:
                # Use provider's default model
                provider_config = self.config_manager.get_provider_config(
                    fallback_provider
                )
                if provider_config:
                    model_id = provider_config.default_model
                    logger.info(
                        f"Using default model for fallback provider '{fallback_provider}': {model_id}"
                    )

        # Create model
        return self.create_model(
            model_id=model_id,
            provider=provider,
            use_fallback=use_fallback,
            provider_models=model_config.provider_models,
            **merged_params,
        )

    def create_embedder_for_agent(
        self, agent_name: str, use_fallback: bool = True, **kwargs
    ):
        """
        Create an embedder for a specific agent using its configuration.

        This method will use the agent's `embedding_model` configuration when
        present. If no embedding config is provided for the agent it will
        attempt to use the agent's primary model provider and select the
        provider's default embedding model.
        """
        # Get agent configuration
        agent_config = self.config_manager.get_agent_config(agent_name)

        if not agent_config:
            raise ValueError(f"Agent configuration not found: {agent_name}")

        if not agent_config.enabled:
            raise ValueError(f"Agent is disabled: {agent_name}")

        # If agent specifies an embedding_model, use it
        if agent_config.embedding_model:
            emb = agent_config.embedding_model
            merged_params = {**emb.parameters, **kwargs}
            logger.info(
                f"Creating embedder for agent '{agent_name}': model_id={emb.model_id}, provider={emb.provider}, params={merged_params}"
            )

            # Check if specified provider is available (has API key)
            provider = emb.provider
            model_id = emb.model_id
            is_valid, error_msg = self.config_manager.validate_provider(provider)

            if not is_valid:
                # If configured provider is not available, use primary provider instead
                fallback_provider = self.config_manager.primary_provider
                logger.warning(
                    f"Configured embedding provider '{provider}' for agent '{agent_name}' is not available: {error_msg}. "
                    f"Falling back to primary provider: {fallback_provider}"
                )
                provider = fallback_provider

                # Update model_id for the fallback provider
                # Priority: provider_models[fallback_provider] > provider's default_embedding_model
                if fallback_provider in emb.provider_models:
                    model_id = emb.provider_models[fallback_provider]
                    logger.info(
                        f"Using provider-specific embedding model for fallback: {fallback_provider} -> {model_id}"
                    )
                else:
                    # Use provider's default embedding model
                    provider_config = self.config_manager.get_provider_config(
                        fallback_provider
                    )
                    if provider_config and provider_config.default_embedding_model:
                        model_id = provider_config.default_embedding_model
                        logger.info(
                            f"Using default embedding model for fallback provider '{fallback_provider}': {model_id}"
                        )

            return self.create_embedder(
                model_id=model_id or None,
                provider=provider,
                use_fallback=use_fallback,
                **merged_params,
            )

        # Fallback: use primary model's provider and let factory pick provider default
        primary = agent_config.primary_model
        merged_params = {**primary.parameters, **kwargs}
        logger.info(
            f"Creating embedder for agent '{agent_name}' using primary provider: {primary.provider}"
        )

        # Check if primary provider is available
        provider = primary.provider
        is_valid, error_msg = self.config_manager.validate_provider(provider)

        if not is_valid:
            logger.warning(
                f"Primary provider '{provider}' for agent '{agent_name}' is not available: {error_msg}. "
                f"Using system primary provider: {self.config_manager.primary_provider}"
            )
            provider = self.config_manager.primary_provider

        return self.create_embedder(
            model_id=None,
            provider=provider,
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

    def create_embedder(
        self,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        use_fallback: bool = True,
        **kwargs,
    ):
        """
        Create an embedder instance with automatic provider selection

        This method:
        1. Automatically selects a provider with embedding support
        2. Falls back to other providers if the primary doesn't work
        3. Uses configuration from YAML + .env + environment variables

        Args:
            model_id: Embedding model ID (optional, uses provider default)
            provider: Provider name (optional, auto-detects from available providers)
            use_fallback: Try fallback providers if primary fails
            **kwargs: Additional embedder parameters (dimensions, encoding_format, etc.)

        Returns:
            Embedder instance

        Raises:
            ValueError: If no provider with embedding support is available

        Examples:
            >>> factory = ModelFactory()
            >>> # Auto-select provider with embedding support
            >>> embedder = factory.create_embedder()
            >>> # Use specific provider
            >>> embedder = factory.create_embedder(provider="openrouter")
            >>> # Override dimensions
            >>> embedder = factory.create_embedder(dimensions=3072)
        """
        # If no provider specified, find one with embedding support
        if provider is None:
            provider = self._find_embedding_provider()
            if not provider:
                raise ValueError(
                    "No provider with embedding support found. "
                    "Please configure at least one provider with embedding models."
                )

        # Try primary provider
        try:
            return self._create_embedder_internal(model_id, provider, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to create embedder with provider {provider}: {e}")

            if not use_fallback:
                raise

            # Try other providers with embedding support
            available_providers = self._get_embedding_providers()
            for fallback_provider in available_providers:
                if fallback_provider == provider:
                    continue  # Skip already tried provider

                try:
                    logger.info(f"Trying fallback provider: {fallback_provider}")
                    return self._create_embedder_internal(
                        model_id, fallback_provider, **kwargs
                    )
                except Exception as fallback_error:
                    logger.warning(
                        f"Fallback provider {fallback_provider} also failed: {fallback_error}"
                    )
                    continue

            # All providers failed
            raise ValueError(
                f"Failed to create embedder. Primary provider ({provider}) "
                f"and all fallback providers failed. Original error: {e}"
            )

    def _find_embedding_provider(self) -> Optional[str]:
        """
        Find the best available provider with embedding support

        Priority:
        1. Primary provider (if it has embedding support)
        2. First enabled provider with embedding support

        Returns:
            Provider name or None
        """
        # Check primary provider first
        primary = self.config_manager.primary_provider
        primary_config = self.config_manager.get_provider_config(primary)
        if primary_config and primary_config.default_embedding_model:
            logger.debug(f"Using primary provider for embeddings: {primary}")
            return primary

        # Find first available provider with embedding support
        for provider_name in self.config_manager.get_enabled_providers():
            provider_config = self.config_manager.get_provider_config(provider_name)
            if provider_config and provider_config.default_embedding_model:
                logger.info(
                    f"Auto-selected provider with embedding support: {provider_name}"
                )
                return provider_name

        return None

    def _get_embedding_providers(self) -> list[str]:
        """
        Get list of providers with embedding support

        Note: This checks all configured providers, not just enabled ones,
        because a provider might be configured with embedding support but
        the API key might not be set yet.

        Returns:
            List of provider names that have embedding configuration
        """
        providers = []

        # Check all available provider configs (not just enabled ones)
        for provider_name in self.config_manager.loader.list_providers():
            provider_config = self.config_manager.get_provider_config(provider_name)

            # Check if provider has embedding configuration
            if provider_config and provider_config.default_embedding_model:
                # Only include if API key is available
                if provider_config.api_key:
                    providers.append(provider_name)

        return providers

    def _create_embedder_internal(
        self, model_id: Optional[str], provider: str, **kwargs
    ):
        """
        Internal method to create embedder without fallback logic

        Args:
            model_id: Embedding model ID
            provider: Provider name
            **kwargs: Embedder parameters

        Returns:
            Embedder instance
        """
        # Check if provider is registered
        if provider not in self._providers:
            raise ValueError(f"Unsupported provider: {provider}")

        # Get provider configuration
        provider_config = self.config_manager.get_provider_config(provider)
        if not provider_config:
            raise ValueError(f"Provider configuration not found: {provider}")

        # Check if provider supports embeddings
        if not provider_config.default_embedding_model:
            raise ValueError(
                f"Provider '{provider}' does not support embedding models. "
                f"Please configure embedding models in providers/{provider}.yaml"
            )

        # Support per-call API key override via kwargs
        override_api_key = kwargs.pop("api_key", None)
        if override_api_key is not None:
            provider_config = ProviderConfig(
                name=provider_config.name,
                enabled=provider_config.enabled,
                api_key=override_api_key,
                base_url=provider_config.base_url,
                default_model=provider_config.default_model,
                models=provider_config.models,
                parameters=provider_config.parameters,
                default_embedding_model=provider_config.default_embedding_model,
                embedding_models=provider_config.embedding_models,
                embedding_parameters=provider_config.embedding_parameters,
                extra_config=provider_config.extra_config,
            )
            if not provider_config.enabled:
                raise ValueError(f"Provider '{provider}' is disabled in config")
            if provider != "ollama" and not provider_config.api_key:
                raise ValueError(
                    f"API key override missing/empty for provider '{provider}'."
                )
            if provider == "azure" and not provider_config.base_url:
                raise ValueError(
                    "Azure endpoint not configured. Please set AZURE_OPENAI_ENDPOINT"
                )
        else:
            # Validate provider using default manager rules
            is_valid, error_msg = self.config_manager.validate_provider(provider)
            if not is_valid:
                raise ValueError(f"Provider validation failed: {error_msg}")

        # Create provider instance
        provider_class = self._providers[provider]
        provider_instance = provider_class(provider_config)

        # Create embedder
        return provider_instance.create_embedder(model_id, **kwargs)


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


def create_embedder(
    model_id: Optional[str] = None, provider: Optional[str] = None, **kwargs
):
    """
    Convenience function to create an embedder instance

    This function automatically:
    1. Selects a provider with embedding support (if not specified)
    2. Uses the provider's default embedding model (if model_id not specified)
    3. Falls back to other providers if the primary fails
    4. Applies configuration from YAML + .env + environment variables

    Args:
        model_id: Embedding model identifier (optional)
        provider: Provider name (optional, auto-detects)
        **kwargs: Embedder parameters (dimensions, encoding_format, etc.)

    Returns:
        Embedder instance

    Examples:
        >>> # Auto-select provider and use default embedding model
        >>> embedder = create_embedder()

        >>> # Use specific provider (auto-selects default model)
        >>> embedder = create_embedder(provider="openrouter")

        >>> # Use specific model
        >>> embedder = create_embedder(model_id="openai/text-embedding-3-large")

        >>> # Override dimensions
        >>> embedder = create_embedder(dimensions=3072)

        >>> # Combine parameters
        >>> embedder = create_embedder(
        ...     provider="openrouter",
        ...     model_id="openai/text-embedding-3-small",
        ...     dimensions=1536
        ... )
    """
    factory = get_model_factory()
    return factory.create_embedder(model_id, provider, **kwargs)


def create_embedder_for_agent(agent_name: str, **kwargs):
    """
    Convenience function to create an embedder configured for a specific agent.

    Args:
        agent_name: Agent name
        **kwargs: Override parameters

    Returns:
        Embedder instance
    """
    factory = get_model_factory()
    return factory.create_embedder_for_agent(agent_name, **kwargs)
