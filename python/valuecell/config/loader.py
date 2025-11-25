"""
YAML-based configuration loader with three-tier override system

Configuration Priority (highest to lowest):
1. Environment Variables (runtime overrides)
2. .env file (user-level configuration)
3. YAML files (system defaults)

Philosophy:
- YAML: System-level defaults, provider capabilities, model registry
- .env: User sets API keys and personal preferences
- Env Vars: Runtime overrides for deployment/CI/CD

Example:
    # Set API key in .env
    OPENROUTER_API_KEY=sk-...

    # Optionally override model for specific agent
    RESEARCH_AGENT_MODEL_ID=anthropic/claude-3.5-sonnet

    # Load config
    from valuecell.config.loader import get_config_loader
    loader = get_config_loader()
    config = loader.load_agent_config("research_agent")
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger

from .constants import CONFIG_DIR


class ConfigLoader:
    """
    Load and manage YAML configuration files with three-tier override system

    The loader automatically merges configurations from:
    1. Base YAML files (system defaults)
    2. .env file values
    3. Environment variables (highest priority)
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration loader

        Args:
            config_dir: Path to configs directory (defaults to CONFIG_DIR from constants)
        """
        self.config_dir = Path(config_dir) if config_dir is not None else CONFIG_DIR

        if not self.config_dir.exists():
            logger.error(f"Config directory not found: {self.config_dir}")

        self.environment = os.getenv("APP_ENVIRONMENT", "development")
        self._cache: Dict[str, Any] = {}

        logger.debug(
            f"ConfigLoader initialized: config_dir={self.config_dir}, env={self.environment}"
        )

    def _resolve_env_vars(self, value: Any) -> Any:
        """
        Recursively resolve environment variables in config values

        Supports syntax:
        - ${VAR_NAME} - required variable
        - ${VAR_NAME:default_value} - with default value

        Args:
            value: Config value (string, dict, list, or other)

        Returns:
            Value with environment variables resolved
        """
        if isinstance(value, str):
            # Pattern: ${VAR_NAME} or ${VAR_NAME:default_value}
            pattern = r"\$\{([^}:]+)(?::([^}]*))?\}"

            def replacer(match):
                var_name = match.group(1)
                default_value = match.group(2) if match.group(2) is not None else ""
                resolved = os.getenv(var_name, default_value)
                logger.debug(f"Resolved ${{{var_name}}} -> {resolved}")
                return resolved

            return re.sub(pattern, replacer, value)

        elif isinstance(value, dict):
            return {k: self._resolve_env_vars(v) for k, v in value.items()}

        elif isinstance(value, list):
            return [self._resolve_env_vars(item) for item in value]

        return value

    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two configuration dictionaries

        Override values take precedence over base values.
        Nested dictionaries are merged recursively.

        Args:
            base: Base configuration
            override: Override configuration

        Returns:
            Merged configuration
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_env_overrides(
        self, config: Dict, env_overrides_map: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Apply environment variable overrides to configuration

        Uses the env_overrides map from the config to determine which
        environment variables can override which config values.

        Args:
            config: Configuration dictionary
            env_overrides_map: Map of ENV_VAR -> config.path.to.value

        Returns:
            Configuration with environment overrides applied
        """
        if not env_overrides_map:
            env_overrides_map = config.get("env_overrides", {})

        result = config.copy()

        for env_var, config_path in env_overrides_map.items():
            env_value = os.getenv(env_var)

            if env_value is not None:
                # Parse config path (e.g., "models.primary.model_id")
                keys = config_path.split(".")

                # Navigate to the parent dict
                current = result
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]

                # Set the value (with type conversion)
                final_key = keys[-1]
                current[final_key] = self._convert_env_value(env_value)

                logger.debug(
                    f"Applied env override: {env_var}={env_value} -> {config_path}"
                )

        return result

    def _convert_env_value(self, value: str) -> Any:
        """
        Convert environment variable string to appropriate type

        Args:
            value: String value from environment variable

        Returns:
            Converted value (bool, int, float, or string)
        """
        # Boolean
        if value.lower() in ("true", "yes", "on", "1"):
            return True
        if value.lower() in ("false", "no", "off", "0"):
            return False

        # Integer
        try:
            return int(value)
        except ValueError:
            pass

        # Float
        try:
            return float(value)
        except ValueError:
            pass

        # String (default)
        return value

    def load_config(self, config_name: str = "config") -> Dict[str, Any]:
        """
        Load main configuration with environment-specific overrides

        Priority:
        1. Environment variables
        2. .env file (already loaded by dotenv)
        3. config.{environment}.yaml
        4. config.yaml

        Args:
            config_name: Name of config file (without .yaml extension)

        Returns:
            Merged configuration dictionary
        """
        cache_key = f"{config_name}_{self.environment}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Load base config
        base_config_path = self.config_dir / f"{config_name}.yaml"
        if not base_config_path.exists():
            raise FileNotFoundError(f"Config file not found: {base_config_path}")

        logger.info(f"Loading config: {base_config_path}")
        with open(base_config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # Load environment-specific overrides
        env_config_path = self.config_dir / f"{config_name}.{self.environment}.yaml"
        if env_config_path.exists():
            logger.info(f"Loading environment config: {env_config_path}")
            with open(env_config_path, "r", encoding="utf-8") as f:
                env_config = yaml.safe_load(f) or {}
            config = self._merge_configs(config, env_config)

        # Resolve environment variables in config values
        config = self._resolve_env_vars(config)

        # Cache the result
        self._cache[cache_key] = config

        return config

    def load_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """
        Load provider-specific configuration

        Args:
            provider_name: Provider name (e.g., "openrouter", "google")

        Returns:
            Provider configuration with environment overrides
        """
        cache_key = f"provider_{provider_name}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        provider_path = self.config_dir / "providers" / f"{provider_name}.yaml"

        if not provider_path.exists():
            logger.warning(f"Provider config not found: {provider_path}")
            return {}

        logger.info(f"Loading provider config: {provider_path}")
        with open(provider_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # Resolve environment variables
        config = self._resolve_env_vars(config)

        # Apply environment overrides if specified
        if "env_overrides" in config:
            config = self._apply_env_overrides(config)

        # Cache the result
        self._cache[cache_key] = config

        return config

    def load_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Load agent-specific configuration with full three-tier override

        This is the key method for the agent proxy layer:
        1. Loads agent YAML (developer pre-configured optimal settings)
        2. Applies .env values (user's API keys and preferences)
        3. Applies environment variable overrides (runtime)

        Args:
            agent_name: Agent name (e.g., "research_agent", "sec_agent")

        Returns:
            Agent configuration with all overrides applied
        """
        cache_key = f"agent_{agent_name}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        agent_path = self.config_dir / "agents" / f"{agent_name}.yaml"

        if not agent_path.exists():
            logger.warning(f"Agent config not found: {agent_path}")
            return {}

        logger.info(f"Loading agent config: {agent_path}")
        with open(agent_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # Step 1: Resolve ${VAR} syntax in YAML values
        config = self._resolve_env_vars(config)

        # Step 2: Apply environment variable overrides via env_overrides map
        if "env_overrides" in config:
            config = self._apply_env_overrides(config)

        # Cache the result
        self._cache[cache_key] = config

        logger.debug(f"Agent config loaded: {agent_name}")
        return config

    def load_third_party_config(self, integration_name: str) -> Dict[str, Any]:
        """
        Load third-party integration configuration

        Args:
            integration_name: Integration name (e.g., "trading_agents")

        Returns:
            Integration configuration with overrides applied
        """
        cache_key = f"third_party_{integration_name}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        integration_path = self.config_dir / "third_party" / f"{integration_name}.yaml"

        if not integration_path.exists():
            logger.warning(f"Third-party config not found: {integration_path}")
            return {}

        logger.info(f"Loading third-party config: {integration_path}")
        with open(integration_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # Resolve environment variables
        config = self._resolve_env_vars(config)

        # Apply environment overrides if specified
        if "env_overrides" in config:
            config = self._apply_env_overrides(config)

        # Cache the result
        self._cache[cache_key] = config

        return config

    def get(
        self, key_path: str, default: Any = None, config_name: str = "config"
    ) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key_path: Path to config key (e.g., "models.primary_provider")
            default: Default value if key not found
            config_name: Config file to load from

        Returns:
            Configuration value

        Example:
            >>> loader.get("models.providers.openrouter.enabled")
            True
            >>> loader.get("models.defaults.temperature", default=0.7)
            0.7
        """
        config = self.load_config(config_name)
        keys = key_path.split(".")

        value = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def clear_cache(self):
        """Clear cache"""
        self._cache.clear()
        logger.info("Configuration cache cleared")

    def list_providers(self) -> List[str]:
        """
        List all available provider configurations

        Returns:
            List of provider names
        """
        providers_dir = self.config_dir / "providers"
        if not providers_dir.exists():
            return []

        return [f.stem for f in providers_dir.glob("*.yaml")]

    def list_agents(self) -> List[str]:
        """
        List all available agent configurations

        Returns:
            List of agent names
        """
        agents_dir = self.config_dir / "agents"
        if not agents_dir.exists():
            return []

        return [f.stem for f in agents_dir.glob("*.yaml")]

    def validate_agent_config(self, agent_name: str) -> tuple[bool, List[str]]:
        """
        Validate agent configuration

        Checks:
        - Required API keys are available
        - Model IDs are valid
        - Provider is configured

        Args:
            agent_name: Agent name to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        config = self.load_agent_config(agent_name)
        if not config:
            return False, [f"Agent config not found: {agent_name}"]

        # Check if agent is enabled
        if not config.get("enabled", True):
            errors.append(f"Agent is disabled: {agent_name}")

        # Check model configuration
        models = config.get("models", {})
        primary = models.get("primary", {})

        provider = primary.get("provider")

        if not provider:
            errors.append("No provider specified for primary model")

        if provider:
            # Load provider config to get API key env var
            provider_config = self.load_provider_config(provider)
            if provider_config:
                api_key_env = provider_config.get("connection", {}).get("api_key_env")
                if api_key_env and not os.getenv(api_key_env):
                    errors.append(f"API key not set: {api_key_env}")

        # Check required API keys for agent
        api_keys = config.get("api_keys", {})
        for key_name, key_config in api_keys.items():
            if key_config.get("required", False):
                key_env = key_config.get("key_env")
                if key_env and not os.getenv(key_env):
                    errors.append(f"Required API key not set: {key_env}")

        return len(errors) == 0, errors


# ============================================
# Singleton Instance
# ============================================

_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """
    Get singleton configuration loader instance

    Note: This is used internally by ConfigManager. Application code
    should use ConfigManager instead for type-safe configuration access.

    Returns:
        ConfigLoader instance
    """
    global _loader
    if _loader is None:
        _loader = ConfigLoader()
    return _loader
