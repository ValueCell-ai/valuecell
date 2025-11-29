"""Internationalization utility functions for ValueCell application."""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytz

from ..config.constants import (
    DEFAULT_LANGUAGE,
    DEFAULT_TIMEZONE,
    LANGUAGE_TIMEZONE_MAPPING,
    SUPPORTED_LANGUAGE_CODES,
    SUPPORTED_LANGUAGES,
)
from ..server.services.i18n_service import get_i18n_service


def detect_browser_language(accept_language_header: str) -> str:
    """Detect preferred language from browser Accept-Language header.

    Args:
        accept_language_header: HTTP Accept-Language header value

    Returns:
        Best matching supported language code
    """
    if not accept_language_header:
        return DEFAULT_LANGUAGE

    # Parse Accept-Language header
    languages = []
    for item in accept_language_header.split(","):
        parts = item.strip().split(";")
        lang = parts[0].strip()

        # Extract quality value
        quality = 1.0
        if len(parts) > 1:
            q_part = parts[1].strip()
            if q_part.startswith("q="):
                try:
                    quality = float(q_part[2:])
                except ValueError:
                    quality = 1.0

        languages.append((lang, quality))

    # Sort by quality (descending)
    languages.sort(key=lambda x: x[1], reverse=True)

    # Find best match
    for lang, _ in languages:
        # Direct match
        if lang in SUPPORTED_LANGUAGE_CODES:
            return lang

        # Try to match language family (e.g., 'zh' -> 'zh-Hans')
        lang_family = lang.split("-")[0]
        for supported_lang in SUPPORTED_LANGUAGE_CODES:
            if supported_lang.startswith(lang_family):
                return supported_lang

    return DEFAULT_LANGUAGE


def detect_user_region(client_ip: Optional[str] = None) -> str:
    """Detect user region based on IP geolocation.

    Args:
        client_ip: Optional client IP address. If None, uses server's IP for detection.

    Returns:
        Region code: 'cn' for China mainland, 'default' for others
    """

    try:
        import httpx

        with httpx.Client(timeout=3.0) as client:
            # Use client IP if provided, otherwise detect server's IP
            url = (
                f"https://ipapi.co/{client_ip}/json/"
                if client_ip
                else "https://ipapi.co/json/"
            )
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                country_code = data.get("country_code", "").upper()

                # China mainland
                if country_code == "CN":
                    return "cn"

                return "default"
            return "default"
    except Exception:
        # If detection fails, return default
        return "default"


async def detect_user_region_async(client_ip: Optional[str] = None) -> str:
    """Async version of detect_user_region for use in FastAPI routes.

    Args:
        client_ip: Optional client IP address. If None, uses server's IP for detection.

    Returns:
        Region code: 'cn' for China mainland, 'default' for others
    """
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3.0) as client:
            url = (
                f"https://ipapi.co/{client_ip}/json/"
                if client_ip
                else "https://ipapi.co/json/"
            )
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                country_code = data.get("country_code", "").upper()

                if country_code == "CN":
                    return "cn"

                return "default"
            return "default"
    except Exception:
        return "default"


def get_timezone_for_language(language: str) -> str:
    """Get default timezone for a language.

    Args:
        language: Language code

    Returns:
        Timezone string
    """
    return LANGUAGE_TIMEZONE_MAPPING.get(language, DEFAULT_TIMEZONE)


def validate_language_code(language: str) -> bool:
    """Validate if language code is supported.

    Args:
        language: Language code to validate

    Returns:
        True if language is supported
    """
    return language in SUPPORTED_LANGUAGE_CODES


def validate_timezone(timezone_str: str) -> bool:
    """Validate if timezone string is valid.

    Args:
        timezone_str: Timezone string to validate

    Returns:
        True if timezone is valid
    """
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.UnknownTimeZoneError:
        return False


def get_available_timezones() -> List[str]:
    """Get list of all available timezones.

    Returns:
        List of timezone strings
    """
    return sorted(pytz.all_timezones)


def get_common_timezones() -> List[str]:
    """Get list of commonly used timezones.

    Returns:
        List of common timezone strings
    """
    return sorted(pytz.common_timezones)


def get_timezone_display_name(timezone_str: str) -> str:
    """Get display name for timezone.

    Args:
        timezone_str: Timezone string

    Returns:
        Human-readable timezone name
    """
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        return f"{timezone_str} (UTC{now.strftime('%z')})"
    except pytz.UnknownTimeZoneError:
        return timezone_str


def convert_timezone(dt: datetime, from_tz: str, to_tz: str) -> datetime:
    """Convert datetime from one timezone to another.

    Args:
        dt: Datetime to convert
        from_tz: Source timezone
        to_tz: Target timezone

    Returns:
        Converted datetime
    """
    try:
        from_timezone = pytz.timezone(from_tz)
        to_timezone = pytz.timezone(to_tz)

        # Localize if naive
        if dt.tzinfo is None:
            dt = from_timezone.localize(dt)

        # Convert to target timezone
        return dt.astimezone(to_timezone)
    except pytz.UnknownTimeZoneError:
        return dt


def parse_utc_datetime(date_str: str) -> datetime:
    """Parse UTC datetime string into timezone-aware datetime object.

    Args:
        date_str: UTC datetime string in ISO format (YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS.fffZ)

    Returns:
        Timezone-aware datetime object in UTC

    Raises:
        ValueError: If date string format is invalid
    """
    # Try different UTC datetime formats
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",  # 2023-12-01T10:30:00Z
        "%Y-%m-%dT%H:%M:%S.%fZ",  # 2023-12-01T10:30:00.123Z
        "%Y-%m-%dT%H:%M:%S.%f",  # 2023-12-01T10:30:00.123 (without Z)
        "%Y-%m-%dT%H:%M:%S",  # 2023-12-01T10:30:00 (without Z)
        "%Y-%m-%d",  # 2023-12-01 (date only)
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # If no timezone info, assume UTC
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            return dt
        except ValueError:
            continue

    raise ValueError(
        f"Invalid UTC datetime format: {date_str}. Expected formats: YYYY-MM-DDTHH:MM:SSZ, YYYY-MM-DDTHH:MM:SS.fffZ, or YYYY-MM-DD"
    )


def format_utc_datetime(dt: datetime, format_type: str = "iso") -> str:
    """Format datetime as UTC string.

    Args:
        dt: Datetime object to format
        format_type: Format type ('iso', 'date', 'time', 'datetime')

    Returns:
        Formatted UTC datetime string
    """
    # Ensure datetime is in UTC
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    elif dt.tzinfo != pytz.UTC:
        dt = dt.astimezone(pytz.UTC)

    if format_type == "iso":
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif format_type == "date":
        return dt.strftime("%Y-%m-%d")
    elif format_type == "time":
        return dt.strftime("%H:%M:%SZ")
    else:  # datetime
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_utc_now() -> datetime:
    """Get current UTC datetime.

    Returns:
        Current datetime in UTC timezone
    """
    return datetime.now(pytz.UTC)


def parse_and_validate_utc_dates(
    start_date: Optional[str], end_date: Optional[str]
) -> tuple[datetime, datetime]:
    """Parse and validate UTC date parameters for API endpoints.

    Args:
        start_date: Start date string in UTC format (optional)
        end_date: End date string in UTC format (optional)

    Returns:
        Tuple of (start_datetime, end_datetime) in UTC

    Raises:
        ValueError: If date format is invalid or start_date >= end_date
    """
    # Parse end date
    if end_date:
        end_dt = parse_utc_datetime(end_date)
    else:
        end_dt = get_utc_now()

    # Parse start date
    if start_date:
        start_dt = parse_utc_datetime(start_date)
    else:
        start_dt = end_dt - timedelta(days=30)

    # Validate date range
    if start_dt >= end_dt:
        raise ValueError("Start date must be before end date")

    return start_dt, end_dt


def format_file_size(size_bytes: int, language: Optional[str] = None) -> str:
    """Format file size according to language settings.

    Args:
        size_bytes: File size in bytes
        language: Language code (uses current if not specified)

    Returns:
        Formatted file size string
    """
    i18n = get_i18n_service()
    target_language = language or i18n.get_current_language()

    if size_bytes == 0:
        return f"0 {i18n.translate('units.bytes', language=target_language)}"

    units = ["bytes", "kb", "mb", "gb", "tb"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    unit_key = f"units.{units[unit_index]}"
    unit_name = i18n.translate(unit_key, language=target_language)

    if unit_index == 0:
        return f"{int(size)} {unit_name}"
    else:
        formatted_size = i18n.format_number(size, 1)
        return f"{formatted_size} {unit_name}"


def get_current_language() -> str:
    """Get current language code."""
    return get_i18n_service().get_current_language()


def get_current_timezone() -> str:
    """Get current timezone."""
    return get_i18n_service().get_current_timezone()


def format_duration(seconds: int, language: Optional[str] = None) -> str:
    """Format duration according to language settings.

    Args:
        seconds: Duration in seconds
        language: Language code (uses current if not specified)

    Returns:
        Formatted duration string
    """
    i18n = get_i18n_service()
    target_language = language or i18n.get_current_language()

    if seconds < 60:
        unit_name = i18n.translate("units.seconds", language=target_language)
        return f"{seconds} {unit_name}"
    elif seconds < 3600:
        minutes = seconds // 60
        unit_name = i18n.translate("units.minutes", language=target_language)
        return f"{minutes} {unit_name}"
    elif seconds < 86400:
        hours = seconds // 3600
        unit_name = i18n.translate("units.hours", language=target_language)
        return f"{hours} {unit_name}"
    else:
        days = seconds // 86400
        unit_name = i18n.translate("units.days", language=target_language)
        return f"{days} {unit_name}"


def pluralize(
    count: int,
    singular: str,
    plural: Optional[str] = None,
    language: Optional[str] = None,
) -> str:
    """Pluralize a word based on count and language rules.

    Args:
        count: Number to determine plural form
        singular: Singular form of the word
        plural: Plural form (auto-generated if not provided)
        language: Language code (uses current if not specified)

    Returns:
        Appropriate word form
    """
    target_language = language or get_i18n_service().get_current_language()

    # Chinese languages don't have plural forms
    if target_language.startswith("zh"):
        return singular

    # English pluralization rules
    if count == 1:
        return singular

    if plural:
        return plural

    # Simple English pluralization
    if singular.endswith(("s", "sh", "ch", "x", "z")):
        return f"{singular}es"
    elif singular.endswith("y") and singular[-2] not in "aeiou":
        return f"{singular[:-1]}ies"
    elif singular.endswith("f"):
        return f"{singular[:-1]}ves"
    elif singular.endswith("fe"):
        return f"{singular[:-2]}ves"
    else:
        return f"{singular}s"


def get_language_direction(language: str) -> str:
    """Get text direction for a language.

    Args:
        language: Language code

    Returns:
        'ltr' for left-to-right, 'rtl' for right-to-left
    """
    # All currently supported languages are LTR
    return "ltr"


def extract_translation_keys(text: str) -> List[str]:
    """Extract translation keys from text using t() function calls.

    Args:
        text: Text to extract keys from

    Returns:
        List of translation keys found
    """
    # Pattern to match t('key') or t("key") calls
    pattern = r't\([\'"]([^\'"]+)[\'"]\)'
    matches = re.findall(pattern, text)
    return list(set(matches))  # Remove duplicates


def validate_translation_file(file_path: Path) -> Dict[str, Any]:
    """Validate a translation JSON file.

    Args:
        file_path: Path to translation file

    Returns:
        Validation result with status and errors
    """
    result = {"valid": True, "errors": [], "warnings": [], "key_count": 0}

    try:
        import json

        if not file_path.exists():
            result["valid"] = False
            result["errors"].append("File does not exist")
            return result

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Count keys recursively
        def count_keys(obj):
            count = 0
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, dict):
                        count += count_keys(value)
                    else:
                        count += 1
            return count

        result["key_count"] = count_keys(data)

        # Check for empty values
        def check_empty_values(obj, prefix=""):
            for key, value in obj.items():
                current_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    check_empty_values(value, current_key)
                elif not value or (isinstance(value, str) and not value.strip()):
                    result["warnings"].append(f"Empty value for key: {current_key}")

        check_empty_values(data)

    except json.JSONDecodeError as e:
        result["valid"] = False
        result["errors"].append(f"Invalid JSON: {str(e)}")
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"Error reading file: {str(e)}")

    return result


def get_missing_translations(base_language: str = "en-US") -> Dict[str, List[str]]:
    """Find missing translations compared to base language.

    Args:
        base_language: Base language to compare against

    Returns:
        Dictionary with missing keys for each language
    """
    i18n = get_i18n_service()
    base_keys = set(i18n.get_translation_keys(base_language))
    missing = {}

    for lang_code, _ in SUPPORTED_LANGUAGES:
        if lang_code == base_language:
            continue

        lang_keys = set(i18n.get_translation_keys(lang_code))
        missing_keys = base_keys - lang_keys

        if missing_keys:
            missing[lang_code] = sorted(list(missing_keys))

    return missing


def create_translation_template(keys: List[str]) -> Dict[str, Any]:
    """Create a translation template with given keys.

    Args:
        keys: List of translation keys

    Returns:
        Nested dictionary template
    """
    template = {}

    for key in keys:
        parts = key.split(".")
        current = template

        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # Last part, set empty string
                current[part] = ""
            else:
                # Create nested dict if doesn't exist
                if part not in current:
                    current[part] = {}
                current = current[part]

    return template


# Decorator for translatable strings
def translatable(key: str, **kwargs):
    """Decorator to mark functions as translatable.

    Args:
        key: Translation key
        **kwargs: Additional translation parameters
    """

    def decorator(func):
        func._translation_key = key
        func._translation_params = kwargs
        return func

    return decorator
