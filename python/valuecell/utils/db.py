import os


def _repo_root() -> str:
    """Resolve repository root and return default DB path valuecell.db.

    Layout assumption: this file is at repo_root/python/valuecell/utils/db.py
    We walk up 3 levels to reach repo_root.
    """
    here = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    return repo_root


def resolve_db_path() -> str:
    return os.environ.get("VALUECELL_SQLITE_DB") or os.path.join(
        _repo_root(), "valuecell.db"
    )


def resolve_lancedb_uri() -> str:
    return os.environ.get("VALUECELL_LANCEDB_URI") or os.path.join(
        _repo_root(), "lancedb"
    )
