"""Pydantic models shared across adapters, services, and the engine.

Each submodule groups a single domain (subprocess execution, future:
browser actions, LLM responses, etc.). Re-exported here so existing
call sites can keep using ``from schema import X``.
"""

from .execution import ProcessOutcome

__all__ = ["ProcessOutcome"]
