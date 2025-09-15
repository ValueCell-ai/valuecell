"""Main entry point for ValueCell Server Backend."""

import uvicorn
from .api.app import create_app
from .config.settings import get_settings


def main():
    """Start the server."""
    settings = get_settings()
    app = create_app()

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_DEBUG,
    )


if __name__ == "__main__":
    main()
