"""
State Executor

The State Executor executes the actions defined in matched states.

This component:
- Executes state action sequences
- Manages timing between actions
- Handles action errors gracefully
- Logs execution progress

Classes:
    StateExecutor: Main executor class for running state actions

Usage:
    from netgent.components.state_executor import StateExecutor
    
    executor = StateExecutor(browser_controller, config)
    executor.run(state)
    
Configuration:
    config = {
        "action_period": 1,  # Wait time between actions (seconds)
    }

Example State:
    state = {
        "name": "Submit Form",
        "actions": [
            {"type": "type", "params": {"text": "user@example.com", "by": "id", "selector": "email"}},
            {"type": "click", "params": {"by": "css selector", "selector": "button[type='submit']"}},
        ]
    }
"""

from .executor import StateExecutor

__all__ = ["StateExecutor"]

