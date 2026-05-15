"""Core exception hierarchy for NetGent.

`NetGentError` is the root for any failure that originates from NetGent
itself. Subclass it to signal whether a failure is the caller's fault
(`BusinessError`) or a temporary infrastructure hiccup that may succeed
on retry (`TransientError`).
"""

from __future__ import annotations


class NetGentError(Exception):
    """Base class for all NetGent-raised exceptions."""


class BusinessError(NetGentError):
    """A request is invalid or violates a domain rule.

    Permanent under the current inputs — retrying with the same arguments
    will fail the same way. Surface to the caller as a 4xx.
    """


class TransientError(NetGentError):
    """A dependency failed in a way that may succeed on retry.

    Network blips, upstream 5xx, rate limits, lock contention. Callers may
    retry with backoff; the operation itself is still valid.
    """


__all__ = ["BusinessError", "NetGentError", "TransientError"]
