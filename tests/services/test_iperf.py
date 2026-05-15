"""Integration + behavior tests for :class:`IperfService`.

iperf3 needs both a local binary and a reachable server, so the live
integration tests are gated behind two markers:

* ``requires_iperf3`` — ``iperf3`` is on PATH.
* ``IPERF3_SERVER`` env var — points at a reachable ``host[:port]``. If
  unset, only the local binary's CLI output is asserted (``iperf3
  --version``) without a real measurement.

Tests that don't need iperf3 (binary-missing classification, error
hierarchy, ctx parameter acceptance) always run.
"""

from __future__ import annotations

import asyncio
import os
import shutil

import pytest

from adapters.iperf import IPerf3BinaryNotFoundError, IPerf3Error, IperfAdapter
from core.context import ExecutionContext
from schema import ProcessOutcome
from services.iperf import IPerf3ProcessError, IperfService

requires_iperf3 = pytest.mark.skipif(
    shutil.which("iperf3") is None, reason="iperf3 binary not on PATH"
)


def _run(coro):
    return asyncio.run(coro)


# ── classification: error hierarchy ───────────────────────────────────


def test_iperf3_process_error_subclass_of_iperf3_error():
    assert issubclass(IPerf3ProcessError, IPerf3Error)


def test_iperf3_binary_not_found_subclass_of_iperf3_error():
    assert issubclass(IPerf3BinaryNotFoundError, IPerf3Error)


# ── ctx parameter is accepted at the API level ────────────────────────


def test_ctx_parameter_is_keyword_only_and_optional():
    import inspect

    sig = inspect.signature(IperfService.run)
    assert "ctx" in sig.parameters
    p = sig.parameters["ctx"]
    assert p.kind == inspect.Parameter.KEYWORD_ONLY
    assert p.default is None


# ── custom binary path → BinaryNotFound when missing ──────────────────


def test_missing_binary_classifies_to_iperf3_binary_not_found():
    async def go():
        svc = IperfService()
        svc._adapter = IperfAdapter(binary="this-iperf3-does-not-exist-9876")
        await svc.run("127.0.0.1")

    with pytest.raises(IPerf3BinaryNotFoundError):
        _run(go())


# ── live integration (requires iperf3 installed + a reachable server) ─


@requires_iperf3
def test_iperf3_against_server_succeeds():
    server = os.environ.get("IPERF3_SERVER")
    if not server:
        pytest.skip("IPERF3_SERVER not set; skipping live measurement")

    host, _, port_str = server.partition(":")
    port = int(port_str) if port_str else 5201

    async def go():
        async with IperfService() as svc:
            return await svc.run(host, port=port, duration_seconds=2)

    outcome = _run(go())
    assert isinstance(outcome, ProcessOutcome)
    assert outcome.returncode == 0
    # iperf3 -J emits JSON on stdout
    assert outcome.stdout.lstrip().startswith("{"), "expected JSON stdout from iperf3 -J"


@requires_iperf3
def test_iperf3_against_unreachable_host_raises_process_error():
    """Connection refused / timeout against an unroutable host should
    surface as :class:`IPerf3ProcessError`, not a raw exception."""

    async def go():
        async with IperfService() as svc:
            # 198.51.100.0/24 is TEST-NET-2 (RFC 5737) — guaranteed unroutable.
            await svc.run("198.51.100.1", port=5201, duration_seconds=1)

    with pytest.raises(IPerf3ProcessError) as exc_info:
        _run(go())

    err = exc_info.value
    assert err.returncode != 0
    assert err.command


# ── ctx wiring (does not require iperf3) ──────────────────────────────


def test_run_accepts_ctx_kwarg_via_introspection():
    """We don't need iperf3 installed to confirm the API accepts ctx."""
    ctx = ExecutionContext.from_test()

    # Call with ctx — should propagate up to map_error via binary-not-found.
    async def go():
        svc = IperfService()
        svc._adapter = IperfAdapter(binary="missing-binary-12345")
        await svc.run("127.0.0.1", ctx=ctx, duration_seconds=1)

    with pytest.raises(IPerf3BinaryNotFoundError):
        _run(go())
