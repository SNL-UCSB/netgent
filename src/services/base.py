"""Root of the services layer.

A service wraps an adapter with service-level concerns — non-zero exit
handling, multi-call orchestration, retry policy — and exposes a typed
public API. Proxies the adapter's open/close lifecycle so callers can
use ``async with`` or call methods directly.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from adapters.base import BaseAdapter


class BaseService:
    """Base class for service wrappers around an adapter.

    Subclasses assign ``self._adapter`` in ``__init__`` and add their own
    operation methods (typically named ``run``). Each operation method
    should ``await self._adapter.open()`` first so the direct-call usage
    path works alongside ``async with``.
    """

    _adapter: BaseAdapter

    async def __aenter__(self) -> Self:
        await self._adapter.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._adapter.close()


__all__ = ["BaseService"]
