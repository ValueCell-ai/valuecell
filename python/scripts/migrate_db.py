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


def index_exists(engine, table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    inspector = inspect(engine)
    indexes = [idx["name"] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def create_index_if_not_exists(engine, table_name: str, column_name: str, index_name: str = None):
    """Create an index on a column if it doesn't exist."""
    if index_name is None:
        index_name = f"ix_{table_name}_{column_name}"
    
    if index_exists(engine, table_name, index_name):
        logger.info(f"Index {index_name} already exists, skipping")
        return True

    try:
        with engine.connect() as conn:
            conn.execute(
                text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})")
            )
            conn.commit()
        logger.info(f"Created index {index_name} on {table_name}.{column_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to create index {index_name}: {e}")
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


def migrate_strategy_details():
    """Migrate strategy_details table to add missing columns."""
    db_manager = get_database_manager()
    engine = db_manager.get_engine()

    # Check if table exists
    inspector = inspect(engine)
    if "strategy_details" not in inspector.get_table_names():
        logger.warning("Table strategy_details does not exist, skipping migration")
        return True

    logger.info("Migrating strategy_details table...")

    # Columns to add with their types and whether they need an index
    # (name, type, nullable, needs_index)
    columns_to_add = [
        ("compose_id", "VARCHAR(200)", True, True),
        ("instruction_id", "VARCHAR(200)", True, True),
        ("avg_exec_price", "NUMERIC(20, 8)", True, False),
        ("realized_pnl", "NUMERIC(20, 8)", True, False),
        ("realized_pnl_pct", "NUMERIC(10, 6)", True, False),
        ("notional_entry", "NUMERIC(20, 8)", True, False),
        ("notional_exit", "NUMERIC(20, 8)", True, False),
        ("fee_cost", "NUMERIC(20, 8)", True, False),
        ("entry_time", "TIMESTAMP", True, False),
        ("exit_time", "TIMESTAMP", True, False),
    ]

    success = True
    for column_name, column_type, nullable, needs_index in columns_to_add:
        # Add column if it doesn't exist
        if not add_column_if_not_exists(engine, "strategy_details", column_name, column_type, nullable):
            success = False

        # Create index if column exists and needs index
        if column_exists(engine, "strategy_details", column_name) and needs_index:
            index_name = f"ix_strategy_details_{column_name}"
            if not create_index_if_not_exists(engine, "strategy_details", column_name, index_name):
                logger.warning(f"Failed to create index on {column_name}, but column exists")

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

        # Migrate strategy_details
        if not migrate_strategy_details():
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

