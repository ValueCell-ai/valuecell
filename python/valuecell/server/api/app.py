"""FastAPI application factory for ValueCell Server."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from ...adapters.assets import get_adapter_manager
from ...utils.env import ensure_system_env_dir, get_system_env_path
from ..config.settings import get_settings
from ..db import init_database
from .exceptions import (
    APIException,
    api_exception_handler,
    general_exception_handler,
    validation_exception_handler,
)
from .routers.agent import create_agent_router
from .routers.agent_stream import create_agent_stream_router
from .routers.conversation import create_conversation_router
from .routers.i18n import create_i18n_router
from .routers.models import create_models_router

# from .routers.strategy_alias import create_strategy_alias_router
from .routers.strategy_api import create_strategy_api_router

# from .routers.strategy_agent import create_strategy_agent_router
from .routers.system import create_system_router
from .routers.task import create_task_router
from .routers.user_profile import create_user_profile_router
from .routers.watchlist import create_watchlist_router

# from .routers.strategy import create_strategy_router
from .schemas import AppInfoData, SuccessResponse


def _ensure_system_env_and_load() -> None:
    """Ensure the system `.env` exists and is loaded; use only the system path.

    Behavior:
    - If the system `.env` exists, load it with `override=True`.
    - If not, and the repository has `.env.example`, copy it to the system path and then load.
    - Do not create or load the repository root `.env`.
    """
    try:
        repo_root = Path(__file__).resolve().parents[4]
        sys_env = get_system_env_path()
        example_file = repo_root / ".env.example"

        try:
            import shutil

            if not sys_env.exists() and example_file.exists():
                ensure_system_env_dir()
                shutil.copy(example_file, sys_env)
        except Exception:
            pass

        # Load system .env into process environment
        if sys_env.exists():
            try:
                from dotenv import load_dotenv

                load_dotenv(sys_env, override=True)
            except Exception:
                # Fallback manual parsing
                try:
                    with open(sys_env, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, value = line.split("=", 1)
                                key = key.strip()
                                value = value.strip()
                                if (value.startswith('"') and value.endswith('"')) or (
                                    value.startswith("'") and value.endswith("'")
                                ):
                                    value = value[1:-1]
                                os.environ[key] = value
                except Exception:
                    pass
    except Exception:
        # Do not block app creation if any step fails
        pass


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    # Ensure .env exists and is loaded before reading settings
    _ensure_system_env_and_load()
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        logger.info(
            f"ValueCell Server starting up on {settings.API_HOST}:{settings.API_PORT}..."
        )

        # Initialize database tables
        try:
            logger.info("Initializing database tables...")
            success = init_database(force=False)
            if success:
                logger.info("✓ Database initialized")
            else:
                logger.info("✗ Database initialization reported failure")
        except Exception as e:
            logger.info(f"✗ Database initialization error: {e}")

        # Initialize and configure adapters
        try:
            logger.info("Configuring data adapters...")
            manager = get_adapter_manager()

            # Configure Yahoo Finance (free, no API key required)
            try:
                manager.configure_yfinance()
                logger.info("✓ Yahoo Finance adapter configured")
            except Exception as e:
                logger.info(f"✗ Yahoo Finance adapter failed: {e}")

            # Configure AKShare (free, no API key required, optimized)
            try:
                manager.configure_akshare()
                logger.info("✓ AKShare adapter configured (optimized)")
            except Exception as e:
                logger.info(f"✗ AKShare adapter failed: {e}")

            logger.info("Data adapters configuration completed")

        except Exception as e:
            logger.info(f"Error configuring adapters: {e}")

        yield
        # Shutdown
        logger.info("ValueCell Server shutting down...")

    app = FastAPI(
        title="ValueCell Server API",
        description="A community-driven, multi-agent platform for financial applications",
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.API_DEBUG else None,
        redoc_url="/redoc" if settings.API_DEBUG else None,
    )

    # Add exception handlers
    _add_exception_handlers(app)

    # Add middleware
    _add_middleware(app, settings)

    # Add routes
    _add_routes(app, settings)

    return app


def _add_middleware(app: FastAPI, settings) -> None:
    """Add middleware to the application."""
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom logging middleware removed


def _add_exception_handlers(app: FastAPI) -> None:
    """Add exception handlers to the application."""
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


API_PREFIX = "/api/v1"


def _add_routes(app: FastAPI, settings) -> None:
    """Add routes to the application."""

    # Root endpoint
    @app.get("/", response_model=SuccessResponse[AppInfoData])
    async def home_page():
        return SuccessResponse.create(
            data=AppInfoData(
                name=settings.APP_NAME,
                version=settings.APP_VERSION,
                environment=settings.APP_ENVIRONMENT,
            ),
            msg="Welcome to ValueCell Server API",
        )

    @app.get(f"{API_PREFIX}/healthz", response_model=SuccessResponse)
    async def health_check():
        return SuccessResponse.create(msg="Welcome to ValueCell!")

    # Include i18n router
    app.include_router(create_i18n_router(), prefix=API_PREFIX)

    # Include system router
    app.include_router(create_system_router(), prefix=API_PREFIX)

    # Include models router
    app.include_router(create_models_router(), prefix=API_PREFIX)

    # Include watchlist router
    app.include_router(create_watchlist_router(), prefix=API_PREFIX)

    # Include conversation router
    app.include_router(create_conversation_router(), prefix=API_PREFIX)

    # Include user profile router
    app.include_router(create_user_profile_router(), prefix=API_PREFIX)

    # Include agent stream router
    app.include_router(create_agent_stream_router(), prefix=API_PREFIX)

    # Include aggregated strategy API router (strategies + strategy agent)
    app.include_router(create_strategy_api_router(), prefix=API_PREFIX)

    # Include agent router
    app.include_router(create_agent_router(), prefix=API_PREFIX)

    # Include task router
    app.include_router(create_task_router(), prefix=API_PREFIX)

    # Include trading router
    try:
        from .routers.trading import create_trading_router

        app.include_router(create_trading_router(), prefix=API_PREFIX)
    except Exception as e:
        logger.info(f"Skip trading router because of import error: {e}")


# For uvicorn
app = create_app()
