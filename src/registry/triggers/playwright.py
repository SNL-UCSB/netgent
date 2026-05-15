from __future__ import annotations

from typing import Any, Literal

from playwright.async_api import Page

from clients.netgent.src.registry.context import Context
from clients.netgent.src.registry.triggers.base import TriggerError, trigger

ElementState = Literal["attached", "detached", "hidden", "visible"]


def _require_page(ctx: Context | None) -> Page:
    page = (ctx or Context()).get("page")
    if isinstance(page, Page):
        return page

    raise TriggerError("Playwright triggers require 'page' in the runtime context")


def _normalize_selector(selector: str) -> str:
    normalized = selector.strip()
    if not normalized:
        raise TriggerError("selector must not be empty")

    if normalized.startswith(("//", ".//", "/", "xpath=")):
        return normalized if normalized.startswith("xpath=") else f"xpath={normalized}"

    return normalized


def _timeout_ms(timeout: float) -> float:
    return max(timeout, 0) * 1000


@trigger(name="check_element")
async def check_element(
    selector: str,
    check_visibility: bool = True,
    timeout: float = 0.1,
    state: ElementState | None = None,
    ctx: Context | None = None,
) -> bool:
    """Check if an element matches the requested Playwright state."""
    page = _require_page(ctx)
    locator = page.locator(_normalize_selector(selector)).first
    target_state = state or ("visible" if check_visibility else "attached")

    try:
        await locator.wait_for(state=target_state, timeout=_timeout_ms(timeout))
        return True
    except Exception:
        return False


@trigger(name="check_url")
def check_url(url: str, ctx: Context | None = None) -> bool:
    """Check if the current page URL exactly matches the provided URL."""
    try:
        return _require_page(ctx).url == url
    except Exception:
        return False


@trigger(name="check_text")
async def check_text(
    text: str,
    check_visibility: bool = True,
    timeout: float = 0.1,
    exact: bool = True,
    ctx: Context | None = None,
) -> bool:
    """Check if text exists on the page and optionally requires visibility."""
    page = _require_page(ctx)
    locator = page.get_by_text(text, exact=exact).first
    target_state: ElementState = "visible" if check_visibility else "attached"

    try:
        await locator.wait_for(state=target_state, timeout=_timeout_ms(timeout))
        return True
    except Exception:
        return False


@trigger(name="check_javascript")
async def check_javascript(
    script: str,
    arg: Any | None = None,
    timeout: float = 0.1,
    ctx: Context | None = None,
) -> bool:
    """Wait for a JavaScript expression or function to become truthy."""
    page = _require_page(ctx)

    try:
        await page.wait_for_function(
            script,
            arg=arg,
            timeout=_timeout_ms(timeout),
        )
        return True
    except Exception:
        return False


PLAYWRIGHT_TRIGGERS = (
    check_element,
    check_javascript,
    check_url,
    check_text,
)


__all__ = [
    "PLAYWRIGHT_TRIGGERS",
    "check_element",
    "check_javascript",
    "check_text",
    "check_url",
]
