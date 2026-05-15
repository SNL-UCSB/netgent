from __future__ import annotations

from typing import Any

from engine.controller import ProgramController
from engine.executor import StateExecutor
from engine.schema import WorkflowSchema


class WorkflowRunner:
    def __init__(
        self,
        controller: ProgramController,
        executor: StateExecutor,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.controller = controller
        self.executor = executor
        self.config = dict(config or {})

    def validate(self, workflow: dict[str, Any]) -> dict[str, Any]:
        validated = WorkflowSchema.model_validate(workflow).model_dump(mode="json")

        for state in validated["states"]:
            for action in state.get("actions", []):
                action_type = action["type"]
                try:
                    definition = self.executor.registry.definition(action_type)
                except Exception as exc:
                    raise ValueError(f"Invalid action '{action_type}': {exc}") from exc
                try:
                    definition.public_signature.bind(**action.get("params", {}))
                except TypeError as exc:
                    raise ValueError(f"Invalid action '{action_type}': {exc}") from exc

        return validated

    def _check_parameters(self, validated_workflow: dict[str, Any]) -> None:
        declared: list[str] = validated_workflow.get("parameters") or []
        if not declared:
            return
        supplied = set(self.executor._parameters or {})
        missing = [name for name in declared if name not in supplied]
        if missing:
            raise ValueError(
                f"Missing required workflow parameters: {', '.join(missing)}"
            )

    async def run(self, workflow: dict[str, Any]) -> list[Any]:
        validated_workflow = self.validate(workflow)
        self._check_parameters(validated_workflow)
        states = validated_workflow["states"]

        passed_states = await self.controller.check(states)
        if not passed_states:
            return []

        return [await self.executor.run(state) for state in passed_states]
