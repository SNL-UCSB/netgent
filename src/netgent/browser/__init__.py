"""
Browser Automation Module

This module handles all browser automation functionality including session management,
action execution, and DOM manipulation.

Components:
    BrowserSession: Manages SeleniumBase browser instances with anti-detection
    BaseController: Abstract base class defining actions and triggers
    PyAutoGUIController: Concrete implementation using PyAutoGUI for robust control
    ActionRegistry: Registry for managing browser actions
    TriggerRegistry: Registry for managing state triggers

Key Features:
    - Undetectable browser mode (bypasses bot detection)
    - Decorator-based action/trigger registration
    - Hybrid Selenium + PyAutoGUI for reliability
    - DOM marking and element detection
    - Coordinate fallback when selectors fail

Usage:
    from netgent.browser import BrowserSession, PyAutoGUIController
    
    # Initialize browser session
    session = BrowserSession()
    driver = session.driver
    
    # Create controller for actions
    controller = PyAutoGUIController(driver)
    
    # Execute actions
    controller.click(by="id", selector="button")
    controller.type_text("Hello", by="css selector", selector="input")
"""

from .session import BrowserSession
from .controller.pyautogui_controller import PyAutoGUIController
from .controller.base import BaseController

__all__ = ["BrowserSession", "PyAutoGUIController", "BaseController"]