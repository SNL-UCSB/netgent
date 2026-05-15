from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WorkflowCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class WorkflowAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class WorkflowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checks: list[WorkflowCheck] = Field(default_factory=list)
    actions: list[WorkflowAction] = Field(default_factory=list)
    end_state: str = ""
    executed: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    specification: str = Field(..., min_length=1)
    states: list[WorkflowState] = Field(..., min_length=1)
    parameters: list[str] = Field(default_factory=list)

    @field_validator("parameters", mode="before")
    @classmethod
    def validate_parameters(cls, value: Any) -> Any:
        if isinstance(value, dict):
            raise ValueError("Workflow 'parameters' must be a list of parameter names")
        return value

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_single_state(cls, data: Any) -> dict[str, Any] | Any:
        if not isinstance(data, dict):
            return data

        if "states" in data:
            return data

        state_keys = {"checks", "actions", "end_state", "executed"}
        if state_keys.isdisjoint(data):
            return data

        state = {
            "checks": data.get("checks", []),
            "actions": data.get("actions", []),
            "end_state": data.get("end_state", ""),
            "executed": data.get("executed", []),
        }
        return {
            "specification": data.get("specification", ""),
            "states": [state],
            "parameters": data.get("parameters", []),
        }


__all__ = [
    "WorkflowAction",
    "WorkflowCheck",
    "WorkflowSchema",
    "WorkflowState",
]
