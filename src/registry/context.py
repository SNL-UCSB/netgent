from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping
from typing import Any, TypeAlias

from registry.exception import NetGentWorkflowError

ContextInput: TypeAlias = "Context | Mapping[str, Any] | Iterable[Any] | Any | None"


class ContextError(NetGentWorkflowError):
    pass


def _normalize_context_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ContextError("Context names must be non-empty")
    return normalized


def _camel_to_snake(value: str) -> str:
    first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


class Context:
    """Generic runtime container injected through the reserved `ctx` parameter."""

    def __init__(self, values: ContextInput = None, /, **kwargs: Any) -> None:
        super().__setattr__("_values", {})
        self.update(values, **kwargs)

    def update(self, values: ContextInput = None, /, **kwargs: Any) -> Context:
        for name, value in self._iter_entries(values):
            self._values[name] = value

        for name, value in kwargs.items():
            self._values[_normalize_context_name(name)] = value

        return self

    def copy(self) -> Context:
        return Context(self._values)

    def as_dict(self) -> dict[str, Any]:
        return dict(self._values)

    @property
    def values(self) -> dict[str, Any]:
        return self._values

    def get(self, name: str, default: Any = None) -> Any:
        return self._values.get(name, default)

    def require(self, name: str) -> Any:
        try:
            return self._values[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._values)) or "<empty>"
            raise ContextError(
                f"Runtime context '{name}' is missing. Available context: {available}"
            ) from exc

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._values

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        return iter(self._values.items())

    def __getattr__(self, name: str) -> Any:
        try:
            return self._values[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        self._values[name] = value

    @classmethod
    def from_value(cls, values: ContextInput = None) -> Context:
        if isinstance(values, cls):
            return values.copy()
        return cls(values)

    @classmethod
    def _iter_entries(cls, values: ContextInput) -> Iterator[tuple[str, Any]]:
        if values is None:
            return

        if isinstance(values, Context):
            yield from values.values.items()
            return

        if isinstance(values, Mapping):
            for name, value in values.items():
                yield _normalize_context_name(str(name)), value
            return

        if isinstance(values, Iterable) and not isinstance(
            values, (str, bytes, bytearray)
        ):
            for value in values:
                if (
                    isinstance(value, tuple)
                    and len(value) == 2
                    and isinstance(value[0], str)
                ):
                    yield _normalize_context_name(value[0]), value[1]
                    continue

                yield cls._infer_entry(value)
            return

        yield cls._infer_entry(values)

    @staticmethod
    def _infer_entry(value: Any) -> tuple[str, Any]:
        explicit_name = getattr(value, "__context_name__", None)
        if isinstance(explicit_name, str) and explicit_name.strip():
            return _normalize_context_name(explicit_name), value

        inferred_name = getattr(value, "__name__", None)
        if not isinstance(inferred_name, str) or not inferred_name.strip():
            inferred_name = value.__class__.__name__

        normalized_name = _camel_to_snake(inferred_name)
        if not normalized_name:
            raise ContextError(
                "Unable to infer a context name. Use a mapping like {'browser': browser}."
            )

        return normalized_name, value


__all__ = ["Context", "ContextError", "ContextInput"]
