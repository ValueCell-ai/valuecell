"""ValueCell - A community-driven, multi-agent platform for financial applications."""

__version__ = "0.1.0"
__author__ = "ValueCell Team"
__description__ = "A community-driven, multi-agent platform for financial applications"

__all__ = [
    "__version__",
    "__author__",
    "__description__",
]

# Load environment variables as early as possible
import os
from pathlib import Path


def load_env_file_early() -> None:
    """Load environment variables from .env file at package import time.

    Uses python-dotenv for reliable parsing and respects existing environment variables.
    Looks for .env file in project root (two levels up from this file).

    Note:
        - Existing environment variables take precedence (override=False)
        - Debug logging can be enabled via VALUECELL_DEBUG=true
        - Falls back to manual parsing if python-dotenv is unavailable
    """
    try:
        from dotenv import load_dotenv

        # Look for .env file in project root (up 2 levels from this file)
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        env_file = project_root / ".env"

        if env_file.exists():
            # Load with override=False to respect existing environment variables
            load_dotenv(env_file, override=False)

            # Optional: Log successful loading if DEBUG is enabled
            if os.getenv("VALUECELL_DEBUG", "false").lower() == "true":
                print(f"✓ Environment variables loaded from {env_file}")
                print(f"  LANG: {os.environ.get('LANG', 'not set')}")
                print(f"  TIMEZONE: {os.environ.get('TIMEZONE', 'not set')}")
        else:
            # Only log if debug mode is enabled
            if os.getenv("VALUECELL_DEBUG", "false").lower() == "true":
                print(f"ℹ️  No .env file found at {env_file}")

    except ImportError:
        # Fallback to manual parsing if python-dotenv is not available
        # This ensures backward compatibility
        _load_env_file_manual()
    except Exception as e:
        # Only log errors if debug mode is enabled
        if os.getenv("VALUECELL_DEBUG", "false").lower() == "true":
            print(f"⚠️  Error loading .env file: {e}")


def _load_env_file_manual() -> None:
    """Fallback manual .env file parsing.

    This function provides a simple .env parser when python-dotenv is not available.
    It respects existing environment variables and handles basic quote removal.

    Note:
        - Lines starting with # are treated as comments
        - Only KEY=VALUE format is supported
        - Existing environment variables are not overwritten
    """
    try:
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        env_file = project_root / ".env"

        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or (
                            value.startswith("'") and value.endswith("'")
                        ):
                            value = value[1:-1]
                        # Only set if not already set (respect existing env vars)
                        if key not in os.environ:
                            os.environ[key] = value
    except Exception:
        # Fail silently to avoid breaking imports
        pass


# Load environment variables immediately when package is imported
load_env_file_early()
