from __future__ import annotations

from adapters.wget import WgetAdapter, WgetBinaryNotFoundError, WgetError
from core.context import ExecutionContext
from schema import ProcessOutcome
from services.base import BaseService


class WgetProcessError(WgetError):
    """Raised when wget exits with a non-zero status."""

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
        _tail = 4000
        err = (self.stderr or "").strip()
        if err:
            parts.append(f"stderr={err[-_tail:]}")
        out = (self.stdout or "").strip()
        if out:
            parts.append(f"stdout_tail={out[-_tail:]}")
        return " | ".join(parts)


class WgetService(BaseService):
    def __init__(self) -> None:
        self._adapter = WgetAdapter()

    async def run(
        self,
        url: str,
        *,
        ctx: ExecutionContext | None = None,
        output_file: str | None = None,
        timeout_seconds: int | None = None,
        tries: int | None = None,
        user_agent: str | None = None,
        no_check_certificate: bool = False,
    ) -> ProcessOutcome:
        await self._adapter.open()
        outcome = (
            await self._adapter.run(
                url,
                output_file=output_file,
                timeout_seconds=timeout_seconds,
                tries=tries,
                user_agent=user_agent,
                no_check_certificate=no_check_certificate,
            )
        ).unwrap()

        if outcome.returncode != 0:
            raise WgetProcessError(
                "wget exited with a non-zero status",
                command=outcome.command,
                returncode=outcome.returncode,
                stdout=outcome.stdout,
                stderr=outcome.stderr,
            )
        return outcome


__all__ = [
    "WgetBinaryNotFoundError",
    "WgetError",
    "WgetProcessError",
    "WgetService",
]
