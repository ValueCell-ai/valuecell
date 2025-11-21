"""
Database migration script to add missing columns to existing tables.

This script handles schema updates for existing databases without losing data.
"""

import logging
import sys
from pathlib import Path

from sqlalchemy import inspect, text

from valuecell.server.config.settings import get_settings
from valuecell.server.db.connection import get_database_manager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def column_exists(engine, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def add_column_if_not_exists(engine, table_name: str, column_name: str, column_type: str, nullable: bool = True):
    """Add a column to a table if it doesn't exist."""
    if column_exists(engine, table_name, column_name):
        logger.info(f"Column {table_name}.{column_name} already exists, skipping")
        return True

    try:
        nullable_clause = "" if nullable else " NOT NULL"
        with engine.connect() as conn:
            conn.execute(
                text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}{nullable_clause}")
            )
            conn.commit()
        logger.info(f"Added column {table_name}.{column_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to add column {table_name}.{column_name}: {e}")
        return False


def migrate_strategy_portfolio_views():
    """Migrate strategy_portfolio_views table to add missing columns."""
    db_manager = get_database_manager()
    engine = db_manager.get_engine()

    # Check if table exists
    inspector = inspect(engine)
    if "strategy_portfolio_views" not in inspector.get_table_names():
        logger.warning("Table strategy_portfolio_views does not exist, skipping migration")
        return True

    logger.info("Migrating strategy_portfolio_views table...")

    # Add missing columns
    migrations = [
        ("total_realized_pnl", "NUMERIC(20, 8)", True),
        ("gross_exposure", "NUMERIC(20, 8)", True),
        ("net_exposure", "NUMERIC(20, 8)", True),
    ]

    success = True
    for column_name, column_type, nullable in migrations:
        if not add_column_if_not_exists(engine, "strategy_portfolio_views", column_name, column_type, nullable):
            success = False

    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration completed with errors")

    return success


def main():
    """Run database migrations."""
    logger.info("Starting database migration...")
    logger.info("=" * 50)

    try:
        # Migrate strategy_portfolio_views
        if not migrate_strategy_portfolio_views():
            logger.error("Migration failed")
            sys.exit(1)

        logger.info("=" * 50)
        logger.info("All migrations completed successfully!")
        sys.exit(0)

    except Exception as e:
        logger.exception(f"Migration failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

