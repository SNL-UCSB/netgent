# Browser Automation

This module handles all browser automation functionality including session management, action execution, and DOM manipulation.

## Overview

The browser module provides a clean abstraction layer over SeleniumBase for reliable web automation. It implements:

- Browser session initialization with anti-detection measures
- Controller pattern for extensible action execution
- Registry system for actions and triggers
- Utilities for DOM interaction and element detection

## Architecture

```
browser/
├── session.py              # Browser session management
├── controller/             # Action execution controllers
│   ├── base.py            # Base controller with common actions/triggers
│   └── pyautogui_controller.py  # PyAutoGUI-based controller
├── registry/              # Registration system
│   ├── action.py          # Action registry and decorators
│   ├── trigger.py         # Trigger registry and decorators
│   └── controller.py      # Combined metaclass for registration
└── utils/                 # DOM utilities
    ├── mark_dom.py        # Visual DOM element marking
    ├── parse_dom.py       # DOM parsing and element extraction
    ├── find_trigger.py    # Trigger element detection
    ├── build_dom.js       # JavaScript for DOM building
    ├── avaliable_trigger.js  # JavaScript for trigger detection
    └── mark_dom.py        # DOM element marking utilities
```

## Components

### session.py - Browser Session Management

Initializes and manages SeleniumBase browser instances with optimized settings.

**Features:**

- Undetectable browser mode (bypasses bot detection)
- Preconfigured Chrome arguments for stability
- Proxy support
- User data directory support
- Fake media streams for testing

**Usage:**

```python
from netgent.browser.session import BrowserSession

# Basic session
session = BrowserSession()
driver = session.driver

# With proxy
session = BrowserSession(proxy="http://proxy:port")

# With custom profile
session = BrowserSession(user_data_dir="/path/to/profile")

# Cleanup
session.quit()
```

**Default Arguments:**

- `--force-device-scale-factor=1`: Consistent rendering
- `--disable-dev-shm-usage`: Prevent shared memory issues
- `--disable-blink-features=AutomationControlled`: Hide automation
- `--no-sandbox`: Required for some environments
- `--use-fake-ui-for-media-stream`: Mock media permissions
- `--use-fake-device-for-media-stream`: Mock media devices

### controller/ - Action Controllers

Controllers implement browser actions using the decorator-based registry pattern.

#### base.py - BaseController

Abstract base class defining common actions and triggers.

**Core Actions:**

- `navigate(url)`: Navigate to URL
- `wait(seconds)`: Wait for specified duration
- `terminate(reason)`: End execution
- `click(by, selector, x, y)`: Click element or coordinates
- `type(text, by, selector, x, y)`: Type text into element
- `scroll_to(by, selector, x, y)`: Scroll to element/coordinates
- `scroll(pixels, direction, by, selector, x, y)`: Scroll by amount
- `press_key(key)`: Press keyboard key
- `move(by, selector, x, y)`: Move mouse to element/coordinates

**Core Triggers:**

- `check_element(by, selector, check_visibility, timeout)`: Check element presence
- `check_url(url)`: Check current URL
- `check_text(text, check_visibility, timeout)`: Check text presence

**Utility Methods:**

```python
# Check if element is visible in viewport
is_visible = controller.is_element_visible_in_viewpoint(element)

# Get absolute screen coordinates for element
abs_x, abs_y = controller.get_element_coordinates(x, y, width, height)
```

**Usage:**

```python
from netgent.browser.controller.base import BaseController

class MyController(BaseController):
    @action()
    def custom_action(self, param: str):
        # Your implementation
        pass

    @trigger(name="custom_check")
    def custom_trigger(self, param: str) -> bool:
        # Return True/False
        pass
```

#### pyautogui_controller.py - PyAutoGUI Controller

Concrete implementation using PyAutoGUI for robust mouse/keyboard control.

**Features:**

- Hybrid approach: Selenium for detection, PyAutoGUI for interaction
- Robust against element state changes
- Handles overlays and dynamic content
- Fallback to coordinates when selectors fail

**Why PyAutoGUI?**

- More reliable for complex UI interactions
- Bypasses JavaScript interception
- Works with elements that block Selenium
- Better handling of overlays and modals

**Usage:**

```python
from netgent.browser.controller import PyAutoGUIController

controller = PyAutoGUIController(driver)
controller.click(by="css selector", selector="#button")
controller.type_text("Hello", x=100, y=200)  # Fallback to coordinates
```

### registry/ - Registration System

Automatic registration of actions and triggers using Python decorators and metaclasses.

#### Decorators

```python
@action(name="custom_name")  # Optional: custom name
def my_action(self, param: str):
    """Action implementation"""
    pass

@trigger(name="custom_check")
def my_trigger(self, param: str) -> bool:
    """Trigger implementation - must return bool"""
    pass
```

#### Registries

```python
from netgent.browser.registry import ActionRegistry, TriggerRegistry

# Action registry
action_registry = ActionRegistry(controller)
result = action_registry.execute("click", {"by": "id", "selector": "button"})
all_actions = action_registry.get_all_actions()

# Trigger registry
trigger_registry = TriggerRegistry(controller)
is_satisfied = trigger_registry.check("element", {"by": "id", "selector": "div"})
all_triggers = trigger_registry.get_all_triggers()
```

### utils/ - DOM Utilities

Helper functions for DOM interaction and element detection.

#### mark_dom.py

Visually marks interactive elements on the page with labels.

**Features:**

- Assigns unique MMIDs (Multi-Modal IDs) to elements
- Overlays visual markers for debugging
- Captures screenshot with annotations
- Returns element data for LLM processing

**Usage:**

```python
from netgent.browser.utils import mark_page

elements, description, screenshot = mark_page(driver).with_retry().invoke(None)
```

**Returns:**

- `elements`: Dict mapping MMID → element data (selector, position, text, etc.)
- `description`: Text description of elements for LLM
- `screenshot`: Base64-encoded annotated screenshot

#### parse_dom.py

Parses the DOM to extract interactive elements and their properties.

**Extracted Properties:**

- CSS selectors (enhanced and standard)
- XPath
- Element position and size
- Text content
- ARIA labels and accessible names
- Visibility status

#### find_trigger.py

Identifies potential trigger elements on the page.

**Features:**

- Detects stable elements for state triggers
- Extracts text content and selectors
- Filters out unstable/temporary elements

**Usage:**

```python
from netgent.browser.utils import find_trigger

triggers = find_trigger(driver)
# Returns list of potential trigger elements with selectors and text
```

## Action/Trigger Parameters

### Common Parameters

**Element Selection:**

- `by`: Locator strategy (`"id"`, `"css selector"`, `"xpath"`, etc.)
- `selector`: The selector string

**Coordinate Fallback:**

- `x`: X coordinate on screen
- `y`: Y coordinate on screen

All element-based actions support fallback to coordinates if selector fails or is not provided.

### Example Action Definitions

```python
# Click using selector
{"type": "click", "params": {"by": "css selector", "selector": "#submit"}}

# Click using coordinates (fallback)
{"type": "click", "params": {"x": 500, "y": 300}}

# Type text with both methods
{"type": "type", "params": {
    "text": "Hello",
    "by": "id",
    "selector": "input",
    "x": 100,  # Fallback if selector fails
    "y": 200
}}

# Scroll with direction
{"type": "scroll", "params": {"pixels": 500, "direction": "down"}}

# Press key
{"type": "press_key", "params": {"key": "Enter"}}

# Navigate
{"type": "navigate", "params": {"url": "https://example.com"}}

# Terminate
{"type": "terminate", "params": {"reason": "Task completed"}}
```

### Example Trigger Definitions

```python
# Check element exists
{"type": "element", "params": {
    "by": "css selector",
    "selector": "#element",
    "check_visibility": True,
    "timeout": 0.1
}}

# Check URL
{"type": "url", "params": {"url": "https://example.com/page"}}

# Check text presence
{"type": "text", "params": {
    "text": "Welcome",
    "check_visibility": True,
    "timeout": 0.1
}}
```

## Extending the System

### Adding New Actions

1. Extend BaseController or an existing controller:

```python
from netgent.browser.controller.base import BaseController
from netgent.browser.registry import action

class MyController(BaseController):
    @action(name="drag")
    def drag_element(self, from_selector: str, to_selector: str):
        # Implementation
        pass
```

2. Actions are automatically registered via the `@action()` decorator
3. Use the action in your workflow:

```python
{"type": "drag", "params": {"from_selector": "#src", "to_selector": "#dst"}}
```

### Adding New Triggers

1. Add trigger method to controller:

```python
from netgent.browser.registry import trigger

class MyController(BaseController):
    @trigger(name="has_class")
    def check_has_class(self, selector: str, class_name: str) -> bool:
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        return class_name in element.get_attribute("class")
```

2. Use the trigger in state checks:

```python
{"type": "has_class", "params": {"selector": "#div", "class_name": "active"}}
```

## Best Practices

1. **Prefer Selectors over Coordinates**: Use CSS selectors or XPath when possible, with coordinates as fallback
2. **Add Waits**: Always wait for page load/element visibility before interactions
3. **Use Enhanced Selectors**: The `enhanced_css_selector` from parse_dom is more robust
4. **Check Visibility**: Use `check_visibility=True` for triggers to avoid hidden elements
5. **Handle Failures Gracefully**: Actions should handle element not found errors
6. **Test Incrementally**: Test new actions/triggers in isolation before integration
7. **Use Appropriate Timeouts**: Balance speed vs reliability in trigger checks

## Troubleshooting

**Element Not Found:**

- Increase timeout values
- Check if element is in iframe
- Verify selector is correct
- Wait for page to fully load

**Click Not Working:**

- Element might be covered by overlay
- Try scrolling element into view first
- Use PyAutoGUI controller for stubborn elements

**Trigger Not Firing:**

- Check visibility requirements
- Verify timeout is sufficient
- Test trigger in browser console
- Check if element is dynamically loaded

## Performance Tips

- Use short timeouts for triggers (0.1-0.5s) to avoid blocking
- Cache DOM elements when making multiple checks
- Minimize screenshot captures (expensive operation)
- Reuse controller instances across actions
- Use CSS selectors over XPath when possible (faster)

## Related Documentation

- [NetGent Core](../README.md)
- [Components](../components/README.md)
- [Examples](../../../examples/README.md)
