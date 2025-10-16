# Components

Core components implementing the NetGent workflow logic. These components work together to create an intelligent, adaptive browser automation system.

## Overview

The components layer implements the four main subsystems of NetGent:

1. **Program Controller**: State checking and workflow routing
2. **State Executor**: Execution of state actions
3. **State Synthesis**: LLM-based state selection and generation
4. **Web Agent**: Intelligent browser interaction using vision-language models

## Architecture

```
components/
├── program_controller/     # State checking and routing
│   └── controller.py
├── state_executor/        # State action execution
│   └── executor.py
├── state_synthesis/       # LLM-based state generation
│   ├── state_synthesis.py
│   ├── prompt.py
│   └── prompts/
│       ├── CHOOSE_STATE_PROMPT.md
│       ├── DEFINE_TRIGGER_PROMPT.md
│       └── PROMPT_ACTION_PROMPT.md
└── web_agent/            # LLM-driven browser interaction
    ├── web_agent.py
    └── prompts/
        ├── ACTION_PROMPT.md
        ├── ACTION_SHORT_PROMPT.md
        ├── EXECUTE_PROMPT.md
        ├── PLAN_PROMPT.md
        ├── REPLAN_PROMPT.md
        └── RULES_PROMPT.md
```

## Components

### program_controller/ - State Checking and Routing

The Program Controller determines which states' trigger conditions are satisfied and routes workflow execution accordingly.

**Class: `ProgramController`**

**Purpose:**

- Evaluate state trigger conditions
- Determine which states should execute
- Enforce single vs. multiple state execution policies

**Configuration:**

```python
config = {
    "allow_multiple_states": False,  # Allow multiple states to match
}
```

**Usage:**

```python
from netgent.components.program_controller.controller import ProgramController

controller = ProgramController(browser_controller, config)
matching_states = controller.check(state_repository)
```

**Key Methods:**

- `check(states: list[dict]) -> list[dict]`: Check all states and return matches

  - Iterates through state repository
  - Evaluates each state's trigger conditions
  - Returns list of matching states
  - Raises error if multiple states match (when not allowed)

- `_check_state(state: dict) -> bool`: Check if single state's triggers are satisfied
  - All triggers must pass (AND logic)
  - Uses TriggerRegistry to evaluate each trigger
  - Returns True only if all triggers satisfied

**How It Works:**

1. Receives state repository from NetGent agent
2. For each state, evaluates all trigger conditions
3. Collects states where ALL triggers pass
4. Validates against multiple state policy
5. Returns matching states for execution

**Example State Check:**

```python
state = {
    "name": "Login Page",
    "checks": [
        {"type": "url", "params": {"url": "https://site.com/login"}},
        {"type": "element", "params": {"by": "id", "selector": "login-form"}}
    ],
    # ... actions
}
# Returns True only if both URL matches AND element exists
```

### state_executor/ - State Action Execution

The State Executor executes the actions defined in matched states.

**Class: `StateExecutor`**

**Purpose:**

- Execute state action sequences
- Manage timing between actions
- Handle action errors gracefully

**Configuration:**

```python
config = {
    "action_period": 1,  # Wait time between actions (seconds)
}
```

**Usage:**

```python
from netgent.components.state_executor.executor import StateExecutor

executor = StateExecutor(browser_controller, config)
executor.run(state)
```

**Key Methods:**

- `run(state: dict)`: Execute all actions in a state

  - Iterates through state's action list
  - Executes each action via ActionRegistry
  - Waits between actions (except after last)
  - Logs execution progress

- `execute(action: dict)`: Execute single action
  - Validates action structure
  - Calls ActionRegistry with action type and params
  - Handles and logs errors
  - Returns action result

**How It Works:**

1. Receives matched state from Program Controller
2. Extracts action list from state
3. For each action:
   - Validates action format
   - Executes via ActionRegistry
   - Waits specified period (except after last action)
4. Logs completion

**Example State Execution:**

```python
state = {
    "name": "Submit Form",
    "actions": [
        {"type": "type", "params": {"text": "user@example.com", "by": "id", "selector": "email"}},
        {"type": "type", "params": {"text": "password", "by": "id", "selector": "pass"}},
        {"type": "click", "params": {"by": "css selector", "selector": "button[type='submit']"}},
        {"type": "wait", "params": {"seconds": 2}}
    ]
}
# Executes each action in sequence with 1-second delays
```

### state_synthesis/ - LLM-Based State Generation

The State Synthesis component uses LLMs to select appropriate states and generate trigger conditions when no existing state matches.

**Class: `StateSynthesis`**

**Purpose:**

- Select appropriate state from user-defined prompts
- Generate trigger conditions for states
- Create action prompts for Web Agent
- Track execution history

**Workflow:**

```
select_state → define_trigger → prompt_action → END
```

**Usage:**

```python
from netgent.components.state_synthesis import StateSynthesis

synthesis = StateSynthesis(llm, browser_controller)
result = synthesis.run(prompts=state_prompts, executed=executed_states)
```

**Key Methods:**

- `run(prompts, executed)`: Execute full synthesis workflow

  - Returns: `{"choice": StatePrompt, "triggers": list, "prompt": str}`

- `_select_state(state)`: Choose appropriate state

  - Analyzes execution history
  - Examines current page state (URL, title)
  - Selects matching state from prompts
  - Uses CHOOSE_STATE_PROMPT template

- `_define_trigger(state)`: Generate trigger conditions

  - Scans page for potential trigger elements
  - Extracts URLs, text, and selectors
  - Prompts LLM to select appropriate triggers
  - Uses DEFINE_TRIGGER_PROMPT template
  - Returns list of trigger definitions

- `_prompt_action(state)`: Generate action prompt
  - Creates detailed instructions for Web Agent
  - Includes execution history context
  - Formats user actions from state prompt
  - Uses PROMPT_ACTION_PROMPT template

**How It Works:**

1. **State Selection:**

   - LLM examines execution history
   - Compares current page state to available prompts
   - Selects most appropriate state to execute

2. **Trigger Definition:**

   - Scans page for stable trigger elements (URL, text, elements)
   - Presents triggers to LLM
   - LLM selects triggers that match state's natural language conditions
   - Converts to executable trigger definitions

3. **Action Prompting:**
   - Formats state's action list
   - Adds execution context
   - Creates detailed prompt for Web Agent

**Example Flow:**

```python
# Input: State prompts
prompts = [
    StatePrompt(
        name="Search Google",
        triggers=["If on Google homepage"],
        actions=["Type query", "Press Enter"]
    )
]

# Output: Synthesized state info
{
    "choice": StatePrompt(...),
    "triggers": [
        {"type": "url", "params": {"url": "https://www.google.com"}},
        {"type": "element", "params": {"by": "css selector", "selector": "input[name='q']"}}
    ],
    "prompt": "1. Type 'SeleniumBase Python' into the search box\n2. Press Enter to search\nTERMINATE ACTION"
}
```

### web_agent/ - LLM-Driven Browser Interaction

The Web Agent uses vision-language models to understand web pages and generate appropriate browser actions.

**Class: `WebAgent`**

**Purpose:**

- Understand web pages using vision (screenshots + DOM)
- Plan action sequences to achieve goals
- Generate executable browser actions
- Adapt to changing page states

**Workflow:**

```
START → annotate → plan → execute → check_continue
          ↑                           |
          └───────────────────────────┘
```

**Usage:**

```python
from netgent.components.web_agent import WebAgent

web_agent = WebAgent(llm, browser_controller)
result = web_agent.run(
    user_query="Type 'hello' into the search box and press Enter",
    wait_period=0.5
)
```

**Key Methods:**

- `run(user_query, messages, wait_period)`: Execute web agent workflow

  - Returns: `{"actions": list, "messages": list}`

- `_annotate(state)`: Capture page state

  - Marks interactive elements with MMIDs
  - Captures screenshot with annotations
  - Extracts element metadata
  - Updates message history

- `_plan(state)`: Create action plan

  - Analyzes user query
  - Examines current page (screenshot + DOM)
  - Reviews action history
  - Generates step-by-step plan
  - Uses PLAN_PROMPT or REPLAN_PROMPT

- `_execute(state)`: Generate and execute action

  - Follows global plan
  - Selects appropriate action and element
  - Converts to executable format (selector + coordinates)
  - Executes via ActionRegistry
  - Updates action history
  - Uses ACTION_PROMPT and EXECUTE_PROMPT

- `_should_continue(state)`: Determine if workflow continues

  - Checks if last action was "terminate"
  - Enforces max timestep limit (50)
  - Returns END or "annotate"

- `_convert_action_to_json(action_output)`: Convert LLM output to executable action
  - Maps MMID to element data (selector, coordinates)
  - Prefers selectors, falls back to coordinates
  - Adds position data for reliability

**How It Works:**

1. **Annotation:**

   - Marks all interactive elements on page
   - Assigns unique MMID to each element
   - Captures screenshot with visual labels
   - Extracts element properties (selector, position, text)

2. **Planning:**

   - LLM analyzes user query and page state
   - Generates multi-step plan
   - Considers action history to avoid loops
   - Creates or updates global plan

3. **Execution:**

   - LLM selects next action from plan
   - Chooses target element by MMID
   - Specifies action parameters
   - System converts to executable format:
     - Looks up element data by MMID
     - Extracts selector (enhanced CSS > CSS > XPath)
     - Calculates absolute screen coordinates
     - Creates action with both selector and coordinates
   - ActionRegistry executes the action
   - Records action in history

4. **Continuation Check:**
   - If action is "terminate": END
   - If max timesteps exceeded: END
   - Otherwise: Return to annotation (observe result of action)

**Example Interaction:**

```python
# Input query
user_query = "Search for 'Python selenium' on Google"

# Web agent output
{
    "actions": [
        {"type": "click", "params": {"by": "css selector", "selector": "input[name='q']", "x": 450, "y": 320}},
        {"type": "type", "params": {"text": "Python selenium", "by": "css selector", "selector": "input[name='q']"}},
        {"type": "press_key", "params": {"key": "Enter"}},
        {"type": "terminate", "params": {"reason": "Search submitted successfully"}}
    ],
    "messages": [...]  # Full interaction history
}
```

## Component Interaction

### Typical Workflow

1. **NetGent Agent** initializes with state_prompts and state_repository
2. **Program Controller** checks if any states match current page
   - **If match found:** → State Executor → back to Program Controller
   - **If no match:** → State Synthesis
3. **State Synthesis** selects appropriate state and generates triggers
4. **Web Agent** generates and executes actions for the state
5. **NetGent Agent** adds generated state to repository
6. Loop back to Program Controller

### Data Flow

```
StatePrompt (natural language)
    ↓
State Synthesis (LLM)
    ↓
State Dictionary (executable)
    ↓
Program Controller (checks triggers)
    ↓
State Executor (executes actions)
```

## Prompt Engineering

All components use carefully engineered prompts stored in `prompts/` directories:

### State Synthesis Prompts

- **CHOOSE_STATE_PROMPT.md**: State selection logic
- **DEFINE_TRIGGER_PROMPT.md**: Trigger generation instructions
- **PROMPT_ACTION_PROMPT.md**: Action prompt formatting

### Web Agent Prompts

- **PLAN_PROMPT.md**: Initial planning instructions
- **REPLAN_PROMPT.md**: Re-planning after actions
- **ACTION_PROMPT.md**: Action generation format
- **ACTION_SHORT_PROMPT.md**: Concise action instructions
- **EXECUTE_PROMPT.md**: Execution context and rules
- **RULES_PROMPT.md**: General behavior rules

## Configuration Best Practices

**Program Controller:**

- Set `allow_multiple_states=False` for deterministic workflows
- Set `allow_multiple_states=True` for parallel state handling

**State Executor:**

- Increase `action_period` for slow-loading pages
- Decrease for faster, static pages

**State Synthesis:**

- Use specific state descriptions for better LLM selection
- Keep trigger descriptions clear and observable

**Web Agent:**

- Adjust `wait_period` based on page load times
- Lower `temperature` for more deterministic actions
- Higher `temperature` for creative problem-solving

## Extending Components

### Adding Custom Synthesis Logic

```python
from netgent.components.state_synthesis import StateSynthesis

class MyStateSynthesis(StateSynthesis):
    def _select_state(self, state):
        # Custom state selection logic
        # Can add scoring, filtering, etc.
        return super()._select_state(state)
```

### Custom Web Agent Behavior

```python
from netgent.components.web_agent import WebAgent

class MyWebAgent(WebAgent):
    def _plan(self, state):
        # Custom planning logic
        # Can add constraints, optimizations, etc.
        return super()._plan(state)
```

## Troubleshooting

**State Synthesis Issues:**

- LLM selects wrong state: Make descriptions more specific
- Triggers don't fire: Check trigger element stability
- Actions unclear: Improve action descriptions

**Web Agent Issues:**

- Wrong elements clicked: Adjust marking algorithm
- Actions fail: Increase wait_period
- Loops endlessly: Check terminate conditions
- Plan doesn't match intent: Refine query or prompts

**Execution Issues:**

- Actions timeout: Increase action_period
- State doesn't match: Review trigger conditions
- Multiple states match: Set allow_multiple_states=False

## Performance Optimization

- **Cache synthesized states**: Reuse state_repository across runs
- **Minimize LLM calls**: Use cached states when possible
- **Optimize prompts**: Shorter prompts = faster responses
- **Batch operations**: Group related actions in single state
- **Smart retries**: Built-in retry logic for transient failures

## Related Documentation

- [NetGent Core](../README.md)
- [Browser Components](../browser/README.md)
- [Message Utils](../../utils/README.md)
- [Examples](../../../examples/README.md)
