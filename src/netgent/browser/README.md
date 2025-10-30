# NetGent Browser Module

This module handles all browser automation functionality including session management, action execution, and DOM manipulation.

## Key Components

- **BrowserSession**: Manages SeleniumBase browser instances with anti-detection
- **BaseController**: Abstract base class for actions and triggers
- **PyAutoGUIController**: Concrete implementation using PyAutoGUI for robust UI control
- **ActionRegistry**: Registry for managing browser actions
- **TriggerRegistry**: Registry for managing state triggers
- **DOM Utilities**: DOM marking, parsing, coordinate fallback, element detection

## Features

- Undetectable browser mode (bypasses bot detection)
- Decorator-based action/trigger registration
- Hybrid Selenium + PyAutoGUI control for reliability
- DOM parsing and marking utilities
- Coordinate fallback for unreliable selectors
