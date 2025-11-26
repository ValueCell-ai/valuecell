import os
import shutil
from pathlib import Path

from .env import get_system_env_dir
from .path import get_repo_root_path


def _strip_sqlite_prefix(url_or_path: str) -> str:
    """Normalize a potential SQLite DSN to a filesystem path.

    - If `url_or_path` starts with `sqlite:///`, return the stripped path portion.
    - Otherwise, return it unchanged.
    """
    if url_or_path.startswith("sqlite:///"):
        return url_or_path.replace("sqlite:///", "", 1)
    return url_or_path


def resolve_db_path() -> str:
    """Resolve the SQLite database file path used by conversation stores.

    Resolution order:
    1) `DATABASE_URL` env var (if starts with `sqlite:///`, strip to path; otherwise ignore)
    2) Default to system application directory (e.g., `~/Library/Application Support/ValueCell/valuecell.db` on macOS)

    Note: This function returns a filesystem path, not a SQLAlchemy DSN.
    """
    # Prefer generic VALUECELL_DATABASE_URL if it points to SQLite
    db_url = os.environ.get("VALUECELL_DATABASE_URL")
    if db_url and db_url.startswith("sqlite:///"):
        return _strip_sqlite_prefix(db_url)

    # Default: store under system application directory alongside `.env`
    return os.path.join(get_system_env_dir(), "valuecell.db")


def resolve_lancedb_uri() -> str:
    """Resolve LanceDB directory path.

    Resolution order:
    1) Default to system application directory: `<system_env_dir>/lancedb`

    Additionally, if an old repo-root `lancedb` directory exists and the new
    system directory does not, migrate the contents once for continuity.
    """
    # Default: system directory
    system_dir = get_system_env_dir()
    new_path = Path(system_dir) / "lancedb"
    new_path.mkdir(parents=True, exist_ok=True)

    # Migrate from old repo-root location if needed
    old_path = Path(get_repo_root_path()) / "lancedb"
    try:
        if old_path.exists() and not any(new_path.iterdir()):
            # Copy contents only if destination is empty
            for item in old_path.iterdir():
                src = item
                dst = new_path / item.name
                if item.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
    except Exception:
        # Non-fatal: if migration fails, just proceed with new_path
        pass

    return str(new_path)
