"""
Host-side actuator: turns NetGent actions into real mouse/keyboard events.

Coordinates come from the live AX tree (``ax.resolve_locator``), never from a
guessed screenshot. Before every interaction the target application is brought
to the foreground and the resolved point is validated against the screen bounds,
which is what stops clicks from landing outside the window or in a background
app.

Runs natively on the host. Requires ``pyautogui`` (and, for AX resolution,
``atomacos``).
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import Any, Optional

from . import ax

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Keyboard via AppleScript / System Events                                    #
#                                                                             #
# PyAutoGUI's keyboard on macOS uses a broken/deprecated Quartz key mapping   #
# that mis-sends many keys and can leave the 'fn' (Globe) modifier asserted,  #
# which triggers OS behaviors (Notification Center, emoji picker, ...).       #
# System Events keystrokes type into the focused element reliably, trigger    #
# the app's own input handling, and have none of those problems. We keep      #
# PyAutoGUI only for the mouse.                                               #
# --------------------------------------------------------------------------- #

# AppleScript key codes for non-character keys.
_KEYCODES = {
    "enter": 36, "return": 36, "tab": 48, "space": 49, " ": 49,
    "delete": 51, "backspace": 51, "forwarddelete": 117,
    "esc": 53, "escape": 53,
    "left": 123, "right": 124, "down": 125, "up": 126,
    "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
}

# Modifier aliases -> AppleScript "... down" clauses.
_MODIFIERS = {
    "command": "command down", "cmd": "command down", "⌘": "command down",
    "control": "control down", "ctrl": "control down", "⌃": "control down",
    "option": "option down", "opt": "option down", "alt": "option down", "⌥": "option down",
    "shift": "shift down", "⇧": "shift down",
}


def _osascript(script: str):
    subprocess.run(["osascript", "-e", script], check=False)


def _as_str(s: str) -> str:
    """Escape a string for embedding inside an AppleScript double-quoted literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def as_type_text(text: str):
    """Type literal text into the focused element via System Events."""
    _osascript(f'tell application "System Events" to keystroke "{_as_str(str(text))}"')


def as_select_all_and_delete():
    _osascript(
        'tell application "System Events"\n'
        '  keystroke "a" using command down\n'
        '  key code 51\n'
        'end tell'
    )


def as_press_key(key: str):
    """Press a single key (special keys by code, otherwise as a keystroke)."""
    k = str(key).strip().lower()
    if k in _KEYCODES:
        _osascript(f'tell application "System Events" to key code {_KEYCODES[k]}')
    else:
        _osascript(f'tell application "System Events" to keystroke "{_as_str(key)}"')


def as_hotkey(keys):
    """Press a chord such as ["command", "n"] via System Events."""
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split(",") if k.strip()]
    mods, main = [], None
    for k in keys:
        kl = k.strip().lower()
        if kl in _MODIFIERS:
            mods.append(_MODIFIERS[kl])
        else:
            main = k.strip()
    using = ""
    if mods:
        using = " using {" + ", ".join(dict.fromkeys(mods)) + "}"
    if main is None:
        return
    ml = main.lower()
    if ml in _KEYCODES:
        _osascript(f'tell application "System Events" to key code {_KEYCODES[ml]}{using}')
    else:
        _osascript(f'tell application "System Events" to keystroke "{_as_str(main)}"{using}')

try:
    import pyautogui  # type: ignore
    pyautogui.FAILSAFE = False
except Exception as e:  # pragma: no cover
    pyautogui = None
    _PYAUTOGUI_IMPORT_ERROR = e
else:
    _PYAUTOGUI_IMPORT_ERROR = None


def _require_pyautogui():
    if pyautogui is None:
        raise RuntimeError(
            "pyautogui is not available on the host. Install the host-bridge "
            "requirements. Original import error: %s" % _PYAUTOGUI_IMPORT_ERROR
        )


def bezier(n, cp1=(0.25, 0.1), cp2=(0.75, 0.9)):
    """Smooth easing for human-like mouse movement (matches the browser path)."""
    if not 0.0 <= n <= 1.0:
        raise ValueError("Argument must be between 0.0 and 1.0.")
    t, u = n, 1 - n
    y = (3 * u ** 2 * t * cp1[1] + 3 * u * t ** 2 * cp2[1] + t ** 3)
    return max(0.0, min(1.0, y))


def _validate_on_screen(x: float, y: float):
    _require_pyautogui()
    w, h = pyautogui.size()
    if not (0 <= x <= w and 0 <= y <= h):
        raise ValueError(
            f"Refusing to act at ({x:.0f}, {y:.0f}): outside screen bounds "
            f"({w}x{h}). The element could not be located in the target window."
        )


def _resolve_xy(app_ref, by, selector, x, y, percentage=0.5) -> tuple[float, float]:
    """Resolve target coordinates, preferring a fresh AX lookup over stale x/y."""
    if by == "ax" and selector:
        try:
            locator = json.loads(selector) if isinstance(selector, str) else selector
        except Exception:
            locator = None
        if locator and app_ref is not None:
            info = ax.resolve_locator(app_ref, locator)
            if info is not None and info["width"] > 0 and info["height"] > 0:
                return (info["x"] + info["width"] * percentage,
                        info["y"] + info["height"] * 0.5)
            logger.warning("AX locator did not resolve; falling back to coordinates")
    if x is not None and y is not None:
        return float(x), float(y)
    raise ValueError("Could not resolve a target: no AX locator match and no (x, y).")


class Actuator:
    """Executes actions for one target application."""

    def __init__(self):
        self.target_app: Optional[str] = None
        self.app_ref = None

    # -- app management --------------------------------------------------- #
    def set_target(self, name: Optional[str]):
        if name and name != self.target_app:
            self.target_app = name
            try:
                self.app_ref = ax.get_app_ref(name)
            except Exception:
                self.app_ref = None
        elif name:
            self.target_app = name

    def ensure_app_ref(self):
        if self.app_ref is None and self.target_app:
            self.app_ref = ax.get_app_ref(self.target_app)
        return self.app_ref

    def _bring_to_front(self):
        if self.target_app:
            try:
                self.app_ref = ax.activate_app(self.target_app, wait=0.4)
            except Exception as e:
                logger.warning("Could not activate %s: %s", self.target_app, e)

    def open_application(self, name: str):
        # Set the target first so that even if attaching is briefly slow (a cold
        # launch), later observation/action cycles re-attach via ensure_app_ref
        # instead of the whole run crashing. launch_app returns None (not raise)
        # if the app hasn't registered in time.
        self.target_app = name
        self.app_ref = ax.launch_app(name)
        return {"app": name, "attached": self.app_ref is not None}

    def activate_application(self, name: str):
        self.target_app = name
        self.app_ref = ax.activate_app(name)
        return {"app": name}

    # -- interactions ----------------------------------------------------- #
    def click(self, by=None, selector=None, x=None, y=None, percentage=0.5):
        _require_pyautogui()
        self._bring_to_front()
        cx, cy = _resolve_xy(self.app_ref, by, selector, x, y, percentage)
        _validate_on_screen(cx, cy)
        pyautogui.click(cx, cy, duration=0.5, tween=lambda n: bezier(n))
        return {"x": cx, "y": cy}

    def move(self, by=None, selector=None, x=None, y=None, percentage=0.5):
        _require_pyautogui()
        self._bring_to_front()
        cx, cy = _resolve_xy(self.app_ref, by, selector, x, y, percentage)
        _validate_on_screen(cx, cy)
        pyautogui.moveTo(cx, cy, duration=0.5, tween=lambda n: bezier(n))
        return {"x": cx, "y": cy}

    def type_text(self, text, by=None, selector=None, x=None, y=None):
        _require_pyautogui()
        self._bring_to_front()
        # Focus the field first if we were given a target.
        if (by is not None and selector is not None) or (x is not None and y is not None):
            cx, cy = _resolve_xy(self.app_ref, by, selector, x, y)
            _validate_on_screen(cx, cy)
            pyautogui.click(cx, cy, duration=0.4, tween=lambda n: bezier(n))
        # Clear existing content, then type -- both via System Events (reliable
        # on macOS; avoids PyAutoGUI's broken key mapping / stuck 'fn' modifier).
        as_select_all_and_delete()
        time.sleep(0.1)
        as_type_text(text)
        return {"typed": text}

    def scroll(self, pixels, direction, by=None, selector=None, x=None, y=None):
        _require_pyautogui()
        self._bring_to_front()
        if (by is not None and selector is not None) or (x is not None and y is not None):
            try:
                cx, cy = _resolve_xy(self.app_ref, by, selector, x, y)
                pyautogui.moveTo(cx, cy, duration=0.2)
            except Exception:
                pass
        amount = int(pixels)
        if direction == "up":
            pyautogui.scroll(amount)
        elif direction == "down":
            pyautogui.scroll(-amount)
        else:
            raise ValueError(f"Invalid direction: {direction}")
        return {"scrolled": amount, "direction": direction}

    def scroll_to(self, by=None, selector=None, x=None, y=None):
        _require_pyautogui()
        self._bring_to_front()
        cx, cy = _resolve_xy(self.app_ref, by, selector, x, y)
        pyautogui.moveTo(cx, cy, duration=0.2)
        return {"x": cx, "y": cy}

    def press_key(self, key):
        self._bring_to_front()
        as_press_key(key)
        return {"key": key}

    def hotkey(self, keys):
        self._bring_to_front()
        as_hotkey(keys)
        return {"keys": keys}

    # -- dispatch --------------------------------------------------------- #
    def execute(self, action: str, params: dict) -> Any:
        params = dict(params or {})
        handler = {
            "open_application": lambda p: self.open_application(p["name"]),
            "activate_application": lambda p: self.activate_application(p["name"]),
            "navigate": lambda p: self.open_application(p.get("url") or p.get("name")),
            "click": lambda p: self.click(**p),
            "type": lambda p: self.type_text(**p),
            "move": lambda p: self.move(**p),
            "scroll": lambda p: self.scroll(**p),
            "scroll_to": lambda p: self.scroll_to(**p),
            "press_key": lambda p: self.press_key(**p),
            "hotkey": lambda p: self.hotkey(**p),
        }.get(action)
        if handler is None:
            raise KeyError(f"Unknown desktop action: {action}")
        return handler(params)
