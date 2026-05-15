from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from browser_use import AgentHistoryList, Controller
from browser_use.agent.views import ActionResult
from dotenv import load_dotenv
from playwright.async_api import Playwright

load_dotenv()


def _is_headless() -> bool:
    return os.getenv("BROWSER_USE_HEADLESS", "true").lower() == "true"


# Fake silent/black media devices are fed to any site that requests mic/camera,
# and permission prompts are auto-accepted so automation never stalls on a dialog.
# Real host mic/camera are never opened.
MEDIA_STREAM_DISABLE_ARGS = [
    "--use-fake-device-for-media-stream",
    "--use-fake-ui-for-media-stream",
]

# Strips the most obvious automation fingerprints that sites like Google Meet
# use to block Playwright/Puppeteer sessions. Covers both the Chrome-level
# "Chrome is being controlled by automated test software" banner and the JS
# `navigator.webdriver === true` signal.
STEALTH_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-default-browser-check",
    "--no-first-run",
    "--disable-sync",
    "--disable-dev-shm-usage",
    "--password-store=basic",
    "--use-mock-keychain",
    "--disable-infobars",
    "--exclude-switches=enable-automation",
    "--window-size=1280,720",
]

# Force a working GL backend so apps that lean on GPU compositing (Google
# Meet's video tiles, glass-effect toolbar, avatar plates) actually paint.
# Without these, Playwright's Chromium often falls back to a degraded
# rasterizer that mounts the React tree but leaves the visible viewport
# black even though the DOM is fully present.
GPU_RENDERING_ARGS = [
    "--ignore-gpu-blocklist",
    "--enable-gpu-rasterization",
    "--enable-zero-copy",
    "--use-gl=angle",
]

# A recent Chrome-on-macOS UA. Using the default Playwright HeadlessChrome /
# Chrome-for-Testing UA is a dead giveaway to bot detection.
STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)

# Injected into every page before any site script runs. Patches the fingerprints
# that headless / automation detection inspects, including the WebGL renderer
# string that Google Meet checks before deciding whether to render its
# GPU-composited video tiles. Without the WebGL patch, Meet sees a generic
# SwiftShader/ANGLE renderer and silently skips the in-call layout, leaving
# a black viewport over a fully-mounted DOM.
STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => false });
if (!window.chrome) { window.chrome = { runtime: {} }; }
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});
// Patch the prototype (not the instance) and use a real `function` so the
// caller's `this` flows through to the native method. Calling the saved
// reference as a bare function throws "Illegal invocation" — Google Meet
// reports that error to /jserror and silently bails out of mounting the
// in-call UI, leaving a black viewport.
const _Permissions = window.Permissions && window.Permissions.prototype;
const _origPermissionsQuery = _Permissions && _Permissions.query;
if (_origPermissionsQuery) {
    _Permissions.query = function (parameters) {
        if (parameters && parameters.name === 'notifications') {
            return Promise.resolve({ state: 'default', onchange: null });
        }
        return _origPermissionsQuery.call(this, parameters);
    };
}
const _getWebGLParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function (param) {
    // 37445 = UNMASKED_VENDOR_WEBGL, 37446 = UNMASKED_RENDERER_WEBGL.
    // Reporting a real-looking GPU vendor/renderer keeps Meet from falling
    // back to its no-GPU rendering path.
    if (param === 37445) return 'Google Inc. (Apple)';
    if (param === 37446) return 'ANGLE (Apple, Apple M1, OpenGL 4.1)';
    return _getWebGLParameter.call(this, param);
};
"""


def _stealth_enabled() -> bool:
    return os.getenv("NETGENT_DISABLE_STEALTH", "").lower() not in ("1", "true", "yes")


IGNORED_ACTIONS = {
    "done",
    "extract_page_content",
    "get_dropdown_options",
    "read_file",
    "replace_file_str",
    "write_file",
}


def _coerce_history_items(
    history: AgentHistoryList | str | dict[str, Any] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(history, AgentHistoryList):
        history = history.model_dump()

    elif hasattr(history, "model_dump") and callable(history.model_dump):
        history = history.model_dump()

    if isinstance(history, str):
        history = json.loads(history)

    if isinstance(history, list):
        return history

    if isinstance(history, dict):
        items = history.get("history")
        if isinstance(items, list):
            return items

    raise ValueError(
        "history must be a list of steps or a dict containing a 'history' list"
    )


def _parse_action(action: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    if not isinstance(action, dict):
        return None, {}

    for action_type, params in action.items():
        if action_type in IGNORED_ACTIONS:
            return None, {}
        if isinstance(params, dict):
            return action_type, params
        return action_type, {}

    return None, {}


def parse_agent_history(
    history: AgentHistoryList | str | dict[str, Any] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    parsed_history: list[dict[str, Any]] = []

    for step in _coerce_history_items(history):
        model_output = step.get("model_output") or {}
        state = step.get("state") or {}

        actions = model_output.get("action") or []
        interacted_elements = state.get("interacted_element") or []

        parsed_actions = []
        for index, action in enumerate(actions):
            action_type, params = _parse_action(action)
            if action_type is None:
                continue

            interacted_element = None
            if index < len(interacted_elements):
                interacted_element = interacted_elements[index]

            parsed_actions.append(
                {
                    "type": action_type,
                    "params": params,
                    "interacted_element": interacted_element,
                }
            )

        parsed_history.append(
            {
                "next_goal": model_output.get("next_goal"),
                "thinking": model_output.get("thinking"),
                "state": state,
                "actions": parsed_actions,
            }
        )

    return parsed_history


def _count_relevant_actions(history: AgentHistoryList) -> int:
    action_count = 0

    for step in _coerce_history_items(history.model_dump()):
        model_output = step.get("model_output") or {}
        actions = model_output.get("action") or []
        for action in actions:
            action_type, _ = _parse_action(action)
            if action_type is not None:
                action_count += 1

    return action_count


def _is_failed_history(history: AgentHistoryList) -> bool:
    return history.is_successful() is False or history.has_errors()


def prune_agenthistorylist(
    history_list: list[AgentHistoryList], top_k: int = 5
) -> list[AgentHistoryList]:
    failed_histories: list[AgentHistoryList] = []
    successful_histories: list[AgentHistoryList] = []

    for history in history_list:
        if _is_failed_history(history):
            failed_histories.append(history)
        else:
            successful_histories.append(history)

    failed_histories.sort(key=_count_relevant_actions)
    successful_histories.sort(key=_count_relevant_actions)

    pruned_histories = list(failed_histories)
    for history in successful_histories:
        if len(pruned_histories) >= len(failed_histories) + max(0, top_k):
            break
        pruned_histories.append(history)

    return pruned_histories


def build_controller(exclude_actions: list[str] | None = None) -> Controller:
    # Ensure "wait" is NOT in exclude_actions — we overwrite it below.
    # The Registry checks exclude_actions on every @action call, so including
    # "wait" would block our custom registration too.
    excluded = [a for a in (exclude_actions or []) if a != "wait"]

    controller = Controller(exclude_actions=excluded)

    @controller.registry.action(
        "Wait for x seconds (minimum 1 second actual sleep). "
        "Use this to pause before the next action when a page needs time to load or animate. "
        "Sleeps for the requested duration, rounded down to a whole number of seconds. "
        "Accepts a sensitive_data placeholder (e.g. x_wait) in place of a literal number."
    )
    async def wait(seconds: str = "3") -> ActionResult:
        try:
            seconds_int = int(float(seconds))
        except (ValueError, TypeError):
            seconds_int = 3
        actual_seconds = max(seconds_int, 1)
        msg = f"Waiting for {actual_seconds} seconds"
        await asyncio.sleep(actual_seconds)
        return ActionResult(extracted_content=msg)

    return controller


def get_browserless_ws_endpoint() -> str | None:
    endpoint = os.getenv("BROWSERLESS_WS_ENDPOINT", "").strip()
    return endpoint or None


async def open_browser_session(
    playwright: Playwright, *, record_har_path: str | None = None
):
    endpoint = get_browserless_ws_endpoint()
    stealth = _stealth_enabled()
    if endpoint:
        browser = await playwright.chromium.connect(endpoint)
    else:
        launch_args = [*MEDIA_STREAM_DISABLE_ARGS, *GPU_RENDERING_ARGS]
        launch_kwargs: dict[str, Any] = {
            "headless": _is_headless(),
            "args": launch_args,
        }
        if stealth:
            launch_kwargs["args"] = [*launch_args, *STEALTH_LAUNCH_ARGS]
            launch_kwargs["ignore_default_args"] = ["--enable-automation"]
        browser = await playwright.chromium.launch(**launch_kwargs)
    # Grant camera + microphone so getUserMedia resolves successfully —
    # the launch flags above feed it silent/black fake devices, so nothing
    # leaks from the real host. Apps like Google Meet refuse to render
    # their in-call UI when the permission is denied (the `<video>` tree
    # never mounts → black canvas), even though we never want their real
    # streams.
    context_kwargs: dict[str, Any] = {
        "permissions": ["camera", "microphone"],
        "viewport": {"width": 1280, "height": 720},
    }
    if stealth:
        context_kwargs["user_agent"] = STEALTH_USER_AGENT
    if record_har_path:
        context_kwargs["record_har_path"] = record_har_path
        context_kwargs["record_har_mode"] = "full"
        context_kwargs["record_har_content"] = "embed"
    browser_context = await browser.new_context(**context_kwargs)
    if stealth:
        await browser_context.add_init_script(STEALTH_INIT_SCRIPT)
    page = await browser_context.new_page()
    return browser, browser_context, page
