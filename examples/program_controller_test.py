"""
Example showing how to use ProgramController to check states with trigger registry.

Triggers are now specified in JSON format: {"type": "trigger_name", "params": {...}}
"""

from netgent.browser import BrowserSession, PyAutoGUIController
from netgent.components.program_controller.controller import ProgramController

# Setup browser and controller
session = BrowserSession()
controller = PyAutoGUIController(session.driver)

# Initialize ProgramController
program = ProgramController(controller)

# Define some states with trigger conditions using the new JSON format
states = [
    {
        "name": "search_box_visible",
        "checks": [
            {
                "type": "element",
                "params": {
                    "by": "css selector",
                    "selector": "textarea[name='q']",
                }
            },
        ]
    },
    # {
    #     "name": "google_homepage",
    #     "checks": [
    #         {
    #             "type": "element",
    #             "params": {
    #                 "by": "css selector",
    #                 "selector": "textarea[name='q']",
    #             }
    #         },
    #     ]
    # },
]

# Navigate to Google
controller.navigate("https://www.google.com")
controller.wait(2)

# Check which states pass
passed_states = program.check(states)
print("Passed states:", [s["name"] for s in passed_states])
# Expected output: ['google_homepage', 'search_box_visible']

# Perform a search
controller.type_text("css selector", "textarea[name='q']", "SeleniumBase Python")
controller.press_key("enter")
controller.wait(3)

# Check states again after navigation
passed_states = program.check(states)
print("After search - Passed states:", [s["name"] for s in passed_states])
# Expected output: ['results_page', 'search_text_visible']

# Cleanup
controller.quit()

