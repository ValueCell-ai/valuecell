"""Database initialization script for ValueCell Server."""

import json
import shutil
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

# Smart path handling: try import first, add path only if needed
# This allows running the script directly: uv run valuecell/server/db/init_db.py
try:
    import valuecell  # noqa: F401
except ImportError:
    # If import fails, add the Python package root to sys.path
    # Calculate path: init_db.py -> db -> server -> valuecell -> python (root)
    _current_file = Path(__file__).resolve()
    _python_root = _current_file.parent.parent.parent.parent
    if str(_python_root) not in sys.path:
        sys.path.insert(0, str(_python_root))

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from valuecell.server.config.settings import get_settings
from valuecell.server.db.connection import DatabaseManager, get_database_manager
from valuecell.server.db.models.agent import Agent
from valuecell.server.db.models.base import Base
from valuecell.server.db.models.strategy_prompt import StrategyPrompt
from valuecell.server.db.repositories.asset_repository import get_asset_repository
from valuecell.server.services.assets import get_asset_service
from valuecell.utils.path import get_agent_card_path


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
            # Extract file path from SQLite URLß
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

                # If old repo-root DB exists and new system-path DB is missing, migrate it
                try:
                    repo_root = (
                        Path(__file__).resolve().parent.parent.parent.parent.parent
                    )
                    old_repo_db = repo_root / "valuecell.db"
                except Exception:
                    old_repo_db = None

                if old_repo_db and old_repo_db.exists() and not db_path.exists():
                    shutil.copy2(old_repo_db, db_path)
                    logger.info(
                        f"Migrated existing database file from repo root to system directory: {db_path}"
                    )

                # Ensure database file exists
                if not db_path.exists():
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

            # Create conversation-related tables that are not in SQLAlchemy models
            logger.info("Creating conversation-related tables...")
            with self.engine.connect() as conn:
                # Create conversations table
                conn.execute(
                    text("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        conversation_id TEXT PRIMARY KEY,
                        user_id TEXT,
                        title TEXT,
                        agent_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'active'
                    )
                """)
                )

                # Create conversation_items table
                conn.execute(
                    text("""
                    CREATE TABLE IF NOT EXISTS conversation_items (
                        item_id TEXT PRIMARY KEY,
                        role TEXT NOT NULL,
                        event TEXT NOT NULL,
                        conversation_id TEXT NOT NULL,
                        thread_id TEXT,
                        task_id TEXT,
                        payload TEXT,
                        agent_name TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                )

                # Create index for conversation_items
                conn.execute(
                    text("""
                    CREATE INDEX IF NOT EXISTS idx_item_conv_time 
                    ON conversation_items(conversation_id, created_at)
                """)
                )

                # Create tasks table for task management
                conn.execute(
                    text("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        title TEXT,
                        query TEXT NOT NULL,
                        conversation_id TEXT NOT NULL,
                        thread_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        agent_name TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        pattern TEXT NOT NULL DEFAULT 'once',
                        schedule_config TEXT,
                        handoff_from_super_agent INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        error_message TEXT
                    )
                    """)
                )

                # Indexes for common task queries
                conn.execute(
                    text("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_conversation 
                    ON tasks(conversation_id)
                    """)
                )
                conn.execute(
                    text("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_user 
                    ON tasks(user_id)
                    """)
                )
                conn.execute(
                    text("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_status 
                    ON tasks(status)
                    """)
                )

                conn.commit()

            logger.info("Database tables created successfully")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Error creating tables: {e}")
            return False

    def initialize_assets_with_service(self) -> bool:
        """Initialize default assets using AssetService pattern."""
        try:
            logger.info("Initializing assets using AssetService...")

            # Get asset service and repository instances
            asset_service = get_asset_service()
            session = self.db_manager.get_session()
            asset_repo = get_asset_repository(db_session=session)

            # Define default tickers to search and initialize
            # Using proper EXCHANGE:SYMBOL format for better adapter matching
            default_tickers = [
                # Major indices
                "NASDAQ:IXIC",  # NASDAQ Composite Index
                "HKEX:HSI",  # Hang Seng Index
                "SSE:000001",  # Shanghai Composite Index
            ]

            try:
                initialized_count = 0

                for ticker in default_tickers:
                    try:
                        logger.info(f"Initializing asset: {ticker}")

                        # Extract symbol for search - try both full ticker and symbol only
                        symbol_only = ticker.split(":")[-1] if ":" in ticker else ticker

                        # Try searching with both formats to maximize chances of finding the asset
                        search_queries = [ticker, symbol_only]
                        search_result = None

                        for query in search_queries:
                            search_result = asset_service.search_assets(
                                query=query, limit=1, language="en-US"
                            )
                            if search_result["success"] and search_result["results"]:
                                logger.info(
                                    f"Found asset data for {ticker} using query '{query}'"
                                )
                                break

                        if not search_result:
                            search_result = {"success": False, "results": []}

                        if search_result["success"] and search_result["results"]:
                            # Asset found via adapter, create or update database record
                            asset_data = search_result["results"][0]

                            # Use the standardized ticker format (ensure EXCHANGE:SYMBOL format)
                            asset_ticker = asset_data.get("ticker", ticker)
                            if ":" not in asset_ticker:
                                # If adapter doesn't return proper format, use our expected format
                                asset_ticker = ticker

                            # Check if asset already exists in database
                            if asset_repo.asset_exists(asset_ticker):
                                # Update existing asset with adapter data
                                metadata_updates = {
                                    "exchange": asset_data.get("exchange")
                                    or ticker.split(":")[0],
                                    "country": asset_data.get("country"),
                                    "currency": asset_data.get("currency"),
                                    "market_status": asset_data.get("market_status"),
                                    "last_updated_from_adapter": True,
                                    "last_search_query": query,
                                }

                                asset_repo.update_asset(
                                    symbol=asset_ticker,
                                    name=asset_data["display_name"],
                                    asset_type=asset_data["asset_type"],
                                )
                                asset_repo.update_asset_metadata(
                                    symbol=asset_ticker,
                                    metadata_updates=metadata_updates,
                                )
                                logger.info(
                                    f"Updated asset from adapter: {asset_ticker} (searched as '{query}')"
                                )
                            else:
                                # Create new asset from adapter data
                                asset_repo.create_asset(
                                    symbol=asset_ticker,
                                    name=asset_data["display_name"],
                                    asset_type=asset_data["asset_type"],
                                    asset_metadata={
                                        "exchange": asset_data.get("exchange")
                                        or ticker.split(":")[0],
                                        "country": asset_data.get("country"),
                                        "currency": asset_data.get("currency"),
                                        "market_status": asset_data.get(
                                            "market_status"
                                        ),
                                        "source": "adapter_search",
                                        "original_search_query": query,
                                        "standardized_ticker": asset_ticker,
                                    },
                                )
                                logger.info(
                                    f"Added asset from adapter: {asset_ticker} (searched as '{query}')"
                                )
                                initialized_count += 1

                        else:
                            # Fallback: create basic asset record for common tickers
                            logger.warning(
                                f"Could not find {ticker} via adapters, creating basic record"
                            )

                            if not asset_repo.asset_exists(ticker):
                                fallback_data = self._get_fallback_asset_data(ticker)
                                if fallback_data:
                                    asset_repo.create_asset(**fallback_data)
                                    logger.info(f"Added fallback asset: {ticker}")
                                    initialized_count += 1

                    except Exception as e:
                        logger.error(f"Error initializing asset {ticker}: {e}")
                        continue

                session.commit()
                logger.info(
                    f"Asset initialization completed successfully. "
                    f"Initialized/updated {initialized_count} out of {len(default_tickers)} assets."
                )

                # Log summary of initialized assets
                if initialized_count > 0:
                    logger.info("Initialized assets summary:")
                    for ticker in default_tickers[:initialized_count]:
                        logger.info(f"  - {ticker}")

                return True

            except Exception as e:
                session.rollback()
                logger.error(f"Error during asset initialization: {e}")
                return False
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error getting asset service or database session: {e}")
            return False

    def _get_fallback_asset_data(self, ticker: str) -> Optional[dict]:
        """Get fallback asset data when adapter search fails.

        Returns:
            Dictionary with asset data suitable for create_asset() method
        """
        # Basic fallback data for common tickers (using proper EXCHANGE:SYMBOL format)
        fallback_configs = {
            "SSE:000001": {
                "name": "Shanghai Composite Index",
                "asset_type": "index",
                "exchange": "SSE",
            },
            "HKEX:HSI": {
                "name": "Hang Seng Index",
                "asset_type": "index",
                "exchange": "HKEX",
            },
            "NASDAQ:IXIC": {
                "name": "NASDAQ Composite Index",
                "asset_type": "index",
                "exchange": "NASDAQ",
            },
        }

        if ticker in fallback_configs:
            config = fallback_configs[ticker]
            return {
                "symbol": ticker,
                "name": config["name"],
                "asset_type": config["asset_type"],
                "sector": config.get("sector"),
                "is_active": True,
                "asset_metadata": {
                    **config.get("metadata", {}),
                    "exchange": config.get("exchange"),
                    "source": "fallback_data",
                    "initialized_at": "database_init",
                },
            }
        return None

    def initialize_basic_data(self) -> bool:
        """Initialize default agent data."""
        try:
            logger.info("Initializing default agent data...")

            # Get a database session
            session = self.db_manager.get_session()

            try:
                # Define default agents
                default_agents = get_local_agent_cards()

                # Insert default agents
                for agent_data in default_agents:
                    agent_name = agent_data["name"]

                    # Check if agent already exists
                    existing_agent = (
                        session.query(Agent).filter_by(name=agent_name).first()
                    )

                    if not existing_agent:
                        # Create new agent
                        agent = Agent.from_config(agent_data)
                        session.add(agent)
                        logger.info(f"Added default agent: {agent_name}")
                    else:
                        # Update existing agent with default data
                        existing_agent.display_name = agent_data.get(
                            "display_name", existing_agent.display_name
                        )
                        existing_agent.description = agent_data.get(
                            "description", existing_agent.description
                        )
                        existing_agent.icon_url = agent_data.get(
                            "icon_url", existing_agent.icon_url
                        )
                        existing_agent.version = agent_data.get(
                            "version", existing_agent.version
                        )
                        existing_agent.enabled = agent_data.get(
                            "enabled", existing_agent.enabled
                        )
                        existing_agent.capabilities = agent_data.get(
                            "capabilities", existing_agent.capabilities
                        )
                        existing_agent.agent_metadata = agent_data.get(
                            "metadata", existing_agent.agent_metadata
                        )
                        existing_agent.config = agent_data.get(
                            "config", existing_agent.config
                        )
                        logger.info(f"Updated default agent: {agent_name}")

                session.commit()
                # Insert default strategy prompt from template if not present
                try:
                    template_path = (
                        Path(__file__).resolve().parents[2]
                        / "agents"
                        / "prompt_strategy_agent"
                        / "templates"
                        / "default.txt"
                    )
                    prompt_id = "prompt-system-default"
                    existing_prompt = (
                        session.query(StrategyPrompt)
                        .filter(StrategyPrompt.id == prompt_id)
                        .first()
                    )
                    if not existing_prompt:
                        if template_path.exists():
                            content = template_path.read_text(encoding="utf-8")
                            prompt = StrategyPrompt(
                                id=prompt_id, name="System Default", content=content
                            )
                            session.add(prompt)
                            session.commit()
                            logger.info(
                                "Inserted default strategy prompt: %s", prompt_id
                            )
                        else:
                            logger.warning(
                                "Default strategy prompt template not found: %s",
                                template_path,
                            )
                except Exception as e:
                    # Do not fail the whole DB init for prompt insertion; log and continue
                    try:
                        session.rollback()
                    except Exception:
                        pass
                    logger.error("Failed to insert default strategy prompt: %s", e)

                # Insert aggressive strategy prompt from template if not present
                try:
                    aggressive_path = (
                        Path(__file__).resolve().parents[2]
                        / "agents"
                        / "prompt_strategy_agent"
                        / "templates"
                        / "aggressive.txt"
                    )
                    aggressive_id = "prompt-system-aggressive"
                    aggressive_existing = (
                        session.query(StrategyPrompt)
                        .filter(StrategyPrompt.id == aggressive_id)
                        .first()
                    )
                    if not aggressive_existing:
                        if aggressive_path.exists():
                            aggressive_content = aggressive_path.read_text(
                                encoding="utf-8"
                            )
                            aggressive_prompt = StrategyPrompt(
                                id=aggressive_id,
                                name="System Aggressive",
                                content=aggressive_content,
                            )
                            session.add(aggressive_prompt)
                            session.commit()
                            logger.info(
                                "Inserted aggressive strategy prompt: %s",
                                aggressive_id,
                            )
                        else:
                            logger.warning(
                                "Aggressive strategy prompt template not found: %s",
                                aggressive_path,
                            )
                except Exception as e:
                    # Do not fail the whole DB init for prompt insertion; log and continue
                    try:
                        session.rollback()
                    except Exception:
                        pass
                    logger.error("Failed to insert aggressive strategy prompt: %s", e)

                logger.info("Default agent data initialization completed")
                return True

            except Exception as e:
                session.rollback()
                logger.error(f"Error initializing default agent data: {e}")
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

        # Step 3: Initialize basic data (agents)
        if not self.initialize_basic_data():
            logger.error("Failed to initialize basic data")
            return False

        # Step 4: Initialize assets with service
        if not self.initialize_assets_with_service():
            logger.error("Failed to initialize assets")
            return False

        # Step 5: Verify initialization
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


def get_local_agent_cards() -> list[dict]:
    """Get list of local agent card configurations."""
    agent_cards_dir = Path(get_agent_card_path())
    agent_cards = []

    if not agent_cards_dir.exists() or not agent_cards_dir.is_dir():
        logger.warning(f"Agent cards directory does not exist: {agent_cards_dir}")
        return agent_cards

    for file_path in agent_cards_dir.glob("*.json"):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                card_config = json.load(f)
                agent_cards.append(card_config)
                logger.info(f"Loaded agent card config: {file_path.name}")
        except Exception as e:
            logger.error(f"Error loading agent card config {file_path.name}: {e}")
            continue

    return agent_cards


def main():
    """Main entry point for database initialization script."""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize ValueCell database")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-initialization even if database exists",
    )

    args = parser.parse_args()

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
