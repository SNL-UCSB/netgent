from __future__ import annotations

from adapters.iperf import IperfAdapter, IPerf3BinaryNotFoundError, IPerf3Error
from core.context import ExecutionContext
from schema import ProcessOutcome
from services.base import BaseService


class IPerf3ProcessError(IPerf3Error):
    """Raised when iperf3 exits with a non-zero status."""

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


class IperfService(BaseService):
    def __init__(self) -> None:
        self._adapter = IperfAdapter()

    async def run(
        self,
        host: str,
        *,
        ctx: ExecutionContext | None = None,
        port: int | None = None,
        duration_seconds: int | None = None,
        interval_seconds: int | None = None,
        omit_seconds: int | None = None,
        udp: bool = False,
        reverse: bool = False,
        bitrate: str | None = None,
        parallel: int | None = None,
    ) -> ProcessOutcome:
        await self._adapter.open()
        outcome = (
            await self._adapter.run(
                host,
                port=port if port is not None else 5201,
                duration_seconds=duration_seconds if duration_seconds is not None else 10,
                interval_seconds=interval_seconds,
                omit_seconds=omit_seconds,
                udp=udp,
                reverse=reverse,
                bitrate=bitrate,
                parallel=parallel,
            )
        ).unwrap()

        if outcome.returncode != 0:
            raise IPerf3ProcessError(
                "iperf3 exited with a non-zero status",
                command=outcome.command,
                returncode=outcome.returncode,
                stdout=outcome.stdout,
                stderr=outcome.stderr,
            )
        return outcome


__all__ = [
    "IPerf3BinaryNotFoundError",
    "IPerf3Error",
    "IPerf3ProcessError",
    "IperfService",
]
