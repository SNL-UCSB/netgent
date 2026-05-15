from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import TracebackType
from typing import Generic, Self, TypeVar

from core.errors import NetGentError

T = TypeVar("T")


@dataclass
class AdapterResult(Generic[T]):
    """Either a successful call's value or the NetGentError that classified
    a failure.

    Returning a result object instead of raising lets callers thread
    failures into the workflow execution layer (where the action registry
    re-raises NetGentErrors so retry routing kicks in) while keeping the
    success path typed cleanly. Inside a workflow step body, callers
    typically call ``.unwrap()``; outside they inspect ``.ok()`` /
    ``.error`` and choose whether to log or emit a timeline event before
    re-raising.
    """

    value: T | None = None
    error: NetGentError | None = None

    def ok(self) -> bool:
        return self.error is None

    def unwrap(self) -> T:
        """Return the value or re-raise the classified error.

        Inside a workflow step body the raise causes the step to fail,
        which the executor then routes through ``ActionRegistry`` —
        ``BusinessError`` vs. ``TransientError`` decides whether the
        action is retried or surfaced as a permanent failure.
        """
        if self.error is not None:
            raise self.error
        # cast is the caller's responsibility — they know whether the
        # operation produces a meaningful value (some return None on
        # success).
        return self.value  # type: ignore[return-value]


class BaseAdapter(ABC):
    """Wraps an external resource behind a uniform async open/close lifecycle.

    Adapter implementations must route every external call through
    :meth:`invoke`, which catches raw exceptions and hands them to
    :meth:`map_error`. The rest of the system therefore only ever sees
    `NetGentError` subclasses (`BusinessError` / `TransientError`) from
    adapters — never the raw library-level exception.
    """

    name: str | None = None

    @classmethod
    def adapter_name(cls) -> str:
        resolved = (cls.name or cls.__name__).strip()
        if not resolved:
            raise ValueError(f"{cls.__name__} must declare a non-empty adapter name")
        return resolved

    @abstractmethod
    async def open(self) -> None:
        """Acquire the underlying resource. Wrap I/O in :meth:`invoke`."""

    @abstractmethod
    async def close(self) -> None:
        """Release the underlying resource. Wrap I/O in :meth:`invoke`."""

    @abstractmethod
    def map_error(self, exc: Exception) -> NetGentError:
        """Translate a raw adapter-level exception into a `NetGentError`.

        Classify each failure mode as either a `BusinessError` (the caller's
        request is invalid or violates a domain rule — retrying won't help)
        or a `TransientError` (a retryable infrastructure hiccup such as a
        network blip, upstream 5xx, or rate limit).
        """

    async def invoke(self, op: Callable[[], Awaitable[T]]) -> AdapterResult[T]:
        """Run `op` and return its outcome as an :class:`AdapterResult`.

        Every adapter operation — `open`, `close`, `run`, and any other
        method that touches the external resource — must wrap its call in
        `invoke`. Exceptions never propagate out of `invoke`: raw failures
        are translated via :meth:`map_error` and packaged in the result's
        ``error`` slot; pre-existing `NetGentError` subclasses are
        preserved as-is so their original classification is not lost.

        Callers that want raise-control-flow can chain ``.unwrap()``;
        callers that want to inspect outcomes explicitly use ``.ok()`` /
        ``.error``.
        """
        try:
            return AdapterResult(value=await op())
        except NetGentError as exc:
            return AdapterResult(error=exc)
        except Exception as exc:
            return AdapterResult(error=self.map_error(exc))

    async def __aenter__(self) -> Self:
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()


__all__ = ["AdapterResult", "BaseAdapter"]
