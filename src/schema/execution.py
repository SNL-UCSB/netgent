"""Subprocess execution result schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProcessOutcome(BaseModel):
    """Raw subprocess result returned by execution adapters."""

    model_config = ConfigDict(extra="forbid")

    command: list[str]
    stdout: str
    stderr: str
    returncode: int


__all__ = ["ProcessOutcome"]
