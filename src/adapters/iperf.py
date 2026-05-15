from __future__ import annotations

from utils.execution import build_execution_command, run_subprocess
from adapters.base import AdapterResult, BaseAdapter
from core.errors import BusinessError, NetGentError, TransientError
from schema import ProcessOutcome


class IPerf3Error(BusinessError):
    """Base exception for iperf3 adapter failures."""


class IPerf3BinaryNotFoundError(IPerf3Error):
    """Raised when the iperf3 binary cannot be found."""


class IperfAdapter(BaseAdapter):
    """Async adapter that drives the ``iperf3`` CLI directly.

    Spawns ``iperf3 -c HOST -J ...`` via ``asyncio.create_subprocess_exec``
    on each :meth:`run` call and returns the raw subprocess outcome. JSON
    decoding and shape interpretation are the service layer's job.
    """

    name = "iperf"

    def __init__(self, *, binary: str = "iperf3") -> None:
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
        port: int = 5201,
        duration_seconds: int = 10,
        interval_seconds: int | None = None,
        omit_seconds: int | None = None,
        udp: bool = False,
        reverse: bool = False,
        bitrate: str | None = None,
        parallel: int | None = None,
        extra_args: list[str] | None = None,
    ) -> AdapterResult[ProcessOutcome]:
        if not self._opened:
            return AdapterResult(error=IPerf3Error("IperfAdapter is not open"))

        command = self._build_command(
            host=host,
            port=port,
            duration_seconds=duration_seconds,
            interval_seconds=interval_seconds,
            omit_seconds=omit_seconds,
            udp=udp,
            reverse=reverse,
            bitrate=bitrate,
            parallel=parallel,
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
            return IPerf3BinaryNotFoundError(str(exc))
        if isinstance(exc, PermissionError):
            return IPerf3Error(f"permission denied invoking iperf3: {exc}")
        if isinstance(exc, RuntimeError):
            return IPerf3Error(str(exc))
        if isinstance(exc, OSError):
            return TransientError(f"iperf3 subprocess I/O error: {exc}")
        return TransientError(f"iperf3 unexpected error: {exc}")

    def _build_command(
        self,
        *,
        host: str,
        port: int,
        duration_seconds: int,
        interval_seconds: int | None,
        omit_seconds: int | None,
        udp: bool,
        reverse: bool,
        bitrate: str | None,
        parallel: int | None,
        extra_args: list[str],
    ) -> list[str]:
        args = [
            "-J",
            "-c",
            host,
            "-p",
            str(port),
            "-t",
            str(duration_seconds),
        ]

        if interval_seconds is not None:
            args.extend(["-i", str(interval_seconds)])
        if omit_seconds is not None:
            args.extend(["-O", str(omit_seconds)])
        if udp:
            args.append("-u")
        if reverse:
            args.append("-R")
        if bitrate:
            args.extend(["-b", bitrate])
        if parallel is not None:
            args.extend(["-P", str(parallel)])

        args.extend(extra_args)
        return build_execution_command(binary=self._binary, args=args)


__all__ = [
    "IPerf3BinaryNotFoundError",
    "IPerf3Error",
    "IperfAdapter",
]
