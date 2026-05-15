from __future__ import annotations

from adapters.ping import PingAdapter, PingBinaryNotFoundError, PingError
from core.context import ExecutionContext
from schema import ProcessOutcome
from services.base import BaseService


class PingProcessError(PingError):
    """Raised when ping exits with a non-zero status."""

    def __init__(
        self,
        message: str,
        *,
        command: list[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        super().__init__(message)
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:
        parts = [super().__str__(), f"returncode={self.returncode}"]
        cmd = " ".join(self.command)
        if cmd:
            parts.append(f"cmd={cmd}")
        # Long tails: 100-ping runs produce large stdout; keep enough for stats line.
        _tail = 6000
        err = (self.stderr or "").strip()
        if err:
            parts.append(f"stderr={err[-_tail:]}")
        out = (self.stdout or "").strip()
        if out:
            parts.append(f"stdout_tail={out[-_tail:]}")
        return " | ".join(parts)


class PingService(BaseService):
    def __init__(self) -> None:
        self._adapter = PingAdapter()

    async def run(
        self,
        host: str,
        *,
        ctx: ExecutionContext | None = None,
        count: int | None = None,
        interval_seconds: float | None = None,
        timeout_seconds: int | None = None,
        packet_size: int | None = None,
    ) -> ProcessOutcome:
        await self._adapter.open()
        outcome = (
            await self._adapter.run(
                host,
                count=count,
                interval_seconds=interval_seconds,
                timeout_seconds=timeout_seconds,
                packet_size=packet_size,
            )
        ).unwrap()

        if outcome.returncode != 0:
            raise PingProcessError(
                "ping exited with a non-zero status",
                command=outcome.command,
                returncode=outcome.returncode,
                stdout=outcome.stdout,
                stderr=outcome.stderr,
            )
        return outcome


__all__ = [
    "PingBinaryNotFoundError",
    "PingError",
    "PingProcessError",
    "PingService",
]
