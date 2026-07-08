#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_PY="$ROOT_DIR/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "Missing .venv. Create it with: python3 -m venv .venv && .venv/bin/python -m pip install -e ."
  exit 1
fi

"$VENV_PY" - <<'PY'
import ast
import json
from pathlib import Path

root = Path.cwd()
workflow_path = root / "examples/web_browsing/twitch-247jynxzi/results/twitch-247jynxzi_result.json"
prompts_path = root / "examples/web_browsing/twitch-247jynxzi/prompts/twitch-247jynxzi_prompts.json"
api_example_path = root / "api_keys.example.json"
controller_base_path = root / "src/netgent/browser/controller/base.py"

workflow = json.loads(workflow_path.read_text())
prompts = json.loads(prompts_path.read_text())
api_example = json.loads(api_example_path.read_text())
controller_tree = ast.parse(controller_base_path.read_text())

assert api_example.get("google_api_key") == "YOUR_GEMINI_API_KEY", (
    "api_keys.example.json must stay as a placeholder template. "
    "Put your real Gemini key in the ignored api_keys.json or .env file instead."
)
assert any(
    "247jynxzi" in action.get("params", {}).get("url", "")
    for state in workflow
    for action in state["actions"]
), "workflow must navigate to https://www.twitch.tv/247jynxzi"
assert any(
    action["type"] == "start_stats_logging"
    for state in workflow
    for action in state["actions"]
), "workflow must start Twitch stats logging"
assert prompts[0]["actions"], "prompts must include agent actions"

registered_actions = set()
for node in ast.walk(controller_tree):
    if not isinstance(node, ast.FunctionDef):
        continue
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call) and getattr(decorator.func, "id", "") == "action":
            action_name = node.name
            for keyword in decorator.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                    action_name = keyword.value.value
            registered_actions.add(action_name)

used_actions = {action["type"] for state in workflow for action in state["actions"]}
missing_actions = used_actions - registered_actions
assert not missing_actions, f"workflow uses unregistered actions: {sorted(missing_actions)}"

print("Static Twitch 247jynxzi smoke checks passed.")
PY

if [[ "${RUN_NETGENT_SMOKE:-0}" == "1" ]]; then
  timeout "${SMOKE_TIMEOUT_SECONDS:-90}" "$VENV_PY" -m netgent \
    -e examples/web_browsing/twitch-247jynxzi/results/twitch-247jynxzi_result.json \
    --user-data-dir browser_cache/twitch-247jynxzi \
    -o out/twitch-247jynxzi/smoke_result.json
fi

if [[ "${RUN_NETGENT_GENERATE:-0}" == "1" ]]; then
  timeout "${SMOKE_TIMEOUT_SECONDS:-180}" "$VENV_PY" -m netgent \
    -g api_keys.json '{}' examples/web_browsing/twitch-247jynxzi/prompts/twitch-247jynxzi_prompts.json \
    --user-data-dir browser_cache/twitch-247jynxzi-generate \
    -o out/twitch-247jynxzi/generated_state_repository.json
fi
