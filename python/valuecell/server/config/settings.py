"""Settings configuration for ValueCell Server."""

import os
from functools import lru_cache
from pathlib import Path

from valuecell.utils.env import get_system_env_dir


def _get_project_root() -> str:
    """Get project root directory path.

    Layout assumption: this file is at repo_root/python/valuecell/server/config/settings.py
    We walk up 4 levels to reach repo_root.
    """
    here = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    return repo_root


def _default_db_path() -> str:
    """Get default database DSN under the system application directory.

    Mirrors `.env` location so the SQLite file lives alongside user-level config:
    - macOS: `~/Library/Application Support/ValueCell/valuecell.db`
    - Linux: `~/.config/valuecell/valuecell.db`
    - Windows: `%APPDATA%\ValueCell\valuecell.db`
    """
    system_dir = get_system_env_dir()
    return f"sqlite:///{os.path.join(str(system_dir), 'valuecell.db')}"


class Settings:
    """Server configuration settings."""

    def __init__(self):
        """Initialize settings from environment variables."""
        # Application Configuration
        self.APP_NAME = os.getenv("APP_NAME", "ValueCell Server")
        self.APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
        self.APP_ENVIRONMENT = os.getenv("APP_ENVIRONMENT", "development")

        # API Configuration
        self.API_HOST = os.getenv("API_HOST", "0.0.0.0")
        self.API_PORT = int(os.getenv("API_PORT", "8000"))
        self.API_DEBUG = os.getenv("API_DEBUG", "false").lower() == "true"

        # CORS Configuration
        cors_origins = os.getenv("CORS_ORIGINS", "*")
        self.CORS_ORIGINS = cors_origins.split(",") if cors_origins != "*" else ["*"]

        # Database Configuration
        # Prefer `VALUECELL_DATABASE_URL` if provided; otherwise use system application directory default.
        env_db = os.getenv("VALUECELL_DATABASE_URL")
        if env_db:
            # If it's already a full DSN (sqlite or other), use as-is
            self.DATABASE_URL = env_db
        else:
            self.DATABASE_URL = _default_db_path()

        # File Paths
        self.BASE_DIR = Path(__file__).parent.parent.parent
        self.LOGS_DIR = self.BASE_DIR / "logs"
        self.LOGS_DIR.mkdir(exist_ok=True)

        # I18n Configuration
        self.LOCALE_DIR = self.BASE_DIR / "configs/locales"

    def get_database_config(self) -> dict:
        """Get database configuration."""
        return {"url": self.DATABASE_URL}

    def update_language(self, language: str) -> None:
        """Update current language setting.

        Args:
            language: Language code to set
        """
        # In a production environment, this might update a database or config file
        # For now, we'll just log the change
        pass

    def update_timezone(self, timezone: str) -> None:
        """Update current timezone setting.

        Args:
            timezone: Timezone to set
        """
        # In a production environment, this might update a database or config file
        # For now, we'll just log the change
        pass


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
