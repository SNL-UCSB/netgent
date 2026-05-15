"""Execution helpers for subprocess-based adapters.

Provides the two primitives every shell-binary adapter needs:

* :func:`build_execution_command` — wraps a binary + args, optionally
  routing it through a Linux network namespace via
  ``nsenter ... ip netns exec``.
* :func:`run_subprocess` — async subprocess runner returning
  ``(returncode, stdout, stderr)``.

Wraps :envvar:`USE_LOCAL` and :envvar:`LINUX_NAMESPACE` as module-level
constants read once at import time.
"""

from __future__ import annotations

import asyncio
import os

from utils.env import get_bool

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency

    def load_dotenv(*args: object, **kwargs: object) -> bool:
        return False


load_dotenv()


USE_LOCAL: bool = get_bool("USE_LOCAL", default=True)
LINUX_NAMESPACE: str = os.getenv("LINUX_NAMESPACE", "ns1").strip() or "ns1"


def build_execution_command(*, binary: str, args: list[str]) -> list[str]:
    if USE_LOCAL:
        return [binary, *args]

    return [
        "nsenter",
        "-t",
        "1",
        "-m",
        "--",
        "ip",
        "netns",
        "exec",
        LINUX_NAMESPACE,
        binary,
        *args,
    ]


async def run_subprocess(command: list[str]) -> tuple[int, str, str]:
    """Spawn ``command`` and return ``(returncode, stdout, stderr)`` as text."""
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate()
    returncode = proc.returncode if proc.returncode is not None else -1
    return returncode, stdout_b.decode(errors="replace"), stderr_b.decode(errors="replace")


__all__ = [
    "LINUX_NAMESPACE",
    "USE_LOCAL",
    "build_execution_command",
    "run_subprocess",
]
