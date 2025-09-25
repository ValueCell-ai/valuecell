import asyncio
import logging
from typing import Callable, Optional

import uvicorn
from a2a.types import Task
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationListener:
    """HTTP server for receiving push notifications from agents.

    Listens on a specified host and port for incoming notification requests,
    validates them, and forwards them to a callback function.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5000,
        notification_callback: Optional[Callable] = None,
    ):
        """Initialize the notification listener.

        Args:
            host: Host to bind the server to
            port: Port to listen on
            notification_callback: Function to call when notifications are received
        """
        self.host = host
        self.port = port
        self.notification_callback = notification_callback
        self.app = self._create_app()

    def _create_app(self):
        """Create the Starlette application with notification routes."""
        app = Starlette()
        app.add_route("/notify", self.handle_notification, methods=["POST"])
        return app

    async def handle_notification(self, request: Request):
        """Handle incoming notification requests.

        Args:
            request: The incoming HTTP request

        Returns:
            JSONResponse with status or error
        """
        try:
            task_dict = await request.json()
            logger.info(
                f"📨 Notification received on {self.host}:{self.port}: {task_dict}"
            )

            if self.notification_callback:
                task = Task.model_validate(task_dict)
                if asyncio.iscoroutinefunction(self.notification_callback):
                    await self.notification_callback(task)
                else:
                    self.notification_callback(task)

            return JSONResponse({"status": "ok"})
        except Exception as e:
            logger.error(f"Error handling notification: {e}")
            return JSONResponse({"error": str(e)}, status_code=500)

    def start(self):
        """Start the notification listener server (blocking)."""
        logger.info(f"Starting listener on {self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)

    async def start_async(self):
        """Start the notification listener server asynchronously."""
        logger.info(f"Starting async listener on {self.host}:{self.port}")
        config = uvicorn.Config(
            self.app, host=self.host, port=self.port, log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


def main():
    """Main entry point for running the notification listener."""
    listener = NotificationListener()
    listener.start()


if __name__ == "__main__":
    main()
