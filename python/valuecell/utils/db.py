import os

from .path import get_repo_root_path


def resolve_db_path() -> str:
    return os.environ.get("VALUECELL_SQLITE_DB") or os.path.join(
        get_repo_root_path(), "valuecell.db"
    )


def resolve_lancedb_uri() -> str:
    return os.environ.get("VALUECELL_LANCEDB_URI") or os.path.join(
        get_repo_root_path(), "lancedb"
    )
