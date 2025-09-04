"""Internationalization module entry point for ValueCell.

This module provides convenient imports for i18n functionality.
Import from here to access all i18n features in one place.
"""

# Core i18n functionality
from .services.i18n_service import (
    get_i18n_service,
    t,
    translate,
    reset_i18n_service,
)

# Configuration
from .config.settings import get_settings
from .config.i18n import (
    get_i18n_config,
    set_i18n_config,
    reset_i18n_config,
    I18nConfig,
)

# Constants
from .core.constants import (
    SUPPORTED_LANGUAGES,
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

# Utilities
from .utils.i18n_utils import (
    detect_browser_language,
    get_timezone_for_language,
    validate_language_code,
    validate_timezone,
    get_available_timezones,
    get_common_timezones,
    get_timezone_display_name,
    convert_timezone,
    format_file_size,
    format_duration,
    pluralize,
    get_language_direction,
    extract_translation_keys,
    validate_translation_file,
    get_missing_translations,
    create_translation_template,
    translatable,
)

# API Router
from .api.router.i18n import get_i18n_router

# Export all i18n functionality
__all__ = [
    # Core services
    "get_i18n_service",
    "t",
    "translate",
    "reset_i18n_service",
    # Configuration
    "get_settings",
    "get_i18n_config",
    "set_i18n_config",
    "reset_i18n_config",
    "I18nConfig",
    # Constants
    "SUPPORTED_LANGUAGES",
    "SUPPORTED_LANGUAGE_CODES",
    "LANGUAGE_TIMEZONE_MAPPING",
    "DEFAULT_LANGUAGE",
    "DEFAULT_TIMEZONE",
    "DATE_FORMATS",
    "TIME_FORMATS",
    "DATETIME_FORMATS",
    "CURRENCY_SYMBOLS",
    "NUMBER_FORMATS",
    # Utilities
    "detect_browser_language",
    "get_timezone_for_language",
    "validate_language_code",
    "validate_timezone",
    "get_available_timezones",
    "get_common_timezones",
    "get_timezone_display_name",
    "convert_timezone",
    "format_file_size",
    "format_duration",
    "pluralize",
    "get_language_direction",
    "extract_translation_keys",
    "validate_translation_file",
    "get_missing_translations",
    "create_translation_template",
    "translatable",
    # API
    "get_i18n_router",
]
