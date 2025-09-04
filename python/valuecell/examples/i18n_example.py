"""Example usage of ValueCell i18n system."""

# TODO: This file is a temporary file, it will be removed in the future.
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory to Python path to enable imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# Set environment for example
os.environ["LANG"] = "zh-Hans"
os.environ["TIMEZONE"] = "Asia/Shanghai"

try:
    # Option 1: Import from dedicated i18n module (recommended)
    from valuecell.i18n import (
        get_settings,
        get_i18n_service,
        t,
        detect_browser_language,
        format_file_size,
        format_duration,
        pluralize,
    )

    # Option 2: Import from specific modules (alternative)
    # from valuecell.config.settings import get_settings
    # from valuecell.services.i18n_service import get_i18n_service, t
    # from valuecell.utils.i18n_utils import detect_browser_language, format_file_size, format_duration, pluralize

except ImportError as e:
    print(f"Import error: {e}")
    print("Please make sure you're running this from the correct directory.")
    print(
        "Try: cd /path/to/valuecell/python && python -m valuecell.examples.i18n_example"
    )
    sys.exit(1)


def main():
    """Main example function."""
    print("=== ValueCell i18n System Example ===\n")

    # Initialize services
    settings = get_settings()
    i18n = get_i18n_service()

    print("1. Current Configuration:")
    print(f"   Language: {i18n.get_current_language()}")
    print(f"   Timezone: {i18n.get_current_timezone()}")
    print(f"   Settings: {settings.to_dict()['i18n']}")
    print()

    # Translation examples
    print("2. Translation Examples:")
    print(f"   Welcome (current): {t('messages.welcome')}")
    print(f"   Welcome (en-US): {i18n.translate('messages.welcome', 'en-US')}")
    print(f"   Welcome (zh-Hant): {i18n.translate('messages.welcome', 'zh-Hant')}")
    print()

    # Translation with variables
    print("3. Translation with Variables:")
    app_version = settings.APP_VERSION
    copyright_year = datetime.now().year
    print(f"   Version: {t('app.version', version=app_version)}")
    print(f"   Copyright: {t('app.copyright', year=copyright_year)}")
    print()

    # Date and time formatting
    print("4. Date and Time Formatting:")
    now = datetime.now()
    print(f"   Current time: {now}")
    print(f"   Formatted date: {i18n.format_datetime(now, 'date')}")
    print(f"   Formatted time: {i18n.format_datetime(now, 'time')}")
    print(f"   Formatted datetime: {i18n.format_datetime(now, 'datetime')}")
    print()

    # Number and currency formatting
    print("5. Number and Currency Formatting:")
    number = 1234567.89
    currency = 9876.54
    print(f"   Original number: {number}")
    print(f"   Formatted number: {i18n.format_number(number)}")
    print(f"   Formatted currency: {i18n.format_currency(currency)}")
    print()

    # Language detection
    print("6. Language Detection:")
    test_headers = [
        "en-US,en;q=0.9,zh;q=0.8",
        "zh-CN,zh;q=0.9,en;q=0.8",
        "zh-TW,zh;q=0.9,en;q=0.8",
        "en-GB,en;q=0.9",
    ]
    for header in test_headers:
        detected = detect_browser_language(header)
        print(f"   '{header}' -> {detected}")
    print()

    # File size and duration formatting
    print("7. Utility Formatting:")
    file_sizes = [512, 1024, 1048576, 1073741824]
    for size in file_sizes:
        formatted = format_file_size(size)
        print(f"   {size} bytes -> {formatted}")

    durations = [30, 120, 3600, 86400]
    for duration in durations:
        formatted = format_duration(duration)
        print(f"   {duration} seconds -> {formatted}")
    print()

    # Pluralization examples
    print("8. Pluralization Examples:")
    words = [("file", None), ("item", None), ("category", "categories")]
    counts = [0, 1, 2, 5]
    for singular, plural in words:
        for count in counts:
            result = pluralize(count, singular, plural)
            print(f"   {count} {result}")
    print()

    # Switch languages and show differences
    print("9. Language Switching:")
    languages = ["en-US", "en-GB", "zh-Hans", "zh-Hant"]

    for lang in languages:
        i18n.set_language(lang)
        welcome = t("messages.welcome")
        success = t("messages.data_saved")
        print(f"   {lang}: {welcome} | {success}")
    print()

    # Show timezone differences
    print("10. Timezone Formatting:")
    test_dt = datetime(2024, 1, 15, 14, 30, 0)
    timezones = [
        "UTC",
        "America/New_York",
        "Europe/London",
        "Asia/Shanghai",
        "Asia/Hong_Kong",
    ]

    for tz in timezones:
        i18n.set_timezone(tz)
        formatted = i18n.format_datetime(test_dt)
        print(f"    {tz}: {formatted}")
    print()

    # Show supported languages
    print("11. Supported Languages:")
    for code, name in i18n.get_supported_languages():
        print(f"    {code}: {name}")
    print()

    print("=== Example Complete ===")


if __name__ == "__main__":
    main()
