"""Main entry point for ValueCell Server Backend."""

from __future__ import annotations

import io
import os
import sys
import threading
from typing import Callable, Optional, TextIO

import uvicorn
from loguru import logger

from valuecell.server.api.app import create_app
from valuecell.server.config.settings import get_settings

EXIT_COMMAND: str = "__EXIT__"

# Set stdout encoding to utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Create app instance for uvicorn
app = create_app()


def control_loop(
    request_stop: Callable[[], None],
    command_stream: Optional[TextIO] = None,
) -> None:
    """Listen for control commands on stdin and request shutdown when needed."""

    stream = command_stream if command_stream is not None else sys.stdin
    for raw_line in stream:
        command = raw_line.strip()
        if command == EXIT_COMMAND:
            logger.info("Received shutdown request via control channel")
            request_stop()
            return
        if command:
            logger.debug("Ignoring unknown control command: {}", command)

    logger.debug("Control channel closed; requesting shutdown")
    request_stop()


def main() -> None:
    """Start the server and coordinate graceful shutdown via stdin control."""

    settings = get_settings()

    config = uvicorn.Config(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="debug" if settings.API_DEBUG else "info",
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = False

    stop_event = threading.Event()

    def request_stop() -> None:
        if stop_event.is_set():
            return

        stop_event.set()
        server.should_exit = True
        logger.info("Shutdown signal propagated to uvicorn")

    # In local development / IDE debug mode (ENV=local_dev) the interactive
    # stdin wrapper (e.g. PyCharm debug) can cause attribute errors when
    # iterating over `sys.stdin`. Skip creating the control thread in that
    # environment to avoid crashing the background thread.
    if os.getenv("ENV") == "local_dev":
        logger.info(
            "ENV=local_dev detected: skipping stdin control thread (IDE debug mode)"
        )
        control_thread = None
    else:
        control_thread = threading.Thread(
            target=control_loop,
            name="stdin-control",
            args=(request_stop,),
            daemon=True,
        )
        control_thread.start()

    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt caught; requesting shutdown")
        request_stop()
    finally:
        request_stop()


if __name__ == "__main__":
    main()
