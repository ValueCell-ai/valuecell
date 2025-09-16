"""Settings configuration for ValueCell Server."""

import os
from pathlib import Path
from functools import lru_cache


class Settings:
    """Server configuration settings."""

    def __init__(self):
        """Initialize settings from environment variables."""
        # Application Configuration
        self.APP_NAME = os.getenv("APP_NAME", "ValueCell Server")
        self.APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
        self.APP_ENVIRONMENT = os.getenv("APP_ENVIRONMENT", "development")

        # API Configuration
        self.API_HOST = os.getenv("API_HOST", "localhost")
        self.API_PORT = int(os.getenv("API_PORT", "8000"))
        self.API_DEBUG = os.getenv("API_DEBUG", "false").lower() == "true"

        # CORS Configuration
        cors_origins = os.getenv("CORS_ORIGINS", "*")
        self.CORS_ORIGINS = cors_origins.split(",") if cors_origins != "*" else ["*"]

        # Database Configuration
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./valuecell.db")
        self.DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

        # Redis Configuration
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

        # Security Configuration
        self.SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )

        # Logging Configuration
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "json")

        # File Paths
        self.BASE_DIR = Path(__file__).parent.parent.parent
        self.LOGS_DIR = self.BASE_DIR / "logs"
        self.LOGS_DIR.mkdir(exist_ok=True)

        # I18n Configuration
        self.LOCALE_DIR = self.BASE_DIR / "locales"

        # Agent Configuration
        self.AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "300"))  # 5 minutes
        self.MAX_CONCURRENT_AGENTS = int(os.getenv("MAX_CONCURRENT_AGENTS", "10"))

        # External APIs
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
        self.ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.APP_ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.APP_ENVIRONMENT == "production"

    def get_database_config(self) -> dict:
        """Get database configuration."""
        return {
            "url": self.DATABASE_URL,
            "echo": self.DB_ECHO,
        }

    def get_redis_config(self) -> dict:
        """Get Redis configuration."""
        return {
            "url": self.REDIS_URL,
        }

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
