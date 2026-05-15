import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from netgent.main import NetGent


def _strip_artifacts(value):
    if isinstance(value, dict):
        return {
            key: _strip_artifacts(nested)
            for key, nested in value.items()
            if key not in ("screenshot", "har")
        }
    if isinstance(value, list):
        return [_strip_artifacts(nested) for nested in value]
    return value


def _write_workflow_artifact(generated: dict) -> None:
    workflow = generated.get("workflow")
    if not isinstance(workflow, dict):
        return

    workflow_dir = os.path.join(os.path.dirname(__file__), "..", "workflow")
    os.makedirs(workflow_dir, exist_ok=True)
    workflow_path = os.path.join(workflow_dir, "run_meet_workflow.json")

    with open(workflow_path, "w", encoding="utf-8") as workflow_file:
        json.dump(workflow, workflow_file, indent=2)
        workflow_file.write("\n")

    print(f"Wrote workflow JSON to {workflow_path}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and run a Google Meet browser workflow locally."
    )
    parser.add_argument(
        "--meeting-code",
        required=True,
        help="Google Meet meeting code (e.g. 'abc-defg-hij').",
    )
    parser.add_argument(
        "--display-name",
        required=True,
        help="Display name to use when asking to join the meeting.",
    )
    parser.add_argument(
        "--wait-seconds",
        default="30",
        help="How long to stay in the meeting (in seconds) before stopping.",
    )
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

    specification = """1. Go to 'https://meet.google.com/<meeting_code> '.
    2. On the pre-join screen, if prompted for a name, type <secret>display_name</secret> into the display name input.
    3. Click the 'Ask to join' button to request entry to the meeting.
    4. Once in the meeting (or while waiting in the lobby to be admitted), wait for <secret>wait_seconds</secret> seconds before stopping."""
    parameters = {
        "meeting_code": args.meeting_code,
        "display_name": args.display_name,
        "wait_seconds": args.wait_seconds,
    }
    client = NetGent(cdp_url=None, headless=False)
    generated = await client.generate(
        type="browser",
        specification=specification,
        parameters=parameters,
    )
    _write_workflow_artifact(generated)
    print(json.dumps(_strip_artifacts(generated), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
