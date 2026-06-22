"""Database package for ValueCell Server."""

from typing import TYPE_CHECKING, Any

from .connection import (
    DatabaseManager,
    get_database_manager,
    get_db,
)
from .models import Agent, Asset, Base

if TYPE_CHECKING:
    from .init_db import DatabaseInitializer

__all__ = [
    # Connection management
    "DatabaseManager",
    "get_database_manager",
    "get_db",
    # Database initialization
    "DatabaseInitializer",
    "init_database",
    # Models
    "Base",
    "Agent",
    "Asset",
]


def __getattr__(name: str) -> Any:
    """Lazily expose database initialization helpers.

    Importing `init_db` from this package initializer makes
    `python -m valuecell.server.db.init_db` warn because the module is loaded
    before runpy executes it as `__main__`.
    """
    if name == "DatabaseInitializer":
        from .init_db import DatabaseInitializer

        return DatabaseInitializer
    if name == "init_database":
        from .init_db import init_database

        return init_database
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
