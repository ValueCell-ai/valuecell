import os
from urllib.parse import urlparse

from .path import get_repo_root_path


def _url_to_path(url: str) -> str:
    """Convert a SQLite SQLAlchemy URL to a filesystem path for aiosqlite.

    This keeps VALUECELL_SQLITE_DB usable as a full SQLAlchemy URL (e.g.
    'sqlite:////app/data/valuecell.db') while allowing conversation stores
    to work with the underlying file path (e.g. '/app/data/valuecell.db').
    """
    if not url.startswith("sqlite://"):
        # Not a SQLite URL, treat as a plain filesystem path
        return url

    parsed = urlparse(url)
    # For URLs like sqlite:////app/data/valuecell.db, parsed.path is
    # '/app/data/valuecell.db', which is exactly what we want.
    return parsed.path or url


def resolve_db_path() -> str:
    env = os.environ.get("VALUECELL_SQLITE_DB")
    if env:
        return _url_to_path(env)

    return os.path.join(get_repo_root_path(), "valuecell.db")


def resolve_lancedb_uri() -> str:
    return os.environ.get("VALUECELL_LANCEDB_URI") or os.path.join(
        get_repo_root_path(), "lancedb"
    )
