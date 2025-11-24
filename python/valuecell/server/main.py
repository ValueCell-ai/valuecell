"""Main entry point for ValueCell Server Backend."""

import io
import sys

import uvicorn

from valuecell.server.api.app import create_app
from valuecell.server.config.settings import get_settings

# Set stdout encoding to utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
# Create app instance for uvicorn
app = create_app()


def main():
    """Start the server."""
    settings = get_settings()

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
    )


if __name__ == "__main__":
    main()
