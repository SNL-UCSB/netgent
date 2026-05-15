"""Integration + behavior tests for :class:`PingService`.

Most assertions invoke the real ``ping`` binary against the loopback
interface, which is available on every supported dev / CI host. Tests
that need ``ping`` are gated by the ``requires_ping`` marker in
``conftest.py`` so they skip cleanly if it's unavailable.
"""

from __future__ import annotations

import asyncio
import shutil

import pytest

from adapters.ping import PingBinaryNotFoundError, PingError
from core.context import ExecutionContext
from schema import ProcessOutcome
from services.ping import PingProcessError, PingService

requires_ping = pytest.mark.skipif(
    shutil.which("ping") is None, reason="ping binary not on PATH"
)


def _run(coro):
    """Drive a coroutine from a sync pytest function."""
    return asyncio.run(coro)


# ── direct usage ──────────────────────────────────────────────────────


@requires_ping
def test_direct_ping_loopback_succeeds():
    async def go():
        return await PingService().run("127.0.0.1", count=1, timeout_seconds=2)

    outcome = _run(go())
    assert isinstance(outcome, ProcessOutcome)
    assert outcome.returncode == 0
    assert "127.0.0.1" in " ".join(outcome.command)
    assert outcome.stdout, "expected non-empty ping stdout"


# ── async-with usage ──────────────────────────────────────────────────


@requires_ping
def test_async_with_ping_loopback_succeeds():
    async def go():
        async with PingService() as svc:
            return await svc.run("127.0.0.1", count=1, timeout_seconds=2)

    outcome = _run(go())
    assert outcome.returncode == 0


# ── ctx parameter is accepted ─────────────────────────────────────────


@requires_ping
def test_ctx_parameter_accepted_when_passed():
    ctx = ExecutionContext.from_test()

    async def go():
        return await PingService().run(
            "127.0.0.1", ctx=ctx, count=1, timeout_seconds=2
        )

    outcome = _run(go())
    assert outcome.returncode == 0


@requires_ping
def test_ctx_parameter_accepted_when_omitted():
    async def go():
        return await PingService().run("127.0.0.1", count=1, timeout_seconds=2)

    outcome = _run(go())
    assert outcome.returncode == 0


# ── non-zero exit raises PingProcessError ─────────────────────────────


@requires_ping
def test_unresolvable_host_raises_process_error():
    async def go():
        async with PingService() as svc:
            await svc.run("does-not-exist.invalid", count=1, timeout_seconds=1)

    with pytest.raises(PingProcessError) as exc_info:
        _run(go())

    err = exc_info.value
    assert err.returncode != 0
    assert err.command  # should carry the executed argv
    # ping's resolver error lands on stderr on darwin and on stdout on linux —
    # accept either as long as one is non-empty
    assert (err.stderr or err.stdout).strip()


# ── classification: PingError hierarchy ───────────────────────────────


def test_ping_process_error_subclass_of_ping_error():
    assert issubclass(PingProcessError, PingError)


def test_ping_binary_not_found_subclass_of_ping_error():
    assert issubclass(PingBinaryNotFoundError, PingError)


# ── reuse a single service across multiple calls ──────────────────────


@requires_ping
def test_reuse_one_service_across_calls():
    async def go():
        svc = PingService()
        results = []
        for _ in range(3):
            results.append(await svc.run("127.0.0.1", count=1, timeout_seconds=2))
        return results

    outcomes = _run(go())
    assert len(outcomes) == 3
    assert all(o.returncode == 0 for o in outcomes)


# ── custom binary path → BinaryNotFound when missing ──────────────────


def test_custom_binary_missing_raises_binary_not_found():
    """Constructing the adapter with a bogus binary surfaces classified error."""

    from adapters.ping import PingAdapter

    async def go():
        svc = PingService()
        # Swap in an adapter pointed at a binary that definitely doesn't exist.
        svc._adapter = PingAdapter(binary="this-binary-does-not-exist-9876")
        await svc.run("127.0.0.1", count=1, timeout_seconds=2)

    with pytest.raises(PingBinaryNotFoundError):
        _run(go())
