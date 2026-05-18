from __future__ import annotations

from utils.execution import build_execution_command, run_subprocess
from adapters.base import AdapterResult, BaseAdapter
from core.errors import BusinessError, NetGentError, TransientError
from schema import ProcessOutcome


class WgetError(BusinessError):
    """Base exception for wget adapter failures."""


class WgetBinaryNotFoundError(WgetError):
    """Raised when the wget binary cannot be found."""


class WgetAdapter(BaseAdapter):
    """Async adapter that drives the system ``wget`` CLI directly.

    Spawns ``wget URL ...`` per :meth:`run` call and returns the raw
    subprocess outcome. Output (download progress / final summary) is
    captured on stderr by default; the service layer is responsible for
    interpreting it.
    """

    name = "wget"

    def __init__(self, *, binary: str = "wget") -> None:
        self._binary = binary
        self._opened = False

    async def open(self) -> None:
        self._opened = True

    async def close(self) -> None:
        self._opened = False

    async def run(
        self,
        url: str,
        *,
        output_file: str | None = None,
        timeout_seconds: int | None = None,
        tries: int | None = None,
        user_agent: str | None = None,
        no_check_certificate: bool = False,
        extra_args: list[str] | None = None,
    ) -> AdapterResult[ProcessOutcome]:
        if not self._opened:
            return AdapterResult(error=WgetError("WgetAdapter is not open"))

        command = self._build_command(
            url=url,
            output_file=output_file,
            timeout_seconds=timeout_seconds,
            tries=tries,
            user_agent=user_agent,
            no_check_certificate=no_check_certificate,
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
            return WgetBinaryNotFoundError(str(exc))
        if isinstance(exc, PermissionError):
            return WgetError(f"permission denied invoking wget: {exc}")
        if isinstance(exc, RuntimeError):
            return WgetError(str(exc))
        if isinstance(exc, OSError):
            return TransientError(f"wget subprocess I/O error: {exc}")
        return TransientError(f"wget unexpected error: {exc}")

    def _build_command(
        self,
        *,
        url: str,
        output_file: str | None,
        timeout_seconds: int | None,
        tries: int | None,
        user_agent: str | None,
        no_check_certificate: bool,
        extra_args: list[str],
    ) -> list[str]:
        # `-q` would silence the per-byte progress noise but we want the final
        # "saved [N/M]" line on stderr for parsing; `--show-progress` keeps
        # that summary without flooding stdout.
        args: list[str] = ["--no-verbose"]
        if output_file is not None:
            args.extend(["-O", output_file])
        if timeout_seconds is not None:
            args.extend(["--timeout", str(timeout_seconds)])
        if tries is not None:
            args.extend(["--tries", str(tries)])
        if user_agent is not None:
            args.extend(["--user-agent", user_agent])
        if no_check_certificate:
            args.append("--no-check-certificate")
        args.extend(extra_args)
        args.append(url)
        return build_execution_command(binary=self._binary, args=args)


__all__ = [
    "WgetAdapter",
    "WgetBinaryNotFoundError",
    "WgetError",
]
