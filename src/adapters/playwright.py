from __future__ import annotations

from typing import Literal

from playwright.async_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from adapters.base import AdapterResult, BaseAdapter
from core.errors import BusinessError, NetGentError, TransientError

BrowserType = Literal["chromium", "firefox", "webkit"]


class PlaywrightAdapter(BaseAdapter):
    """Async Playwright lifecycle wrapper.

    Calls `async_playwright()` to drive the browser primitives directly —
    no sync→thread bridging needed since `playwright.async_api` is natively
    async. Exposes the underlying ``playwright``, ``browser``, ``context``,
    and ``page`` handles for callers that want to drive Playwright directly.
    """

    name = "playwright"

    def __init__(
        self,
        *,
        browser: BrowserType = "chromium",
        headless: bool = True,
        args: list[str] | None = None,
    ) -> None:
        self._browser_type = browser
        self._headless = headless
        self._args = list(args or [])
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def playwright(self) -> Playwright:
        if self._playwright is None:
            raise BusinessError("PlaywrightAdapter is not open")
        return self._playwright

    @property
    def browser(self) -> Browser:
        if self._browser is None:
            raise BusinessError("PlaywrightAdapter is not open")
        return self._browser

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise BusinessError("PlaywrightAdapter is not open")
        return self._context

    @property
    def page(self) -> Page:
        if self._page is None:
            raise BusinessError("PlaywrightAdapter is not open")
        return self._page

    async def open(self) -> None:
        (await self.invoke(self._open)).unwrap()

    async def close(self) -> None:
        (await self.invoke(self._close)).unwrap()

    async def goto(self, url: str, **kwargs: object) -> AdapterResult[None]:
        return await self.invoke(lambda: self.page.goto(url, **kwargs))

    async def content(self) -> AdapterResult[str]:
        return await self.invoke(lambda: self.page.content())

    async def screenshot(self, **kwargs: object) -> AdapterResult[bytes]:
        return await self.invoke(lambda: self.page.screenshot(**kwargs))

    def map_error(self, exc: Exception) -> NetGentError:
        if isinstance(exc, PlaywrightTimeoutError):
            return TransientError(f"playwright timeout: {exc}")
        if isinstance(exc, PlaywrightError):
            return TransientError(f"playwright error: {exc}")
        if isinstance(exc, OSError):
            return TransientError(f"playwright I/O error: {exc}")
        return TransientError(f"playwright unexpected error: {exc}")

    async def _open(self) -> None:
        self._playwright = await async_playwright().start()
        launcher = getattr(self._playwright, self._browser_type)
        self._browser = await launcher.launch(headless=self._headless, args=self._args)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()

    async def _close(self) -> None:
        if self._page is not None:
            await self._page.close()
            self._page = None
        if self._context is not None:
            await self._context.close()
            self._context = None
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None


__all__ = ["BrowserType", "PlaywrightAdapter"]
