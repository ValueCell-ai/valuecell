"""
Unit and integration tests for MiniMax provider in the model factory.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from valuecell.adapters.models.factory import (
    MiniMaxProvider,
    ModelFactory,
    ModelProvider,
)
from valuecell.config.manager import ProviderConfig


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def minimax_provider_config():
    """Create a MiniMax ProviderConfig for testing."""
    return ProviderConfig(
        name="minimax",
        enabled=True,
        api_key="test-minimax-api-key",
        base_url="https://api.minimax.io/v1",
        default_model="MiniMax-M2.7",
        models=[
            {
                "id": "MiniMax-M2.7",
                "name": "MiniMax M2.7",
                "context_length": 204000,
                "description": "MiniMax M2.7 - latest flagship model",
            },
            {
                "id": "MiniMax-M2.7-highspeed",
                "name": "MiniMax M2.7 Highspeed",
                "context_length": 204000,
                "description": "MiniMax M2.7 Highspeed - faster variant",
            },
            {
                "id": "MiniMax-M2.5",
                "name": "MiniMax M2.5",
                "context_length": 204000,
                "description": "MiniMax M2.5 model",
            },
            {
                "id": "MiniMax-M2.5-highspeed",
                "name": "MiniMax M2.5 Highspeed",
                "context_length": 204000,
                "description": "MiniMax M2.5 Highspeed - faster variant",
            },
        ],
        parameters={"temperature": 0.7, "max_tokens": 8096},
    )


@pytest.fixture
def minimax_provider(minimax_provider_config):
    """Create a MiniMaxProvider instance for testing."""
    return MiniMaxProvider(minimax_provider_config)


@pytest.fixture
def disabled_minimax_config():
    """Create a disabled MiniMax ProviderConfig."""
    return ProviderConfig(
        name="minimax",
        enabled=False,
        api_key="test-key",
        base_url="https://api.minimax.io/v1",
        default_model="MiniMax-M2.7",
        models=[],
        parameters={},
    )


@pytest.fixture
def no_key_minimax_config():
    """Create a MiniMax ProviderConfig without API key."""
    return ProviderConfig(
        name="minimax",
        enabled=True,
        api_key=None,
        base_url="https://api.minimax.io/v1",
        default_model="MiniMax-M2.7",
        models=[],
        parameters={},
    )


# ============================================
# Unit Tests: MiniMaxProvider
# ============================================


class TestMiniMaxProviderInit:
    """Test MiniMaxProvider initialization."""

    def test_inherits_model_provider(self):
        """MiniMaxProvider should be a subclass of ModelProvider."""
        assert issubclass(MiniMaxProvider, ModelProvider)

    def test_provider_stores_config(self, minimax_provider, minimax_provider_config):
        """Provider should store the config."""
        assert minimax_provider.config is minimax_provider_config

    def test_is_available_with_key(self, minimax_provider):
        """Provider with API key should be available."""
        assert minimax_provider.is_available() is True

    def test_is_not_available_without_key(self, no_key_minimax_config):
        """Provider without API key should not be available."""
        provider = MiniMaxProvider(no_key_minimax_config)
        assert provider.is_available() is False

    def test_has_no_embedding_support(self, minimax_provider):
        """MiniMax provider should not have embedding support."""
        assert minimax_provider.has_embedding_support() is False


class TestMiniMaxProviderCreateModel:
    """Test MiniMaxProvider.create_model()."""

    @patch("valuecell.adapters.models.factory.OpenAILike", create=True)
    def test_create_model_default(self, mock_openai_like_cls, minimax_provider):
        """create_model() without model_id should use default model."""
        # Patch the import inside the method
        mock_model = MagicMock()
        with patch.dict(
            "sys.modules",
            {"agno": MagicMock(), "agno.models": MagicMock(), "agno.models.openai": MagicMock()},
        ):
            with patch(
                "valuecell.adapters.models.factory.MiniMaxProvider.create_model"
            ) as mock_create:
                mock_create.return_value = mock_model
                result = minimax_provider.create_model()
                assert result is mock_model

    def test_create_model_uses_openai_like(self, minimax_provider):
        """create_model() should use agno's OpenAILike."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            mock_instance = MagicMock()
            MockOpenAILike.return_value = mock_instance

            result = minimax_provider.create_model()

            MockOpenAILike.assert_called_once_with(
                id="MiniMax-M2.7",
                api_key="test-minimax-api-key",
                base_url="https://api.minimax.io/v1",
                temperature=0.7,
                max_tokens=8096,
                top_p=None,
                frequency_penalty=None,
                presence_penalty=None,
            )
            assert result is mock_instance

    def test_create_model_specific_model_id(self, minimax_provider):
        """create_model() with specific model_id should use it."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            mock_instance = MagicMock()
            MockOpenAILike.return_value = mock_instance

            result = minimax_provider.create_model(model_id="MiniMax-M2.7-highspeed")

            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["id"] == "MiniMax-M2.7-highspeed"
            assert result is mock_instance

    def test_create_model_m25(self, minimax_provider):
        """create_model() should work with M2.5 model."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            MockOpenAILike.return_value = MagicMock()
            minimax_provider.create_model(model_id="MiniMax-M2.5")
            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["id"] == "MiniMax-M2.5"

    def test_create_model_m25_highspeed(self, minimax_provider):
        """create_model() should work with M2.5-highspeed model."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            MockOpenAILike.return_value = MagicMock()
            minimax_provider.create_model(model_id="MiniMax-M2.5-highspeed")
            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["id"] == "MiniMax-M2.5-highspeed"


class TestMiniMaxTemperatureClamping:
    """Test temperature clamping for MiniMax provider."""

    def test_temperature_normal(self, minimax_provider):
        """Normal temperature (0.7) should pass through."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            MockOpenAILike.return_value = MagicMock()
            minimax_provider.create_model(temperature=0.7)
            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["temperature"] == 0.7

    def test_temperature_zero_clamped(self, minimax_provider):
        """Temperature 0.0 should be clamped to 0.01 (MiniMax requires > 0)."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            MockOpenAILike.return_value = MagicMock()
            minimax_provider.create_model(temperature=0.0)
            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["temperature"] == 0.01

    def test_temperature_above_one_clamped(self, minimax_provider):
        """Temperature > 1.0 should be clamped to 1.0."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            MockOpenAILike.return_value = MagicMock()
            minimax_provider.create_model(temperature=1.5)
            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["temperature"] == 1.0

    def test_temperature_exactly_one(self, minimax_provider):
        """Temperature 1.0 should stay as 1.0."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            MockOpenAILike.return_value = MagicMock()
            minimax_provider.create_model(temperature=1.0)
            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["temperature"] == 1.0

    def test_temperature_negative_clamped(self, minimax_provider):
        """Negative temperature should be clamped to 0.01."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            MockOpenAILike.return_value = MagicMock()
            minimax_provider.create_model(temperature=-0.5)
            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["temperature"] == 0.01

    def test_temperature_none_passthrough(self, minimax_provider_config):
        """Temperature None should pass through as None."""
        config = ProviderConfig(
            name="minimax",
            enabled=True,
            api_key="test-key",
            base_url="https://api.minimax.io/v1",
            default_model="MiniMax-M2.7",
            models=[],
            parameters={},
        )
        provider = MiniMaxProvider(config)
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            MockOpenAILike.return_value = MagicMock()
            provider.create_model()
            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["temperature"] is None


class TestMiniMaxProviderParameters:
    """Test parameter merging for MiniMax provider."""

    def test_kwargs_override_defaults(self, minimax_provider):
        """Kwargs should override default parameters."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            MockOpenAILike.return_value = MagicMock()
            minimax_provider.create_model(max_tokens=4096, top_p=0.9)
            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["max_tokens"] == 4096
            assert call_kwargs["top_p"] == 0.9

    def test_base_url_from_config(self, minimax_provider):
        """Base URL should come from config."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            MockOpenAILike.return_value = MagicMock()
            minimax_provider.create_model()
            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["base_url"] == "https://api.minimax.io/v1"

    def test_api_key_from_config(self, minimax_provider):
        """API key should come from config."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            MockOpenAILike.return_value = MagicMock()
            minimax_provider.create_model()
            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["api_key"] == "test-minimax-api-key"


class TestMiniMaxProviderEmbedding:
    """Test embedding support for MiniMax provider."""

    def test_create_embedder_raises(self, minimax_provider):
        """MiniMax provider should raise NotImplementedError for embeddings."""
        with pytest.raises(NotImplementedError, match="does not support embedding"):
            minimax_provider.create_embedder()


# ============================================
# Unit Tests: ModelFactory Registration
# ============================================


class TestMiniMaxFactoryRegistration:
    """Test MiniMax registration in ModelFactory."""

    def test_minimax_in_providers_registry(self):
        """MiniMax should be in the factory's _providers dict."""
        assert "minimax" in ModelFactory._providers

    def test_minimax_maps_to_correct_class(self):
        """MiniMax should map to MiniMaxProvider class."""
        assert ModelFactory._providers["minimax"] is MiniMaxProvider

    def test_minimax_provider_count(self):
        """Factory should have 10 providers (including minimax)."""
        assert len(ModelFactory._providers) == 10


# ============================================
# Unit Tests: model_should_use_json_mode
# ============================================


class TestMiniMaxJsonMode:
    """Test model_should_use_json_mode for MiniMax models."""

    def test_minimax_base_url_triggers_json_mode(self):
        """Models with minimax.io base_url should use JSON mode."""
        from valuecell.utils.model import model_should_use_json_mode

        mock_model = MagicMock()
        mock_model.provider = "openai_like"
        mock_model.name = "OpenAILike"
        mock_model.base_url = "https://api.minimax.io/v1"

        # Need to set provider/name to match OpenAILike
        from agno.models.openai import OpenAILike

        mock_model.provider = OpenAILike.provider
        mock_model.name = OpenAILike.name

        result = model_should_use_json_mode(mock_model)
        assert result is True


# ============================================
# Unit Tests: Provider YAML Config
# ============================================


class TestMiniMaxYamlConfig:
    """Test MiniMax YAML configuration file."""

    def test_yaml_exists(self):
        """MiniMax YAML config file should exist."""
        import os

        yaml_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "configs",
            "providers",
            "minimax.yaml",
        )
        assert os.path.exists(yaml_path), f"minimax.yaml not found at {yaml_path}"

    def test_yaml_content(self):
        """MiniMax YAML should have correct content."""
        import os

        import yaml

        yaml_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "configs",
            "providers",
            "minimax.yaml",
        )
        with open(yaml_path) as f:
            config = yaml.safe_load(f)

        assert config["name"] == "MiniMax"
        assert config["provider_type"] == "minimax"
        assert config["enabled"] is True
        assert config["connection"]["base_url"] == "https://api.minimax.io/v1"
        assert config["connection"]["api_key_env"] == "MINIMAX_API_KEY"
        assert config["default_model"] == "MiniMax-M2.7"

    def test_yaml_models_list(self):
        """YAML should list all MiniMax models."""
        import os

        import yaml

        yaml_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "configs",
            "providers",
            "minimax.yaml",
        )
        with open(yaml_path) as f:
            config = yaml.safe_load(f)

        model_ids = [m["id"] for m in config["models"]]
        assert "MiniMax-M2.7" in model_ids
        assert "MiniMax-M2.7-highspeed" in model_ids
        assert "MiniMax-M2.5" in model_ids
        assert "MiniMax-M2.5-highspeed" in model_ids

    def test_yaml_context_length(self):
        """All MiniMax models should have 204K context length."""
        import os

        import yaml

        yaml_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "configs",
            "providers",
            "minimax.yaml",
        )
        with open(yaml_path) as f:
            config = yaml.safe_load(f)

        for model in config["models"]:
            assert model["context_length"] == 204000, (
                f"Model {model['id']} should have 204K context"
            )


# ============================================
# Unit Tests: config.yaml Registration
# ============================================


class TestMiniMaxConfigRegistration:
    """Test MiniMax registration in config.yaml."""

    def test_minimax_in_config_yaml(self):
        """MiniMax should be registered in config.yaml."""
        import os

        import yaml

        config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "configs",
            "config.yaml",
        )
        with open(config_path) as f:
            config = yaml.safe_load(f)

        providers = config.get("models", {}).get("providers", {})
        assert "minimax" in providers
        assert providers["minimax"]["config_file"] == "providers/minimax.yaml"
        assert providers["minimax"]["api_key_env"] == "MINIMAX_API_KEY"


# ============================================
# Integration Tests
# ============================================


class TestMiniMaxIntegrationWithConfigManager:
    """Integration tests for MiniMax with ConfigManager."""

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-integration-key"})
    def test_config_manager_loads_minimax(self):
        """ConfigManager should load MiniMax provider config."""
        from valuecell.config.manager import ConfigManager

        manager = ConfigManager()
        config = manager.get_provider_config("minimax")

        assert config is not None
        assert config.name == "minimax"
        assert config.api_key == "test-integration-key"
        assert config.base_url == "https://api.minimax.io/v1"
        assert config.default_model == "MiniMax-M2.7"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"})
    def test_config_manager_validates_minimax(self):
        """ConfigManager should validate MiniMax provider successfully."""
        from valuecell.config.manager import ConfigManager

        manager = ConfigManager()
        is_valid, error = manager.validate_provider("minimax")
        assert is_valid is True
        assert error is None

    def test_config_manager_validates_minimax_no_key(self):
        """ConfigManager should fail validation without API key."""
        env = os.environ.copy()
        env.pop("MINIMAX_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            from valuecell.config.manager import ConfigManager

            manager = ConfigManager()
            is_valid, error = manager.validate_provider("minimax")
            assert is_valid is False
            assert "MINIMAX_API_KEY" in error

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-factory-key"})
    def test_factory_creates_minimax_model(self):
        """ModelFactory should create MiniMax model end-to-end."""
        with patch("agno.models.openai.OpenAILike") as MockOpenAILike:
            mock_model = MagicMock()
            MockOpenAILike.return_value = mock_model

            factory = ModelFactory()
            result = factory.create_model(provider="minimax", use_fallback=False)

            assert result is mock_model
            call_kwargs = MockOpenAILike.call_args[1]
            assert call_kwargs["id"] == "MiniMax-M2.7"
            assert call_kwargs["api_key"] == "test-factory-key"
            assert call_kwargs["base_url"] == "https://api.minimax.io/v1"

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"})
    def test_minimax_in_enabled_providers(self):
        """MiniMax should appear in enabled providers when API key is set."""
        from valuecell.config.manager import ConfigManager

        manager = ConfigManager()
        enabled = manager.get_enabled_providers()
        assert "minimax" in enabled

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"})
    def test_minimax_available_models(self):
        """ConfigManager should list MiniMax models."""
        from valuecell.config.manager import ConfigManager

        manager = ConfigManager()
        models = manager.get_available_models("minimax")
        model_ids = [m["id"] for m in models]
        assert "MiniMax-M2.7" in model_ids
        assert "MiniMax-M2.7-highspeed" in model_ids
