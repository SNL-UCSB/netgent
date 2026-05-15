from __future__ import annotations

from utils.execution import build_execution_command, run_subprocess
from adapters.base import AdapterResult, BaseAdapter
from core.errors import BusinessError, NetGentError, TransientError
from schema import ProcessOutcome


class PingError(BusinessError):
    """Base exception for ping adapter failures."""


class PingBinaryNotFoundError(PingError):
    """Raised when the ping binary cannot be found."""


class PingAdapter(BaseAdapter):
    """Async adapter that drives the system ``ping`` CLI directly.

    Spawns ``ping -c COUNT HOST ...`` per :meth:`run` call and returns the
    raw subprocess outcome. Parsing the textual output into structured
    statistics is the responsibility of the service layer.
    """

    name = "ping"

    def __init__(self, *, binary: str = "ping") -> None:
        self._binary = binary
        self._opened = False

    async def open(self) -> None:
        self._opened = True

    async def close(self) -> None:
        self._opened = False

    async def run(
        self,
        host: str,
        *,
        count: int = 4,
        interval_seconds: float | None = None,
        timeout_seconds: int | None = None,
        packet_size: int | None = None,
        extra_args: list[str] | None = None,
    ) -> AdapterResult[ProcessOutcome]:
        if not self._opened:
            return AdapterResult(error=PingError("PingAdapter is not open"))

        command = self._build_command(
            host=host,
            count=count,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
            packet_size=packet_size,
            extra_args=list(extra_args or []),
        )

        subprocess_result = await self.invoke(lambda: run_subprocess(command))
        if not subprocess_result.ok():
            return AdapterResult(error=subprocess_result.error)
        returncode, stdout, stderr = subprocess_result.value
        return AdapterResult(
            value=ProcessOutcome(
                command=command,
                stdout=stdout,
                stderr=stderr,
                returncode=returncode,
            )
        )

    def map_error(self, exc: Exception) -> NetGentError:
        if isinstance(exc, FileNotFoundError):
            return PingBinaryNotFoundError(str(exc))
        if isinstance(exc, PermissionError):
            return PingError(f"permission denied invoking ping: {exc}")
        if isinstance(exc, RuntimeError):
            return PingError(str(exc))
        if isinstance(exc, OSError):
            return TransientError(f"ping subprocess I/O error: {exc}")
        return TransientError(f"ping unexpected error: {exc}")

    def _build_command(
        self,
        *,
        host: str,
        count: int,
        interval_seconds: float | None,
        timeout_seconds: int | None,
        packet_size: int | None,
        extra_args: list[str],
    ) -> list[str]:
        args = ["-c", str(count)]
        if interval_seconds is not None:
            args.extend(["-i", str(interval_seconds)])
        if timeout_seconds is not None:
            args.extend(["-W", str(timeout_seconds)])
        if packet_size is not None:
            args.extend(["-s", str(packet_size)])
        args.extend(extra_args)
        args.append(host)
        return build_execution_command(binary=self._binary, args=args)


__all__ = [
    "PingAdapter",
    "PingBinaryNotFoundError",
    "PingError",
]
