"""Internationalization service for ValueCell application."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...config.constants import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGE_CODES
from ..config.i18n import get_i18n_config
from ..config.settings import get_settings


class TranslationManager:
    """Manages translation loading and caching."""

    def __init__(self, locale_dir: Optional[Path] = None):
        """Initialize translation manager.

        Args:
            locale_dir: Directory containing translation files
        """
        self._locale_dir = locale_dir or get_settings().LOCALE_DIR
        self._translations: Dict[str, Dict[str, Any]] = {}
        self._load_all_translations()

    def _load_all_translations(self) -> None:
        """Load all translation files."""
        for lang_code in SUPPORTED_LANGUAGE_CODES:
            self._load_translation(lang_code)

    def _load_translation(self, language: str) -> None:
        """Load translation for specific language.

        Args:
            language: Language code to load
        """
        translation_file = self._locale_dir / f"{language}.json"

        if translation_file.exists():
            try:
                with open(translation_file, "r", encoding="utf-8") as f:
                    self._translations[language] = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading translation file {translation_file}: {e}")
                self._translations[language] = {}
        else:
            # Create empty translation if file doesn't exist
            self._translations[language] = {}

    def get_translation(self, language: str, key: str, **kwargs) -> str:
        """Get translated string for given key and language.

        Args:
            language: Language code
            key: Translation key (supports dot notation for nested keys)
            **kwargs: Variables for string formatting

        Returns:
            Translated string or key if translation not found
        """
        if language not in self._translations:
            language = DEFAULT_LANGUAGE

        translations = self._translations.get(language, {})

        # Support dot notation for nested keys
        keys = key.split(".")
        value = translations

        try:
            for k in keys:
                value = value[k]
        except (KeyError, TypeError):
            # Fallback to default language
            if language != DEFAULT_LANGUAGE:
                return self.get_translation(DEFAULT_LANGUAGE, key, **kwargs)
            return key  # Return key if no translation found

        # Format string with provided variables
        if isinstance(value, str) and kwargs:
            try:
                return value.format(**kwargs)
            except (KeyError, ValueError):
                return value

        return str(value)

    def reload_translations(self) -> None:
        """Reload all translation files."""
        self._translations.clear()
        self._load_all_translations()

    def get_available_keys(self, language: str) -> List[str]:
        """Get all available translation keys for a language.

        Args:
            language: Language code

        Returns:
            List of available translation keys
        """
        translations = self._translations.get(language, {})

        def _get_keys(obj: Dict[str, Any], prefix: str = "") -> List[str]:
            keys = []
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    keys.extend(_get_keys(value, full_key))
                else:
                    keys.append(full_key)
            return keys

        return _get_keys(translations)


class I18nService:
    """Main internationalization service."""

    def __init__(self):
        """Initialize i18n service."""
        self._translation_manager = TranslationManager()
        self._i18n_config = get_i18n_config()

    def translate(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """Translate a key to current or specified language.

        Args:
            key: Translation key
            language: Target language (uses current if not specified)
            **kwargs: Variables for string formatting

        Returns:
            Translated string
        """
        target_language = language or self._i18n_config.language
        return self._translation_manager.get_translation(target_language, key, **kwargs)

    def t(self, key: str, **kwargs) -> str:
        """Short alias for translate method.

        Args:
            key: Translation key
            **kwargs: Variables for string formatting

        Returns:
            Translated string
        """
        return self.translate(key, **kwargs)

    def get_current_language(self) -> str:
        """Get current language code."""
        return self._i18n_config.language

    def get_current_timezone(self) -> str:
        """Get current timezone."""
        return self._i18n_config.timezone

    def set_language(self, language: str) -> bool:
        """Set current language.

        Args:
            language: Language code to set

        Returns:
            True if language was set successfully
        """
        if language in SUPPORTED_LANGUAGE_CODES:
            self._i18n_config.set_language(language)
            get_settings().update_language(language)
            return True
        return False

    def set_timezone(self, timezone: str) -> bool:
        """Set current timezone.

        Args:
            timezone: Timezone to set

        Returns:
            True if timezone was set successfully
        """
        try:
            self._i18n_config.set_timezone(timezone)
            get_settings().update_timezone(timezone)
            return True
        except Exception:
            return False

    def format_datetime(self, dt: datetime, format_type: str = "datetime") -> str:
        """Format datetime according to current language settings.

        Args:
            dt: Datetime to format
            format_type: Type of format ('date', 'time', 'datetime')

        Returns:
            Formatted datetime string
        """
        return self._i18n_config.format_datetime(dt, format_type)

    def format_number(self, number: float, decimal_places: int = 2) -> str:
        """Format number according to current language settings.

        Args:
            number: Number to format
            decimal_places: Number of decimal places

        Returns:
            Formatted number string
        """
        return self._i18n_config.format_number(number, decimal_places)

    def format_currency(self, amount: float, decimal_places: int = 2) -> str:
        """Format currency according to current language settings.

        Args:
            amount: Amount to format
            decimal_places: Number of decimal places

        Returns:
            Formatted currency string
        """
        return self._i18n_config.format_currency(amount, decimal_places)

    def get_supported_languages(self) -> List[tuple]:
        """Get list of supported languages.

        Returns:
            List of (code, name) tuples
        """
        from ...config.constants import SUPPORTED_LANGUAGES

        return SUPPORTED_LANGUAGES

    def get_language_name(self, language_code: str) -> str:
        """Get display name for language code.

        Args:
            language_code: Language code

        Returns:
            Display name or code if not found
        """
        from ...config.constants import SUPPORTED_LANGUAGES

        for code, name in SUPPORTED_LANGUAGES:
            if code == language_code:
                return name
        return language_code

    def reload_translations(self) -> None:
        """Reload all translation files."""
        self._translation_manager.reload_translations()

    def get_translation_keys(self, language: Optional[str] = None) -> List[str]:
        """Get all available translation keys for a language.

        Args:
            language: Language code (uses current if not specified)

        Returns:
            List of available translation keys
        """
        target_language = language or self._i18n_config.language
        return self._translation_manager.get_available_keys(target_language)

    def to_dict(self) -> Dict[str, Any]:
        """Get current i18n configuration as dictionary.

        Returns:
            Dictionary with i18n configuration matching I18nConfigData schema
        """
        config_dict = self._i18n_config.to_dict()
        return {
            "language": config_dict["language"],
            "timezone": config_dict["timezone"],
            "date_format": config_dict["date_format"],
            "time_format": config_dict["time_format"],
            "datetime_format": config_dict["datetime_format"],
            "currency_symbol": config_dict["currency_symbol"],
            "number_format": config_dict["number_format"],
            "is_rtl": config_dict["is_rtl"],
        }


# Global i18n service instance
_i18n_service: Optional[I18nService] = None


def get_i18n_service() -> I18nService:
    """Get global i18n service instance."""
    global _i18n_service
    if _i18n_service is None:
        _i18n_service = I18nService()
    return _i18n_service


def reset_i18n_service() -> None:
    """Reset global i18n service instance."""
    global _i18n_service
    _i18n_service = None


# Convenience functions
def t(key: str, **kwargs) -> str:
    """Translate a key (convenience function).

    Args:
        key: Translation key
        **kwargs: Variables for string formatting

    Returns:
        Translated string
    """
    return get_i18n_service().translate(key, **kwargs)


def translate(key: str, language: Optional[str] = None, **kwargs) -> str:
    """Translate a key to specified language (convenience function).

    Args:
        key: Translation key
        language: Target language
        **kwargs: Variables for string formatting

    Returns:
        Translated string
    """
    return get_i18n_service().translate(key, language, **kwargs)
