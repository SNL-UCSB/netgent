"""
Combined metaclass for controllers that need both actions and triggers.

This module provides ActionTriggerMeta, a metaclass that combines both
ActionMeta and TriggerMeta to allow a single class to use both @action
and @trigger decorators without metaclass conflicts.
"""

from abc import ABCMeta
from typing import Dict

from .action import ActionMeta
from .trigger import TriggerMeta


class ActionTriggerMeta(ActionMeta, TriggerMeta):
    """
    Combined metaclass that handles both actions and triggers.
    
    This metaclass resolves the metaclass conflict that would occur if a class
    tried to inherit from both ActionController and TriggerController.
    
    It processes both @action and @trigger decorated methods and creates
    both __actions__ and __triggers__ mappings on the class.
    """
    
    def __new__(mcls, name, bases, ns):
        # Process actions (from ActionMeta)
        actions: Dict[str, str] = {}
        for base in bases:
            actions.update(getattr(base, "__actions__", {}))

        for attr_name, obj in ns.items():
            func = obj.__func__ if isinstance(obj, (staticmethod, classmethod)) else obj
            meta = getattr(func, "_action_meta", None)
            if meta:
                action_name = meta["name"]
                if action_name in actions and actions[action_name] != attr_name:
                    raise ValueError(
                        f"Duplicate action name '{action_name}' in class '{name}' "
                        f"(existing: '{actions[action_name]}', new: '{attr_name}')"
                    )
                actions[action_name] = attr_name

        ns["__actions__"] = actions

        # Process triggers (from TriggerMeta)
        triggers: Dict[str, str] = {}
        for base in bases:
            triggers.update(getattr(base, "__triggers__", {}))

        for attr_name, obj in ns.items():
            func = obj.__func__ if isinstance(obj, (staticmethod, classmethod)) else obj
            meta = getattr(func, "_trigger_meta", None)
            if meta:
                trigger_name = meta["name"]
                if trigger_name in triggers and triggers[trigger_name] != attr_name:
                    raise ValueError(
                        f"Duplicate trigger name '{trigger_name}' in class '{name}' "
                        f"(existing: '{triggers[trigger_name]}', new: '{attr_name}')"
                    )
                triggers[trigger_name] = attr_name

        ns["__triggers__"] = triggers

        # Call ABCMeta's __new__ (common parent of both ActionMeta and TriggerMeta)
        return ABCMeta.__new__(mcls, name, bases, ns)

