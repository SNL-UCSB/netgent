"""Browser registry system for actions and triggers."""

from .action import action, ActionController, ActionRegistry, ActionMeta
from .trigger import trigger, TriggerController, TriggerRegistry, TriggerMeta
from .controller import ActionTriggerMeta

__all__ = [
    "action", "ActionController", "ActionRegistry", "ActionMeta",
    "trigger", "TriggerController", "TriggerRegistry", "TriggerMeta",
    "ActionTriggerMeta"
]

