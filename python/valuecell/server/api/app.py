"""FastAPI application factory for ValueCell Server."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .exceptions import (
    APIException,
    api_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)

from ..config.settings import get_settings
from .routers.i18n import create_i18n_router
from .routers.system import create_system_router
from .routers.websocket import create_websocket_router
from .routers.watchlist import create_watchlist_router
from .schemas import SuccessResponse, AppInfoData
from ...adapters.assets import get_adapter_manager


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        print(
            f"ValueCell Server starting up on {settings.API_HOST}:{settings.API_PORT}..."
        )

        # Initialize and configure adapters
        try:
            print("Configuring data adapters...")
            manager = get_adapter_manager()

            # Configure Yahoo Finance (free, no API key required)
            try:
                manager.configure_yfinance()
                print("✓ Yahoo Finance adapter configured")
            except Exception as e:
                print(f"✗ Yahoo Finance adapter failed: {e}")

            # Configure AKShare (free, no API key required, optimized)
            try:
                manager.configure_akshare()
                print("✓ AKShare adapter configured (optimized)")
            except Exception as e:
                print(f"✗ AKShare adapter failed: {e}")

            print("Data adapters configuration completed")

        except Exception as e:
            print(f"Error configuring adapters: {e}")

        yield
        # Shutdown
        print("ValueCell Server shutting down...")

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


def _add_exception_handlers(app: FastAPI):
    """Add exception handlers."""
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


def _add_routes(app: FastAPI, settings) -> None:
    """Add routes to the application."""

    @app.get(
        "/",
        response_model=SuccessResponse[AppInfoData],
        summary="Get application info",
        description="Get ValueCell application basic information including name, version and environment",
        tags=["Root"],
    )
    async def root():
        """Root endpoint - Get application basic information."""
        app_info = AppInfoData(
            name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.APP_ENVIRONMENT,
        )
        return SuccessResponse.create(data=app_info, msg="Welcome to ValueCell API")

    # Include i18n router
    app.include_router(create_i18n_router())

    # Include system router
    app.include_router(create_system_router())

    # Include websocket router
    app.include_router(create_websocket_router())
    # Include watchlist router
    app.include_router(create_watchlist_router())


# For uvicorn
app = create_app()
