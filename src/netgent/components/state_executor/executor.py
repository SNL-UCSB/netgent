import logging
import time
import re
from typing import Optional
from netgent.browser.controller.base import BaseController
from netgent.browser.registry import ActionRegistry

logger = logging.getLogger(__name__)


class StateExecutor:
    def __init__(self, controller: BaseController, config: Optional[dict] = None):
        self.controller = controller
        self.registry = ActionRegistry(controller)
        
        default_config = {
            "action_period": 1,
        }
        self.config = {**default_config, **(config or {})}
        
        logger.info(f"StateExecutor initialized with actions: {list(self.registry.get_all_actions().keys())}")

    def execute(self, action: dict, variables: Optional[dict] = None):
        if "type" not in action:
            raise ValueError("Action dictionary must contain 'type' key")
        
        action_type = action["type"]
        params = action.get("params", {})
        variables = variables or {}

        if variables:
            params = self._render_value(params, variables)
        
        logger.debug(f"Executing action: {action_type} with params: {params}")
        
        try:
            result = self.registry.execute(action_type, params)
            logger.debug(f"Action {action_type} executed successfully")
            return result
        except KeyError as e:
            logger.error(f"Action not found: {e}")
            raise
        except TypeError as e:
            logger.error(f"Invalid parameters for action {action_type}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}")
            raise

    def run(self, state: dict, variables: Optional[dict] = None):
        if "actions" not in state:
            raise ValueError("State dictionary must contain 'actions' key")
        
        actions = state["actions"]
        variables = variables or state.get("variables") or {}
        logger.info(f"Running state with {len(actions)} actions")
        for i, action in enumerate(actions):
            logger.debug(f"Action {i + 1}/{len(actions)}: {action.get('type', 'unknown')}")
            self.execute(action, variables)
            # Wait between actions based on config
            if i < len(actions) - 1:  # Don't wait after the last action
                time.sleep(self.config["action_period"])
        
        logger.info("State execution completed successfully")

    def _render_value(self, value, variables: dict):
        if isinstance(value, str):
            pattern = re.compile(r"%([^%]+)%")

            def replace(match):
                key = match.group(1)
                if key in variables:
                    return str(variables[key])
                return match.group(0)

            return pattern.sub(replace, value)
        if isinstance(value, dict):
            return {k: self._render_value(v, variables) for k, v in value.items()}
        if isinstance(value, list):
            return [self._render_value(item, variables) for item in value]
        if isinstance(value, tuple):
            return tuple(self._render_value(item, variables) for item in value)
        return value
    
