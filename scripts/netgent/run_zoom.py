import argparse
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from main import NetGent


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
    workflow_path = os.path.join(workflow_dir, "run_zoom_workflow.json")

    with open(workflow_path, "w", encoding="utf-8") as workflow_file:
        json.dump(workflow, workflow_file, indent=2)
        workflow_file.write("\n")

    print(f"Wrote workflow JSON to {workflow_path}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and run a Zoom web client browser workflow locally."
    )
    parser.add_argument(
        "--meeting-id",
        required=True,
        help="Zoom meeting ID (digits, spaces allowed — e.g. '123 456 7890').",
    )
    parser.add_argument(
        "--passcode",
        required=True,
        help="Zoom meeting passcode.",
    )
    parser.add_argument(
        "--display-name",
        required=True,
        help="Display name to use when joining the meeting.",
    )
    parser.add_argument(
        "--wait-seconds",
        default="30",
        help="How long to stay in the meeting (in seconds) before stopping.",
    )
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

    specification = """1. Go to 'https://app.zoom.us/wc'.
    2. If a consent, cookie, or welcome dialog appears, dismiss it.
    3. Click the 'Join a Meeting' (or 'Join Meeting') button / link to open the join form.
    4. In the meeting ID / meeting number input, type <secret>meeting_id</secret>.
    5. Submit the meeting ID by clicking the 'Join' button (or pressing Enter) to advance to the next screen.
    6. If the browser prompts for camera / microphone permissions, dismiss or continue through it — do not cancel.
    7. If a passcode input appears, type <secret>passcode</secret> into the passcode field and submit it.
    8. If a display name / 'Your Name' input appears, type <secret>display_name</secret> into it.
    9. Click the final 'Join' / 'Join Meeting' button to enter the meeting.
    10. Once inside the meeting (or while waiting in the lobby / waiting room to be admitted), wait for <secret>wait_seconds</secret> seconds before stopping."""
    parameters = {
        "meeting_id": args.meeting_id,
        "passcode": args.passcode,
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
