from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from registry.base import RegistryBase, RegistryDefinition
from registry.context import Context, ContextInput
from registry.exception import NetGentWorkflowError

RegisteredTrigger = Callable[..., Any]
TRIGGER_NAME_ATTRIBUTE = "__trigger_name__"
RESERVED_TRIGGER_PARAMETERS = frozenset({"ctx"})


class TriggerError(NetGentWorkflowError):
    pass


@dataclass(frozen=True, slots=True)
class TriggerDefinition(RegistryDefinition):
    @property
    def trigger(self) -> RegisteredTrigger:
        return self.entry


class TriggerRegistry(RegistryBase):
    """Registry for boolean trigger checks."""

    ERROR = TriggerError
    LABEL = "Trigger"
    NAME_ATTRIBUTE = TRIGGER_NAME_ATTRIBUTE
    RESERVED_PARAMETERS = RESERVED_TRIGGER_PARAMETERS
    DEFINITION_CLASS = TriggerDefinition

    def __init__(
        self,
        *,
        context: ContextInput = None,
        triggers: Iterable[RegisteredTrigger] | None = None,
    ) -> None:
        super().__init__(context=context, entries=triggers)

    def add_trigger(
        self,
        trigger_obj: RegisteredTrigger,
        *,
        name: str | None = None,
        overwrite: bool = False,
    ) -> RegisteredTrigger:
        return self.register(trigger_obj, name=name, overwrite=overwrite)

    def add_triggers(
        self,
        triggers: Iterable[RegisteredTrigger] | None = None,
        *,
        overwrite: bool = False,
    ) -> tuple[RegisteredTrigger, ...]:
        return super().add_entries(triggers, overwrite=overwrite)  # type: ignore[return-value]

    def trigger(
        self,
        target: str | RegisteredTrigger | None = None,
        *,
        name: str | None = None,
        overwrite: bool = False,
    ) -> RegisteredTrigger | Callable[[RegisteredTrigger], RegisteredTrigger]:
        return self.decorator(target, name=name, overwrite=overwrite)  # type: ignore[return-value]

    def get_all_triggers(self) -> dict[str, RegisteredTrigger]:
        return dict(self.items())

    async def run(
        self,
        name: str | RegisteredTrigger,
        *args: Any,
        param: dict[str, Any] | None = None,
        ctx: ContextInput = None,
        **kwargs: Any,
    ) -> bool:
        definition = self.definition(name)
        runtime_context = self._build_runtime_context(ctx)
        call_kwargs = self._merge_call_kwargs(param=param, kwargs=kwargs)

        try:
            result = self._invoke_callable(
                definition.trigger,
                definition,
                args=args,
                kwargs=call_kwargs,
                ctx=runtime_context,
            )
            if inspect.isawaitable(result):
                result = await result
        except TriggerError:
            raise
        except Exception as exc:
            raise TriggerError(f"Trigger '{definition.name}' failed: {exc}") from exc

        if not isinstance(result, bool):
            raise TriggerError(f"Trigger '{definition.name}' must return a boolean value")

        return result


trigger_registry = TriggerRegistry()
trigger = trigger_registry.trigger
register_trigger = trigger_registry.trigger

from registry.triggers.base_action import always_true

__all__ = [
    "TriggerDefinition",
    "TriggerError",
    "TriggerRegistry",
    "always_true",
    "register_trigger",
    "trigger",
    "trigger_registry",
]
