from __future__ import annotations
from typing import Optional
from netgent.browser.controller.base import BaseController
from netgent.browser.registry import TriggerRegistry
import time

class ProgramController:
    def __init__(self, controller: BaseController, config: Optional[dict] = None):
        self.controller = controller
        self.trigger_registry = TriggerRegistry(controller)
        
        default_config = {
            "allow_multiple_states": False,
        }
        self.config = {**default_config, **(config or {})}

    def check(self, states: list[dict]) -> list[dict]:
        start_time = time.time()
        matching_states = []
        for state in states:
            start_time = time.time()
            if self._check_state(state):
                matching_states.append(state)
            end_time = time.time()
            print(f"State checking took {end_time - start_time:.4f} seconds")
        end_time = time.time()
        print(f"State checking took {end_time - start_time:.4f} seconds")
        
        if not self.config["allow_multiple_states"] and len(matching_states) > 1:
            raise ValueError(f"Multiple states matched: {len(matching_states)} states found: {matching_states}")
        
        return matching_states

    def _check_state(self, state: dict) -> bool:
        checks = state.get("checks", [])
        
        for check in checks:
            trigger_type = check.get("type")
            params = check.get("params", {})
            
            if not trigger_type:
                return False
            
            try:
                result = self.trigger_registry.check(trigger_type, params)
                print(f"Result: {result} on {trigger_type} and {params}")
                if not result:
                    return False
            except (KeyError, TypeError) as e:
                print(f"Error checking trigger '{trigger_type}': {e}")
                return False
                
        return True

