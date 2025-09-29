## CliGent: Finite-State Synthesis and Execution for Robust Web Automation

### Abstract

CliGent is a multi-agent system that compiles high-level natural language workflows into deterministic, reusable finite-state machines (FSMs) for web automation. The system emphasizes diversity (rapid onboarding of new apps), repeatability (static code artifacts), complexity (non-linear workflows with branching), and robustness (automatic regeneration under UI drift with state caching). This README outlines the architecture, FSM model, execution semantics, and implementation details using the Disney Plus ESPN workflow as a running example.

### Design Goals and Rationale

- **Diversity**: New applications can be onboarded quickly by specifying high-level state prompts, without low-level scripting.
- **Repeatability**: Workflows are compiled into static JSON+Python artifacts. Subsequent runs can skip LLMs entirely.
- **Complexity**: FSMs model non-linear flows with conditional branching and multiple terminal states.
- **Robustness**: When UI changes break triggers or actions, the system regenerates precise FSM states from the current DOM and reuses cached components.

### System Overview

CliGent ingests a user intent along with high-level step descriptions called State Prompts. It synthesizes a precise FSM whose states are guarded by DOM-aware triggers and whose actions are deterministic Python calls to a browser controller. The system provides two execution modes:

- Deterministic replay from compiled FSM JSON (no LLM).
- Regenerative execution with LLMs for state synthesis when needed (on failure or missing states).

### Architecture

- **State Agent (FSM Orchestrator)** — `state_agent/state_agent/agent.py`

  - Builds a `langgraph` workflow with nodes for `execute` and on-demand `generate_state`.
  - Coordinates two sub-agents: a Judge Agent to select the next state from abstract prompts and a Browser Agent to concretize actions.
  - Terminates on success, on error, or when an explicit `end_state` is reached.

- **Browser Agent (Percept–Plan–Act)** — `state_agent/state_agent/browser_agent/agent.py`

  - Loop: annotate → plan → execute → conditional terminate.
  - Annotate: captures interactable elements and screenshots via `BrowserManager.mark_page`, backed by `state_agent/dom/webmarker.py` and `state_agent/dom/dom_parser.py`.
  - Plan/Execute: prompt templates (`state_agent/state_agent/browser_agent/prompt.py`) guide a vision-LLM to emit one Python action per round; execution occurs in a constrained locals environment that logs structured `Code` messages.

- **State Executor (Deterministic FSM Runner)** — `state_agent/actions/state_executor.py`

  - Filters states by evaluating conjunctive triggers against live DOM signals.
  - Executes each state’s action list deterministically using a whitelist of `BrowserManager` functions.
  - Enforces timeouts and termination conditions; returns on first error.

- **Browser Manager (Low-level Control + Trigger Detection)** — `state_agent/actions/browser_manager.py`
  - Wraps `seleniumbase.Driver` (undetected Chrome) and exposes robust operations: `click`, `type`, `press_key`, `scroll_to`, `scroll`, `wait`, `navigate_to`.
  - DOM Perception: `mark_page` injects a DOM snapshotter; `parse_dom` builds a human-readable element prompt and an id→selector map.
  - Trigger Detection: `detect_trigger` supports `url`, exact `text`, and stable `element` via enhanced CSS selectors from `state_agent/dom/webmarker.py` and `state_agent/dom/avaliable_trigger.js`.

### FSM Model

Each FSM node (state) is a dict with fields:

- `name`, `description`
- `checks`: list of trigger predicates; all must pass
  - `{ "type": "url" | "text" | "element", "value": ... }`
- `actions`: ordered Python call strings bound to the browser API
- `end_state` (optional): string reason that marks a terminal state

Execution semantics (in `StateExecutor.execute`):

- Poll for passing states every `transition_period` seconds.
- If none pass, run a no-states timer and either continue or fail with `no_states_timeout`.
- If multiple pass and `allow_multiple_states=False`, fail with a diagnostic.
- When a state passes, execute its `actions` with spacing `action_period`.
- If the same state repeats and is not marked continuous, enforce a `state_timeout`.
- Succeed immediately if a state has `end_state`.

### Synthesis and Regeneration

- Input specification: a list of `StatePrompt` entries (name, description, triggers, actions, optional terminal message), e.g., in `streaming/disney-plus-espn.py`.
- On-demand synthesis (`StateAgent._generate_state`):
  - Judge Agent chooses the next concrete state (producing `checks` and an `end_state` if applicable).
  - Browser Agent converts the judged instruction into executable `Code` messages; `Message.Code.to_code` serializes them into Python action strings and adds coordinate fallbacks.
  - The synthesized state is prepended to `states` and appended to `executed`. If terminal, execution ends with success.
- Caching and reuse: compiled states are persisted to JSON (e.g., `streaming/states/4-disney-plus-espn.json`) for deterministic replay without LLMs.

### Triggers and Actions (Implemented)

- Triggers (`BrowserManager.detect_trigger`):
  - `url`: strict URL equality
  - `text`: exact text presence via XPath
  - `element`: presence/visibility of an `enhancedCssSelector` element
- Actions (whitelisted):
  - `navigate_to(url)`, `click(by, selector, ...)`, `type(by, selector, text, ...)`
  - `press_key(key)`, `scroll(direction, scroll_amount, ...)`, `scroll_to(by, selector)`
  - `wait(seconds)`, `save_html(filename)`

### Example: Disney Plus ESPN Workflow

The Disney Plus ESPN task is specified via `StatePrompt` objects and compiled into a concrete FSM JSON at `streaming/states/4-disney-plus-espn.json`. A shortened excerpt illustrates checks and actions:

```json
{
  "name": "On the Disney Plus Home Page (When Logged In)",
  "checks": [{ "type": "url", "value": "https://www.disneyplus.com/home" }],
  "actions": [
    "click(by='css selector', selector='a...[data-testid=\"set-item\"][aria-label=\"ESPN\"][href=\"/browse/espn\"]', button='left', percentage=0.5, scroll_to=True, ...)"
  ]
}
```

```json
{
  "name": "On the Movie/Show Page",
  "checks": [
    { "type": "text", "value": "CONTINUE" },
    {
      "type": "element",
      "value": "a...[data-testid=\"playback-action-button\"]"
    }
  ],
  "actions": [
    "press_key(key='tab')",
    "press_key(key='enter')",
    "press_key(key='space')",
    "click(by='css selector', selector='div.progress-bar__container...', percentage=0.2, ...)",
    "wait(seconds=5)"
  ],
  "end_state": "Action Completed"
}
```

### Execution Modes

- Deterministic Replay (no LLM):
  - Load states from JSON and call `StateExecutor.execute(states, parameters, config)`.
- Regenerative Mode (with LLM):
  - When no states pass or at startup without prior states, `StateAgent` routes to synthesis.
  - New states are generated from current DOM perception and high-level prompts, then executed.

### Robustness Mechanisms

- Stable selectors via `enhancedCssSelector` and exact text matching.
- Fallback coordinates embedded by `Message.Code.to_code` for resilient clicking/typing under minor layout shifts.
- Timeouts: `no_states_timeout`, `state_timeout`, and `recursion_limit` prevent deadlocks.
- Error routing: When `use_llm=True`, actionable errors transfer control to synthesis; otherwise, execution fails fast with diagnostics.

### Key Implementation References

- FSM Orchestration: `state_agent/state_agent/agent.py` (class `StateAgent`)
- Deterministic Execution: `state_agent/actions/state_executor.py` (class `StateExecutor`)
- Browser Control + Triggers: `state_agent/actions/browser_manager.py` (class `BrowserManager`)
- Browser Agent Loop + Prompts: `state_agent/state_agent/browser_agent/agent.py`, `state_agent/state_agent/browser_agent/prompt.py`
- DOM Utilities: `state_agent/dom/webmarker.py`, `state_agent/dom/dom_parser.py`
- Example Entrypoint: `streaming/disney-plus-espn.py`
- Compiled FSM Artifact: `streaming/states/4-disney-plus-espn.json`

### Reproducibility & Running the Example

- Persisted FSMs enable reproducible runs without LLM calls. The Disney Plus ESPN example reads/writes `streaming/states/4-disney-plus-espn.json` and executes with:
  - `StateAgent.run(prompt, states, parameters, use_llm=True|False)`
  - Config knobs: `allow_multiple_states`, `transition_period`, `no_states_timeout`, `action_period`, `state_timeout`, `recursion_limit`.

### Notes on Privacy and Security

- Credentials and personal data should be injected via `parameters` and managed with environment variables or secret stores. Avoid hardcoding sensitive values in prompts or actions.
- Headless-evading browser configurations are used for stability; respect site terms and consent requirements.

### Limitations and Future Work

- Richer trigger logic (e.g., semantic matching, fuzzy selectors) with graceful degradation.
- Learning-to-cache shared subgraphs across workflows and applications.
- Formal guarantees on synthesis minimality and recovery strategies under aggressive UI changes.
