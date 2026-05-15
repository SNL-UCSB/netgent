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
    workflow_path = os.path.join(workflow_dir, "run_puffer_workflow.json")

    with open(workflow_path, "w", encoding="utf-8") as workflow_file:
        json.dump(workflow, workflow_file, indent=2)
        workflow_file.write("\n")

    print(f"Wrote workflow JSON to {workflow_path}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and run a Puffer browser workflow locally."
    )
    parser.add_argument(
        "--username",
        required=True,
        help="Puffer account username.",
    )
    parser.add_argument(
        "--password",
        required=True,
        help="Puffer account password.",
    )
    parser.add_argument(
        "--watch-seconds",
        default="30",
        help="How long to wait on the player screen before stopping.",
    )
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

    specification = """1. Go to 'https://puffer.stanford.edu/accounts/login'.
    2. On the Puffer login page, enter username <secret>username</secret> and password <secret>password</secret>.
    3. If a consent or agreement checkbox is present, select it.
    4. Submit the login form.
    5. After login, click the 'Watch TV' button.
    6. Wait for the channel page to finish loading.
    7. Select the 'Fox' channel.
    8. When the player screen is active and playback has started, wait for <secret>watch_seconds</secret> seconds before stopping."""
    parameters = {
        "username": args.username,
        "password": args.password,
        "watch_seconds": args.watch_seconds,
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
