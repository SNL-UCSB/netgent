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
    workflow_path = os.path.join(workflow_dir, "run_webex_workflow.json")

    with open(workflow_path, "w", encoding="utf-8") as workflow_file:
        json.dump(workflow, workflow_file, indent=2)
        workflow_file.write("\n")

    print(f"Wrote workflow JSON to {workflow_path}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and run a Webex browser workflow locally."
    )
    parser.add_argument(
        "--meeting-code",
        required=True,
        help="Webex meeting number / code (e.g. '2559 467 3784').",
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

    specification = """1. Go to 'https://signin.webex.com/joinameeting'.
    2. If a consent, cookie, or welcome dialog appears, dismiss it.
    3. Locate the meeting number / meeting code input on the page and type <secret>meeting_code</secret> into it.
    4. Submit the meeting number (click the 'Join' / 'Next' button, or press Enter) to advance to the join options page.
    5. Click the 'Join from Browser' link or button to continue in the browser instead of the desktop app.
    6. If a 'Use Microphone and Camera' (or similar device permission) prompt appears, click it to accept the devices.
    7. On the pre-join screen, type <secret>display_name</secret> into the display name input.
    8. Click the 'Join meeting' button (or equivalent join/continue button) to enter the meeting.
    9. Once inside the meeting (or while waiting in the lobby to be admitted), wait for <secret>wait_seconds</secret> seconds before stopping."""
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
