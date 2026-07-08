"""Generate or refresh the NetGent workflow for watching a Hulu video."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from netgent import NetGent, StatePrompt

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = ROOT / "examples" / "web_browsing" / "hulu-watch"
PROMPTS_PATH = WORKFLOW_DIR / "prompts" / "hulu-watch_prompts.json"
RESULT_PATH = WORKFLOW_DIR / "results" / "hulu-watch_result.json"
API_KEYS_PATH = ROOT / "api_keys.json"


def load_google_api_key() -> str:
    if os.getenv("GOOGLE_API_KEY"):
        return os.environ["GOOGLE_API_KEY"]

    if API_KEYS_PATH.exists():
        with API_KEYS_PATH.open() as f:
            api_keys = json.load(f)
        if api_keys.get("google_api_key"):
            return api_keys["google_api_key"]

    raise RuntimeError(
        "Set GOOGLE_API_KEY in .env or create api_keys.json from api_keys.example.json."
    )


def load_prompts() -> list[StatePrompt]:
    with PROMPTS_PATH.open() as f:
        prompt_data = json.load(f)

    return [
        StatePrompt(
            name=item["name"],
            description=item["description"],
            triggers=item.get("triggers", []),
            actions=item.get("actions", []),
            end_state=item.get("end_state", ""),
        )
        for item in prompt_data
    ]


def main() -> None:
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("NETGENT_LLM_MODEL", "gemini-2.0-flash-exp"),
        temperature=0.2,
        api_key=load_google_api_key(),
    )
    agent = NetGent(llm=llm, llm_enabled=True, user_data_dir="examples/user_data")
    prompts = load_prompts()

    try:
        with RESULT_PATH.open() as f:
            state_repository = json.load(f)
    except FileNotFoundError:
        state_repository = []

    result = agent.run(state_prompts=prompts, state_repository=state_repository)

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULT_PATH.open("w") as f:
        json.dump(result["state_repository"], f, indent=2)


if __name__ == "__main__":
    main()
