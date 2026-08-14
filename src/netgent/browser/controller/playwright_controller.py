"""
Playwright controller.

A drop-in ``BaseController`` sibling to ``PyAutoGUIController``: it registers
the exact same actions and triggers, so the program controller, state
executor, and any hand-authored/generated JSON workflow are completely
unaware of which backend is driving the browser.

Where PyAutoGUIController drives a real Selenium/SeleniumBase browser and
then simulates OS-level mouse/keyboard input on top of it (for anti-bot
realism), PlaywrightController drives the browser directly over Playwright's
own protocol -- faster and more deterministic, at the cost of not looking
like a real user's OS input to bot-detection scripts.

Design note -- why some BaseController methods are overridden and others
aren't: BaseController's non-abstract methods (navigate, check_element,
check_url, check_text, quit, and the perception layer: snapshot,
get_context, build_trigger_candidates, resolve_element_action,
get_element_coordinates) are written directly against the Selenium/
SeleniumBase driver API (``driver.get()``, ``driver.execute_cdp_cmd()``,
``WebDriverWait`` + ``expected_conditions``, ``driver.get_window_position()``,
etc.), none of which exists on a Playwright ``Page``. PyAutoGUIController
gets away with inheriting them unmodified because its ``self.driver`` really
is a Selenium driver. This controller cannot, so it overrides everything
that actually gets exercised by JSON-workflow execution (actions + triggers
+ navigate + quit). ``wait`` is also overridden -- not because BaseController's
``time.sleep()`` is wrong, but because it doubles as the pump point for the
QoE thread-safety adapter below.

The perception layer (snapshot / build_trigger_candidates / etc.) is used
only by the LLM-driven generation path (web_agent / state_synthesis) and by
the desktop pre-action snapshot (which is gated to the desktop domain and
never reached here). Reimplementing it would mean porting the DOM-marking
scripts (build_dom.js / avaliable_trigger.js) from CDP injection to
Playwright's own page-script APIs -- real work, out of scope for this pass.
Those methods are left inherited (and therefore non-functional) on purpose;
``NetGent`` and the CLI both refuse ``backend="playwright"`` with
``llm_enabled=True`` / ``-g`` up front with a clear error rather than letting
generation mode hit them and fail confusingly deep inside LangGraph.

QoE/stats-logging (start_stats_logging / stop_stats_logging, Matthew's
module) is reused completely as-is: ``VideoStatsLogger`` only needs an
object exposing ``.current_url`` and ``.execute_script(js)``, so
``self.driver`` here is a tiny adapter around the Playwright ``Page`` that
provides exactly those two members. That lets BaseController.__init__'s
existing ``VideoStatsLogger(driver)`` line work unmodified -- no changes to
stats_logger.py.

Thread-safety wrinkle this adapter has to work around: VideoStatsLogger
samples from its own background thread (by design -- see stats_logger.py),
but Playwright's *sync* API only allows calls from the thread that started
it; calling ``page.evaluate()`` from another thread raises "Cannot switch to
a different thread". So ``_PlaywrightStatsAdapter.execute_script`` doesn't
call Playwright directly -- it enqueues the script and blocks for a result,
and ``PlaywrightController.wait()`` (the main thread) drains that queue
periodically while it sleeps. This only touches how *this controller* talks
to Playwright; VideoStatsLogger itself is untouched.
"""

from __future__ import annotations

import logging
import queue
import random
import time
from typing import Optional

from .base import BaseController

logger = logging.getLogger(__name__)

# Selenium locator strategies actually produced by this codebase's JSON
# workflows (see BaseController.resolve_element_action): "css selector" is
# what the browser domain always emits; "xpath" is BaseController's documented
# fallback. Anything else isn't something real workflows send us.
_SUPPORTED_BY = ("css selector", "xpath")

# PyAutoGUI-style lowercase key names (used by existing JSON workflows) mapped
# to Playwright's capitalized key names. Anything not listed here is passed
# through to page.keyboard.press() as-is (works for single characters and for
# keys that already use Playwright's naming, e.g. "Enter").
_KEY_ALIASES = {
    "enter": "Enter",
    "return": "Enter",
    "space": "Space",
    "tab": "Tab",
    "esc": "Escape",
    "escape": "Escape",
    "backspace": "Backspace",
    "delete": "Delete",
    "up": "ArrowUp",
    "down": "ArrowDown",
    "left": "ArrowLeft",
    "right": "ArrowRight",
    "ctrl": "Control",
    "control": "Control",
    "alt": "Alt",
    "option": "Alt",
    "shift": "Shift",
    "meta": "Meta",
    "command": "Meta",
    "cmd": "Meta",
    "win": "Meta",
}


class _PlaywrightStatsAdapter:
    """The minimal shim VideoStatsLogger needs from ``driver``.

    VideoStatsLogger.sample() only ever touches ``driver.current_url`` and
    ``driver.execute_script(js)`` -- so that's the entire surface this adapter
    implements, delegating to the real Playwright Page. Everything else in
    this controller talks to Playwright directly via ``self._page``.

    ``execute_script`` is called from VideoStatsLogger's own background
    thread, but Playwright's sync API forbids calling into it from any thread
    other than the one that started it. So this doesn't call ``self._page``
    directly -- it hands the script to ``PlaywrightController.wait()`` (which
    runs on the main/Playwright-owning thread) via a request queue, and
    blocks for the result. See ``pump_pending()``.
    """

    def __init__(self, page):
        self._page = page
        self._pending: "queue.Queue[tuple[str, queue.Queue]]" = queue.Queue()

    @property
    def current_url(self) -> str:
        # Reading Page.url is a local attribute read (Playwright keeps it
        # in sync via its event stream), not a round-trip call into the
        # driver -- unlike evaluate(), this is safe from any thread.
        return self._page.url

    def execute_script(self, script: str):
        result_q: "queue.Queue" = queue.Queue(maxsize=1)
        self._pending.put((script, result_q))
        result = result_q.get(timeout=10)
        if isinstance(result, BaseException):
            raise result
        return result

    def pump_pending(self) -> None:
        """Run any pending execute_script() requests. Must be called from the
        main thread (the one that owns the Playwright sync connection)."""
        while True:
            try:
                script, result_q = self._pending.get_nowait()
            except queue.Empty:
                return
            try:
                # Selenium's execute_script wraps `script` as a function BODY
                # (so a bare top-level `return`, which stats_logger.py's
                # _STATS_JS relies on, works). Playwright's page.evaluate()
                # expects an expression or a function, so replicate Selenium's
                # wrapping here rather than touching the shared QoE script.
                value = self._page.evaluate("(script) => new Function(script)()", script)
                result_q.put(value)
            except Exception as e:
                result_q.put(e)


class PlaywrightController(BaseController):
    """A BaseController that drives a real browser via Playwright."""

    def __init__(self, user_data_dir: Optional[str] = None, headless: bool = False):
        from playwright.sync_api import sync_playwright  # lazy import

        self._playwright = sync_playwright().start()
        # Rough parity with BrowserSession's anti-detection flags (session.py).
        # Playwright doesn't need the Xvfb/Xlib dance PyAutoGUIController's
        # BrowserSession does -- it drives the browser over CDP, not by moving
        # the OS mouse, so there's no real screen/display dependency here.
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            "--disable-gpu",
        ]
        viewport = {"width": 1920, "height": 1080}

        if user_data_dir:
            # Persistent context: same purpose as BrowserSession's
            # user_data_dir (saved logins/cookies across runs). Playwright
            # models this as launch_persistent_context rather than a
            # separate browser + context.
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir, headless=headless, args=launch_args, viewport=viewport,
            )
            self._browser = None
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        else:
            self._browser = self._playwright.chromium.launch(headless=headless, args=launch_args)
            self._context = self._browser.new_context(viewport=viewport)
            self._page = self._context.new_page()

        stats_adapter = _PlaywrightStatsAdapter(self._page)
        self._stats_adapter = stats_adapter
        super().__init__(stats_adapter)
        logger.info("PlaywrightController launched chromium")

    # ------------------------------------------------------------------ #
    # Helpers                                                             #
    # ------------------------------------------------------------------ #
    def _locator(self, by: str, selector: str):
        # .first: Playwright's action methods (click, wait_for, bounding_box)
        # are strict-mode by default and raise if a selector matches more than
        # one element. Selenium's find_element (what Selenium-based
        # BaseController triggers/PyAutoGUIController effectively use) has no
        # such guard -- it silently returns the first DOM match. Real pages
        # routinely have non-unique selectors (e.g. YouTube reuses
        # id="video-title" on every search result row), so to keep this
        # controller's behavior consistent with the rest of the codebase's
        # single-element assumption, always resolve to the first match here.
        if by in (None, "css selector"):
            return self._page.locator(selector).first
        if by == "xpath":
            return self._page.locator(f"xpath={selector}").first
        raise ValueError(
            f"PlaywrightController does not support by={by!r} "
            f"(supported: {_SUPPORTED_BY})"
        )

    # ------------------------------------------------------------------ #
    # Navigation (overrides BaseController.navigate: driver.get -> page.goto)#
    # ------------------------------------------------------------------ #
    def navigate(self, url: str):
        """Navigate to a specified URL"""
        self._page.goto(url)

    def wait(self, seconds: float):
        """Wait for a specified number of seconds.

        Overrides BaseController.wait's plain time.sleep() to also drain
        _PlaywrightStatsAdapter's pending execute_script() requests -- this is
        the main thread, so it's the only place that's actually allowed to
        make those calls while the QoE background thread (VideoStatsLogger)
        blocks waiting for a result. See _PlaywrightStatsAdapter.
        """
        deadline = time.time() + seconds
        while True:
            self._stats_adapter.pump_pending()
            remaining = deadline - time.time()
            if remaining <= 0:
                return
            time.sleep(min(0.2, remaining))

    # ------------------------------------------------------------------ #
    # Actions -- same names/signatures as PyAutoGUIController             #
    # ------------------------------------------------------------------ #
    def click(self, by: str = None, selector: str = None, x: float = None, y: float = None, percentage: float = 0.5):
        """Click on a specified element or coordinates"""
        if by is not None and selector is not None:
            try:
                locator = self._locator(by, selector)
                # bounding_box() only waits for the element to be attached, not
                # visible -- it can return a stale/zero box (or None) while the
                # element is still animating in. wait_for(state="visible") is
                # what Playwright's own page.click() does internally; without
                # it this races YouTube's play-button fade-in and fails.
                locator.wait_for(state="visible", timeout=5000)
                box = locator.bounding_box()
                if box is None:
                    raise ValueError(f"Element not visible: by={by}, selector={selector}")
                locator.click(
                    position={"x": box["width"] * percentage, "y": box["height"] * 0.5},
                    timeout=5000,
                )
                return
            except Exception as e:
                logger.warning(f"Could not click element with by={by}, selector={selector}: {e}")
                # Fall through to use x,y coordinates if available

        if x is not None and y is not None:
            self._page.mouse.click(x, y)
            return

        raise ValueError("Must provide either (by, selector) or (x, y) coordinates")

    def type_text(self, text: str, by: str = None, selector: str = None, x: float = None, y: float = None):
        """Type text into a specified element or at coordinates"""
        self.click(by=by, selector=selector, x=x, y=y)
        self._page.keyboard.press("ControlOrMeta+A")
        self._page.keyboard.press("Delete")
        ## Type the New Text
        self._page.keyboard.type(text, delay=random.uniform(20, 60))

    def move(self, by: str = None, selector: str = None, x: float = None, y: float = None, percentage: float = 0.5):
        """Move to a specified element or coordinates"""
        if by is not None and selector is not None:
            try:
                locator = self._locator(by, selector)
                locator.wait_for(state="visible", timeout=5000)
                box = locator.bounding_box()
                if box is None:
                    raise ValueError(f"Element not visible: by={by}, selector={selector}")
                move_x = box["x"] + box["width"] * percentage
                move_y = box["y"] + box["height"] * 0.5
                self._page.mouse.move(move_x, move_y)
                return
            except Exception as e:
                logger.warning(f"Could not find element with by={by}, selector={selector}: {e}")
                # Fall through to use x,y coordinates if available

        if x is not None and y is not None:
            self._page.mouse.move(x, y)
            return

        raise ValueError("Must provide either (by, selector) or (x, y) coordinates")

    def scroll_to(self, by: str = None, selector: str = None, x: float = None, y: float = None):
        """Scroll to a specified element or coordinates"""
        if by is not None and selector is not None:
            try:
                self._locator(by, selector).scroll_into_view_if_needed(timeout=5000)
                return
            except Exception as e:
                logger.warning(f"Could not scroll to element: {e}, trying coordinates")

        if x is not None and y is not None:
            self._page.mouse.move(x, y)
            return

        raise ValueError("Must provide either (by, selector) or (x, y) coordinates")

    def scroll(self, pixels: int, direction: str, by: str = None, selector: str = None, x: float = None, y: float = None):
        """Scroll the page or a specific element.

        Args:
            pixels: Number of pixels to scroll
            direction: Direction to scroll ("up" or "down")
            by: Locator strategy (optional, if provided will scroll to element first)
            selector: Selector string (optional, if provided will scroll to element first)
            x: X coordinate (optional, if provided will move to coordinates before scrolling)
            y: Y coordinate (optional, if provided will move to coordinates before scrolling)
        """
        if by is not None and selector is not None:
            try:
                self._locator(by, selector).scroll_into_view_if_needed(timeout=5000)
            except Exception as e:
                logger.warning(f"Could not move to element before scrolling: {e}")
                if x is not None and y is not None:
                    self._page.mouse.move(x, y)
        elif x is not None and y is not None:
            self._page.mouse.move(x, y)

        if direction == "up":
            self._page.mouse.wheel(0, -pixels)
        elif direction == "down":
            self._page.mouse.wheel(0, pixels)
        else:
            raise ValueError(f"Invalid direction: {direction}")

    def press_key(self, key: str):
        # Workflows may use PyAutoGUI combo notation like "ctrl+l".
        # Translate each segment through _KEY_ALIASES and rejoin with "+".
        if "+" in key:
            parts = [_KEY_ALIASES.get(p.strip().lower(), p.strip()) for p in key.split("+")]
            self._page.keyboard.press("+".join(parts))
        else:
            self._page.keyboard.press(_KEY_ALIASES.get(key.lower(), key))

    # ------------------------------------------------------------------ #
    # Triggers -- same names/signatures as BaseController, reimplemented  #
    # against Playwright instead of Selenium's WebDriverWait/EC           #
    # ------------------------------------------------------------------ #
    def check_element(self, by: str, selector: str, check_visibility: bool = True, timeout: float = 0.1) -> bool:
        """Check if an element exists and optionally if it's visible."""
        try:
            state = "visible" if check_visibility else "attached"
            self._locator(by, selector).first.wait_for(state=state, timeout=timeout * 1000)
            return True
        except Exception:
            return False

    _START_PAGE_URLS = frozenset({
        "about:blank",
        "chrome://new-tab-page/",
        "chrome://newtab/",
    })

    def check_url(self, url: str) -> bool:
        """Check if the current URL matches the given URL."""
        try:
            current = self._page.url
            if current == url:
                return True
            return current in self._START_PAGE_URLS and url in self._START_PAGE_URLS
        except Exception:
            return False

    def check_text(self, text: str, check_visibility: bool = True, timeout: float = 0.1) -> bool:
        """Check if text exists on the page and optionally if it's visible."""
        try:
            # Same normalize-space XPath match BaseController.check_text uses,
            # so this trigger behaves identically regardless of backend.
            escaped = text.replace('"', '\\"')
            locator = self._page.locator(f'xpath=//*[normalize-space(text())="{escaped}"]')
            state = "visible" if check_visibility else "attached"
            locator.first.wait_for(state=state, timeout=timeout * 1000)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # Lifecycle                                                          #
    # ------------------------------------------------------------------ #
    def quit(self):
        """Quit the browser (not an action - used for cleanup)"""
        if self.stats_logger:
            self.stats_logger.stop()
        try:
            if self._context is not None:
                self._context.close()
            if self._browser is not None:
                self._browser.close()
        finally:
            if self._playwright is not None:
                self._playwright.stop()
