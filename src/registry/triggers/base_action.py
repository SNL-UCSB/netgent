from __future__ import annotations

from registry.triggers.base import trigger


@trigger(name="always_true")
def always_true() -> bool:
    return True


__all__ = ["always_true"]
