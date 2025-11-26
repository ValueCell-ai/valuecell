"""
Model Adapters - Factory and providers for creating AI model instances

This module provides a unified interface for creating and managing different AI model providers
through the ModelFactory class and various provider implementations.

Main Components:
- ModelFactory: Factory class for creating model instances
- ModelProvider: Abstract base class for provider implementations
- Provider implementations: OpenRouterProvider, GoogleProvider, AzureProvider, etc.

Usage:
    >>> from valuecell.adapters.models import create_model, create_model_for_agent
    >>>
    >>> # Create a model with default provider
    >>> model = create_model()
    >>>
    >>> # Create a model for a specific agent
    >>> model = create_model_for_agent("research_agent")
"""

from valuecell.adapters.models.factory import (
    AzureProvider,
    DashScopeProvider,
    DeepSeekProvider,
    GoogleProvider,
    ModelFactory,
    ModelProvider,
    OpenAICompatibleProvider,
    OpenAIProvider,
    OpenRouterProvider,
    SiliconFlowProvider,
    create_model,
    create_model_for_agent,
    get_model_factory,
)

__all__ = [
    # Factory and base classes
    "ModelFactory",
    "ModelProvider",
    "get_model_factory",
    # Provider implementations
    "OpenAIProvider",
    "OpenAICompatibleProvider",
    "OpenRouterProvider",
    "GoogleProvider",
    "AzureProvider",
    "SiliconFlowProvider",
    "DeepSeekProvider",
    "DashScopeProvider",
    # Convenience functions
    "create_model",
    "create_model_for_agent",
]
