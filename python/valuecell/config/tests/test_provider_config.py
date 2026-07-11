"""Tests for provider configuration loading.

Validates that config-driven providers (openrouter, requesty) load through the
shared ConfigLoader / ConfigManager path with the expected connection settings.
"""

import os

import pytest

from valuecell.config.loader import ConfigLoader
from valuecell.config.manager import ConfigManager


@pytest.fixture()
def manager() -> ConfigManager:
    loader = ConfigLoader()
    return ConfigManager(loader=loader)


def test_requesty_provider_is_discovered():
    """requesty.yaml is picked up by the provider glob, like openrouter.yaml."""
    loader = ConfigLoader()
    providers = loader.list_providers()
    assert "openrouter" in providers
    assert "requesty" in providers


def test_requesty_provider_config_matches_expected(manager: ConfigManager):
    """Requesty loads through the same code path as OpenRouter with its
    fixed OpenAI-compatible base URL, API-key env var, and analytics headers."""
    config = manager.get_provider_config("requesty")

    assert config is not None
    assert config.name == "requesty"
    assert config.enabled is True
    assert config.base_url == "https://router.requesty.ai/v1"
    assert config.default_model == "openai/gpt-4o-mini"

    # provider/model id convention, mirroring OpenRouter
    model_ids = {m["id"] for m in config.models}
    assert "openai/gpt-4o-mini" in model_ids
    assert all("/" in mid for mid in model_ids)

    # Analytics headers mirror OpenRouter's HTTP-Referer / X-Title
    extra_headers = config.extra_config.get("extra_headers", {})
    assert extra_headers.get("X-Title") == "ValueCell"
    assert "HTTP-Referer" in extra_headers


def test_requesty_reads_api_key_env(manager: ConfigManager, monkeypatch):
    """REQUESTY_API_KEY is resolved into the provider config."""
    monkeypatch.setenv("REQUESTY_API_KEY", "sk-test-requesty")
    # Fresh manager to avoid loader cache picking up an earlier (empty) value
    fresh = ConfigManager(loader=ConfigLoader())
    config = fresh.get_provider_config("requesty")
    assert config is not None
    assert config.api_key == "sk-test-requesty"


def test_requesty_registered_in_factory():
    """The requesty provider name maps to a provider class in the factory."""
    from valuecell.adapters.models.factory import ModelFactory, RequestyProvider

    assert ModelFactory._providers.get("requesty") is RequestyProvider
