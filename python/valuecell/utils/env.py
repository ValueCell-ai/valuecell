"""Utilities for resolving system-level .env paths consistently across OSes.

Provides helpers to locate the OS user configuration directory for ValueCell
and to construct the system `.env` file path. This centralizes path logic so
other modules can mirror or write environment variables consistently.
"""

import os
from pathlib import Path


def get_system_env_dir() -> Path:
    """Return the OS user configuration directory for ValueCell.

    - macOS: ~/Library/Application Support/ValueCell
    - Linux: ~/.config/valuecell
    - Windows: %APPDATA%\\ValueCell
    """
    home = Path.home()
    # Windows
    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        base = Path(appdata) if appdata else (home / "AppData" / "Roaming")
        return base / "ValueCell"
    # macOS (posix with darwin kernel)
    if sys_platform_is_darwin():
        # Correct macOS Application Support directory path
        return home / "Library" / "Application Support" / "ValueCell"
    # Linux and other Unix-like
    return home / ".config" / "valuecell"


def get_system_env_path() -> Path:
    """Return the full path to the system `.env` file."""
    return get_system_env_dir() / ".env"


def ensure_system_env_dir() -> Path:
    """Ensure the system config directory exists and return it."""
    d = get_system_env_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def sys_platform_is_darwin() -> bool:
    """Detect macOS platform without importing `platform` globally."""
    try:
        import sys

        return sys.platform == "darwin"
    except Exception:
        return False


def agent_debug_mode_enabled() -> bool:
    """Return whether agent debug mode is enabled via environment.

    Checks `AGENT_DEBUG_MODE`.
    """
    flag = os.getenv("AGENT_DEBUG_MODE", "false")
    return str(flag).lower() == "true"


# Port file management for dynamic port allocation
PORT_FILE_NAME = "backend.port"


def get_port_file_path() -> Path:
    """Return the full path to the backend port file.

    The port file is stored alongside the .env file in the system config directory.
    """
    return get_system_env_dir() / PORT_FILE_NAME


def write_port_file(port: int) -> Path:
    """Write the backend port to a file for the client to read.

    Args:
        port: The port number the backend is listening on.

    Returns:
        Path to the port file.
    """
    ensure_system_env_dir()
    port_file = get_port_file_path()
    port_file.write_text(str(port), encoding="utf-8")
    return port_file


def read_port_file() -> int | None:
    """Read the backend port from the port file.

    Returns:
        The port number if the file exists and is valid, None otherwise.
    """
    port_file = get_port_file_path()
    if not port_file.exists():
        return None
    try:
        content = port_file.read_text(encoding="utf-8").strip()
        return int(content)
    except (ValueError, OSError):
        return None


def remove_port_file() -> None:
    """Remove the port file if it exists."""
    port_file = get_port_file_path()
    if port_file.exists():
        try:
            port_file.unlink()
        except OSError:
            pass


def auto_port_enabled() -> bool:
    """Return whether auto port allocation is enabled.

    When API_PORT is set to "0" or "auto", the server will automatically
    find an available port.
    """
    port_env = os.getenv("API_PORT", "8000")
    return port_env == "0" or port_env.lower() == "auto"
