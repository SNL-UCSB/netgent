"""
Desktop controller.

NetGent's orchestrator (the LangGraph state machine, state synthesis and web
agent) runs inside Docker, but a container cannot touch the host's macOS
accessibility API or move its real mouse/keyboard. This controller keeps the
orchestrator in the container and forwards every *observation* and *action* to a
small host bridge (``netgent_hostbridge``) that runs natively on the user's Mac.

It is a drop-in ``BaseController``: it registers the same actions and triggers,
so the program controller, state executor, state synthesis and web agent are
completely unaware they are driving a desktop application rather than a browser.

Design mirrors the browser path exactly:

    DOM tree                <->  macOS accessibility (AX) tree
    build_dom.js elements    <->  AX elements (role/title/value + AXPosition/AXSize)
    CSS selector / xpath     <->  AX locator (role-path re-resolved on the host)
    get_element_coordinates  <->  AX coordinates (already global, no drift)
    PyAutoGUI click at (x,y)  ->  PyAutoGUI click at (x,y) on the host

Because the element list and coordinates come from the AX tree (not a guessed
screenshot), and because the bridge activates + scopes to the target app before
every observation/action, the agent never clicks outside the window and is not
influenced by background applications.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any, Optional

from .base import BaseController, ELEMENT_ACTIONS
from ..registry import action, trigger

logger = logging.getLogger(__name__)

DEFAULT_HOSTBRIDGE_URL = os.environ.get(
    "NETGENT_HOSTBRIDGE_URL", "http://host.docker.internal:8765"
)


class HostBridgeError(RuntimeError):
    """Raised when the host bridge is unreachable or returns an error."""


class DesktopController(BaseController):
    """A BaseController that drives macOS desktop apps via the host bridge."""

    def __init__(self, bridge_url: Optional[str] = None, target_app: Optional[str] = None,
                 request_timeout: float = 60.0):
        # Intentionally do NOT call super().__init__: there is no Selenium driver
        # and no video stats logger in the desktop domain.
        self.driver = None
        self.stats_logger = None
        self.bridge_url = (bridge_url or DEFAULT_HOSTBRIDGE_URL).rstrip("/")
        # The application all observations/actions are scoped to. Set by the
        # open_application / activate_application actions; the bridge also honors
        # it so background apps never pollute the AX tree or steal clicks.
        self.target_app = target_app
        self.request_timeout = request_timeout
        logger.info("DesktopController using host bridge at %s", self.bridge_url)

    # ------------------------------------------------------------------ #
    # Host bridge transport (stdlib only)                                #
    # ------------------------------------------------------------------ #
    def _post(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        url = f"{self.bridge_url}{path}"
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            raise HostBridgeError(f"Host bridge {path} failed ({e.code}): {detail}") from e
        except urllib.error.URLError as e:
            raise HostBridgeError(
                f"Could not reach host bridge at {url}: {e.reason}. "
                f"Is 'python -m netgent_hostbridge' running on the host, and is "
                f"NETGENT_HOSTBRIDGE_URL correct?"
            ) from e
        if not data.get("ok", False):
            raise HostBridgeError(f"Host bridge {path} error: {data.get('error')}")
        return data

    def _with_app(self, payload: dict) -> dict:
        """Attach the current target app so the bridge scopes correctly."""
        if self.target_app and "app" not in payload:
            payload["app"] = self.target_app
        return payload

    def _run_action(self, name: str, params: dict) -> Any:
        data = self._post("/action", self._with_app({"action": name, "params": params}))
        return data.get("result")

    def _check_trigger(self, ttype: str, params: dict) -> bool:
        data = self._post("/trigger", self._with_app({"type": ttype, "params": params}))
        return bool(data.get("result", False))

    # ------------------------------------------------------------------ #
    # Application-management actions (the desktop analogue of navigate)  #
    # ------------------------------------------------------------------ #
    @action()
    def open_application(self, name: str):
        """Launch a desktop application by name or bundle id.

        Uses macOS launch services (``open -a``, the same mechanism Spotlight
        uses) -- it does NOT navigate Finder. Sets this app as the scoped target
        for subsequent observations/actions.
        """
        self.target_app = name
        return self._run_action("open_application", {"name": name})

    @action()
    def activate_application(self, name: str):
        """Bring an already-running application to the foreground and scope to it."""
        self.target_app = name
        return self._run_action("activate_application", {"name": name})

    @action()
    def navigate(self, url: str):
        """Desktop domain has no URL navigation; open the named application instead."""
        # Kept for interface parity. Treat the argument as an application name so
        # generic tooling degrades gracefully.
        return self.open_application(url)

    @action()
    def hotkey(self, keys: str):
        """Press a chord of keys together, e.g. "command,space" or "command,n"."""
        parts = [k.strip() for k in keys.split(",") if k.strip()]
        return self._run_action("hotkey", {"keys": parts})

    # QoE video stats logging is browser-only; make these harmless no-ops so a
    # workflow that references them does not crash on the desktop path.
    @action()
    def start_stats_logging(self, out_path: str = "netgent_video_stats.jsonl", interval: float = 2.0):
        """No-op on desktop (video 'Stats for Nerds' logging is browser-only)."""
        logger.info("start_stats_logging is a no-op in desktop mode")
        return out_path

    @action()
    def stop_stats_logging(self):
        """No-op on desktop (video 'Stats for Nerds' logging is browser-only)."""
        logger.info("stop_stats_logging is a no-op in desktop mode")

    # ------------------------------------------------------------------ #
    # Element-interaction actions (resolved against the live AX tree on   #
    # the host, exactly like the browser re-resolves CSS selectors)       #
    # ------------------------------------------------------------------ #
    def click(self, by: str = None, selector: str = None, x: float = None, y: float = None, percentage: float = 0.5):
        return self._run_action("click", {
            "by": by, "selector": selector, "x": x, "y": y, "percentage": percentage,
        })

    def type_text(self, text: str, by: str = None, selector: str = None, x: float = None, y: float = None):
        return self._run_action("type", {
            "text": text, "by": by, "selector": selector, "x": x, "y": y,
        })

    def move(self, by: str = None, selector: str = None, x: float = None, y: float = None, percentage: float = 0.5):
        return self._run_action("move", {
            "by": by, "selector": selector, "x": x, "y": y, "percentage": percentage,
        })

    def scroll_to(self, by: str = None, selector: str = None, x: float = None, y: float = None):
        return self._run_action("scroll_to", {"by": by, "selector": selector, "x": x, "y": y})

    def scroll(self, pixels: int, direction: str, by: str = None, selector: str = None, x: float = None, y: float = None):
        return self._run_action("scroll", {
            "pixels": pixels, "direction": direction,
            "by": by, "selector": selector, "x": x, "y": y,
        })

    def press_key(self, key: str):
        return self._run_action("press_key", {"key": key})

    # ------------------------------------------------------------------ #
    # Triggers (AX-tree based)                                            #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _negate(result: bool, negate: bool) -> bool:
        """Apply an optional ``negate`` flag to a trigger result.

        Negation is the key primitive for multi-state desktop workflows: it lets
        a state trigger on the *absence* of something (e.g. "Maps is not yet
        frontmost", "the results/Directions button has not appeared yet"), so a
        state stops matching once its work is done and the next state takes over.
        """
        return (not result) if negate else result

    @trigger(name="element")
    def check_element(self, by: str, selector: str, check_visibility: bool = True,
                      timeout: float = 0.1, negate: bool = False) -> bool:
        """Check that an accessibility element matching (by, selector) exists.

        With ``negate: true`` the check is inverted (element is *absent*).
        """
        result = self._check_trigger("element", {
            "by": by, "selector": selector,
            "check_visibility": check_visibility, "timeout": timeout,
        })
        return self._negate(result, negate)

    @trigger(name="text")
    def check_text(self, text: str, check_visibility: bool = True,
                   timeout: float = 0.1, negate: bool = False) -> bool:
        """Check that the given text is present in the app's AX tree (invert with ``negate``)."""
        result = self._check_trigger("text", {
            "text": text, "check_visibility": check_visibility, "timeout": timeout,
        })
        return self._negate(result, negate)

    @trigger(name="app")
    def check_app(self, name: str, negate: bool = False) -> bool:
        """Check that the named application is running/open (invert with ``negate``).

        Uses "is it running" rather than "is it frontmost", so this stays stable
        regardless of which window the operator has focused.
        """
        return self._negate(self._check_trigger("app", {"name": name}), negate)

    @trigger(name="window")
    def check_window(self, title: str, negate: bool = False) -> bool:
        """Check that the target app has a window titled ``title`` (invert with ``negate``)."""
        return self._negate(self._check_trigger("window", {"title": title}), negate)

    @trigger(name="url")
    def check_url(self, url: str, negate: bool = False) -> bool:
        """Desktop reinterpretation: true when ``url`` names the frontmost app."""
        return self._negate(self._check_trigger("app", {"name": url}), negate)

    # ------------------------------------------------------------------ #
    # Perception layer (overrides the browser/DOM implementations)        #
    # ------------------------------------------------------------------ #
    def snapshot(self) -> tuple[dict, str, str]:
        data = self._post("/snapshot", self._with_app({"include_screenshot": True}))
        elements = data.get("elements", {}) or {}
        prompt = data.get("prompt", "") or "No accessibility elements found."
        screenshot = data.get("screenshot", "") or ""
        return elements, prompt, screenshot

    def get_context(self) -> dict:
        data = self._post("/context", self._with_app({}))
        ctx = data.get("context", {}) or {}
        # Present app+window under the same url/title keys the agent expects.
        return {
            "url": ctx.get("app", self.target_app or ""),
            "title": ctx.get("title", ""),
        }

    def build_trigger_candidates(self) -> dict:
        data = self._post("/triggers", self._with_app({}))
        return data.get("candidates", {}) or {}

    def resolve_element_action(self, action_output: dict, elements: dict) -> dict:
        """Map an mmid-referencing action to a replayable action.

        The durable locator is the element's AX path (re-resolved on the host at
        replay time); absolute screen coordinates from the snapshot are attached
        as a fallback. This is the desktop twin of the browser's selector logic.
        """
        action_name = action_output.get("action")
        mmid = action_output.get("mmid")
        params = dict(action_output.get("params", {}))

        if mmid is not None and action_name in ELEMENT_ACTIONS and elements:
            element_data = elements.get(str(mmid))
            if element_data:
                locator = element_data.get("ax_locator")
                if locator is None:
                    # Fall back to composing a locator from role/title/path.
                    locator = {
                        "path": element_data.get("ax_path"),
                        "role": element_data.get("role"),
                        "title": element_data.get("title"),
                    }
                params["by"] = "ax"
                params["selector"] = json.dumps(locator)
                abs_x, abs_y = self.get_element_coordinates(
                    element_data.get("x", 0),
                    element_data.get("y", 0),
                    element_data.get("width", 0),
                    element_data.get("height", 0),
                    percentage=0.5,
                )
                params["x"] = abs_x
                params["y"] = abs_y

        return {"type": action_name, "params": params}

    def get_element_coordinates(self, x, y, width, height, percentage=0.5):
        """AX coordinates are already global (top-left origin); just center them."""
        x = x or 0
        y = y or 0
        width = width or 0
        height = height or 0
        return x + width * percentage, y + height * 0.5

    # ------------------------------------------------------------------ #
    # Lifecycle                                                          #
    # ------------------------------------------------------------------ #
    def quit(self):
        """Nothing to tear down in the container; leave host apps untouched."""
        return None
