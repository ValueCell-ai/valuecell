import asyncio
import os
from datetime import datetime
from typing import Optional

from agno.media import Image
from loguru import logger
from playwright.async_api import Browser, Page, Playwright, async_playwright

from .interfaces import BaseScreenshotDataSource


class PlaywrightScreenshotDataSource(BaseScreenshotDataSource):
    """
    Concrete implementation using Playwright.
    Implements Async Context Manager protocol for automatic setup and teardown.
    """

    def __init__(self, target_url: str, file_path: str):
        """
        Initializes configuration.
        """
        self.target_url = target_url
        self.file_path = file_path

        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

        # Ensure dummy file exists if not present
        if not os.path.exists(self.file_path):
            logger.warning(
                f"File {self.file_path} not found. Creating empty JSON file."
            )
            with open(self.file_path, "w") as f:
                f.write("{}")

    async def __aenter__(self):
        """
        Magic method for 'async with'.
        Starts the browser, navigates to the URL, and performs the setup automation.
        """
        # Delegate to explicit open() so callers can avoid repeated __aenter__ overhead
        return await self.open()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Magic method for 'async with'.
        Handles cleanup of browser resources.
        """
        if exc_type:
            logger.error(f"Exiting session due to exception: {exc_val}")

        await self.close()

    async def _cleanup(self):
        """
        Internal helper to close browser resources.
        """
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def open(self):
        """Explicit initialization to support one-time setup.

        Returns:
            self: the initialized data source (same as __aenter__ would).
        """
        try:
            logger.info("Initializing Playwright session...")
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)

            context = await self.browser.new_context(
                viewport={"width": 1600, "height": 900}
            )
            self.page = await context.new_page()

            logger.info(f"Navigating to {self.target_url}")
            await self.page.goto(self.target_url, wait_until="networkidle")

            logger.info("Waiting for core UI elements...")
            # Wait for the green menu button to ensure page load
            menu_btn = self.page.locator("#menu .menu__button")
            await menu_btn.wait_for(state="visible", timeout=60000)

            logger.info("Page loaded. Executing setup sequence.")

            # 1. Click Menu
            await menu_btn.click()

            # 2. Click Settings
            await self.page.get_by_text("Settings", exact=True).click()

            # 3. Click New
            await self.page.locator("button").filter(has_text="New").click()

            # 4. Handle File Upload
            logger.info("Uploading file...")
            async with self.page.expect_file_chooser() as fc_info:
                await self.page.get_by_text("Upload template file").click()

            file_chooser = await fc_info.value
            await file_chooser.set_files(self.file_path)

            # Wait slightly for UI render
            await asyncio.sleep(1)

            # 5. Click IMPORT
            logger.info("Confirming import...")
            import_btn = self.page.locator("button").filter(has_text="IMPORT")
            await import_btn.wait_for(state="visible")
            await import_btn.click()

            logger.info("Import successful. Waiting for modal to close...")
            await asyncio.sleep(3)

            return self

        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            # Ensure cleanup happens if initialization fails mid-way
            await self._cleanup()
            raise e

    async def close(self):
        """Explicit cleanup to support one-time teardown.

        Calls internal cleanup helpers and logs session close.
        """
        await self._cleanup()
        logger.info("Session closed.")

    async def capture(self, *args, **kwargs) -> Image:
        """
        Captures the current state of the page.
        """
        if not self.page:
            raise RuntimeError("Page is not initialized. Use 'async with' context.")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            logger.info(f"Capturing screenshot at {timestamp}...")

            # Capture screenshot bytes
            screenshot_bytes = await self.page.screenshot(full_page=True)

            # Create agno Image object
            # Assuming Image can be initialized with content/bytes.
            # If agno.media.Image requires a file path, we would save it to disk first.
            image_obj = Image(content=screenshot_bytes)

            logger.info("Screenshot captured successfully.")
            return image_obj

        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            raise e
