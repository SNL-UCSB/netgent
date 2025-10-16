# Utilities

Common utilities and data structures used throughout the NetGent framework.

## Overview

The utils package provides:

- Pydantic models for type-safe message passing
- Formatting functions for LLM context
- State representation classes
- Serialization helpers

## Components

### message.py - Message Models and Utilities

Defines data models for structured communication between NetGent components and LLMs.

## Message Models

### Base Classes

#### `Message`

Base class for all message types. Used for type checking and polymorphism.

#### `Element`

Represents a DOM element with its properties.

**Fields:**

- `enhanced_css_selector`: Enhanced CSS selector (most robust)
- `css_selector`: Standard CSS selector
- `aria_label`: ARIA label attribute
- `accessible_name`: Accessibility name
- `text`: Visible text content
- `x`, `y`: Position coordinates
- `width`, `height`: Element dimensions

**String Representation:**

```xml
<element>
    enhanced css selector: button#submit
    text: Submit Form
    x: 450, y: 320
</element>
```

### Communication Messages

#### `Toolcall`

Represents an executed action/tool call.

**Fields:**

- `name`: Action name (e.g., "click", "type")
- `args`: Action arguments
- `element`: Optional Element that was interacted with
- `error`: Optional error message if action failed

**Usage:**

```python
toolcall = Toolcall(
    name="click",
    args={"by": "id", "selector": "submit"},
    element=Element(text="Submit", x=100, y=200)
)
```

#### `ActionOutput`

Structured output from LLM for action generation.

**Fields:**

- `action`: Action name
- `mmid`: Multi-modal ID of target element
- `params`: Action parameters
- `reasoning`: Explanation of why this action was chosen

**Usage:**

```python
action = ActionOutput(
    action="click",
    mmid=42,
    params={"by": "css selector", "selector": "#button"},
    reasoning="User requested to submit the form"
)
```

#### `Decision`

Represents an agent's decision.

**Fields:**

- `action`: The chosen action
- `reasoning`: Detailed explanation

**Usage:**

```python
decision = Decision(
    action="Navigate to login page",
    reasoning="User is not authenticated and needs to log in"
)
```

#### `Reflection`

Agent's reflection on action success/failure.

**Fields:**

- `is_successful`: Whether action succeeded
- `reason`: Explanation of success/failure
- `next_step`: Recommended next action

**Usage:**

```python
reflection = Reflection(
    is_successful=True,
    reason="Successfully clicked login button",
    next_step="Wait for page to load and verify login"
)
```

#### `Metadata`

Captures page state at a specific point in time.

**Fields:**

- `timestamp`: Iteration/step number
- `elements`: Dict of MMID → Element data
- `element_description`: Text description of elements
- `screenshot`: Base64-encoded screenshot
- `dom`: DOM HTML (optional)
- `url`: Current page URL
- `title`: Page title

**Usage:**

```python
metadata = Metadata(
    timestamp=5,
    elements={1: {...}, 2: {...}},
    element_description="Input field, Submit button",
    screenshot="base64...",
    dom="<html>...</html>",
    url="https://example.com",
    title="Example Page"
)
```

#### `ExecutedState`

Represents a state that has been executed.

**Fields:**

- `timestamp`: When state was executed
- `name`: State name
- `description`: What state does
- `checks`: Trigger conditions
- `actions`: Actions performed

**Usage:**

```python
executed = ExecutedState(
    timestamp=3,
    name="Login",
    description="Authenticate user",
    checks=[{"type": "url", "params": {"url": "..."}}],
    actions=[{"type": "type", "params": {...}}]
)
```

### State Definition

#### `StatePrompt`

High-level state definition for LLM-based state synthesis.

**Fields:**

- `name`: State identifier
- `description`: What the state does
- `triggers`: Natural language trigger conditions
- `actions`: Natural language action descriptions
- `end_state`: Optional termination reason

**Usage:**

```python
state_prompt = StatePrompt(
    name="Submit Search",
    description="Execute a search query",
    triggers=["If search box is visible", "If on search page"],
    actions=[
        "Type the search query into the search box",
        "Click the search button or press Enter"
    ],
    end_state=""  # Empty = continue, non-empty = end workflow
)
```

**String Representation:**

```markdown
## State: Submit Search

- **Description:** Execute a search query
- **Triggers:**
  1. If search box is visible
  2. If on search page
- **Actions:**
  1. Type the search query into the search box
  2. Click the search button or press Enter
```

## Utility Functions

### Context Formatting

#### `format_context(context: list[Message]) -> str`

Formats message history for LLM consumption.

**Features:**

- Converts messages to string representations
- Adds special formatting for Metadata (timesteps)
- Includes all message types

**Usage:**

```python
from utils.message import format_context

context = [
    Metadata(timestamp=1, ...),
    ActionOutput(action="click", ...),
    Metadata(timestamp=2, ...),
    ActionOutput(action="type", ...)
]

formatted = format_context(context)
# Results in human-readable context for LLM
```

#### `format_context_without_reflection(context: list[Message]) -> str`

Same as `format_context` but excludes `Reflection` messages.

**Usage:**

```python
# Useful when you want action history without agent's internal reflections
formatted = format_context_without_reflection(context)
```

### Serialization

#### `save_context_to_file(context: list[Message], filename: str)`

Saves message context to JSON file.

**Usage:**

```python
from utils.message import save_context_to_file

save_context_to_file(messages, "interaction_log.json")
```

#### `load_context_from_file(filename: str) -> list[Message]`

Loads message context from JSON file.

**Features:**

- Automatically detects message types
- Reconstructs appropriate Pydantic models
- Supports Decision, Toolcall, Reflection, and Metadata

**Usage:**

```python
from utils.message import load_context_from_file

messages = load_context_from_file("interaction_log.json")
```

## Type Safety

All message models use Pydantic for:

- Automatic validation
- Type checking
- JSON serialization/deserialization
- Clear error messages

**Example:**

```python
# This will raise validation error - missing required fields
action = ActionOutput(action="click")  # Error: missing reasoning

# This works
action = ActionOutput(
    action="click",
    mmid=1,
    params={},
    reasoning="Clicking submit button"
)
```

## Integration with Components

### Web Agent

Uses `ActionOutput`, `Metadata`, and `Toolcall` for action generation and history tracking:

```python
# Web agent generates ActionOutput
action = ActionOutput(action="click", mmid=5, ...)

# Metadata captures page state
metadata = Metadata(timestamp=1, elements={...}, ...)

# History maintained as list of Messages
state["messages"] = [metadata, action, ...]
```

### State Synthesis

Uses `StatePrompt` for high-level state definitions:

```python
prompts = [
    StatePrompt(name="Login", triggers=[...], actions=[...]),
    StatePrompt(name="Search", triggers=[...], actions=[...])
]

result = state_synthesis.run(prompts=prompts, executed=[])
```

### Program Controller

Receives executed states and checks trigger conditions:

```python
executed = [
    ExecutedState(name="Login", timestamp=1, ...),
    ExecutedState(name="Search", timestamp=2, ...)
]
```

## Best Practices

1. **Use Type Hints**: Leverage Pydantic's type checking

   ```python
   def process_action(action: ActionOutput) -> None:
       # IDE will autocomplete fields
       print(action.reasoning)
   ```

2. **Validate Early**: Let Pydantic catch errors at creation

   ```python
   try:
       action = ActionOutput(**data)
   except ValidationError as e:
       print(f"Invalid action: {e}")
   ```

3. **Use String Representations**: Format for LLM consumption

   ```python
   # Human-readable format for prompts
   prompt = f"Previous action:\n{str(action)}"
   ```

4. **Serialize for Persistence**: Save/load workflow history

   ```python
   save_context_to_file(messages, "workflow_log.json")
   messages = load_context_from_file("workflow_log.json")
   ```

5. **Keep Messages Immutable**: Create new instances rather than modifying

   ```python
   # Good
   new_action = action.model_copy(update={"reasoning": "Updated reason"})

   # Avoid
   action.reasoning = "Updated reason"  # Mutates original
   ```

## Examples

### Complete Workflow Context

```python
from utils.message import (
    StatePrompt, Metadata, ActionOutput,
    format_context, save_context_to_file
)

# Define high-level workflow
state_prompts = [
    StatePrompt(
        name="Navigate to Site",
        description="Open the target website",
        triggers=["If browser is on homepage"],
        actions=["Navigate to https://example.com"]
    )
]

# Track execution
messages = []

# Add page state
messages.append(Metadata(
    timestamp=1,
    url="https://example.com",
    title="Example",
    elements={},
    element_description="Homepage loaded",
    screenshot="...",
    dom=""
))

# Add action
messages.append(ActionOutput(
    action="navigate",
    mmid=None,
    params={"url": "https://example.com"},
    reasoning="Starting workflow"
))

# Format for LLM
context_str = format_context(messages)

# Save for later
save_context_to_file(messages, "workflow_history.json")
```

## Related Documentation

- [NetGent Core](../netgent/README.md)
- [Components](../netgent/components/README.md)
- [Examples](../../examples/README.md)
