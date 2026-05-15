from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Mapping
from typing import Any

from registry.triggers.base import TriggerRegistry, trigger_registry

logger = logging.getLogger(__name__)


class ProgramController:
    def __init__(
        self,
        *,
        registry: TriggerRegistry | None = None,
        context: Any = None,
        triggers: Iterable[Any] | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> None:
        if registry is not None and (context is not None or triggers is not None):
            raise ValueError(
                "Pass either `registry` or `context` / `triggers`, not both"
            )

        self.registry = registry or TriggerRegistry(
            context=context,
            triggers=triggers if triggers is not None else tuple(trigger_registry),
        )

        default_config = {
            "allow_multiple_states": False,
            "log_timing": True,
        }
        self.config = {**default_config, **dict(config or {})}

        logger.info(
            "ProgramController initialized with triggers: %s",
            list(self.registry.names()),
        )

    async def check(self, states: list[dict[str, Any]]) -> list[dict[str, Any]]:
        overall_start = time.perf_counter()
        matching_states: list[dict[str, Any]] = []

        for state in states:
            state_start = time.perf_counter()
            if await self._check_state(state):
                matching_states.append(state)

            if self.config["log_timing"]:
                logger.info(
                    "State check completed in %.4f seconds",
                    time.perf_counter() - state_start,
                )

        if self.config["log_timing"]:
            logger.info(
                "Checked %s states in %.4f seconds",
                len(states),
                time.perf_counter() - overall_start,
            )

        if not self.config["allow_multiple_states"] and len(matching_states) > 1:
            raise ValueError(
                f"Multiple states matched: {len(matching_states)} states found: {matching_states}"
            )

        return matching_states

    async def _check_state(self, state: Mapping[str, Any]) -> bool:
        checks = state.get("checks", state.get("triggers", []))
        if not isinstance(checks, list):
            raise ValueError("State 'checks' must be a list")

        for check in checks:
            if not isinstance(check, Mapping):
                raise ValueError("Each state check must be a dictionary")

            trigger_name = check.get("type", check.get("name"))
            if not isinstance(trigger_name, str) or not trigger_name.strip():
                return False

            params = check.get("params", check.get("param", {}))
            if not isinstance(params, Mapping):
                raise ValueError("Check 'params' must be a dictionary")

            result = await self.registry.run(trigger_name, param=dict(params))
            logger.debug(
                "Trigger '%s' returned %s for params=%s",
                trigger_name,
                result,
                params,
            )
            if not result:
                return False

        return True


__all__ = ["ProgramController"]
