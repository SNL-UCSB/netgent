# from netgent.agent import NetGent
from netgent.components.program_controller.controller import ProgramController
from netgent.browser.controller import PyAutoGUIController
from netgent.browser import BrowserSession


state_repository = [
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
        ],
        "actions": [
            {
                "type": "type",
                "params": {
                    "by": "css selector",
                    "selector": "textarea[name='q']",
                    "text": "SeleniumBase Python"
                }
            },
            {"type": "wait", "params": {"seconds": 1}},
            {"type": "press_key", "params": {"key": "enter"}},
            {"type": "wait", "params": {"seconds": 10}},
        ],
        "end_state": "Action is Completed"
    },
    {
    "name": "On Browser Home Page",
    "checks": [{ "type": "url", "params": {"url": "chrome://new-tab-page/" }}],
    "actions": [{"type": "navigate", "params": {"url": "https://www.google.com/"}}],
  }
]

# agent.run(state_repository)

program = ProgramController(PyAutoGUIController(BrowserSession().driver))

passed_states = program.check(state_repository)
