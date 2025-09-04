"""Core constants for ValueCell application."""

from typing import Dict, List, Tuple

# Supported Languages Configuration
SUPPORTED_LANGUAGES: List[Tuple[str, str]] = [
    ("en-US", "English (United States)"),
    ("en-GB", "English (United Kingdom)"),
    ("zh-Hans", "简体中文 (Simplified Chinese)"),
    ("zh-Hant", "繁體中文 (Traditional Chinese)"),
]

# Language to Timezone Mapping
LANGUAGE_TIMEZONE_MAPPING: Dict[str, str] = {
    "en-US": "America/New_York",
    "en-GB": "Europe/London",
    "zh-Hans": "Asia/Shanghai",
    "zh-Hant": "Asia/Hong_Kong",
}

# Default Language and Timezone
DEFAULT_LANGUAGE = "en-US"
DEFAULT_TIMEZONE = "UTC"

# Supported Language Codes
SUPPORTED_LANGUAGE_CODES = [lang[0] for lang in SUPPORTED_LANGUAGES]

# Database Configuration
DB_CHARSET = "utf8mb4"
DB_COLLATION = "utf8mb4_unicode_ci"

# Date and Time Format Configuration
DATE_FORMATS: Dict[str, str] = {
    "en-US": "%m/%d/%Y",
    "en-GB": "%d/%m/%Y",
    "zh-Hans": "%Y年%m月%d日",
    "zh-Hant": "%Y年%m月%d日",
}

TIME_FORMATS: Dict[str, str] = {
    "en-US": "%I:%M %p",
    "en-GB": "%H:%M",
    "zh-Hans": "%H:%M",
    "zh-Hant": "%H:%M",
}

DATETIME_FORMATS: Dict[str, str] = {
    "en-US": "%m/%d/%Y %I:%M %p",
    "en-GB": "%d/%m/%Y %H:%M",
    "zh-Hans": "%Y年%m月%d日 %H:%M",
    "zh-Hant": "%Y年%m月%d日 %H:%M",
}

# Currency Configuration
CURRENCY_SYMBOLS: Dict[str, str] = {
    "en-US": "$",
    "en-GB": "£",
    "zh-Hans": "¥",
    "zh-Hant": "HK$",
}

# Number Formatting Configuration
NUMBER_FORMATS: Dict[str, Dict[str, str]] = {
    "en-US": {"decimal": ".", "thousands": ","},
    "en-GB": {"decimal": ".", "thousands": ","},
    "zh-Hans": {"decimal": ".", "thousands": ","},
    "zh-Hant": {"decimal": ".", "thousands": ","},
}
