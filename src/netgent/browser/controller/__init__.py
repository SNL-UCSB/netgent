"""
Browser Controllers

Controllers implement browser actions using the decorator-based registry pattern.

This module provides:
    - Abstract base class with common actions and triggers
    - PyAutoGUI-based implementation for robust interaction
    - Decorators for action/trigger registration
    - Registry classes for managing actions and triggers

Classes:
    BaseController: Abstract base with common browser operations
    PyAutoGUIController: Concrete implementation using PyAutoGUI
    
Decorators:
    @action(): Register a method as a browser action
    @trigger(): Register a method as a state trigger
    
Registries:
    ActionRegistry: Execute and manage browser actions
    TriggerRegistry: Check and manage state triggers

Usage:
    from netgent.browser.controller import BaseController, action, trigger
    
    class MyController(BaseController):
        @action()
        def custom_action(self, param: str):
            # Implementation
            pass
        
        @trigger(name="custom_check")
        def custom_trigger(self, param: str) -> bool:
            # Return True/False
            return True
"""

from .base import BaseController
from .pyautogui_controller import PyAutoGUIController
from ..registry import (
    action, ActionRegistry, ActionController,
    trigger, TriggerRegistry, TriggerController,
    ActionTriggerMeta
)

__all__ = [
    "BaseController", "PyAutoGUIController",
    "action", "ActionRegistry", "ActionController",
    "trigger", "TriggerRegistry", "TriggerController",
    "ActionTriggerMeta"
]