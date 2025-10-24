"""System related API routes."""

from datetime import datetime

from fastapi import APIRouter

from ...config.settings import get_settings
from ..schemas import AppInfoData, HealthCheckData, SuccessResponse


def create_system_router() -> APIRouter:
    """Create system related routes."""
    router = APIRouter(prefix="/system", tags=["System"])
    settings = get_settings()

    @router.get(
        "/info",
        response_model=SuccessResponse[AppInfoData],
        summary="Get application info",
        description="Get ValueCell application basic information including name, version and environment",
    )
    async def get_app_info():
        """Get application basic information."""
        app_info = AppInfoData(
            name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.APP_ENVIRONMENT,
        )
        return SuccessResponse.create(
            data=app_info, msg="Application info retrieved successfully"
        )

    @router.get(
        "/health",
        response_model=SuccessResponse[HealthCheckData],
        summary="Health check",
        description="Check service running status and version information",
    )
    async def health_check():
        """Service health status check."""
        health_data = HealthCheckData(
            status="healthy", version=settings.APP_VERSION, timestamp=datetime.now()
        )
        return SuccessResponse.create(
            data=health_data, msg="Service is running normally"
        )

    return router
