from __future__ import annotations

import asyncio
import base64
from functools import wraps
from pathlib import Path
from typing import Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from registry.actions.base import ActionContext, action
from registry.actions.exception import ActionError


def _require_page(ctx: ActionContext) -> Page:
    page = ctx.get("page")
    if isinstance(page, Page):
        return page

    raise ActionError("Playwright actions require 'page' in the runtime context")


def _resolve_page(ctx: ActionContext) -> Page:
    return _require_page(ctx)


async def _capture_progress_screenshot(ctx: ActionContext | None) -> str | None:
    if ctx is None:
        return None

    page = ctx.get("page")
    if not isinstance(page, Page):
        return None

    try:
        screenshot = await page.screenshot(type="png")
    except Exception:
        return None

    return base64.b64encode(screenshot).decode("ascii")


def with_progress_screenshot(func):
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = await func(*args, **kwargs)
        ctx = kwargs.get("ctx")
        screenshot_b64 = await _capture_progress_screenshot(ctx)

        if isinstance(result, dict):
            enriched_result = dict(result)
        else:
            enriched_result = {"result": result}

        enriched_result["screenshot"] = {
            "b64": screenshot_b64,
            "format": "png",
        }
        return enriched_result

    return wrapper


def _normalize_selector(selector: str) -> str:
    normalized = selector.strip()
    if not normalized:
        raise ActionError("selector must not be empty")

    if normalized.startswith(("//", ".//", "/", "xpath=")):
        return normalized if normalized.startswith("xpath=") else f"xpath={normalized}"

    return normalized


def _xpath_string_literal(value: str) -> str:
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'

    parts = value.split("'")
    xpath_parts: list[str] = []
    for index, part in enumerate(parts):
        if part:
            xpath_parts.append(f"'{part}'")
        if index < len(parts) - 1:
            xpath_parts.append('"\'"')

    return f"concat({', '.join(xpath_parts)})"


async def _wait_after_action(page: Page) -> None:
    try:
        await page.wait_for_load_state()
    except Exception:
        pass


def _is_context_loss_error(error: Exception) -> bool:
    error_text = str(error)
    return "Cannot find context with specified id" in error_text or "Protocol error" in error_text


def _is_network_error(error: Exception) -> bool:
    error_text = str(error)
    return any(
        marker in error_text
        for marker in (
            "ERR_NAME_NOT_RESOLVED",
            "ERR_INTERNET_DISCONNECTED",
            "ERR_CONNECTION_REFUSED",
            "ERR_TIMED_OUT",
            "net::",
        )
    )


async def _prepare_locator(locator: Any, timeout_ms: int) -> None:
    try:
        await locator.wait_for(state="attached", timeout=timeout_ms)
    except Exception:
        pass

    try:
        await locator.scroll_into_view_if_needed(timeout=timeout_ms)
    except Exception:
        pass


async def _run_click_and_wait(
    page: Page,
    click_func: Any,
    *,
    ctx: ActionContext,
) -> tuple[Page, bool, int | None]:
    initial_pages = tuple(page.context.pages)
    popup_page: Page | None = None
    popup_future = asyncio.get_running_loop().create_future()

    def handle_popup(next_page: Page) -> None:
        if not popup_future.done():
            popup_future.set_result(next_page)

    try:
        page.context.on("page", handle_popup)
        await click_func()
    finally:
        remove_listener = getattr(page.context, "remove_listener", None)
        if callable(remove_listener):
            remove_listener("page", handle_popup)
        else:
            off = getattr(page.context, "off", None)
            if callable(off):
                off("page", handle_popup)

    await asyncio.sleep(0)
    if popup_future.done():
        popup_page = popup_future.result()

    if popup_page is None:
        current_pages = tuple(page.context.pages)
        for candidate in reversed(current_pages):
            if candidate not in initial_pages:
                popup_page = candidate
                break

    if popup_page is None:
        await _wait_after_action(page)
        return page, False, None

    try:
        await popup_page.wait_for_load_state()
    except Exception:
        pass

    ctx.page = popup_page
    return popup_page, True, popup_page.context.pages.index(popup_page)


async def _fallback_coordinate_click(
    page: Page,
    locator: Any,
    *,
    ctx: ActionContext,
    timeout_ms: int,
) -> tuple[Page, bool, int | None]:
    try:
        await locator.scroll_into_view_if_needed(timeout=timeout_ms)
    except Exception:
        pass

    box = await locator.bounding_box()
    if box is None:
        raise ActionError("Failed to click selector by coordinates: bounding box unavailable")

    width = float(box.get("width") or 0)
    height = float(box.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ActionError("Failed to click selector by coordinates: element has no visible size")

    x = float(box["x"]) + width / 2
    y = float(box["y"]) + height / 2
    return await _run_click_and_wait(
        page,
        lambda: page.mouse.click(x, y),
        ctx=ctx,
    )


@action(name="go_to_url")
@with_progress_screenshot
async def go_to_url(
    url: str,
    new_tab: bool = False,
    ctx: ActionContext | None = None,
) -> dict[str, Any]:
    ctx = ctx or ActionContext()

    try:
        if new_tab:
            current_page = _require_page(ctx)
            browser_context = current_page.context
            page = await browser_context.new_page()
            await page.goto(url)
            await _wait_after_action(page)

            page_id = browser_context.pages.index(page)

            return {
                "url": page.url,
                "new_tab": True,
                "page_id": page_id,
                "message": f"Opened new tab #{page_id} with url {url}",
            }

        page = _resolve_page(ctx)
        await page.goto(url)
        await _wait_after_action(page)
        return {
            "url": page.url,
            "new_tab": False,
            "message": f"Navigated to {url}",
        }
    except PlaywrightError as exc:
        if _is_network_error(exc):
            raise ActionError(f"Site unavailable: {url} - {exc}") from exc
        raise ActionError(f"Failed to navigate to {url}") from exc


@action(name="go_back")
@with_progress_screenshot
async def go_back(ctx: ActionContext | None = None) -> dict[str, Any]:
    ctx = ctx or ActionContext()
    page = _resolve_page(ctx)
    try:
        response = await page.go_back()
        await _wait_after_action(page)
        return {
            "url": page.url,
            "navigated": response is not None,
            "message": "Navigated back",
        }
    except PlaywrightError as exc:
        raise ActionError("Failed to navigate back") from exc


@action(name="wait")
@with_progress_screenshot
async def wait(seconds: str = "3", ctx: ActionContext | None = None) -> dict[str, Any]:
    ctx = ctx or ActionContext()
    _resolve_page(ctx)
    try:
        seconds_int = int(float(seconds))
    except (ValueError, TypeError):
        seconds_int = 3
    actual_seconds = max(seconds_int, 1)
    await asyncio.sleep(actual_seconds)
    return {
        "seconds": str(actual_seconds),
        "slept_seconds": str(actual_seconds),
        "message": f"Waiting for {actual_seconds} seconds",
    }


@action(name="click_element")
@with_progress_screenshot
async def click_element(
    selector: str,
    timeout_ms: int = 2_000,
    ctx: ActionContext | None = None,
) -> dict[str, Any]:
    ctx = ctx or ActionContext()
    page = _resolve_page(ctx)

    normalized_selector = _normalize_selector(selector)
    base_locator = page.locator(normalized_selector)
    locator = base_locator.first

    count = await base_locator.count()
    if count == 0:
        raise ActionError(f"Selector matched no elements: {selector}")

    await _prepare_locator(locator, timeout_ms)

    async def build_locator() -> Any:
        next_locator = page.locator(normalized_selector).first
        await _prepare_locator(next_locator, timeout_ms)
        return next_locator

    def build_result(
        active_page: Page,
        method: str,
        *,
        new_tab: bool,
        page_id: int | None,
    ) -> dict[str, Any]:
        result = {
            "selector": selector,
            "clicked": True,
            "url": active_page.url,
            "method": method,
            "new_tab": new_tab,
        }
        if page_id is not None:
            result["page_id"] = page_id
        return result

    try:
        active_page, new_tab, page_id = await _run_click_and_wait(
            page,
            lambda: locator.click(timeout=timeout_ms),
            ctx=ctx,
        )
        return build_result(
            active_page,
            "locator.click",
            new_tab=new_tab,
            page_id=page_id,
        )
    except Exception as first_exc:
        locator_click_error = first_exc

    js_locator = locator
    if _is_context_loss_error(locator_click_error):
        js_locator = await build_locator()

    try:
        handle = await js_locator.element_handle()
        if handle is None:
            raise ActionError(f"Element handle disappeared for selector: {selector}")

        active_page, new_tab, page_id = await _run_click_and_wait(
            page,
            lambda: page.evaluate("(el) => el.click()", handle),
            ctx=ctx,
        )
        return build_result(
            active_page,
            "js-click",
            new_tab=new_tab,
            page_id=page_id,
        )
    except Exception as second_exc:
        js_click_error = second_exc

    coordinate_locator = js_locator
    if _is_context_loss_error(js_click_error):
        coordinate_locator = await build_locator()

    try:
        active_page, new_tab, page_id = await _fallback_coordinate_click(
            page,
            coordinate_locator,
            ctx=ctx,
            timeout_ms=timeout_ms,
        )
        return build_result(
            active_page,
            "coordinate-click",
            new_tab=new_tab,
            page_id=page_id,
        )
    except Exception as third_exc:
        raise ActionError(f"Failed to click selector: {selector}") from third_exc


@action(name="input_text")
@with_progress_screenshot
async def input_text(
    selector: str,
    text: str,
    timeout_ms: int = 2_000,
    ctx: ActionContext | None = None,
) -> dict[str, Any]:
    ctx = ctx or ActionContext()
    page = _resolve_page(ctx)

    normalized_selector = _normalize_selector(selector)
    locator = page.locator(normalized_selector).first

    count = await locator.count()
    if count == 0:
        raise ActionError(f"Selector matched no elements: {selector}")

    try:
        await locator.wait_for(state="attached", timeout=timeout_ms)
    except Exception:
        pass

    try:
        await locator.scroll_into_view_if_needed(timeout=timeout_ms)
    except Exception:
        pass

    try:
        await locator.evaluate("""
            (el) => {
                if ('value' in el) {
                    el.value = '';
                }
                if (el.isContentEditable) {
                    el.textContent = '';
                }
            }
            """)
        await locator.click(timeout=timeout_ms)
        await page.keyboard.type(text)
        return {
            "selector": selector,
            "text": text,
            "input": True,
            "url": page.url,
            "method": "click+keyboard.type",
        }
    except Exception:
        pass

    try:
        await locator.fill(text, timeout=3_000)
        return {
            "selector": selector,
            "text": text,
            "input": True,
            "url": page.url,
            "method": "locator.fill",
        }
    except Exception:
        pass

    try:
        await locator.evaluate("""
            (el) => {
                if ('value' in el) {
                    el.value = '';
                }
                if (el.isContentEditable) {
                    el.textContent = '';
                }
            }
            """)
        await locator.type(text, delay=5, timeout=5_000)
        return {
            "selector": selector,
            "text": text,
            "input": True,
            "url": page.url,
            "method": "locator.type",
        }
    except Exception:
        pass

    try:
        handle = await locator.element_handle()
        if handle is None:
            raise ActionError(f"Element handle disappeared for selector: {selector}")

        await page.evaluate(
            """
            ({ el, value }) => {
                const tagName = el.tagName.toLowerCase();

                if (el.isContentEditable) {
                    el.textContent = value;
                } else if ('value' in el) {
                    el.value = value;
                } else if (tagName === 'textarea' || tagName === 'input') {
                    el.value = value;
                } else {
                    el.textContent = value;
                }

                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
            """,
            {"el": handle, "value": text},
        )

        return {
            "selector": selector,
            "text": text,
            "input": True,
            "url": page.url,
            "method": "js-set-value",
        }
    except Exception as exc:
        raise ActionError(f"Failed to input text into selector: {selector}") from exc


@action(name="scroll")
@with_progress_screenshot
async def scroll(
    down: bool,
    num_pages: float,
    selector: str | None = None,
    ctx: ActionContext | None = None,
) -> dict[str, Any]:
    ctx = ctx or ActionContext()
    page = _resolve_page(ctx)
    if num_pages < 0:
        raise ActionError("num_pages must be >= 0")

    window_height = await page.evaluate("() => window.innerHeight")
    window_height = int(window_height or 0)

    scroll_amount = int(window_height * num_pages)
    dy = scroll_amount if down else -scroll_amount
    direction = "down" if down else "up"

    if selector is None:
        await page.evaluate("(y) => window.scrollBy(0, y)", dy)
        return {
            "scrolled": True,
            "target": "page",
            "direction": direction,
            "num_pages": num_pages,
            "url": page.url,
            "method": "window.scrollBy",
        }

    normalized_selector = _normalize_selector(selector)
    locator = page.locator(normalized_selector).first

    count = await locator.count()
    if count == 0:
        raise ActionError(f"Selector matched no elements: {selector}")

    try:
        await locator.scroll_into_view_if_needed(timeout=2_000)
    except Exception:
        pass

    handle = await locator.element_handle()
    if handle is None:
        raise ActionError(f"Element handle disappeared for selector: {selector}")

    result = await page.evaluate(
        """
        ({ el, dy }) => {
            let current = el;
            let attempts = 0;

            while (current && attempts < 10) {
                const style = window.getComputedStyle(current);
                const hasScrollableY = /(auto|scroll|overlay)/.test(style.overflowY);
                const canScrollVertically = current.scrollHeight > current.clientHeight;

                if (hasScrollableY && canScrollVertically) {
                    const before = current.scrollTop;
                    const maxScroll = current.scrollHeight - current.clientHeight;

                    let delta = dy / 3;

                    if (delta > 0) {
                        delta = Math.min(delta, maxScroll - before);
                    } else {
                        delta = Math.max(delta, -before);
                    }

                    current.scrollTop = before + delta;
                    const after = current.scrollTop;
                    const actual = after - before;

                    if (Math.abs(actual) > 0.5) {
                        return {
                            success: true,
                            target: "container",
                            tag: current.tagName.toLowerCase(),
                            id: current.id || "",
                            className: current.className || "",
                            scrollDelta: actual
                        };
                    }
                }

                if (current === document.body || current === document.documentElement) {
                    break;
                }

                current = current.parentElement;
                attempts++;
            }

            window.scrollBy(0, dy);

            return {
                success: true,
                target: "page_fallback",
                scrollDelta: dy
            };
        }
        """,
        {"el": handle, "dy": dy},
    )

    target = result.get("target", "unknown")
    method = "element.scrollTop" if target == "container" else "window.scrollBy"

    return {
        "scrolled": True,
        "selector": selector,
        "direction": direction,
        "num_pages": num_pages,
        "url": page.url,
        "target": target,
        "method": method,
        "details": result,
    }


@action(name="send_keys")
@with_progress_screenshot
async def send_keys(keys: str, ctx: ActionContext | None = None) -> dict[str, Any]:
    ctx = ctx or ActionContext()
    page = _resolve_page(ctx)
    try:
        await page.keyboard.press(keys)
        return {
            "keys": keys,
            "url": page.url,
            "method": "keyboard.press",
        }
    except Exception as exc:
        if "Unknown key" not in str(exc):
            raise ActionError(f"Failed to send keys: {keys}") from exc

        try:
            for key in keys:
                await page.keyboard.press(key)
        except Exception as fallback_exc:
            raise ActionError(f"Failed to send keys: {keys}") from fallback_exc

        return {
            "keys": keys,
            "url": page.url,
            "method": "keyboard.press.each",
        }


@action(name="scroll_to_text")
@with_progress_screenshot
async def scroll_to_text(
    text: str,
    ctx: ActionContext | None = None,
) -> dict[str, Any]:
    ctx = ctx or ActionContext()
    page = _resolve_page(ctx)
    xpath_text = _xpath_string_literal(text)
    locators = [
        page.get_by_text(text, exact=False),
        page.locator(f"text={text}"),
        page.locator(f"xpath=//*[contains(text(), {xpath_text})]"),
    ]

    try:
        for locator in locators:
            try:
                if await locator.count() == 0:
                    continue

                element = locator.first
                is_visible = await element.is_visible()
                bbox = await element.bounding_box()

                if is_visible and bbox is not None:
                    if bbox.get("width", 0) <= 0 or bbox.get("height", 0) <= 0:
                        continue

                    await element.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    return {
                        "text": text,
                        "scrolled": True,
                        "found": True,
                        "url": page.url,
                    }
            except Exception:
                continue

        return {
            "text": text,
            "scrolled": False,
            "found": False,
            "url": page.url,
        }
    except Exception as exc:
        raise ActionError(f"Failed to scroll to text '{text}'") from exc


@action(name="select_dropdown_option")
@with_progress_screenshot
async def select_dropdown_option(
    selector: str,
    text: str,
    timeout_ms: int = 2_000,
    ctx: ActionContext | None = None,
) -> dict[str, Any]:
    ctx = ctx or ActionContext()
    page = _resolve_page(ctx)
    normalized_selector = _normalize_selector(selector)
    locator = page.locator(normalized_selector).first

    count = await locator.count()
    if count == 0:
        raise ActionError(f"Selector matched no elements: {selector}")

    try:
        await locator.wait_for(state="attached", timeout=timeout_ms)
    except Exception:
        pass

    try:
        await locator.scroll_into_view_if_needed(timeout=timeout_ms)
    except Exception:
        pass

    try:
        await locator.select_option(label=text, timeout=3_000)
        await _wait_after_action(page)
        return {
            "selector": selector,
            "text": text,
            "selected": True,
            "url": page.url,
            "method": "select_option(label)",
        }
    except Exception:
        pass

    try:
        await locator.select_option(value=text, timeout=3_000)
        await _wait_after_action(page)
        return {
            "selector": selector,
            "text": text,
            "selected": True,
            "url": page.url,
            "method": "select_option(value)",
        }
    except Exception:
        pass

    try:
        await locator.click(timeout=timeout_ms)
    except Exception:
        pass

    option_locators = [
        page.get_by_role("option", name=text, exact=True).first,
        page.get_by_role("menuitem", name=text, exact=True).first,
        page.get_by_role("button", name=text, exact=True).first,
        page.get_by_text(text, exact=True).first,
        page.locator(f'[role="option"] >> text="{text}"').first,
        page.locator(f'[role="menuitem"] >> text="{text}"').first,
        page.locator(f'text="{text}"').first,
    ]

    last_error: Exception | None = None

    for option_locator in option_locators:
        try:
            if await option_locator.count() == 0:
                continue

            await option_locator.scroll_into_view_if_needed(timeout=timeout_ms)
            await option_locator.click(timeout=timeout_ms)
            await _wait_after_action(page)

            return {
                "selector": selector,
                "text": text,
                "selected": True,
                "url": page.url,
                "method": "click-visible-option",
            }
        except Exception as exc:
            last_error = exc
            continue

    try:
        handle = await locator.element_handle()
        if handle is None:
            raise ActionError(f"Element handle disappeared for selector: {selector}")

        clicked = await page.evaluate(
            """
            ({ root, targetText }) => {
                const normalize = (s) => (s || '').replace(/\\s+/g, ' ').trim();

                const candidates = root.querySelectorAll(
                    '[role="option"], [role="menuitem"], option, li, button, div, span'
                );

                for (const el of candidates) {
                    const text = normalize(el.textContent);
                    if (text === targetText) {
                        el.click();
                        return true;
                    }
                }

                return false;
            }
            """,
            {"root": handle, "targetText": text},
        )

        if clicked:
            await _wait_after_action(page)
            return {
                "selector": selector,
                "text": text,
                "selected": True,
                "url": page.url,
                "method": "js-click-option",
            }
    except Exception as exc:
        last_error = exc

    raise ActionError(
        f"Failed to select dropdown option '{text}' for selector: {selector}"
    ) from last_error


PLAYWRIGHT_ACTIONS = (
    go_to_url,
    go_back,
    wait,
    click_element,
    input_text,
    scroll,
    send_keys,
    scroll_to_text,
    select_dropdown_option,
)


__all__ = [
    "PLAYWRIGHT_ACTIONS",
    "click_element",
    "go_back",
    "go_to_url",
    "input_text",
    "scroll",
    "scroll_to_text",
    "select_dropdown_option",
    "send_keys",
    "wait",
]
