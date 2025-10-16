# NetGent Core

The core NetGent framework for agent-based automation of network application workflows.

## Overview

NetGent is an AI-agent framework that combines the flexibility of language-based agents with the reliability of compiled execution. It allows users to specify workflows as natural-language rules that define state-dependent actions, which are then compiled into executable code.

## Architecture

```
netgent/
├── agent.py                    # Main NetGent orchestrator
├── browser/                    # Browser automation components
│   ├── session.py             # Browser session management
│   ├── controller/            # Action execution controllers
│   ├── registry/              # Action and trigger registries
│   └── utils/                 # DOM manipulation utilities
└── components/                # Core workflow components
    ├── program_controller/    # State checking and routing
    ├── state_executor/        # State action execution
    ├── state_synthesis/       # LLM-based state generation
    └── web_agent/            # LLM-driven browser interaction
```

## Core Components

### agent.py - NetGent Orchestrator

The main entry point that orchestrates the entire workflow using a LangGraph state machine.

**Key Classes:**

- `NetGent`: Main agent class
- `NetGentState`: TypedDict defining the workflow state

**Workflow Nodes:**

1. **program_controller**: Checks which states' triggers are satisfied
2. **state_executor**: Executes actions of matched states
3. **state_synthesis**: Uses LLM to select and define new states
4. **web_agent**: Generates and executes browser actions using LLM

**Configuration Options:**

```python
config = {
    "action_period": 1,          # Wait time between actions (seconds)
    "transition_period": 3,      # Wait time between state checks (seconds)
    "recursion_limit": 100,      # Max workflow iterations
    "allow_multiple_states": False,  # Allow multiple states to match
    "state_timeout": 30,         # Timeout for non-continuous states (seconds)
}
```

**Usage:**

```python
from netgent.agent import NetGent
from langchain_google_vertexai import ChatVertexAI

agent = NetGent(
    driver=None,  # Optional: custom browser driver
    controller=None,  # Optional: custom controller
    llm=ChatVertexAI(model="gemini-2.0-flash-exp"),
    config=config
)

result = agent.run(
    state_prompts=[...],      # Natural language state definitions
    state_repository=[...]    # Previously compiled states
)
```

### browser/

Browser automation layer providing session management, action execution, and DOM interaction.

See [browser/README.md](browser/README.md) for details.

### components/

Core components implementing the NetGent workflow logic.

See [components/README.md](components/README.md) for details.

## Workflow Execution

The NetGent workflow follows this cycle:

1. **Start** → program_controller
2. **program_controller**: Check if any state triggers are satisfied
   - If triggers match → state_executor
   - If no match → state_synthesis
   - If recursion limit reached → END
3. **state_executor**: Execute matched state's actions → program_controller
4. **state_synthesis**: Select appropriate state from prompts → web_agent
5. **web_agent**: Generate and execute browser actions
   - If end_state defined → END
   - Otherwise → program_controller

## State Repository

The state repository is a list of state dictionaries with the following structure:

```python
{
    "name": "State Name",
    "description": "What this state does",
    "checks": [
        {"type": "url", "params": {"url": "https://example.com"}},
        {"type": "text", "params": {"text": "Welcome"}}
    ],
    "actions": [
        {"type": "click", "params": {"by": "css selector", "selector": "#button"}},
        {"type": "type", "params": {"text": "Hello", "by": "id", "selector": "input"}}
    ],
    "end_state": "",  # Optional: reason to terminate workflow
    "executed": [],   # Child states executed from this state
    "config": {
        "continuous": False  # If True, skip timeout checks
    }
}
```

## State Prompts

State prompts provide high-level descriptions for LLM-based state synthesis:

```python
from utils.message import StatePrompt

prompt = StatePrompt(
    name="Login to Site",
    description="Authenticate user on login page",
    triggers=["If login form is visible"],
    actions=[
        "Enter username into username field",
        "Enter password into password field",
        "Click login button"
    ],
    end_state=""  # Empty = continue workflow, non-empty = terminate
)
```

## Error Handling

NetGent includes several safety mechanisms:

- **Recursion Limit**: Prevents infinite loops
- **State Timeout**: Detects stuck states
- **Action Registry**: Validates actions before execution
- **Trigger Validation**: Ensures trigger conditions are checkable

## Best Practices

1. **Define Clear State Descriptions**: Help the LLM understand workflow intent
2. **Use Specific Triggers**: More specific triggers = better state matching
3. **Cache States**: Store state repository to reduce LLM API calls
4. **Set Appropriate Timeouts**: Balance responsiveness with reliability
5. **Handle End States**: Always define clear termination conditions
6. **Test Incrementally**: Build complex workflows from simple components

## Advanced Features

### State Timeout

Non-continuous states that repeatedly match will timeout after `state_timeout` seconds:

```python
# This state will timeout if it keeps matching without transitioning
{
    "name": "Waiting for Result",
    "config": {"continuous": False},  # Default
    # ... checks and actions
}

# This state will never timeout
{
    "name": "Streaming Video",
    "config": {"continuous": True},
    # ... checks and actions
}
```

### Executed State Tracking

Each state tracks which child states were generated from it:

```python
{
    "name": "Parent State",
    "executed": [
        {"name": "Child State 1", ...},
        {"name": "Child State 2", ...}
    ]
}
```

This enables:

- Workflow visualization
- State reuse detection
- Debugging state transitions

## Extending NetGent

### Adding Custom Controllers

```python
from netgent.browser.controller.base import BaseController

class MyController(BaseController):
    @action()
    def my_custom_action(self, param: str):
        # Implementation
        pass

agent = NetGent(controller=MyController(driver))
```

### Custom LLM Integration

NetGent works with any LangChain-compatible LLM:

```python
from langchain_anthropic import ChatAnthropic

agent = NetGent(llm=ChatAnthropic(model="claude-3-sonnet"))
```

## Performance Optimization

- **State Caching**: Reuse compiled states across runs
- **Reduced Prompting**: State repository minimizes LLM calls
- **Parallel Checking**: Triggers checked efficiently
- **Smart Retry**: Built-in retry logic for DOM operations

## Troubleshooting

**Workflow Stuck in Loop:**

- Check state timeout settings
- Verify trigger conditions are mutually exclusive
- Review executed state history

**LLM Not Following Instructions:**

- Adjust temperature (lower = more deterministic)
- Make state descriptions more specific
- Review prompt templates in components

**Actions Failing:**

- Increase wait periods between actions
- Check element selectors are correct
- Verify page load timing

## Related Documentation

- [Browser Components](browser/README.md)
- [Workflow Components](components/README.md)
- [Examples](../../examples/README.md)
