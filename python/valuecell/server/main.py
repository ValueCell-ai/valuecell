"""Main entry point for ValueCell Server Backend."""

from __future__ import annotations

import io
import socket
import sys
import threading
from typing import Callable, Optional, TextIO

import uvicorn
from loguru import logger

from valuecell.server.api.app import create_app
from valuecell.server.config.settings import get_settings
from valuecell.utils.env import (
    auto_port_enabled,
    remove_port_file,
    write_port_file,
)

EXIT_COMMAND: str = "__EXIT__"

# Set stdout encoding to utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Create app instance for uvicorn
app = create_app()


def find_available_port(host: str = "127.0.0.1") -> int:
    """Find an available port by binding to port 0.

    Args:
        host: The host to bind to.

    Returns:
        An available port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.getsockname()[1]


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

    # Determine the port to use
    if auto_port_enabled():
        # Auto-allocate an available port
        actual_port = find_available_port(settings.API_HOST)
        logger.info("Auto-allocated port: {port}", port=actual_port)
    else:
        actual_port = settings.API_PORT

    # Write port file for client discovery
    port_file = write_port_file(actual_port)
    logger.info("Port file written to: {path}", path=str(port_file))

    config = uvicorn.Config(
        app,
        host=settings.API_HOST,
        port=actual_port,
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
        # Clean up port file on shutdown
        remove_port_file()
        logger.info("Port file removed")


if __name__ == "__main__":
    main()
