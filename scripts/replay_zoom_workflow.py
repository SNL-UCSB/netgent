"""Replay the saved Zoom workflow JSON via the engine only — no LLM.

Usage:
    uv run python scripts/replay_zoom_workflow.py \
        --meeting-id "827 7109 1016" \
        --passcode "56XJKk" \
        --display-name "ThinWaistBot" \
        --wait-seconds 30
"""

import argparse
import asyncio
import json
import os
import sys

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_HERE, "..", "src"))

from main import NetGent  # noqa: E402


def _strip_artifacts(value):
    if isinstance(value, dict):
        return {
            k: _strip_artifacts(v) for k, v in value.items() if k not in ("screenshot", "har")
        }
    if isinstance(value, list):
        return [_strip_artifacts(v) for v in value]
    return value


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meeting-id", required=True)
    parser.add_argument("--passcode", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--wait-seconds", default="50")
    parser.add_argument(
        "--workflow",
        default=os.path.join(_HERE, "workflow", "run_zoom_workflow.json"),
    )
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    with open(args.workflow, encoding="utf-8") as f:
        workflow = json.load(f)

    client = NetGent(cdp_url=None, headless=args.headless)
    result = await client.arun_workflow(
        workflow,
        parameters={
            "meeting_id": args.meeting_id,
            "passcode": args.passcode,
            "display_name": args.display_name,
            "wait_seconds": args.wait_seconds,
        },
        type="browser",
    )
    print(json.dumps(_strip_artifacts(result), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
