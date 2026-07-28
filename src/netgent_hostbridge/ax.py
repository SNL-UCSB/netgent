"""
macOS Accessibility (AX) tree perception for the host bridge.

This module is the desktop analogue of the browser's ``build_dom.js`` +
``parse_dom``: it walks the accessibility tree of a *single* target application
and produces a flat list of interactable elements, each with a stable role-path
locator and its **absolute screen** position/size (AX reports global,
top-left-origin coordinates in points, which is exactly what PyAutoGUI expects
on macOS -- so there is no coordinate guessing and no window-offset math).

Scoping every walk to one application is what prevents the agent from being
influenced by background apps or clicking outside the target window.

Runs natively on the host (never in Docker). Requires ``atomacos`` and
``pyobjc`` and the Accessibility permission for the process running it.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import atomacos  # type: ignore
except Exception as e:  # pragma: no cover - only importable on macOS host
    atomacos = None
    _ATOMACOS_IMPORT_ERROR = e
else:
    _ATOMACOS_IMPORT_ERROR = None

try:
    from AppKit import NSWorkspace  # type: ignore
except Exception:  # pragma: no cover
    NSWorkspace = None


# Roles that represent something the agent can meaningfully act on. Static text
# is included so the agent can target labels/links rendered as text, mirroring
# how the DOM path exposes text-bearing elements.
INTERACTABLE_ROLES = {
    "AXButton", "AXMenuButton", "AXPopUpButton", "AXMenuItem", "AXMenuBarItem",
    "AXTextField", "AXTextArea", "AXComboBox", "AXSearchField",
    "AXCheckBox", "AXRadioButton", "AXSlider", "AXIncrementor", "AXStepper",
    "AXLink", "AXTabGroup", "AXTab", "AXCell", "AXRow", "AXDisclosureTriangle",
    "AXStaticText", "AXImage",
}

MAX_ELEMENTS = 400
MAX_DEPTH = 40


def _require_atomacos():
    if atomacos is None:
        raise RuntimeError(
            "atomacos is not available on the host. Install the host-bridge "
            f"requirements (pip install -r src/netgent_hostbridge/requirements.txt). "
            f"Original import error: {_ATOMACOS_IMPORT_ERROR}"
        )


# --------------------------------------------------------------------------- #
# Attribute coercion helpers (atomacos returns different shapes by version)     #
# --------------------------------------------------------------------------- #
def _attr(el: Any, name: str, default=None):
    try:
        val = getattr(el, name)
        return val if val is not None else default
    except Exception:
        return default


def _num(v, default=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _point(v) -> tuple[float, float]:
    """Coerce an AXPosition value into (x, y)."""
    if v is None:
        return 0.0, 0.0
    for xa, ya in (("x", "y"),):
        if hasattr(v, xa) and hasattr(v, ya):
            return _num(getattr(v, xa)), _num(getattr(v, ya))
    if isinstance(v, (tuple, list)) and len(v) >= 2:
        return _num(v[0]), _num(v[1])
    # Some versions stringify as "<NSPoint x=.. y=..>" or "x=.. y=.."
    try:
        s = str(v)
        import re
        m = re.search(r"x[=:\s]+(-?[\d.]+).*?y[=:\s]+(-?[\d.]+)", s)
        if m:
            return float(m.group(1)), float(m.group(2))
    except Exception:
        pass
    return 0.0, 0.0


def _size(v) -> tuple[float, float]:
    """Coerce an AXSize value into (width, height)."""
    if v is None:
        return 0.0, 0.0
    if hasattr(v, "width") and hasattr(v, "height"):
        return _num(v.width), _num(v.height)
    if isinstance(v, (tuple, list)) and len(v) >= 2:
        return _num(v[0]), _num(v[1])
    try:
        s = str(v)
        import re
        m = re.search(r"w(?:idth)?[=:\s]+(-?[\d.]+).*?h(?:eight)?[=:\s]+(-?[\d.]+)", s)
        if m:
            return float(m.group(1)), float(m.group(2))
    except Exception:
        pass
    return 0.0, 0.0


def _label(el: Any) -> str:
    """Best human-readable label for an element (title/value/desc/help)."""
    for name in ("AXTitle", "AXValue", "AXDescription", "AXHelp",
                 "AXPlaceholderValue", "AXRoleDescription"):
        v = _attr(el, name)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


# --------------------------------------------------------------------------- #
# Application lookup / lifecycle                                               #
# --------------------------------------------------------------------------- #
def _looks_like_bundle_id(name: str) -> bool:
    return name.count(".") >= 2 and " " not in name


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it -- still alive.
        return True
    except Exception:
        return False


def _find_pid_nsworkspace(name: str) -> Optional[int]:
    if NSWorkspace is None:
        return None
    try:
        for app in NSWorkspace.sharedWorkspace().runningApplications():
            local_name = str(app.localizedName() or "")
            bundle_id = str(app.bundleIdentifier() or "")
            if name == local_name or name == bundle_id:
                pid = int(app.processIdentifier())
                # NSWorkspace's list is a snapshot that can go stale in this
                # process (no NSRunLoop pumping it), so a match here may
                # reference a pid that has since quit. Verify liveness before
                # trusting it -- otherwise an app that was open earlier and
                # has since been quit keeps reading as "running" forever.
                if _pid_is_alive(pid):
                    return pid
    except Exception:
        pass
    return None


def _find_pid_system_events(name: str) -> Optional[int]:
    """Fresh pid lookup via System Events (osascript).

    Unlike NSWorkspace.runningApplications(), which can return a STALE cached
    list in a process without an NSRunLoop (so an app launched after the bridge
    started never shows up), this queries the live process list every call --
    essential for detecting an app we just opened. Matches by process name.
    """
    try:
        script = (
            'tell application "System Events" to '
            f'get unix id of (first process whose name is "{name}")'
        )
        out = subprocess.run(["osascript", "-e", script],
                             capture_output=True, text=True, timeout=5)
        s = (out.stdout or "").strip()
        if s.isdigit():
            return int(s)
    except Exception:
        pass
    return None


def _find_pid(name: str) -> Optional[int]:
    """Resolve a running application's pid by name or bundle id.

    Tries NSWorkspace first (fast, and handles bundle-id inputs), then falls
    back to a fresh System Events query so apps launched *after* the bridge
    started are still detected (NSWorkspace's list can be stale here).
    """
    pid = _find_pid_nsworkspace(name)
    if pid is not None:
        return pid
    return _find_pid_system_events(name)


def is_app_running(name: str) -> bool:
    """True if an application with this localized name or bundle id is running.

    This is the right signal for an "is the app open?" trigger: it stays true
    once the app is launched regardless of which app is *frontmost*. (Using
    frontmost here is fragile -- e.g. it flips false the moment the operator
    focuses their terminal, causing an "open the app" state to fire repeatedly.)
    """
    return _find_pid(name) is not None


def get_app_ref(name: str, retries: int = 3, retry_delay: float = 1.0):
    """Return an atomacos reference to a running application by name or bundle id.

    Retries briefly (the app may still be registering with launch services /
    the accessibility subsystem right after being opened) and, if atomacos's
    own name-lookup helpers error out, falls back to resolving the pid via
    NSWorkspace ourselves and attaching through that -- this sidesteps a
    TypeError some atomacos versions raise internally for perfectly valid,
    running applications.
    """
    _require_atomacos()
    last_err = None
    for attempt in range(retries):
        if _looks_like_bundle_id(name):
            try:
                return atomacos.getAppRefByBundleId(name)
            except Exception as e:
                last_err = e
        try:
            return atomacos.getAppRefByLocalizedName(name)
        except Exception as e:
            last_err = e

        pid = _find_pid(name)
        if pid is not None and hasattr(atomacos, "getAppRefByPid"):
            try:
                return atomacos.getAppRefByPid(pid)
            except Exception as e:
                last_err = e

        if attempt < retries - 1:
            time.sleep(retry_delay)

    raise RuntimeError(f"Could not attach to application '{name}': {last_err}")


def launch_app(name: str, wait: float = 1.0, timeout: float = 25.0):
    """Launch an application by name or bundle id (via `open`) and scope to it.

    A cold launch can take several seconds to appear in the running-apps /
    accessibility lists, so we POLL until the app registers (up to ``timeout``)
    rather than waiting a fixed interval, then give the AX tree a moment to
    populate. Returns None if it never registers (the caller keeps the target
    set and re-attaches on a later cycle rather than crashing).
    """
    if _looks_like_bundle_id(name):
        subprocess.run(["open", "-b", name], check=False)
    else:
        subprocess.run(["open", "-a", name], check=False)

    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_app_running(name):
            break
        time.sleep(0.5)
    # Let the window/AX hierarchy finish building before we attach.
    time.sleep(wait)
    try:
        ref = get_app_ref(name, retries=6, retry_delay=1.0)
    except Exception as e:
        logger.warning("Launched '%s' but could not attach yet: %s", name, e)
        return None

    # Being 'running' is not enough: the window (and its search field, buttons,
    # etc.) render a moment later. Wait until the app actually has a window with
    # some interactable content, so the very next state's element checks don't
    # observe an empty tree and miss.
    wdeadline = time.time() + 10.0
    while time.time() < wdeadline:
        try:
            windows = _attr(ref, "AXWindows", []) or []
            if windows and walk_app(ref):
                break
        except Exception:
            pass
        time.sleep(0.5)
    return ref


def activate_app(name: str, wait: float = 1.0):
    """Bring an application to the foreground (launching it if needed)."""
    ref = None
    try:
        ref = get_app_ref(name)
    except Exception:
        return launch_app(name, wait=max(wait, 3.0))
    try:
        ref.activate()
    except Exception:
        # Fall back to `open`, which also activates.
        if _looks_like_bundle_id(name):
            subprocess.run(["open", "-b", name], check=False)
        else:
            subprocess.run(["open", "-a", name], check=False)
    time.sleep(wait)
    return ref


def frontmost_app() -> dict:
    """Return {name, bundle_id} of the current frontmost application."""
    if NSWorkspace is None:
        return {"name": "", "bundle_id": ""}
    try:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return {
            "name": str(app.localizedName() or ""),
            "bundle_id": str(app.bundleIdentifier() or ""),
        }
    except Exception:
        return {"name": "", "bundle_id": ""}


# --------------------------------------------------------------------------- #
# Tree walking                                                                #
# --------------------------------------------------------------------------- #
def _walk(el: Any, path: list, out: list, depth: int):
    # NOTE: we deliberately do NOT dedup nodes by id(). atomacos returns fresh
    # wrapper objects on each attribute access, so their id()s get recycled as
    # earlier wrappers are garbage-collected -- an id()-based "seen" set then
    # wrongly skips not-yet-visited elements, causing perception/triggers to
    # miss real controls. AX hierarchies are trees, so depth + the element cap
    # are sufficient bounds without a visited set.
    if depth > MAX_DEPTH or len(out) >= MAX_ELEMENTS:
        return

    role = _attr(el, "AXRole", "") or ""
    x, y = _point(_attr(el, "AXPosition"))
    w, h = _size(_attr(el, "AXSize"))
    label = _label(el)
    enabled = bool(_attr(el, "AXEnabled", True))

    # Record actionable, on-screen, sized elements.
    if role in INTERACTABLE_ROLES and w > 0 and h > 0:
        out.append({
            "role": role,
            "title": label,
            "enabled": enabled,
            "x": x, "y": y, "width": w, "height": h,
            "ax_path": list(path),
        })

    children = _attr(el, "AXChildren", []) or []
    # Track sibling index per role so the path is stable for re-resolution.
    role_counts: dict = {}
    for child in children:
        try:
            crole = _attr(child, "AXRole", "") or "AXUnknown"
            idx = role_counts.get(crole, 0)
            role_counts[crole] = idx + 1
            _walk(child, path + [[crole, idx]], out, depth + 1)
        except Exception:
            continue


def walk_app(app_ref) -> list:
    """Return a flat list of interactable element dicts for an application."""
    out: list = []
    try:
        _walk(app_ref, [], out, 0)
    except Exception as e:
        logger.warning("AX walk failed: %s", e)
    return out


def build_snapshot(app_ref) -> tuple[dict, str]:
    """Return (elements_dict, prompt_string) keyed by mmid, like parse_dom."""
    elements = walk_app(app_ref)
    elements_dict: dict = {}
    prompt_lines: list[str] = []
    for mmid, el in enumerate(elements):
        locator = {"path": el["ax_path"], "role": el["role"], "title": el["title"]}
        elements_dict[str(mmid)] = {
            "role": el["role"],
            "title": el["title"],
            "ax_path": el["ax_path"],
            "ax_locator": locator,
            "x": el["x"], "y": el["y"],
            "width": el["width"], "height": el["height"],
        }
        label = el["title"] if el["title"] else "<empty/>"
        state = "" if el["enabled"] else " (disabled)"
        prompt_lines.append(f"{mmid} (<{el['role']}/>){state}: {label}")
    prompt = "\n".join(prompt_lines) if prompt_lines else "No accessibility elements found."
    return elements_dict, prompt


# --------------------------------------------------------------------------- #
# Locator resolution (replay): re-find an element in the *live* tree          #
# --------------------------------------------------------------------------- #
def resolve_locator(app_ref, locator: dict) -> Optional[dict]:
    """Re-resolve an AX locator against the current tree; return element info.

    Tries the exact role-path first (robust to the window moving), then falls
    back to matching role+title anywhere in the tree.
    """
    path = locator.get("path")
    if path:
        el = _follow_path(app_ref, path)
        if el is not None:
            return _element_geometry(el)

    role = locator.get("role")
    title = locator.get("title")
    if role:
        match = _find_by_role_title(app_ref, role, title)
        if match is not None:
            return _element_geometry(match)
    return None


def _follow_path(el: Any, path: list):
    cur = el
    for step in path:
        role, idx = step[0], step[1]
        children = _attr(cur, "AXChildren", []) or []
        same_role = [c for c in children if (_attr(c, "AXRole", "") or "AXUnknown") == role]
        if idx < 0 or idx >= len(same_role):
            return None
        cur = same_role[idx]
    return cur


def _find_by_role_title(el: Any, role: str, title: Optional[str], depth: int = 0):
    # No id()-based visited set (see _walk): atomacos recycles wrapper id()s,
    # which would wrongly prune real elements. Depth bounds the acyclic tree.
    if depth > MAX_DEPTH:
        return None
    if (_attr(el, "AXRole", "") or "") == role:
        if not title or _label(el) == title:
            return el
    for child in (_attr(el, "AXChildren", []) or []):
        found = _find_by_role_title(child, role, title, depth + 1)
        if found is not None:
            return found
    return None


def _element_geometry(el: Any) -> dict:
    x, y = _point(_attr(el, "AXPosition"))
    w, h = _size(_attr(el, "AXSize"))
    return {
        "role": _attr(el, "AXRole", ""),
        "title": _label(el),
        "x": x, "y": y, "width": w, "height": h,
        "center_x": x + w / 2.0, "center_y": y + h / 2.0,
    }


# --------------------------------------------------------------------------- #
# Trigger checks                                                              #
# --------------------------------------------------------------------------- #
def text_present(app_ref, text: str) -> bool:
    for el in walk_app(app_ref):
        if text and text in (el.get("title") or ""):
            return True
    return False


def _title_matches(want: str, have: str) -> bool:
    """Tolerant label comparison for triggers.

    Accessibility labels vary slightly across OS versions / app states (extra
    whitespace, case, a value appended to a placeholder), so exact equality is
    too brittle for a *presence* check. We normalize whitespace/case and accept
    either string containing the other.
    """
    w = " ".join(want.split()).lower()
    h = " ".join(have.split()).lower()
    if not w:
        return True
    return w == h or w in h or h in w


def element_present(app_ref, by: str, selector: str, check_visibility: bool = True) -> bool:
    """(by, selector) semantics for desktop:

    - by == "ax": selector is a JSON locator ({path, role, title}).
    - by in ("role", "ax role"): selector is a role, optionally "AXRole:Title".
    """
    if by == "ax":
        import json
        try:
            locator = json.loads(selector)
        except Exception:
            logger.warning("element_present: bad selector JSON: %r", selector)
            return False
        role = locator.get("role")
        title = (locator.get("title") or "").strip()
        # Match against the SAME walk that /snapshot and the agent use, so a
        # trigger sees exactly what perception sees. (Previously this used a
        # separate resolver that could disagree with the snapshot.)
        if role:
            walked = walk_app(app_ref)
            same_role = [el for el in walked if el.get("role") == role]
            for el in same_role:
                el_title = (el.get("title") or "").strip()
                if title and not _title_matches(title, el_title):
                    continue
                if check_visibility and not (el.get("width", 0) > 0 and el.get("height", 0) > 0):
                    continue
                return True
            # Diagnostic: one line that distinguishes the possible causes --
            # empty tree (window not ready / wrong scope) vs. the control having
            # a different role vs. a different title.
            from collections import Counter
            role_counts = Counter(el.get("role") for el in walked)
            logger.info(
                "element_present MISS: want role=%s title=%r | walked %d elems; "
                "roles=%s | same-role titles=%s",
                role, title, len(walked), dict(role_counts),
                [(e.get("title") or "") for e in same_role][:10],
            )
            # Fall through to path/role resolution (handles path-only locators
            # and roles not collected by walk_app).
        info = resolve_locator(app_ref, locator)
        if info is None:
            return False
        if check_visibility:
            return info["width"] > 0 and info["height"] > 0
        return True

    # role / role:title form
    role, _, title = selector.partition(":")
    role = role.strip()
    title = title.strip() or None
    return _find_by_role_title(app_ref, role, title) is not None


def window_titled(app_ref, title: str) -> bool:
    try:
        windows = _attr(app_ref, "AXWindows", []) or []
        for w in windows:
            if _label(w) == title or title in (_label(w) or ""):
                return True
    except Exception:
        pass
    return False


def context(app_ref, app_name: Optional[str] = None) -> dict:
    """Return {app, title} for the *target* application.

    ``app`` is the target app we are automating -- NOT the globally frontmost
    app. Reporting the frontmost app here caused generated `app` triggers to
    capture whatever else happened to be in focus during synthesis (e.g. the
    editor the run was launched from), so the state matched forever. We use the
    explicit target name when known, then the app element's own AXTitle, and
    only fall back to the frontmost app as a last resort.
    """
    app = app_name or ""
    if not app:
        app = _attr(app_ref, "AXTitle", "") or ""
    if not app:
        app = frontmost_app().get("name", "")

    win_title = ""
    try:
        focused = _attr(app_ref, "AXFocusedWindow")
        if focused is not None:
            win_title = _label(focused)
        if not win_title:
            windows = _attr(app_ref, "AXWindows", []) or []
            if windows:
                win_title = _label(windows[0])
    except Exception:
        pass
    return {"app": app, "title": win_title}


def build_trigger_candidates(app_ref, app_name: Optional[str] = None) -> dict:
    """Offer state synthesis a menu of concrete triggers (app/window/text/element).

    Returns no candidates when ``app_name`` is not yet known -- i.e. before any
    open_application/activate_application has run in this workflow. At that
    point "whatever is currently frontmost" is just the operator's own
    environment (their editor, terminal, ...), not a meaningful automation
    precondition, and must not be offered as a trigger. With no candidates,
    state synthesis's filtering guarantees an empty (always-true) trigger set
    for that state -- exactly right for a bootstrap state whose first action
    is to open the target application.
    """
    if not app_name:
        return {}
    import json
    candidates: dict = {}
    # Always offer app-level triggers for the target, whether or not it is
    # running yet. APP_ABSENT (app not running) is what a bootstrap "open the
    # app" state uses -- true until the app launches, then false -- which makes
    # that state self-clearing so synthesis can advance to the next state.
    candidates["APP"] = {"type": "app", "params": {"name": app_name}}
    candidates["APP_ABSENT"] = {"type": "app", "params": {"name": app_name, "negate": True}}

    # If the target app is not running/available yet, there is nothing to walk;
    # app-level triggers are all we can (and should) offer for the bootstrap.
    if app_ref is None:
        return candidates

    ctx = context(app_ref, app_name=app_name)
    if ctx.get("title"):
        candidates["WINDOW"] = {"type": "window", "params": {"title": ctx["title"]}}

    elements = walk_app(app_ref)
    text_seen = set()
    for i, el in enumerate(elements):
        title = (el.get("title") or "").strip()
        if title and title not in text_seen and len(title) < 80:
            text_seen.add(title)
            candidates[f"TEXT_{i}"] = {"type": "text", "params": {"text": title}}
        if el.get("role"):
            locator = {"path": el["ax_path"], "role": el["role"], "title": title}
            sel = json.dumps(locator)
            # Offer both "present" and "absent" (negated) forms so synthesis can
            # build mutually-exclusive, self-clearing triggers across states
            # (e.g. a search state triggers while the results/Directions element
            # is still ABSENT, and stops once it appears).
            candidates[f"ELEMENT_{i}"] = {
                "type": "element",
                "params": {"by": "ax", "selector": sel},
            }
            candidates[f"ELEMENT_{i}_ABSENT"] = {
                "type": "element",
                "params": {"by": "ax", "selector": sel, "negate": True},
            }
        if len(candidates) > 80:
            break
    return candidates
