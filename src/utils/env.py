"""Environment variable helpers."""

from __future__ import annotations

import os

_TRUTHY_VALUES = frozenset({"1", "true", "yes", "on"})


def get_bool(name: str, default: bool = False) -> bool:
    """Return the boolean value of the env var ``name``.

    Values are stripped + lowercased and matched against the truthy set
    ``{"1", "true", "yes", "on"}``. Anything else — including ``"false"``,
    ``"0"``, or an unset variable — yields ``default``.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY_VALUES


__all__ = ["get_bool"]
