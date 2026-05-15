"""Run NetGent workflows directly via the client.

Usage:
    uv run python scripts/run_netgent.py                      # Pre-built browser workflow (headful)
    uv run python scripts/run_netgent.py --headless           # Pre-built browser, headless
    uv run python scripts/run_netgent.py shell                # Pre-built shell workflow (ping)
    uv run python scripts/run_netgent.py generate             # Generate + run browser (headful)
    uv run python scripts/run_netgent.py generate --headless  # Generate + run browser, headless
"""

import argparse
import asyncio
import json
import os
import sys

# `pyproject.toml` declares pythonpath=["src"] for pytest; we replicate it
# here so `from main import NetGent` and bare imports like
# `from services.ping import ...` both resolve when running the script.
_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, "..", "src"))

# Shell actions read USE_LOCAL once at import time to decide between direct
# execution and namespace execution (`ip netns exec`). Force local mode
# before importing netgent — on macOS namespace mode fails because iproute2
# is Linux-only, and this script is for local testing only.
os.environ["USE_LOCAL"] = "true"

from main import NetGent
from dotenv import load_dotenv

# Load .env from repo root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


def _strip_screenshots(value):
    """Recursively remove base64 screenshot/har blobs for readable output."""
    if isinstance(value, dict):
        return {
            k: _strip_screenshots(v)
            for k, v in value.items()
            if k not in ("screenshot", "har")
        }
    if isinstance(value, list):
        return [_strip_screenshots(v) for v in value]
    return value


def run_prebuilt(*, headless: bool = False):
    """Execute a pre-built workflow (engine only, no LLM)."""
    client = NetGent(cdp_url=None, headless=headless)

    workflow = {
        "specification": "Go to a website and wait",
        "states": [
            {
                "checks": [{"type": "always_true", "params": {}}],
                "actions": [
                    {
                        "type": "go_to_url",
                        "params": {"url": "{{url}}", "new_tab": False},
                    },
                    {"type": "wait", "params": {"seconds": "{{wait_seconds}}"}},
                ],
                "end_state": "done",
            }
        ],
        "parameters": ["url", "wait_seconds"],
    }

    result = client.run_workflow(
        workflow,
        parameters={"url": "https://example.com", "wait_seconds": "5"},
        type="browser",
    )
    print(json.dumps(_strip_screenshots(result), indent=2, default=str))


async def generate_workflow(*, headless: bool = False):
    """Generate a workflow from natural language and run it (LLM agent)."""
    client = NetGent(cdp_url=None, headless=headless)
    spec = "Go to https://example.com and wait for 5 seconds"

    print(f"Generating workflow for: {spec!r}\n")
    result = await client.generate(spec, type="browser")

    # Show the generated workflow and key result fields
    generated = _strip_screenshots(result)
    print(json.dumps(generated, indent=2, default=str))


def run_shell():
    """Execute a pre-built shell workflow (ping)."""
    client = NetGent()

    workflow = {
        "specification": "Ping 8.8.8.8 three times",
        "states": [
            {
                "checks": [{"type": "always_true", "params": {}}],
                "actions": [
                    {
                        "type": "ping",
                        "params": {"host": "{{host}}", "count": "{{count}}"},
                    }
                ],
                "end_state": "done",
            }
        ],
        "parameters": ["host", "count"],
    }

    result = client.run_workflow(
        workflow,
        parameters={"host": "8.8.8.8", "count": "3"},
        type="shell",
    )
    print(json.dumps(result, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="Run or generate NetGent workflows.")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["run", "shell", "generate"],
        default="run",
        help="run browser (default), shell, or generate from NL spec",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="run Chromium headless (default: headful/visible)",
    )
    args = parser.parse_args()

    if args.mode == "generate":
        asyncio.run(generate_workflow(headless=args.headless))
    elif args.mode == "shell":
        run_shell()
    else:
        run_prebuilt(headless=args.headless)


if __name__ == "__main__":
    main()
