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
    ("en", "English"),
    ("zh_CN", "简体中文 (Simplified Chinese)"),
    ("zh_TW", "繁體中文 (Traditional Chinese)"),
    ("ja", "日本語 (Japanese)"),
]

# Language to Timezone Mapping
LANGUAGE_TIMEZONE_MAPPING: Dict[str, str] = {
    "en": "America/New_York",
    "zh_CN": "Asia/Shanghai",
    "zh_TW": "Asia/Hong_Kong",
    "ja": "Asia/Tokyo",
}

# Default Language and Timezone
DEFAULT_LANGUAGE = "en"
DEFAULT_TIMEZONE = "UTC"

# Supported Language Codes
SUPPORTED_LANGUAGE_CODES = [lang[0] for lang in SUPPORTED_LANGUAGES]

# Database Configuration
DB_CHARSET = "utf8mb4"
DB_COLLATION = "utf8mb4_unicode_ci"

# Date and Time Format Configuration
DATE_FORMATS: Dict[str, str] = {
    "en": "%m/%d/%Y",
    "zh_CN": "%Y年%m月%d日",
    "zh_TW": "%Y年%m月%d日",
    "ja": "%Y/%m/%d",
}

TIME_FORMATS: Dict[str, str] = {
    "en": "%I:%M %p",
    "zh_CN": "%H:%M",
    "zh_TW": "%H:%M",
    "ja": "%H:%M",
}

DATETIME_FORMATS: Dict[str, str] = {
    "en": "%m/%d/%Y %I:%M %p",
    "zh_CN": "%Y年%m月%d日 %H:%M",
    "zh_TW": "%Y年%m月%d日 %H:%M",
    "ja": "%Y/%m/%d %H:%M",
}

# Currency Configuration
CURRENCY_SYMBOLS: Dict[str, str] = {
    "en": "$",
    "zh_CN": "¥",
    "zh_TW": "HK$",
    "ja": "¥",
}

# Number Formatting Configuration
NUMBER_FORMATS: Dict[str, Dict[str, str]] = {
    "en": {"decimal": ".", "thousands": ","},
    "zh_CN": {"decimal": ".", "thousands": ","},
    "zh_TW": {"decimal": ".", "thousands": ","},
    "ja": {"decimal": ".", "thousands": ","},
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
