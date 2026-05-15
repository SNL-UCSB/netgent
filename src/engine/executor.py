from __future__ import annotations

import asyncio
import inspect
import logging
import re
import types
import typing
from collections.abc import Iterable, Mapping
from typing import Any


def _coerce_to_annotation(value: str, annotation: Any) -> Any:
    """Best-effort coercion of a resolved string to match a type annotation."""
    if annotation is inspect.Parameter.empty:
        return value

    # "none" / "null" → None for Optional fields
    if value.lower() in ("none", "null"):
        return None

    # Unwrap Union / Optional — coerce to the first non-None member
    origin = getattr(annotation, "__origin__", None)
    is_union = isinstance(annotation, types.UnionType) or origin is typing.Union
    if is_union:
        non_none = [a for a in annotation.__args__ if a is not type(None)]
        if non_none:
            return _coerce_to_annotation(value, non_none[0])
        return value

    if annotation is int:
        try:
            return int(value)
        except (ValueError, TypeError):
            return value

    if annotation is float:
        try:
            return float(value)
        except (ValueError, TypeError):
            return value

    if annotation is bool:
        return value.lower() in ("true", "1", "yes")

    return value


def _get_type_hints(func: Any) -> dict[str, Any]:
    """Return resolved type hints for *func*, falling back to {} on failure."""
    try:
        return typing.get_type_hints(func)
    except Exception:
        return {}


_PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _resolve_params(
    params: Mapping[str, Any],
    parameters: dict[str, str],
    type_hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replace ``{{key}}`` placeholders in action params with values from
    *parameters*.

    Supports both full-value placeholders (``"{{key}}"``) and embedded
    placeholders (``"https://example.com/{{key}}"``). Full-value placeholders
    are additionally coerced to match the action's type annotation when
    *type_hints* is provided (e.g. ``"5"`` → ``5`` for ``int``). Embedded
    placeholders always produce a string.
    """
    resolved: dict[str, Any] = {}
    for k, v in params.items():
        if not isinstance(v, str):
            resolved[k] = v
            continue

        match = _PLACEHOLDER_RE.fullmatch(v.strip())
        if match is not None:
            placeholder_key = match.group(1)
            value = parameters.get(placeholder_key, v)
            if type_hints is not None and k in type_hints and isinstance(value, str):
                value = _coerce_to_annotation(value, type_hints[k])
            resolved[k] = value
            continue

        if "{{" in v:
            resolved[k] = _PLACEHOLDER_RE.sub(
                lambda m: parameters.get(m.group(1), m.group(0)),
                v,
            )
            continue

        resolved[k] = v
    return resolved


from registry.actions.base import ActionRegistry
from registry.actions.network import NETWORK_ACTIONS

logger = logging.getLogger(__name__)


class StateExecutor:
    def __init__(
        self,
        *,
        registry: ActionRegistry | None = None,
        context: Any = None,
        actions: Iterable[Any] | None = None,
        config: Mapping[str, Any] | None = None,
        parameters: dict[str, str] | None = None,
    ) -> None:
        if registry is not None and (context is not None or actions is not None):
            raise ValueError(
                "Pass either `registry` or `context` / `actions`, not both"
            )

        self.registry = registry or ActionRegistry(
            context=context,
            actions=actions if actions is not None else NETWORK_ACTIONS,
        )

        self._parameters: dict[str, str] = dict(parameters or {})

        default_config = {
            "action_period": 5,
        }
        self.config = {**default_config, **dict(config or {})}

        logger.info(
            "StateExecutor initialized with actions: %s",
            list(self.registry.names()),
        )

    async def execute(
        self,
        action: Mapping[str, Any],
    ) -> Any:
        if "type" not in action:
            raise ValueError("Action dictionary must contain 'type' key")

        action_type = action["type"]
        params = action.get("params", {})
        if not isinstance(params, Mapping):
            raise ValueError("Action 'params' must be a dictionary")

        if self._parameters:
            action_func = self.registry.get(action_type)
            params = _resolve_params(
                params, self._parameters, _get_type_hints(action_func)
            )

        logger.info("Executing action '%s' with params=%s", action_type, params)

        result = await self.registry.run(action_type, param=dict(params))

        logger.info("Action '%s' executed successfully", action_type)
        return result

    async def run(
        self,
        state: Mapping[str, Any],
    ) -> list[Any]:
        if "actions" not in state:
            raise ValueError("State dictionary must contain 'actions' key")

        actions = state["actions"]
        if not isinstance(actions, list):
            raise ValueError("State 'actions' must be a list")

        logger.info("Running state with %s actions", len(actions))

        results: list[Any] = []
        for index, action in enumerate(actions):
            if not isinstance(action, Mapping):
                raise ValueError("Each action must be a dictionary")

            logger.debug(
                "Action %s/%s: %s",
                index + 1,
                len(actions),
                action.get("type", "unknown"),
            )
            results.append(await self.execute(action))

            if index < len(actions) - 1:
                await asyncio.sleep(self.config["action_period"])

        logger.info("State execution completed successfully")
        return results


__all__ = ["StateExecutor"]
