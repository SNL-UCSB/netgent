from __future__ import annotations

from typing import Literal

from adapters.ndt import NdtAdapter, NDT7BinaryNotFoundError, NDT7Error
from core.context import ExecutionContext
from schema import ProcessOutcome
from services.base import BaseService


class NDT7ProcessError(NDT7Error):
    """Raised when the ndt7 client exits with a non-zero status."""

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


class NdtService(BaseService):
    """Run an ndt7 measurement and surface the raw subprocess outcome.

    Can be used directly::

        svc = NdtService()
        outcome = await svc.run(timeout="55s")

    or as an async context manager (pairs adapter open/close to a scope)::

        async with NdtService() as svc:
            outcome = await svc.run(timeout="55s")

    Non-zero exits raise :class:`NDT7ProcessError`.
    """

    def __init__(self) -> None:
        self._adapter = NdtAdapter()

    async def run(
        self,
        *,
        ctx: ExecutionContext | None = None,
        timeout: str | None = None,
        download: bool = True,
        upload: bool = True,
        server: str | None = None,
        service_url: str | None = None,
        scheme: Literal["ws", "wss"] | None = None,
        no_verify: bool = False,
        client_name: str | None = None,
    ) -> ProcessOutcome:
        await self._adapter.open()
        outcome = (
            await self._adapter.run(
                timeout=timeout if timeout is not None else "55s",
                download=download,
                upload=upload,
                server=server,
                service_url=service_url,
                scheme=scheme,
                no_verify=no_verify,
                client_name=client_name,
            )
        ).unwrap()

        if outcome.returncode != 0:
            raise NDT7ProcessError(
                "ndt7 client exited with a non-zero status",
                command=outcome.command,
                returncode=outcome.returncode,
                stdout=outcome.stdout,
                stderr=outcome.stderr,
            )
        return outcome


__all__ = [
    "NDT7BinaryNotFoundError",
    "NDT7Error",
    "NDT7ProcessError",
    "NdtService",
]
