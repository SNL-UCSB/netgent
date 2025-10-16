# NetGent API Reference

Complete API documentation for the NetGent framework.

## Table of Contents

- [Core Classes](#core-classes)
- [Browser Components](#browser-components)
- [Workflow Components](#workflow-components)
- [Utilities](#utilities)
- [Type Definitions](#type-definitions)

---

## Core Classes

### NetGent

Main orchestrator class for workflow automation.

```python
from netgent import NetGent

agent = NetGent(
    driver: Driver = None,
    controller: BaseController = None,
    llm: BaseChatModel = None,
    config: Optional[dict] = None
)
```

**Parameters:**

- `driver` (Driver, optional): Custom SeleniumBase driver instance
- `controller` (BaseController, optional): Custom controller implementation
- `llm` (BaseChatModel, optional): LangChain-compatible LLM
- `config` (dict, optional): Configuration dictionary

**Configuration Options:**

```python
{
    "action_period": 1,              # Wait between actions (seconds)
    "transition_period": 3,          # Wait between state checks (seconds)
    "recursion_limit": 100,          # Max workflow iterations
    "allow_multiple_states": False,  # Allow multiple states to match
    "state_timeout": 30,             # Timeout for non-continuous states
}
```

**Methods:**

#### `run(state_prompts, state_repository)`

Execute workflow with given state prompts and repository.

```python
result = agent.run(
    state_prompts: list[StatePrompt] = [],
    state_repository: list[dict[str, Any]] = []
)
```

**Parameters:**

- `state_prompts`: List of StatePrompt objects defining workflow states
- `state_repository`: Previously compiled state definitions

**Returns:**

- `dict`: Contains `state_repository`, `executed_states`, and other workflow data

**Example:**

```python
from netgent import NetGent
from utils.message import StatePrompt
from langchain_google_vertexai import ChatVertexAI

agent = NetGent(llm=ChatVertexAI(model="gemini-2.0-flash-exp"))

prompts = [
    StatePrompt(
        name="Navigate",
        triggers=["If on homepage"],
        actions=["Go to https://example.com"]
    )
]

result = agent.run(state_prompts=prompts)
```

---

## Browser Components

### BrowserSession

Manages browser session with SeleniumBase.

```python
from netgent import BrowserSession

session = BrowserSession(
    proxy: str = None,
    user_data_dir: str | None = None
)
```

**Parameters:**

- `proxy` (str, optional): Proxy URL (e.g., "http://proxy:port")
- `user_data_dir` (str, optional): Chrome user data directory path

**Properties:**

- `driver`: SeleniumBase Driver instance

**Methods:**

#### `start()`

Initialize browser session.

#### `quit()`

Close browser and clean up.

**Example:**

```python
session = BrowserSession(proxy="http://proxy:8080")
driver = session.driver
driver.get("https://example.com")
session.quit()
```

---

### BaseController

Abstract base class for browser controllers.

```python
from netgent.browser.controller import BaseController

class MyController(BaseController):
    def __init__(self, driver: Driver):
        super().__init__(driver)
```

**Core Actions:**

#### `navigate(url: str)`

Navigate to specified URL.

#### `click(by: str = None, selector: str = None, x: float = None, y: float = None)`

Click element or coordinates.

#### `type_text(text: str, by: str = None, selector: str = None, x: float = None, y: float = None)`

Type text into element.

#### `scroll_to(by: str = None, selector: str = None, x: float = None, y: float = None)`

Scroll to element or coordinates.

#### `scroll(pixels: int, direction: str, by: str = None, selector: str = None, x: float = None, y: float = None)`

Scroll by amount in direction ("up" or "down").

#### `press_key(key: str)`

Press keyboard key.

#### `move(by: str = None, selector: str = None, x: float = None, y: float = None)`

Move mouse to element or coordinates.

#### `wait(seconds: float)`

Wait for specified duration.

#### `terminate(reason: str = "Task completed")`

End workflow execution.

**Core Triggers:**

#### `check_element(by: str, selector: str, check_visibility: bool = True, timeout: float = 0.1) -> bool`

Check if element exists and is visible.

#### `check_url(url: str) -> bool`

Check if current URL matches.

#### `check_text(text: str, check_visibility: bool = True, timeout: float = 0.1) -> bool`

Check if text exists on page.

**Example:**

```python
from netgent.browser.controller import BaseController, action, trigger

class CustomController(BaseController):
    @action()
    def custom_click(self, element_id: str):
        self.click(by="id", selector=element_id)

    @trigger(name="has_element")
    def check_has_element(self, element_id: str) -> bool:
        return self.check_element(by="id", selector=element_id)
```

---

### PyAutoGUIController

Concrete controller using PyAutoGUI for actions.

```python
from netgent import PyAutoGUIController

controller = PyAutoGUIController(driver: Driver)
```

Inherits all methods from BaseController with PyAutoGUI implementation.

---

## Workflow Components

### ProgramController

Checks state trigger conditions and routes execution.

```python
from netgent.components import ProgramController

controller = ProgramController(
    controller: BaseController,
    config: Optional[dict] = None
)
```

**Configuration:**

```python
{
    "allow_multiple_states": False
}
```

**Methods:**

#### `check(states: list[dict]) -> list[dict]`

Check which states' triggers are satisfied.

**Example:**

```python
controller = ProgramController(browser_controller)
matching_states = controller.check(state_repository)
```

---

### StateExecutor

Executes actions defined in states.

```python
from netgent.components import StateExecutor

executor = StateExecutor(
    controller: BaseController,
    config: Optional[dict] = None
)
```

**Configuration:**

```python
{
    "action_period": 1  # Wait between actions
}
```

**Methods:**

#### `run(state: dict)`

Execute all actions in a state.

#### `execute(action: dict)`

Execute single action.

**Example:**

```python
executor = StateExecutor(browser_controller)
state = {
    "name": "Login",
    "actions": [
        {"type": "type", "params": {"text": "user", "by": "id", "selector": "username"}},
        {"type": "click", "params": {"by": "id", "selector": "submit"}}
    ]
}
executor.run(state)
```

---

### StateSynthesis

LLM-based state selection and generation.

```python
from netgent.components import StateSynthesis

synthesis = StateSynthesis(
    llm: BaseChatModel,
    controller: BaseController
)
```

**Methods:**

#### `run(prompts: list[StatePrompt], executed: list[dict]) -> dict`

Execute state synthesis workflow.

**Returns:**

```python
{
    "choice": StatePrompt,      # Selected state
    "triggers": list[dict],     # Generated trigger definitions
    "prompt": str              # Action prompt for Web Agent
}
```

**Example:**

```python
synthesis = StateSynthesis(llm, controller)
result = synthesis.run(prompts=state_prompts, executed=[])
```

---

### WebAgent

LLM-driven browser interaction using vision.

```python
from netgent.components import WebAgent

web_agent = WebAgent(
    llm: BaseChatModel,
    controller: BaseController
)
```

**Methods:**

#### `run(user_query: str, messages: list[Message] = [], wait_period: float = 0.5) -> dict`

Execute web agent to accomplish query.

**Parameters:**

- `user_query`: Natural language task description
- `messages`: Previous interaction history
- `wait_period`: Wait time for page loads

**Returns:**

```python
{
    "actions": list[dict],     # Executed actions
    "messages": list[Message]  # Interaction history
}
```

**Example:**

```python
web_agent = WebAgent(llm, controller)
result = web_agent.run(
    user_query="Search for 'Python' and click first result"
)
```

---

## Utilities

### StatePrompt

High-level state definition for workflows.

```python
from utils.message import StatePrompt

prompt = StatePrompt(
    name: str,
    description: str,
    triggers: list[str],
    actions: list[str],
    end_state: Optional[str] = ""
)
```

**Fields:**

- `name`: State identifier
- `description`: What the state does
- `triggers`: Natural language trigger conditions
- `actions`: Natural language action descriptions
- `end_state`: Optional termination reason (empty = continue)

**Example:**

```python
prompt = StatePrompt(
    name="Login",
    description="Authenticate user",
    triggers=["If on login page", "If login form is visible"],
    actions=["Enter username", "Enter password", "Click login"],
    end_state=""  # Empty = continue workflow
)
```

---

### Message Types

#### ActionOutput

LLM-generated action.

```python
from utils.message import ActionOutput

action = ActionOutput(
    action: str,
    mmid: Optional[int],
    params: dict,
    reasoning: str
)
```

#### Metadata

Page state snapshot.

```python
from utils.message import Metadata

metadata = Metadata(
    timestamp: int,
    elements: dict,
    element_description: str,
    screenshot: str,
    dom: str,
    url: str,
    title: str
)
```

---

### Utility Functions

#### `format_context(context: list[Message]) -> str`

Format message history for LLM.

```python
from utils.message import format_context

formatted = format_context(messages)
```

#### `save_context_to_file(context: list[Message], filename: str)`

Save messages to JSON file.

```python
from utils.message import save_context_to_file

save_context_to_file(messages, "history.json")
```

#### `load_context_from_file(filename: str) -> list[Message]`

Load messages from JSON file.

```python
from utils.message import load_context_from_file

messages = load_context_from_file("history.json")
```

---

## Type Definitions

### NetGentState

TypedDict for NetGent workflow state.

```python
class NetGentState(TypedDict):
    state_repository: Optional[list[dict[str, Any]]]
    state_prompts: list[StatePrompt]
    passed_states: Optional[list[dict[str, Any]]]
    recursion_count: Optional[int]
    last_passed_state_name: Optional[str]
    state_timeout_start: Optional[float]
    synthesis_prompt: Optional[str]
    synthesis_choice: Optional[StatePrompt]
    synthesis_triggers: Optional[list[str]]
    executed_states: Optional[list[dict[str, Any]]]
```

### WebAgentState

TypedDict for Web Agent state.

```python
class WebAgentState(TypedDict):
    user_query: str
    messages: List[Message]
    global_plan: str
    timestep: int
    actions: List[dict]
```

---

## Decorator API

### @action()

Register method as browser action.

```python
from netgent.browser.controller import action

@action(name="custom_name")  # Optional custom name
def my_action(self, param: str):
    # Implementation
    pass
```

### @trigger()

Register method as state trigger.

```python
from netgent.browser.controller import trigger

@trigger(name="custom_check")
def my_trigger(self, param: str) -> bool:
    # Must return bool
    return True
```

---

## Registry API

### ActionRegistry

```python
from netgent.browser.registry import ActionRegistry

registry = ActionRegistry(controller)
registry.execute("click", {"by": "id", "selector": "button"})
all_actions = registry.get_all_actions()
```

### TriggerRegistry

```python
from netgent.browser.registry import TriggerRegistry

registry = TriggerRegistry(controller)
is_satisfied = registry.check("url", {"url": "https://example.com"})
all_triggers = registry.get_all_triggers()
```

---

## Complete Example

```python
from netgent import NetGent
from utils.message import StatePrompt
from langchain_google_vertexai import ChatVertexAI
import json

# Initialize agent
agent = NetGent(
    llm=ChatVertexAI(model="gemini-2.0-flash-exp", temperature=0.2),
    config={
        "action_period": 1,
        "transition_period": 3,
        "state_timeout": 30
    }
)

# Define workflow
prompts = [
    StatePrompt(
        name="Navigate to Google",
        description="Open Google homepage",
        triggers=["If browser is ready"],
        actions=["Navigate to https://www.google.com"]
    ),
    StatePrompt(
        name="Perform Search",
        description="Search for NetGent",
        triggers=["If on Google homepage", "If search box visible"],
        actions=["Type 'NetGent' into search", "Press Enter"],
        end_state="Search completed"
    )
]

# Load existing states (if any)
try:
    with open("states.json", "r") as f:
        state_repo = json.load(f)
except FileNotFoundError:
    state_repo = []

# Run workflow
result = agent.run(state_prompts=prompts, state_repository=state_repo)

# Save updated states
with open("states.json", "w") as f:
    json.dump(result["state_repository"], f, indent=2)

print(f"Executed {len(result['executed_states'])} states")
```

---

## See Also

- [README](README.md) - Overview and features
- [INSTALLATION](INSTALLATION.md) - Setup guide
- [Examples](examples/README.md) - Sample workflows
- [Research Paper](https://arxiv.org/abs/2406.08392) - NetGent paper
