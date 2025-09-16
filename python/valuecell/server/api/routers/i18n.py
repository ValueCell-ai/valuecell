"""RESTful i18n API router module."""

from fastapi import APIRouter
from ..i18n_api import get_i18n_api


def create_i18n_router() -> APIRouter:
    """Create RESTful style i18n router.

    API path design:
    - GET /api/v1/i18n/config - Get i18n configuration
    - GET /api/v1/i18n/languages - Get supported languages list
    - PUT /api/v1/i18n/language - Set language
    - GET /api/v1/i18n/timezones - Get supported timezones list
    - PUT /api/v1/i18n/timezone - Set timezone
    - POST /api/v1/i18n/language/detect - Detect language
    - POST /api/v1/i18n/translate - Translate text
    - POST /api/v1/i18n/format/datetime - Format datetime
    - POST /api/v1/i18n/format/number - Format number
    - POST /api/v1/i18n/format/currency - Format currency
    - GET /api/v1/i18n/users/{user_id}/settings - Get user i18n settings
    - PUT /api/v1/i18n/users/{user_id}/settings - Update user i18n settings
    - GET /api/v1/i18n/agents/context - Get Agent i18n context

    Returns:
        APIRouter: Configured i18n router
    """
    # Get existing i18n router, but modify prefix to comply with RESTful style
    i18n_api = get_i18n_api()
    router = i18n_api.router

    # Update router prefix to comply with RESTful API versioning
    router.prefix = "/api/v1/i18n"

    return router


def get_i18n_router() -> APIRouter:
    """Get i18n router instance (backward compatible).

    Returns:
        APIRouter: Configured i18n router
    """
    return create_i18n_router()


# Export the router functions
__all__ = ["create_i18n_router", "get_i18n_router"]
