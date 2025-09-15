"""FastAPI application factory for ValueCell Server."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from ..config.settings import get_settings
from .routers import health, agents, assets, i18n


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        print(f"ValueCell Server starting up on {settings.API_HOST}:{settings.API_PORT}...")
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
    
    # Add middleware
    _add_middleware(app, settings)
    
    # Add routes
    _add_routes(app)
    
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


def _add_routes(app: FastAPI) -> None:
    """Add routes to the application."""
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
    app.include_router(assets.router, prefix="/api/v1/assets", tags=["assets"])
    app.include_router(i18n.router, prefix="/api/v1", tags=["i18n"])