from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import partial
from typing import Any, TypeVar

from registry.actions.exception import ActionError
from registry.base import RegistryBase, RegistryDefinition
from registry.context import Context, ContextInput

ActionType = TypeVar("ActionType", bound="Action")
RegisteredAction = type["Action"] | Callable[..., Any]
ACTION_NAME_ATTRIBUTE = "__action_name__"
RESERVED_ACTION_PARAMETERS = frozenset({"ctx"})


@dataclass(frozen=True, slots=True)
class ActionDefinition(RegistryDefinition):
    @property
    def action(self) -> RegisteredAction:
        return self.entry


class Action(ABC):
    """Base class for class-based actions."""

    name: str | None = None

    @classmethod
    def action_name(cls) -> str:
        metadata_name = getattr(cls, ACTION_NAME_ATTRIBUTE, None)
        if isinstance(metadata_name, str) and metadata_name.strip():
            return metadata_name.strip()

        resolved_name = cls.name or cls.__name__
        normalized = resolved_name.strip()
        if not normalized:
            raise ActionError(f"{cls.__name__} must define a non-empty action name")
        return normalized

    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the action."""


class ActionRegistry(RegistryBase):
    """Registry for function-based and class-based actions."""

    ERROR = ActionError
    LABEL = "Action"
    NAME_ATTRIBUTE = ACTION_NAME_ATTRIBUTE
    RESERVED_PARAMETERS = RESERVED_ACTION_PARAMETERS
    DEFINITION_CLASS = ActionDefinition

    def __init__(
        self,
        *,
        context: ContextInput = None,
        actions: Iterable[RegisteredAction] | None = None,
    ) -> None:
        super().__init__(context=context, entries=actions)

    def add_action(
        self,
        action_obj: RegisteredAction,
        *,
        name: str | None = None,
        overwrite: bool = False,
    ) -> RegisteredAction:
        return self.register(action_obj, name=name, overwrite=overwrite)

    def add_actions(
        self,
        actions: Iterable[RegisteredAction] | None = None,
        *,
        overwrite: bool = False,
    ) -> tuple[RegisteredAction, ...]:
        return super().add_entries(actions, overwrite=overwrite)  # type: ignore[return-value]

    def action(
        self,
        target: str | RegisteredAction | None = None,
        *,
        name: str | None = None,
        overwrite: bool = False,
    ) -> RegisteredAction | Callable[[RegisteredAction], RegisteredAction]:
        return self.decorator(target, name=name, overwrite=overwrite)  # type: ignore[return-value]

    def create(
        self,
        name: str | RegisteredAction,
        *args: Any,
        param: dict[str, Any] | None = None,
        ctx: ContextInput = None,
        **kwargs: Any,
    ) -> Action | Callable[..., Any]:
        action_obj = self.get(name)
        if isinstance(action_obj, type) and issubclass(action_obj, Action):
            instance = action_obj()
            if not args and not param and not kwargs and ctx is None:
                return instance

            return partial(self.run, action_obj, *args, param=param, ctx=ctx, **kwargs)

        if args or param or kwargs or ctx is not None:
            return partial(self.run, action_obj, *args, param=param, ctx=ctx, **kwargs)

        return action_obj

    async def run(
        self,
        name: str | RegisteredAction,
        *args: Any,
        param: dict[str, Any] | None = None,
        ctx: ContextInput = None,
        **kwargs: Any,
    ) -> Any:
        definition = self.definition(name)
        action_obj = definition.action
        runtime_context = self._build_runtime_context(ctx)
        call_kwargs = self._merge_call_kwargs(param=param, kwargs=kwargs)

        try:
            if isinstance(action_obj, type) and issubclass(action_obj, Action):
                result = self._invoke_callable(
                    action_obj().run,
                    definition,
                    args=args,
                    kwargs=call_kwargs,
                    ctx=runtime_context,
                )
            else:
                result = self._invoke_callable(
                    action_obj,
                    definition,
                    args=args,
                    kwargs=call_kwargs,
                    ctx=runtime_context,
                )
        except ActionError:
            raise
        except Exception as exc:
            raise ActionError(f"Action '{definition.name}' failed: {exc}") from exc

        if inspect.isawaitable(result):
            try:
                return await result
            except ActionError:
                raise
            except Exception as exc:
                raise ActionError(f"Action '{definition.name}' failed: {exc}") from exc
        return result

    def _signature_for(self, entry_obj: RegisteredAction) -> inspect.Signature:
        target = (
            entry_obj.run
            if isinstance(entry_obj, type) and issubclass(entry_obj, Action)
            else entry_obj
        )
        signature = inspect.signature(target)
        parameters = list(signature.parameters.values())
        if parameters and parameters[0].name in {"self", "cls"}:
            parameters = parameters[1:]
        return signature.replace(parameters=parameters)

    def _resolve_name(self, entry_obj: RegisteredAction, name: str | None) -> str:
        if name is not None:
            return self._normalize_name(name)

        metadata_name = self._metadata_name(entry_obj)
        if isinstance(metadata_name, str) and metadata_name.strip():
            return self._normalize_name(metadata_name)

        if isinstance(entry_obj, type) and issubclass(entry_obj, Action):
            return self._normalize_name(entry_obj.action_name())

        inferred_name = getattr(entry_obj, "__name__", entry_obj.__class__.__name__)
        return self._normalize_name(inferred_name)

    def _set_entry_metadata(self, entry_obj: RegisteredAction, entry_name: str) -> None:
        if isinstance(entry_obj, type) and issubclass(entry_obj, Action):
            entry_obj.name = entry_name

        super()._set_entry_metadata(entry_obj, entry_name)


ActionContext = Context
action_registry = ActionRegistry()
action = action_registry.action
register_action = action_registry.action


__all__ = [
    "Action",
    "ActionContext",
    "ActionDefinition",
    "ActionRegistry",
    "ACTION_NAME_ATTRIBUTE",
    "Context",
    "ContextInput",
    "RESERVED_ACTION_PARAMETERS",
    "action",
    "action_registry",
    "register_action",
]
