from __future__ import annotations

from typing import Literal

from utils.execution import build_execution_command, run_subprocess
from adapters.base import AdapterResult, BaseAdapter
from core.errors import BusinessError, NetGentError, TransientError
from schema import ProcessOutcome


class NDT7Error(BusinessError):
    """Base exception for ndt7 adapter failures."""


class NDT7BinaryNotFoundError(NDT7Error):
    """Raised when the ndt7 client binary cannot be found."""


class NdtAdapter(BaseAdapter):
    """Async adapter that drives the ``ndt-client`` CLI directly.

    Spawns ``ndt-client -format json ...`` per :meth:`run` call and returns
    the raw subprocess outcome. Parsing the streamed JSON event/summary
    lines is the responsibility of the service layer.
    """

    name = "ndt"

    def __init__(self, *, binary: str = "ndt-client") -> None:
        self._binary = binary
        self._opened = False

    async def open(self) -> None:
        self._opened = True

    async def close(self) -> None:
        self._opened = False

    async def run(
        self,
        *,
        timeout: str = "55s",
        download: bool = True,
        upload: bool = True,
        server: str | None = None,
        service_url: str | None = None,
        scheme: Literal["ws", "wss"] | None = None,
        no_verify: bool = False,
        client_name: str | None = None,
        extra_args: list[str] | None = None,
    ) -> AdapterResult[ProcessOutcome]:
        if not self._opened:
            return AdapterResult(error=NDT7Error("NdtAdapter is not open"))

        command = self._build_command(
            timeout=timeout,
            download=download,
            upload=upload,
            server=server,
            service_url=service_url,
            scheme=scheme,
            no_verify=no_verify,
            client_name=client_name,
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
            return NDT7BinaryNotFoundError(str(exc))
        if isinstance(exc, PermissionError):
            return NDT7Error(f"permission denied invoking ndt-client: {exc}")
        if isinstance(exc, RuntimeError):
            return NDT7Error(str(exc))
        if isinstance(exc, OSError):
            return TransientError(f"ndt7 subprocess I/O error: {exc}")
        return TransientError(f"ndt7 unexpected error: {exc}")

    def _build_command(
        self,
        *,
        timeout: str,
        download: bool,
        upload: bool,
        server: str | None,
        service_url: str | None,
        scheme: Literal["ws", "wss"] | None,
        no_verify: bool,
        client_name: str | None,
        extra_args: list[str],
    ) -> list[str]:
        args = ["-format", "json", "-timeout", timeout]

        if not download:
            args.extend(["-download=false"])
        if not upload:
            args.extend(["-upload=false"])
        if server:
            args.extend(["-server", server])
        if service_url:
            args.extend(["-service-url", service_url])
        if scheme:
            args.extend(["-scheme", scheme])
        if no_verify:
            args.append("-no-verify")
        if client_name:
            args.extend(["-client-name", client_name])

        args.extend(extra_args)
        return build_execution_command(binary=self._binary, args=args)


__all__ = [
    "NDT7BinaryNotFoundError",
    "NDT7Error",
    "NdtAdapter",
]
