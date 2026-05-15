from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from registry.context import Context, ContextInput


@dataclass(frozen=True, slots=True)
class RegistryDefinition:
    name: str
    entry: Callable[..., Any]
    signature: inspect.Signature
    public_signature: inspect.Signature
    reserved_parameters: frozenset[str]


class RegistryBase:
    """Shared registration and invocation logic for callable registries."""

    ERROR = Exception
    LABEL = "Registry entry"
    NAME_ATTRIBUTE = "__registry_name__"
    RESERVED_PARAMETERS = frozenset({"ctx"})
    DEFINITION_CLASS = RegistryDefinition

    def __init__(
        self,
        *,
        context: ContextInput = None,
        entries: Iterable[Callable[..., Any]] | None = None,
    ) -> None:
        self._entries: dict[str, RegistryDefinition] = {}
        self.context = Context.from_value(context)
        if entries is not None:
            self.add_entries(entries)

    def add_context(self, context: ContextInput = None, /, **kwargs: Any) -> Context:
        self.context.update(context, **kwargs)
        return self.context

    def register(
        self,
        entry_obj: Callable[..., Any],
        *,
        name: str | None = None,
        overwrite: bool = False,
    ) -> Callable[..., Any]:
        if not callable(entry_obj):
            raise self.ERROR(f"Registered {self.LABEL.lower()}s must be callable")

        entry_name = self._resolve_name(entry_obj, name)
        if not overwrite and entry_name in self._entries:
            existing = self._get_definition_entry(self._entries[entry_name])
            raise self.ERROR(
                f"{self.LABEL} '{entry_name}' is already registered by {self._display_name(existing)}"
            )

        self._set_entry_metadata(entry_obj, entry_name)
        self._entries[entry_name] = self._build_definition(entry_name, entry_obj)
        return entry_obj

    def add_entries(
        self,
        entries: Iterable[Callable[..., Any]] | None = None,
        *,
        overwrite: bool = False,
    ) -> tuple[Callable[..., Any], ...]:
        entry_list = list(entries or [])
        for entry_obj in entry_list:
            self.register(entry_obj, overwrite=overwrite)
        return tuple(entry_list)

    def decorator(
        self,
        target: str | Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        overwrite: bool = False,
    ) -> Callable[..., Any] | Callable[[Callable[..., Any]], Callable[..., Any]]:
        if target is not None and not isinstance(target, str):
            if name is not None:
                raise self.ERROR(
                    f"Use either `@{self.LABEL.lower()}(name=...)` or `@{self.LABEL.lower()}(...)`, not both"
                )
            return self.register(target, overwrite=overwrite)

        resolved_name = name or target

        def decorate(entry_obj: Callable[..., Any]) -> Callable[..., Any]:
            return self.register(entry_obj, name=resolved_name, overwrite=overwrite)

        return decorate

    def get(self, name: str | Callable[..., Any]) -> Callable[..., Any]:
        definition = self.definition(name)
        return self._get_definition_entry(definition)

    def definition(self, name: str | Callable[..., Any]) -> RegistryDefinition:
        entry_name = self._resolve_requested_name(name)
        try:
            return self._entries[entry_name]
        except KeyError as exc:
            available = ", ".join(sorted(self._entries)) or "<empty>"
            raise self.ERROR(
                f"Unknown {self.LABEL.lower()} '{entry_name}'. Available {self.LABEL.lower()}s: {available}"
            ) from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))

    def items(self) -> tuple[tuple[str, Callable[..., Any]], ...]:
        return tuple((name, self.get(name)) for name in self.names())

    def __contains__(self, name: object) -> bool:
        try:
            self.definition(name)  # type: ignore[arg-type]
        except self.ERROR:
            return False
        return True

    def __iter__(self) -> Iterator[Callable[..., Any]]:
        for _, entry_obj in self.items():
            yield entry_obj

    def _build_definition(
        self, entry_name: str, entry_obj: Callable[..., Any]
    ) -> RegistryDefinition:
        signature = self._signature_for(entry_obj)
        reserved_parameters = frozenset(
            parameter.name
            for parameter in signature.parameters.values()
            if parameter.name in self.RESERVED_PARAMETERS
        )

        if "ctx" in reserved_parameters:
            parameter = signature.parameters["ctx"]
            if parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
                raise self.ERROR(
                    f"Reserved {self.LABEL.lower()} parameter 'ctx' cannot be positional-only"
                )

        public_parameters = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.name not in self.RESERVED_PARAMETERS
        ]
        public_signature = signature.replace(parameters=public_parameters)

        return self.DEFINITION_CLASS(
            name=entry_name,
            entry=entry_obj,
            signature=signature,
            public_signature=public_signature,
            reserved_parameters=reserved_parameters,
        )

    def _signature_for(self, entry_obj: Callable[..., Any]) -> inspect.Signature:
        signature = inspect.signature(entry_obj)
        parameters = list(signature.parameters.values())
        if parameters and parameters[0].name in {"self", "cls"}:
            parameters = parameters[1:]
        return signature.replace(parameters=parameters)

    def _merge_call_kwargs(
        self,
        *,
        param: Mapping[str, Any] | None,
        kwargs: Mapping[str, Any],
    ) -> dict[str, Any]:
        merged: dict[str, Any] = {}

        if param is not None:
            if not isinstance(param, Mapping):
                raise self.ERROR(f"`param` must be a mapping of {self.LABEL.lower()} arguments")
            merged.update(param)

        duplicate_keys = merged.keys() & kwargs.keys()
        if duplicate_keys:
            duplicates = ", ".join(sorted(duplicate_keys))
            raise self.ERROR(f"Duplicate {self.LABEL.lower()} arguments provided: {duplicates}")

        merged.update(kwargs)

        if "ctx" in merged:
            raise self.ERROR("`ctx` is reserved for runtime context injection")

        return merged

    def _build_runtime_context(self, ctx: ContextInput) -> Context:
        runtime_context = self.context
        if ctx is not None:
            runtime_context.update(ctx)
        return runtime_context

    def _invoke_callable(
        self,
        callable_obj: Callable[..., Any],
        definition: RegistryDefinition,
        *,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        ctx: Context,
    ) -> Any:
        try:
            bound_arguments = definition.public_signature.bind(*args, **kwargs)
        except TypeError as exc:
            raise self.ERROR(
                f"Invalid parameters for {self.LABEL.lower()} '{definition.name}': {exc}"
            ) from exc

        call_args = list(bound_arguments.args)
        call_kwargs = dict(bound_arguments.kwargs)
        if "ctx" in definition.reserved_parameters:
            call_kwargs["ctx"] = ctx

        return callable_obj(*call_args, **call_kwargs)

    def _normalize_name(self, name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise self.ERROR(f"{self.LABEL} names must be non-empty")
        return normalized

    def _resolve_name(self, entry_obj: Callable[..., Any], name: str | None) -> str:
        if name is not None:
            return self._normalize_name(name)

        metadata_name = self._metadata_name(entry_obj)
        if isinstance(metadata_name, str) and metadata_name.strip():
            return self._normalize_name(metadata_name)

        inferred_name = getattr(entry_obj, "__name__", entry_obj.__class__.__name__)
        return self._normalize_name(inferred_name)

    def _resolve_requested_name(self, value: str | Callable[..., Any]) -> str:
        if isinstance(value, str):
            return self._normalize_name(value)

        if not callable(value):
            raise self.ERROR(
                f"{self.LABEL} lookups must use a {self.LABEL.lower()} name or a callable"
            )

        metadata_name = self._metadata_name(value)
        if isinstance(metadata_name, str) and metadata_name in self._entries:
            return metadata_name

        for name, definition in self._entries.items():
            if self._get_definition_entry(definition) is value:
                return name

        display_name = self._display_name(value)
        raise self.ERROR(f"{self.LABEL} '{display_name}' is not registered")

    def _metadata_name(self, entry_obj: Callable[..., Any]) -> str | None:
        metadata_name = getattr(entry_obj, self.NAME_ATTRIBUTE, None)
        if isinstance(metadata_name, str) and metadata_name.strip():
            return metadata_name

        function = getattr(entry_obj, "__func__", None)
        metadata_name = getattr(function, self.NAME_ATTRIBUTE, None)
        if isinstance(metadata_name, str) and metadata_name.strip():
            return metadata_name

        return None

    def _set_entry_metadata(self, entry_obj: Callable[..., Any], entry_name: str) -> None:
        for target in (entry_obj, getattr(entry_obj, "__func__", None)):
            if target is None:
                continue
            try:
                setattr(target, self.NAME_ATTRIBUTE, entry_name)
            except (AttributeError, TypeError):
                pass

    def _get_definition_entry(self, definition: RegistryDefinition) -> Callable[..., Any]:
        return definition.entry

    @staticmethod
    def _display_name(entry_obj: Callable[..., Any]) -> str:
        return getattr(entry_obj, "__name__", entry_obj.__class__.__name__)


__all__ = ["RegistryBase", "RegistryDefinition"]
