"""Replay the saved Google Meet workflow JSON via the engine only — no LLM.

Usage:
    uv run python scripts/replay_meet_workflow.py \
        --meeting-code rea-aicf-fig \
        --display-name "ThinWaistBot" \
        --wait-seconds 30
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from netgent.main import NetGent  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meeting-code", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--wait-seconds", default="30")
    parser.add_argument(
        "--workflow",
        default=os.path.join(
            os.path.dirname(__file__), "workflow", "run_meet_workflow.json"
        ),
        help="Path to the saved workflow JSON.",
    )
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    with open(args.workflow, encoding="utf-8") as f:
        workflow = json.load(f)

    result = NetGent(cdp_url=None, headless=args.headless).run_workflow(
        workflow,
        parameters={
            "meeting_code": args.meeting_code,
            "display_name": args.display_name,
            "wait_seconds": args.wait_seconds,
        },
        type="browser",
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
