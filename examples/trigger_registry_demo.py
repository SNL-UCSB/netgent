"""
Demo showing the trigger registry system.

This demonstrates:
1. How triggers are automatically registered using the @trigger decorator
2. How to use TriggerRegistry to check triggers by name
3. JSON format for trigger checks: {"type": "trigger_name", "params": {...}}
"""

from netgent.browser import BrowserSession, PyAutoGUIController
from netgent.browser.registry import TriggerRegistry

# Setup browser and controller
session = BrowserSession()
controller = PyAutoGUIController(session.driver)

# Create trigger registry
trigger_registry = TriggerRegistry(controller)

# Show all available triggers
print("Available triggers:", list(trigger_registry.get_all_triggers().keys()))
# Output: ['element', 'url', 'text']

# Navigate to a page
controller.navigate("https://www.google.com")
controller.wait(2)

# Check triggers directly using the registry
print("\n--- Direct trigger checking ---")

# Check URL trigger
is_google = trigger_registry.check("url", {"url": "https://www.google.com/"})
print(f"Is Google homepage: {is_google}")

# Check element trigger
has_search_box = trigger_registry.check("element", {
    "by": "css selector",
    "selector": "textarea[name='q']",
    "check_visibility": True
})
print(f"Has search box: {has_search_box}")

# Check text trigger (should fail - no "results" text on homepage)
has_results_text = trigger_registry.check("text", {
    "text": "results",
    "check_visibility": True
})
print(f"Has results text: {has_results_text}")

# Get trigger metadata
print("\n--- Trigger metadata ---")
element_meta = trigger_registry.get_trigger_metadata("element")
print(f"Element trigger metadata: {element_meta}")

# Cleanup
controller.quit()

