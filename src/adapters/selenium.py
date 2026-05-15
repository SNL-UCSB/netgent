from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, Literal

from selenium import webdriver
from selenium.common.exceptions import (
    InvalidArgumentException,
    NoSuchElementException,
    SessionNotCreatedException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver

from adapters.base import AdapterResult, BaseAdapter
from core.errors import BusinessError, NetGentError, TransientError

BrowserType = Literal["chrome", "firefox"]


class SeleniumAdapter(BaseAdapter):
    """Async Selenium lifecycle wrapper.

    Selenium's WebDriver API is sync-only, so every driver call is bounced
    through ``asyncio.to_thread`` to keep the event loop free. The raw
    driver handle is exposed via :attr:`driver` for callers that need to
    issue primitives directly — wrap each call in :meth:`call` (or your own
    ``to_thread``) when doing so.
    """

    name = "selenium"

    def __init__(
        self,
        *,
        browser: BrowserType = "chrome",
        headless: bool = True,
        args: list[str] | None = None,
    ) -> None:
        self._browser_type = browser
        self._headless = headless
        self._args = list(args or [])
        self._driver: WebDriver | None = None

    @property
    def driver(self) -> WebDriver:
        if self._driver is None:
            raise BusinessError("SeleniumAdapter is not open")
        return self._driver

    async def open(self) -> None:
        self._driver = (
            await self.invoke(lambda: asyncio.to_thread(self._build_driver))
        ).unwrap()

    async def close(self) -> None:
        if self._driver is None:
            return
        driver, self._driver = self._driver, None
        (await self.invoke(lambda: asyncio.to_thread(driver.quit))).unwrap()

    async def call(
        self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any
    ) -> AdapterResult[Any]:
        """Run an arbitrary sync Selenium operation on a worker thread."""
        return await self.invoke(lambda: asyncio.to_thread(fn, *args, **kwargs))

    async def goto(self, url: str) -> AdapterResult[None]:
        return await self.invoke(lambda: asyncio.to_thread(self.driver.get, url))

    async def page_source(self) -> AdapterResult[str]:
        return await self.invoke(
            lambda: asyncio.to_thread(lambda: self.driver.page_source)
        )

    async def screenshot(self) -> AdapterResult[bytes]:
        return await self.invoke(
            lambda: asyncio.to_thread(self.driver.get_screenshot_as_png)
        )

    def map_error(self, exc: Exception) -> NetGentError:
        if isinstance(exc, SessionNotCreatedException):
            return BusinessError(f"selenium session not created: {exc}")
        if isinstance(exc, InvalidArgumentException):
            return BusinessError(f"selenium invalid argument: {exc}")
        if isinstance(exc, NoSuchElementException):
            return BusinessError(f"selenium element not found: {exc}")
        if isinstance(exc, TimeoutException):
            return TransientError(f"selenium timeout: {exc}")
        if isinstance(exc, WebDriverException):
            return TransientError(f"selenium webdriver error: {exc}")
        if isinstance(exc, OSError):
            return TransientError(f"selenium I/O error: {exc}")
        return TransientError(f"selenium unexpected error: {exc}")

    def _build_driver(self) -> WebDriver:
        if self._browser_type == "chrome":
            options = ChromeOptions()
            if self._headless:
                options.add_argument("--headless=new")
            for arg in self._args:
                options.add_argument(arg)
            return webdriver.Chrome(options=options)

        options = FirefoxOptions()
        if self._headless:
            options.add_argument("--headless")
        for arg in self._args:
            options.add_argument(arg)
        return webdriver.Firefox(options=options)


__all__ = ["BrowserType", "SeleniumAdapter"]
