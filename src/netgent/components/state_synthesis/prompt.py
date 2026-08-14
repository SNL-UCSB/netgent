import os

def _read_markdown(file_name: str) -> str:
    base_dir = os.path.join(os.path.dirname(__file__), "prompts")
    file_path = os.path.join(base_dir, file_name)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def get_prompt(name: str, domain: str = "web") -> str:
    mapping = {
        "CHOOSE_STATE_PROMPT": "CHOOSE_STATE_PROMPT.md",
        "DEFINE_TRIGGER_PROMPT": "DEFINE_TRIGGER_PROMPT.md",
        "PROMPT_ACTION_PROMPT": "PROMPT_ACTION_PROMPT.md",
    }
    if name not in mapping:
        raise ValueError(f"Unknown prompt name: {name}")
    # Prefer a domain-specific variant (prompts/<domain>/<file>) when present.
    if domain and domain != "web":
        base_dir = os.path.join(os.path.dirname(__file__), "prompts")
        domain_file = os.path.join(base_dir, domain, mapping[name])
        if os.path.isfile(domain_file):
            return _read_markdown(os.path.join(domain, mapping[name]))
    return _read_markdown(mapping[name])

CHOOSE_STATE_PROMPT = _read_markdown("CHOOSE_STATE_PROMPT.md")
DEFINE_TRIGGER_PROMPT = _read_markdown("DEFINE_TRIGGER_PROMPT.md")
PROMPT_ACTION_PROMPT = _read_markdown("PROMPT_ACTION_PROMPT.md")