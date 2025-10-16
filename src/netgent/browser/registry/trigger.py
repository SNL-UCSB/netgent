"""
Trigger registry system using metaclasses for optimal performance.

This module provides a decorator (@trigger) and metaclass-based system for
automatically collecting and executing controller triggers.
"""

import inspect
from abc import ABCMeta
from typing import Callable, Dict, Any, Optional


def trigger(name: Optional[str] = None, **meta):
    """Decorator to mark a method as a trigger."""
    def deco(fn: Callable) -> Callable:
        fn._trigger_meta = {"name": name or fn.__name__, **meta}
        return fn
    return deco


class TriggerMeta(ABCMeta):
    def __new__(mcls, name, bases, ns):
        # Inherit triggers from parent classes
        triggers: Dict[str, str] = {}
        for base in bases:
            triggers.update(getattr(base, "__triggers__", {}))

        # Register decorated methods in this class
        for attr_name, obj in ns.items():
            # Unwrap staticmethod/classmethod for metadata check
            func = obj.__func__ if isinstance(obj, (staticmethod, classmethod)) else obj
            meta = getattr(func, "_trigger_meta", None)
            if meta:
                trigger_name = meta["name"]
                # Detect duplicate trigger names early
                if trigger_name in triggers and triggers[trigger_name] != attr_name:
                    raise ValueError(
                        f"Duplicate trigger name '{trigger_name}' in class '{name}' "
                        f"(existing: '{triggers[trigger_name]}', new: '{attr_name}')"
                    )
                triggers[trigger_name] = attr_name

        # Store trigger mappings on the class
        ns["__triggers__"] = triggers
        return super().__new__(mcls, name, bases, ns)


class TriggerController(metaclass=TriggerMeta):
    pass


class TriggerRegistry:
    def __init__(self, controller: Any):
        self.controller = controller
        self.triggers: Dict[str, Callable] = {}
        self._bind_triggers()

    def _bind_triggers(self):
        """Bind class-level trigger mappings to instance methods."""
        cls = self.controller.__class__
        for trigger_name, attr_name in getattr(cls, "__triggers__", {}).items():
            method = getattr(self.controller, attr_name, None)
            if callable(method):
                self.triggers[trigger_name] = method

    def get_trigger(self, trigger_name: str) -> Callable:
        try:
            return self.triggers[trigger_name]
        except KeyError as e:
            available = ", ".join(sorted(self.triggers))
            raise KeyError(
                f"Trigger '{trigger_name}' not found. Available: {available}"
            ) from e

    def has_trigger(self, trigger_name: str) -> bool:
        """Check if a trigger exists."""
        return trigger_name in self.triggers

    def get_all_triggers(self) -> Dict[str, Callable]:
        """Get all registered triggers."""
        return dict(self.triggers)

    def check(self, trigger_name: str, params: Dict[str, Any] | None = None) -> bool:
        """
        Check a trigger with strict parameter validation.
        
        Uses inspect.signature.bind() for validation that catches
        both missing and unexpected parameters.
        
        Args:
            trigger_name: Name of the trigger to check
            params: Parameters to pass to the trigger
            
        Returns:
            Boolean result of the trigger check
            
        Raises:
            KeyError: If trigger not found
            TypeError: If parameters don't match signature
        """
        params = params or {}
        method = self.get_trigger(trigger_name)
        sig = inspect.signature(method)

        # Filter out 'self' from params (shouldn't be present, but be safe)
        kwargs = {k: v for k, v in params.items() if k != 'self'}

        try:
            # Use bind() for strict validation
            # Method is already bound to instance, so don't pass self
            bound = sig.bind(**kwargs)
            bound.apply_defaults()
        except TypeError as e:
            # Provide clearer error message
            param_names = [
                p.name for p in sig.parameters.values() 
                if p.name != 'self' and p.default is inspect.Parameter.empty
            ]
            provided = list(kwargs.keys())
            raise TypeError(
                f"Invalid parameters for trigger '{trigger_name}': {e}\n"
                f"  Required: {param_names}\n"
                f"  Provided: {provided}"
            ) from e
        
        return method(**bound.arguments)

    def get_trigger_metadata(self, trigger_name: str) -> Dict[str, Any]:
        """
        Get metadata attached to a trigger via the decorator.
        
        Args:
            trigger_name: Name of the trigger
            
        Returns:
            Dictionary of metadata
        """
        method = self.get_trigger(trigger_name)
        # Get the underlying function (unwrap bound method)
        func = method.__func__ if hasattr(method, '__func__') else method
        return getattr(func, '_trigger_meta', {})

