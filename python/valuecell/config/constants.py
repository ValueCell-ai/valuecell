"""Core constants for ValueCell application."""

from pathlib import Path
from typing import Dict, List, Tuple

# Project Root Directory
# This points to the python/ directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Configuration Directory
CONFIG_DIR = PROJECT_ROOT / "configs"

# Supported Languages Configuration
SUPPORTED_LANGUAGES: List[Tuple[str, str]] = [
    ("en-US", "English (United States)"),
    ("en-GB", "English (United Kingdom)"),
    ("zh-Hans", "简体中文 (Simplified Chinese)"),
    ("zh-Hant", "繁體中文 (Traditional Chinese)"),
    ("ja-JP", "日本語 (Japanese)"),
    ("de-DE", "Deutsch (German)"),
    ("fr-FR", "Français (French)"),
    ("ca-ES", "Català (Catalan)"),
    ("es-ES", "Español (Spanish)"),
    ("it-IT", "Italiano (Italian)"),
    ("pl-PL", "Polski (Polish)"),
    ("tr-TR", "Türkçe (Turkish)"),
    ("ru-RU", "Русский (Russian)"),
    ("pt-PT", "Português (Portuguese)"),
    ("id-ID", "Bahasa Indonesia (Indonesian)"),
    ("ms-MY", "Bahasa Melayu (Malay)"),
    ("th-TH", "ภาษาไทย (Thai)"),
    ("vi-VN", "Tiếng Việt (Vietnamese)"),
    ("ko-KR", "한국어 (Korean)"),
]

# Language to Timezone Mapping
LANGUAGE_TIMEZONE_MAPPING: Dict[str, str] = {
    "en-US": "America/New_York",
    "en-GB": "Europe/London",
    "zh-Hans": "Asia/Shanghai",
    "zh-Hant": "Asia/Hong_Kong",
    "ja-JP": "Asia/Tokyo",
    "de-DE": "Europe/Berlin",
    "fr-FR": "Europe/Paris",
    "ca-ES": "Europe/Madrid",
    "es-ES": "Europe/Madrid",
    "it-IT": "Europe/Rome",
    "pl-PL": "Europe/Warsaw",
    "tr-TR": "Europe/Istanbul",
    "ru-RU": "Europe/Moscow",
    "pt-PT": "Europe/Lisbon",
    "id-ID": "Asia/Jakarta",
    "ms-MY": "Asia/Kuala_Lumpur",
    "th-TH": "Asia/Bangkok",
    "vi-VN": "Asia/Ho_Chi_Minh",
    "ko-KR": "Asia/Seoul",
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
    "ja-JP": "%Y/%m/%d",
    "de-DE": "%d.%m.%Y",
    "fr-FR": "%d/%m/%Y",
    "ca-ES": "%d/%m/%Y",
    "es-ES": "%d/%m/%Y",
    "it-IT": "%d/%m/%Y",
    "pl-PL": "%d.%m.%Y",
    "tr-TR": "%d.%m.%Y",
    "ru-RU": "%d.%m.%Y",
    "pt-PT": "%d/%m/%Y",
    "id-ID": "%d/%m/%Y",
    "ms-MY": "%d/%m/%Y",
    "th-TH": "%d/%m/%Y",
    "vi-VN": "%d/%m/%Y",
    "ko-KR": "%Y. %m. %d.",
}

TIME_FORMATS: Dict[str, str] = {
    "en-US": "%I:%M %p",
    "en-GB": "%H:%M",
    "zh-Hans": "%H:%M",
    "zh-Hant": "%H:%M",
    "ja-JP": "%H:%M",
    "de-DE": "%H:%M",
    "fr-FR": "%H:%M",
    "ca-ES": "%H:%M",
    "es-ES": "%H:%M",
    "it-IT": "%H:%M",
    "pl-PL": "%H:%M",
    "tr-TR": "%H:%M",
    "ru-RU": "%H:%M",
    "pt-PT": "%H:%M",
    "id-ID": "%H:%M",
    "ms-MY": "%H:%M",
    "th-TH": "%H:%M",
    "vi-VN": "%H:%M",
    "ko-KR": "%H:%M",
}

DATETIME_FORMATS: Dict[str, str] = {
    "en-US": "%m/%d/%Y %I:%M %p",
    "en-GB": "%d/%m/%Y %H:%M",
    "zh-Hans": "%Y年%m月%d日 %H:%M",
    "zh-Hant": "%Y年%m月%d日 %H:%M",
    "ja-JP": "%Y/%m/%d %H:%M",
    "de-DE": "%d.%m.%Y %H:%M",
    "fr-FR": "%d/%m/%Y %H:%M",
    "ca-ES": "%d/%m/%Y %H:%M",
    "es-ES": "%d/%m/%Y %H:%M",
    "it-IT": "%d/%m/%Y %H:%M",
    "pl-PL": "%d.%m.%Y %H:%M",
    "tr-TR": "%d.%m.%Y %H:%M",
    "ru-RU": "%d.%m.%Y %H:%M",
    "pt-PT": "%d/%m/%Y %H:%M",
    "id-ID": "%d/%m/%Y %H:%M",
    "ms-MY": "%d/%m/%Y %H:%M",
    "th-TH": "%d/%m/%Y %H:%M",
    "vi-VN": "%d/%m/%Y %H:%M",
    "ko-KR": "%Y. %m. %d. %H:%M",
}

# Currency Configuration
CURRENCY_SYMBOLS: Dict[str, str] = {
    "en-US": "$",
    "en-GB": "£",
    "zh-Hans": "¥",
    "zh-Hant": "HK$",
    "ja-JP": "¥",
    "de-DE": "€",
    "fr-FR": "€",
    "ca-ES": "€",
    "es-ES": "€",
    "it-IT": "€",
    "pl-PL": "zł",
    "tr-TR": "₺",
    "ru-RU": "₽",
    "pt-PT": "€",
    "id-ID": "Rp",
    "ms-MY": "RM",
    "th-TH": "฿",
    "vi-VN": "₫",
    "ko-KR": "₩",
}

# Number Formatting Configuration
NUMBER_FORMATS: Dict[str, Dict[str, str]] = {
    "en-US": {"decimal": ".", "thousands": ","},
    "en-GB": {"decimal": ".", "thousands": ","},
    "zh-Hans": {"decimal": ".", "thousands": ","},
    "zh-Hant": {"decimal": ".", "thousands": ","},
    "ja-JP": {"decimal": ".", "thousands": ","},
    "de-DE": {"decimal": ",", "thousands": "."},
    "fr-FR": {"decimal": ",", "thousands": " "},
    "ca-ES": {"decimal": ",", "thousands": "."},
    "es-ES": {"decimal": ",", "thousands": "."},
    "it-IT": {"decimal": ",", "thousands": "."},
    "pl-PL": {"decimal": ",", "thousands": " "},
    "tr-TR": {"decimal": ",", "thousands": "."},
    "ru-RU": {"decimal": ",", "thousands": " "},
    "pt-PT": {"decimal": ",", "thousands": " "},
    "id-ID": {"decimal": ",", "thousands": "."},
    "ms-MY": {"decimal": ".", "thousands": ","},
    "th-TH": {"decimal": ".", "thousands": ","},
    "vi-VN": {"decimal": ",", "thousands": "."},
    "ko-KR": {"decimal": ".", "thousands": ","},
}

# Region-based default tickers for homepage display
# 'cn' for China mainland users (A-share indices via akshare/baostock)
# 'default' for other regions (global indices via yfinance)
REGION_DEFAULT_TICKERS: Dict[str, List[Dict[str, str]]] = {
    # China mainland users - A-share indices only
    "cn": [
        {"ticker": "SSE:000001", "symbol": "上证指数", "name": "上证指数"},
        {"ticker": "SZSE:399001", "symbol": "深证成指", "name": "深证成指"},
        {"ticker": "SSE:000300", "symbol": "沪深300", "name": "沪深300指数"},
    ],
    # Default for other regions - global mixed indices
    "default": [
        {"ticker": "NASDAQ:IXIC", "symbol": "NASDAQ", "name": "NASDAQ Composite"},
        {"ticker": "HKEX:HSI", "symbol": "HSI", "name": "Hang Seng Index"},
        {"ticker": "SSE:000001", "symbol": "SSE", "name": "Shanghai Composite"},
    ],
}
