"""
NetGent host bridge HTTP server (stdlib only).

Runs natively on the user's macOS machine and exposes a tiny JSON API that the
Dockerized NetGent orchestrator calls to observe and control desktop apps:

    GET  /health              -> liveness check
    POST /snapshot   {app?}   -> {elements, prompt, screenshot, context}
    POST /context    {app?}   -> {context: {app, title}}
    POST /triggers   {app?}   -> {candidates: {...}}
    POST /trigger    {type, params, app?} -> {result: bool}
    POST /action     {action, params, app?} -> {result}

Every observation/action is scoped to a single target application, which the
container selects via the ``app`` field (set by the open/activate actions). This
scoping is what keeps background apps from interfering.

Start it with:  python -m netgent_hostbridge  [--host 0.0.0.0] [--port 8765]
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import ax
from .actuator import Actuator

logger = logging.getLogger("netgent_hostbridge")

# Bump when the bridge's behavior changes so a running instance can be
# identified via GET /health. Lets you confirm a restart actually took effect
# (a common trap: the new process fails to bind the port because the old one is
# still running, so the stale code keeps answering).
BRIDGE_VERSION = "2026.07.11-fresh-pid-lookup"

# One actuator (and therefore one target-app scope) per bridge process.
_ACTUATOR = Actuator()


def _capture_screenshot() -> str:
    """Return a base64 PNG of the current screen, or '' if unavailable."""
    try:
        import pyautogui
        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as e:
        logger.warning("Screenshot capture failed: %s", e)
        return ""


def _resolve_app_ref(app: str | None, fallback_frontmost: bool = True):
    """Pick the AX app reference for THIS request.

    If the caller specifies ``app``, scope to it and remember it as the
    actuator's persistent target (so later actions know what to activate/click).

    ``fallback_frontmost`` controls what happens when the requested app is not
    running yet (or none was requested):
    - True  (observation endpoints: /snapshot, /context): fall back to the
      frontmost app so the agent can still perceive the screen in order to,
      e.g., issue the action that opens the target.
    - False (trigger candidates: /triggers): return None instead, so we never
      walk the *wrong* app's tree and offer its controls as triggers. The
      caller then offers app-level (running / not-running) triggers only.
    """
    if app:
        _ACTUATOR.set_target(app)
        try:
            ref = _ACTUATOR.ensure_app_ref()
        except Exception:
            ref = None
        if ref is not None:
            return ref
        if not fallback_frontmost:
            return None

    if not fallback_frontmost:
        return None

    front = ax.frontmost_app()
    name = front.get("name") or front.get("bundle_id")
    if not name:
        return None
    try:
        return ax.get_app_ref(name)
    except Exception:
        return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep the console readable
        logger.info("%s - %s", self.address_string(), fmt % args)

    # -- helpers ---------------------------------------------------------- #
    def _send(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    # -- routes ----------------------------------------------------------- #
    def do_GET(self):
        if self.path.rstrip("/") in ("/health", ""):
            self._send(200, {"ok": True, "service": "netgent-hostbridge", "version": BRIDGE_VERSION})
        else:
            self._send(404, {"ok": False, "error": f"Unknown path {self.path}"})

    def do_POST(self):
        try:
            body = self._read_json()
            route = self.path.rstrip("/")
            if route == "/snapshot":
                self._send(200, self._snapshot(body))
            elif route == "/context":
                self._send(200, self._context(body))
            elif route == "/triggers":
                self._send(200, self._triggers(body))
            elif route == "/trigger":
                self._send(200, self._trigger(body))
            elif route == "/action":
                self._send(200, self._action(body))
            else:
                self._send(404, {"ok": False, "error": f"Unknown path {self.path}"})
        except Exception as e:
            logger.exception("Request failed")
            self._send(200, {"ok": False, "error": str(e)})

    # -- handlers --------------------------------------------------------- #
    def _snapshot(self, body):
        # Observation: scope to the requested app, but if it is not open yet
        # fall back to the frontmost app so the agent can still see the screen
        # (e.g. to issue the action that opens the target).
        app = body.get("app")
        ref = _resolve_app_ref(app, fallback_frontmost=True)
        if ref is None:
            return {"ok": True, "elements": {}, "prompt": "No accessibility elements found.",
                    "screenshot": "", "context": {"app": app or "", "title": ""}}
        elements, prompt = ax.build_snapshot(ref)
        screenshot = _capture_screenshot() if body.get("include_screenshot", True) else ""
        return {
            "ok": True,
            "elements": elements,
            "prompt": prompt,
            "screenshot": screenshot,
            "context": ax.context(ref, app_name=app),
        }

    def _context(self, body):
        app = body.get("app")
        ref = _resolve_app_ref(app, fallback_frontmost=True)
        if ref is None:
            return {"ok": True, "context": {"app": app or "", "title": ""}}
        return {"ok": True, "context": ax.context(ref, app_name=app)}

    def _triggers(self, body):
        # Trigger candidates: do NOT fall back to the frontmost app -- if the
        # target is not open yet we only offer app-level (running / not-running)
        # triggers, never controls from whatever unrelated app is in front.
        app = body.get("app")
        ref = _resolve_app_ref(app, fallback_frontmost=False)
        return {"ok": True, "candidates": ax.build_trigger_candidates(ref, app_name=app)}

    def _trigger(self, body):
        ttype = body.get("type")
        params = body.get("params", {}) or {}
        # 'app' trigger can be answered without an AX tree walk.
        # Checks whether the app is RUNNING (stable regardless of focus), not
        # whether it is frontmost -- the latter flips false whenever the
        # operator clicks away (e.g. to the terminal), which made "open the app"
        # states re-fire in a loop.
        if ttype == "app":
            name = params.get("name", "")
            return {"ok": True, "result": bool(ax.is_app_running(name))}

        # Element/text/window checks are scoped strictly to the target app (no
        # frontmost fallback): if the target is not running, its controls are
        # simply absent, so the trigger is False.
        ref = _resolve_app_ref(body.get("app"), fallback_frontmost=False)
        if ref is None:
            return {"ok": True, "result": False}
        if ttype == "element":
            result = ax.element_present(
                ref, params.get("by"), params.get("selector"),
                params.get("check_visibility", True),
            )
        elif ttype == "text":
            result = ax.text_present(ref, params.get("text", ""))
        elif ttype == "window":
            result = ax.window_titled(ref, params.get("title", ""))
        else:
            return {"ok": False, "error": f"Unknown trigger type: {ttype}"}
        return {"ok": True, "result": bool(result)}

    def _action(self, body):
        if body.get("app"):
            _ACTUATOR.set_target(body["app"])
        action = body.get("action")
        params = body.get("params", {}) or {}
        result = _ACTUATOR.execute(action, params)
        return {"ok": True, "result": result}


def serve(host: str = "0.0.0.0", port: int = 8765):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [hostbridge] %(levelname)s %(message)s",
    )
    if ax.atomacos is None:
        logger.warning(
            "atomacos failed to import; accessibility perception will not work. "
            "Install host requirements: pip install -r "
            "src/netgent_hostbridge/requirements.txt"
        )
    try:
        server = ThreadingHTTPServer((host, port), Handler)
    except OSError as e:
        logger.error(
            "Could not bind %s:%d (%s). Another host bridge is probably still "
            "running on this port -- this new process would exit and the OLD "
            "(stale) one would keep serving. Kill it first, e.g.:\n"
            "    pkill -f 'netgent_hostbridge'   (or: lsof -ti:%d | xargs kill)",
            host, port, e, port,
        )
        raise SystemExit(1)
    logger.info("NetGent host bridge v%s listening on http://%s:%d", BRIDGE_VERSION, host, port)
    logger.info("From Docker, reach it at http://host.docker.internal:%d", port)
    logger.info("Grant Accessibility (and Screen Recording, for screenshots) to "
                "this process in System Settings > Privacy & Security.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down host bridge.")
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="NetGent macOS host bridge")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="Port (default 8765)")
    args = parser.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
