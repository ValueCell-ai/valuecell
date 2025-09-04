"""Internationalization configuration for ValueCell application."""

import os
from typing import Optional
import pytz
from datetime import datetime

from ..core.constants import (
    SUPPORTED_LANGUAGE_CODES,
    LANGUAGE_TIMEZONE_MAPPING,
    DEFAULT_LANGUAGE,
    DEFAULT_TIMEZONE,
    DATE_FORMATS,
    TIME_FORMATS,
    DATETIME_FORMATS,
    CURRENCY_SYMBOLS,
    NUMBER_FORMATS,
)


class I18nConfig:
    """Configuration class for internationalization settings."""

    def __init__(self, language: Optional[str] = None, timezone: Optional[str] = None):
        """Initialize i18n configuration.

        Args:
            language: Language code (e.g., 'en-US', 'zh-Hans')
            timezone: Timezone string (e.g., 'America/New_York', 'Asia/Shanghai')
        """
        self._language = self._validate_language(language or self._get_env_language())
        self._timezone = self._validate_timezone(timezone or self._get_env_timezone())

    def _get_env_language(self) -> str:
        """Get language from environment variables."""
        return os.getenv("LANG", DEFAULT_LANGUAGE)

    def _get_env_timezone(self) -> str:
        """Get timezone from environment variables or auto-detect from language."""
        env_timezone = os.getenv("TIMEZONE", "")
        if env_timezone:
            return env_timezone
        # Auto-select timezone based on language
        return LANGUAGE_TIMEZONE_MAPPING.get(self._language, DEFAULT_TIMEZONE)

    def _validate_language(self, language: str) -> str:
        """Validate and return language code."""
        if language not in SUPPORTED_LANGUAGE_CODES:
            return DEFAULT_LANGUAGE
        return language

    def _validate_timezone(self, timezone: str) -> str:
        """Validate and return timezone string."""
        try:
            pytz.timezone(timezone)
            return timezone
        except pytz.UnknownTimeZoneError:
            return DEFAULT_TIMEZONE

    @property
    def language(self) -> str:
        """Get current language code."""
        return self._language

    @property
    def timezone(self) -> str:
        """Get current timezone string."""
        return self._timezone

    @property
    def timezone_obj(self) -> pytz.BaseTzInfo:
        """Get current timezone object."""
        return pytz.timezone(self._timezone)

    def set_language(self, language: str) -> None:
        """Set language and update timezone if needed."""
        self._language = self._validate_language(language)
        # Auto-update timezone if it was auto-selected
        if not os.getenv("TIMEZONE"):
            self._timezone = LANGUAGE_TIMEZONE_MAPPING.get(
                self._language, DEFAULT_TIMEZONE
            )

    def set_timezone(self, timezone: str) -> None:
        """Set timezone."""
        self._timezone = self._validate_timezone(timezone)

    def get_date_format(self) -> str:
        """Get date format for current language."""
        return DATE_FORMATS.get(self._language, DATE_FORMATS[DEFAULT_LANGUAGE])

    def get_time_format(self) -> str:
        """Get time format for current language."""
        return TIME_FORMATS.get(self._language, TIME_FORMATS[DEFAULT_LANGUAGE])

    def get_datetime_format(self) -> str:
        """Get datetime format for current language."""
        return DATETIME_FORMATS.get(self._language, DATETIME_FORMATS[DEFAULT_LANGUAGE])

    def get_currency_symbol(self) -> str:
        """Get currency symbol for current language."""
        return CURRENCY_SYMBOLS.get(self._language, CURRENCY_SYMBOLS[DEFAULT_LANGUAGE])

    def get_number_format(self) -> dict:
        """Get number format configuration for current language."""
        return NUMBER_FORMATS.get(self._language, NUMBER_FORMATS[DEFAULT_LANGUAGE])

    def format_datetime(self, dt: datetime, format_type: str = "datetime") -> str:
        """Format datetime according to current language settings.

        Args:
            dt: Datetime object to format
            format_type: Type of format ('date', 'time', 'datetime')

        Returns:
            Formatted datetime string
        """
        # Convert to local timezone
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        local_dt = dt.astimezone(self.timezone_obj)

        # Get appropriate format
        if format_type == "date":
            fmt = self.get_date_format()
        elif format_type == "time":
            fmt = self.get_time_format()
        else:
            fmt = self.get_datetime_format()

        return local_dt.strftime(fmt)

    def format_number(self, number: float, decimal_places: int = 2) -> str:
        """Format number according to current language settings.

        Args:
            number: Number to format
            decimal_places: Number of decimal places

        Returns:
            Formatted number string
        """
        number_config = self.get_number_format()
        decimal_sep = number_config["decimal"]
        thousands_sep = number_config["thousands"]

        # Format with specified decimal places
        formatted = f"{number:,.{decimal_places}f}"

        # Replace separators if different from default
        if decimal_sep != ".":
            formatted = formatted.replace(".", "DECIMAL_TEMP")
        if thousands_sep != ",":
            formatted = formatted.replace(",", thousands_sep)
        if decimal_sep != ".":
            formatted = formatted.replace("DECIMAL_TEMP", decimal_sep)

        return formatted

    def format_currency(self, amount: float, decimal_places: int = 2) -> str:
        """Format currency according to current language settings.

        Args:
            amount: Amount to format
            decimal_places: Number of decimal places

        Returns:
            Formatted currency string
        """
        symbol = self.get_currency_symbol()
        number = self.format_number(amount, decimal_places)

        # Different currency placement for different languages
        if self._language.startswith("zh"):
            return f"{symbol}{number}"
        else:
            return f"{symbol}{number}"

    def is_rtl(self) -> bool:
        """Check if current language is right-to-left."""
        # None of our supported languages are RTL, but keeping for extensibility
        return False

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "language": self._language,
            "timezone": self._timezone,
            "date_format": self.get_date_format(),
            "time_format": self.get_time_format(),
            "datetime_format": self.get_datetime_format(),
            "currency_symbol": self.get_currency_symbol(),
            "number_format": self.get_number_format(),
            "is_rtl": self.is_rtl(),
        }


# Global i18n configuration instance
_i18n_config: Optional[I18nConfig] = None


def get_i18n_config() -> I18nConfig:
    """Get global i18n configuration instance."""
    global _i18n_config
    if _i18n_config is None:
        _i18n_config = I18nConfig()
    return _i18n_config


def set_i18n_config(config: I18nConfig) -> None:
    """Set global i18n configuration instance."""
    global _i18n_config
    _i18n_config = config


def reset_i18n_config() -> None:
    """Reset global i18n configuration instance."""
    global _i18n_config
    _i18n_config = None
