from __future__ import annotations

from clients.netgent.src.registry.triggers.base import trigger


@trigger(name="always_true")
def always_true() -> bool:
    return True


__all__ = ["always_true"]
