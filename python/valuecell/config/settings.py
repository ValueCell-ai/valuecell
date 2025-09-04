"""Settings configuration for ValueCell application."""

import os
from typing import Optional
from pathlib import Path

from ..core.constants import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGE_CODES,
    DB_CHARSET,
    DB_COLLATION,
)
from .i18n import I18nConfig


class Settings:
    """Application settings configuration."""

    def __init__(self):
        """Initialize settings from environment variables."""
        # Application Configuration
        self.APP_NAME = os.getenv("APP_NAME", "ValueCell")
        self.APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
        self.APP_ENVIRONMENT = os.getenv("APP_ENVIRONMENT", "development")

        # API Configuration
        self.API_HOST = os.getenv("API_HOST", "localhost")
        self.API_PORT = int(os.getenv("API_PORT", "8000"))
        self.API_DEBUG = os.getenv("API_DEBUG", "false").lower() == "true"

        # Database Configuration
        self.DB_CHARSET = os.getenv("DB_CHARSET", DB_CHARSET)
        self.DB_COLLATION = os.getenv("DB_COLLATION", DB_COLLATION)

        # Internationalization Configuration
        self.LANG = os.getenv("LANG", DEFAULT_LANGUAGE)
        self.TIMEZONE = os.getenv("TIMEZONE", "")

        # Validate language
        if self.LANG not in SUPPORTED_LANGUAGE_CODES:
            self.LANG = DEFAULT_LANGUAGE

        # File and Directory Configuration
        self.BASE_DIR = Path(__file__).parent.parent.parent
        self.LOCALE_DIR = self.BASE_DIR / "locales"

        # Ensure locale directory exists
        self.LOCALE_DIR.mkdir(exist_ok=True)

        # Initialize i18n configuration
        self._i18n_config = I18nConfig(self.LANG, self.TIMEZONE)

        # API Configuration
        self.API_ENABLED = os.getenv("API_ENABLED", "true").lower() == "true"
        self.API_I18N_ENABLED = os.getenv("API_I18N_ENABLED", "true").lower() == "true"

    @property
    def i18n(self) -> I18nConfig:
        """Get i18n configuration."""
        return self._i18n_config

    def update_language(self, language: str) -> None:
        """Update application language."""
        if language in SUPPORTED_LANGUAGE_CODES:
            self.LANG = language
            self._i18n_config.set_language(language)

    def update_timezone(self, timezone: str) -> None:
        """Update application timezone."""
        self.TIMEZONE = timezone
        self._i18n_config.set_timezone(timezone)

    def get_api_config(self) -> dict:
        """Get API configuration."""
        return {
            "enabled": self.API_ENABLED,
            "host": self.API_HOST,
            "port": self.API_PORT,
            "debug": self.API_DEBUG,
            "i18n_enabled": self.API_I18N_ENABLED,
        }

    def get_i18n_config(self) -> dict:
        """Get i18n configuration."""
        return self._i18n_config.to_dict()

    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return {
            "app_name": self.APP_NAME,
            "app_version": self.APP_VERSION,
            "app_environment": self.APP_ENVIRONMENT,
            "api": self.get_api_config(),
            "db_charset": self.DB_CHARSET,
            "db_collation": self.DB_COLLATION,
            "language": self.LANG,
            "timezone": self.TIMEZONE,
            "i18n": self.get_i18n_config(),
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset global settings instance."""
    global _settings
    _settings = None
