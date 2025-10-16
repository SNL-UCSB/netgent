"""
Action registry system using metaclasses for optimal performance.

This module provides a decorator (@action) and metaclass-based system for
automatically collecting and executing controller actions.
"""

import inspect
from abc import ABCMeta
from typing import Callable, Dict, Any, Optional


def action(name: Optional[str] = None, **meta):
    def deco(fn: Callable) -> Callable:
        fn._action_meta = {"name": name or fn.__name__, **meta}
        return fn
    return deco


class ActionMeta(ABCMeta):
    def __new__(mcls, name, bases, ns):
        # Inherit actions from parent classes
        actions: Dict[str, str] = {}
        for base in bases:
            actions.update(getattr(base, "__actions__", {}))

        # Register decorated methods in this class
        for attr_name, obj in ns.items():
            # Unwrap staticmethod/classmethod for metadata check
            func = obj.__func__ if isinstance(obj, (staticmethod, classmethod)) else obj
            meta = getattr(func, "_action_meta", None)
            if meta:
                action_name = meta["name"]
                # Detect duplicate action names early
                if action_name in actions and actions[action_name] != attr_name:
                    raise ValueError(
                        f"Duplicate action name '{action_name}' in class '{name}' "
                        f"(existing: '{actions[action_name]}', new: '{attr_name}')"
                    )
                actions[action_name] = attr_name

        # Store action mappings on the class
        ns["__actions__"] = actions
        return super().__new__(mcls, name, bases, ns)


class ActionController(metaclass=ActionMeta):
    pass


class ActionRegistry:
    def __init__(self, controller: Any):
        self.controller = controller
        self.actions: Dict[str, Callable] = {}
        self._bind_actions()

    def _bind_actions(self):
        """Bind class-level action mappings to instance methods."""
        cls = self.controller.__class__
        for action_name, attr_name in getattr(cls, "__actions__", {}).items():
            method = getattr(self.controller, attr_name, None)
            if callable(method):
                self.actions[action_name] = method

    def get_action(self, action_name: str) -> Callable:
        try:
            return self.actions[action_name]
        except KeyError as e:
            available = ", ".join(sorted(self.actions))
            raise KeyError(
                f"Action '{action_name}' not found. Available: {available}"
            ) from e

    def has_action(self, action_name: str) -> bool:
        """Check if an action exists."""
        return action_name in self.actions

    def get_all_actions(self) -> Dict[str, Callable]:
        """Get all registered actions."""
        return dict(self.actions)

    def execute(self, action_name: str, params: Dict[str, Any] | None = None) -> Any:
        """
        Execute an action with strict parameter validation.
        
        Uses inspect.signature.bind() for validation that catches
        both missing and unexpected parameters.
        
        Args:
            action_name: Name of the action to execute
            params: Parameters to pass to the action
            
        Returns:
            Result of the action execution
            
        Raises:
            KeyError: If action not found
            TypeError: If parameters don't match signature
        """
        params = params or {}
        method = self.get_action(action_name)
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
                f"Invalid parameters for action '{action_name}': {e}\n"
                f"  Required: {param_names}\n"
                f"  Provided: {provided}"
            ) from e
        
        return method(**bound.arguments)

    async def aexecute(self, action_name: str, params: Dict[str, Any] | None = None) -> Any:
        """
        Execute an action asynchronously.
        
        Works with both sync and async methods.
        
        Args:
            action_name: Name of the action to execute
            params: Parameters to pass to the action
            
        Returns:
            Result of the action execution
            
        Raises:
            KeyError: If action not found
            TypeError: If parameters don't match signature
        """
        params = params or {}
        method = self.get_action(action_name)
        sig = inspect.signature(method)
        
        kwargs = {k: v for k, v in params.items() if k != 'self'}
        
        try:
            bound = sig.bind(**kwargs)
            bound.apply_defaults()
        except TypeError as e:
            param_names = [
                p.name for p in sig.parameters.values() 
                if p.name != 'self' and p.default is inspect.Parameter.empty
            ]
            provided = list(kwargs.keys())
            raise TypeError(
                f"Invalid parameters for action '{action_name}': {e}\n"
                f"  Required: {param_names}\n"
                f"  Provided: {provided}"
            ) from e

        if inspect.iscoroutinefunction(method):
            return await method(**bound.arguments)
        return method(**bound.arguments)
    
    def get_action_metadata(self, action_name: str) -> Dict[str, Any]:
        """
        Get metadata attached to an action via the decorator.
        
        Args:
            action_name: Name of the action
            
        Returns:
            Dictionary of metadata
        """
        method = self.get_action(action_name)
        # Get the underlying function (unwrap bound method)
        func = method.__func__ if hasattr(method, '__func__') else method
        return getattr(func, '_action_meta', {})

