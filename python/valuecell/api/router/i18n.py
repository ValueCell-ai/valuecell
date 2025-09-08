"""I18n router module for ValueCell API."""

from fastapi import APIRouter
from ..i18n_api import create_i18n_router


def get_i18n_router() -> APIRouter:
    """Get i18n router instance.

    This function creates and returns an i18n router that can be included
    in the main FastAPI application.

    Returns:
        APIRouter: The configured i18n router
    """
    return create_i18n_router()


# Export the router function
__all__ = ["get_i18n_router"]
