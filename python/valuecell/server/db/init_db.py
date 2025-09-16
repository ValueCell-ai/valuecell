"""Database initialization script for ValueCell Server."""

import logging
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

from .connection import get_database_manager, DatabaseManager
from .models.base import Base
from ..config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Database initialization manager."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize database initializer."""
        self.db_manager = db_manager or get_database_manager()
        self.settings = get_settings()
        self.engine = self.db_manager.get_engine()

    def check_database_exists(self) -> bool:
        """Check if database file exists (for SQLite)."""
        database_url = self.settings.DATABASE_URL

        if database_url.startswith("sqlite:///"):
            # Extract file path from SQLite URL
            db_path = database_url.replace("sqlite:///", "")
            if db_path.startswith("./"):
                # Relative path
                db_path = Path.cwd() / db_path[2:]
            else:
                db_path = Path(db_path)

            return db_path.exists()

        # For other databases, try to connect
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False

    def check_tables_exist(self) -> bool:
        """Check if tables exist in database."""
        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()

            # Get all table names from metadata
            expected_tables = list(Base.metadata.tables.keys())

            if not expected_tables:
                logger.info("No tables defined in models")
                return True

            # Check if all expected tables exist
            missing_tables = set(expected_tables) - set(existing_tables)
            if missing_tables:
                logger.info(f"Missing tables: {missing_tables}")
                return False

            logger.info(f"All tables exist: {existing_tables}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Error checking tables: {e}")
            return False

    def create_database_file(self) -> bool:
        """Create database file (for SQLite)."""
        database_url = self.settings.DATABASE_URL

        if database_url.startswith("sqlite:///"):
            # Extract file path from SQLite URL
            db_path = database_url.replace("sqlite:///", "")
            if db_path.startswith("./"):
                # Relative path
                db_path = Path.cwd() / db_path[2:]
            else:
                db_path = Path(db_path)

            try:
                # Create parent directories if they don't exist
                db_path.parent.mkdir(parents=True, exist_ok=True)

                # Create empty database file
                db_path.touch()
                logger.info(f"Created database file: {db_path}")
                return True

            except Exception as e:
                logger.error(f"Error creating database file: {e}")
                return False

        logger.info("Database file creation not needed for non-SQLite databases")
        return True

    def create_tables(self) -> bool:
        """Create all tables."""
        try:
            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Error creating tables: {e}")
            return False

    def initialize_basic_data(self) -> bool:
        """Initialize agent data from configuration files."""
        try:
            logger.info("Initializing agent data...")

            # Get a database session
            session = self.db_manager.get_session()

            try:
                # Import models here to avoid circular imports
                from .models.agent import Agent
                import json
                import os
                from pathlib import Path

                # Get the project root directory
                project_root = Path(__file__).parent.parent.parent.parent
                agent_configs_dir = project_root / "configs" / "agent_cards"

                if not agent_configs_dir.exists():
                    logger.warning(
                        f"Agent configs directory not found: {agent_configs_dir}"
                    )
                    return True

                # Load agent configurations from JSON files
                for config_file in agent_configs_dir.glob("*.json"):
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            config_data = json.load(f)

                        agent_name = config_data.get("name")
                        if not agent_name:
                            logger.warning(
                                f"Agent config missing 'name' field: {config_file}"
                            )
                            continue

                        # Check if agent already exists
                        existing_agent = (
                            session.query(Agent).filter_by(name=agent_name).first()
                        )
                        if not existing_agent:
                            # Create new agent from config
                            agent = Agent.from_config(config_data)
                            session.add(agent)
                            logger.info(f"Added agent: {agent_name}")
                        else:
                            # Update existing agent with new config data
                            existing_agent.display_name = config_data.get(
                                "display_name", existing_agent.display_name
                            )
                            existing_agent.description = config_data.get(
                                "description", existing_agent.description
                            )
                            existing_agent.url = config_data.get(
                                "url", existing_agent.url
                            )
                            existing_agent.version = config_data.get(
                                "version", existing_agent.version
                            )
                            existing_agent.enabled = config_data.get(
                                "enabled", existing_agent.enabled
                            )
                            existing_agent.capabilities = config_data.get(
                                "capabilities", existing_agent.capabilities
                            )
                            existing_agent.agent_metadata = config_data.get(
                                "metadata", existing_agent.agent_metadata
                            )
                            existing_agent.config = config_data.get(
                                "config", existing_agent.config
                            )
                            logger.info(f"Updated agent: {agent_name}")

                    except Exception as e:
                        logger.error(f"Error loading agent config {config_file}: {e}")
                        continue

                session.commit()
                logger.info("Agent data initialization completed")
                return True

            except Exception as e:
                session.rollback()
                logger.error(f"Error initializing agent data: {e}")
                return False
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error getting database session: {e}")
            return False

    def verify_initialization(self) -> bool:
        """Verify database initialization."""
        try:
            # Test database connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

            # Check if tables exist
            if not self.check_tables_exist():
                logger.error("Table verification failed")
                return False

            logger.info("Database initialization verified successfully")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Database verification failed: {e}")
            return False

    def initialize(self, force: bool = False) -> bool:
        """Initialize database completely."""
        logger.info("Starting database initialization...")

        # Check if database already exists and is properly initialized
        if not force and self.check_database_exists() and self.check_tables_exist():
            logger.info("Database already exists and is properly initialized")
            return True

        # Step 1: Create database file (for SQLite)
        if not self.create_database_file():
            logger.error("Failed to create database file")
            return False

        # Step 2: Create tables
        if not self.create_tables():
            logger.error("Failed to create tables")
            return False

        # Step 3: Initialize basic data
        if not self.initialize_basic_data():
            logger.error("Failed to initialize basic data")
            return False

        # Step 4: Verify initialization
        if not self.verify_initialization():
            logger.error("Database initialization verification failed")
            return False

        logger.info("Database initialization completed successfully")
        return True


def init_database(force: bool = False) -> bool:
    """Initialize database with all tables and basic data."""
    try:
        initializer = DatabaseInitializer()
        return initializer.initialize(force=force)
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def main():
    """Main entry point for database initialization script."""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize ValueCell database")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-initialization even if database exists",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("ValueCell Database Initialization")
    logger.info("=" * 50)

    success = init_database(force=args.force)

    if success:
        logger.info("Database initialization completed successfully!")
        sys.exit(0)
    else:
        logger.error("Database initialization failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
