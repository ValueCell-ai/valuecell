"""Main API application for ValueCell."""

from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .schemas import SuccessResponse
from .i18n_api import create_i18n_router
from ..config.settings import get_settings


class ValueCellAPI:
    """Main API class for ValueCell."""

    def __init__(self):
        """Initialize API application."""
        self.settings = get_settings()
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:
        """Create FastAPI application."""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            print("ValueCell API starting up...")
            yield
            # Shutdown
            print("ValueCell API shutting down...")

        app = FastAPI(
            title="ValueCell API",
            description="A community-driven, multi-agent platform for financial applications",
            version=self.settings.APP_VERSION,
            lifespan=lifespan,
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure properly in production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add routes
        self._add_routes(app)

        return app

    def _add_routes(self, app: FastAPI):
        """Add API routes."""

        @app.get("/", response_model=SuccessResponse)
        async def root():
            """Root endpoint."""
            return SuccessResponse(
                message="Welcome to ValueCell API",
                data={
                    "name": self.settings.APP_NAME,
                    "version": self.settings.APP_VERSION,
                    "environment": self.settings.APP_ENVIRONMENT,
                },
            )

        @app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy", "version": self.settings.APP_VERSION}

        # Include i18n router
        app.include_router(create_i18n_router())


# Global API instance
_api: Optional[ValueCellAPI] = None


def get_api() -> ValueCellAPI:
    """Get global API instance."""
    global _api
    if _api is None:
        _api = ValueCellAPI()
    return _api


def create_app() -> FastAPI:
    """Create FastAPI application."""
    return get_api().app


# For uvicorn
app = create_app()
