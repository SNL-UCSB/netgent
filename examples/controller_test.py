
from netgent.components.state_executor.executor import StateExecutor
from netgent.browser import BrowserSession, PyAutoGUIController

session = BrowserSession()
controller = PyAutoGUIController(session.driver)
executor = StateExecutor(controller)

state = {
    "actions": [
        {"type": "navigate", "params": {"url": "https://www.google.com"}},
        {"type": "wait", "params": {"seconds": 10}},
        {"type": "type", "params": {"by": "css selector", "selector": "textarea[name='q']", "text": "SeleniumBase Python"}},
        {"type": "wait", "params": {"seconds": 1}},
        {"type": "press_key", "params": {"key": "enter"}},
        {"type": "wait", "params": {"seconds": 10}},
    ]
}

# Execute the state
executor.run(state)