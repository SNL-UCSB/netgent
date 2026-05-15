"""Integration + behavior tests for :class:`NdtService`.

A real ndt7 measurement requires both the ``ndt-client`` binary on PATH
and outbound internet to an M-Lab server, which makes the live path
flaky in CI. The success-path test is gated by:

* ``requires_ndt`` — ``ndt-client`` is on PATH.
* ``NETGENT_ALLOW_NDT_LIVE=1`` — opt-in flag to actually hit M-Lab.

Tests that don't need the binary (binary-missing classification, error
hierarchy, ctx parameter acceptance, the upload/download argument check)
always run.
"""

from __future__ import annotations

import asyncio
import os
import shutil

import pytest

from adapters.ndt import NDT7BinaryNotFoundError, NDT7Error, NdtAdapter
from core.context import ExecutionContext
from schema import ProcessOutcome
from services.ndt import NDT7ProcessError, NdtService

requires_ndt = pytest.mark.skipif(
    shutil.which("ndt-client") is None, reason="ndt-client binary not on PATH"
)


def _run(coro):
    return asyncio.run(coro)


# ── classification: error hierarchy ───────────────────────────────────


def test_ndt7_process_error_subclass_of_ndt7_error():
    assert issubclass(NDT7ProcessError, NDT7Error)


def test_ndt7_binary_not_found_subclass_of_ndt7_error():
    assert issubclass(NDT7BinaryNotFoundError, NDT7Error)


# ── ctx parameter is accepted at the API level ────────────────────────


def test_ctx_parameter_is_keyword_only_and_optional():
    import inspect

    sig = inspect.signature(NdtService.run)
    assert "ctx" in sig.parameters
    p = sig.parameters["ctx"]
    assert p.kind == inspect.Parameter.KEYWORD_ONLY
    assert p.default is None


# ── custom binary path → BinaryNotFound when missing ──────────────────


def test_missing_binary_classifies_to_ndt7_binary_not_found():
    async def go():
        svc = NdtService()
        svc._adapter = NdtAdapter(binary="this-ndt-client-does-not-exist-9876")
        await svc.run()

    with pytest.raises(NDT7BinaryNotFoundError):
        _run(go())


# ── ctx is accepted and the call still classifies correctly ───────────


def test_run_accepts_ctx_kwarg():
    ctx = ExecutionContext.from_test()

    async def go():
        svc = NdtService()
        svc._adapter = NdtAdapter(binary="missing-binary-12345")
        await svc.run(ctx=ctx)

    with pytest.raises(NDT7BinaryNotFoundError):
        _run(go())


# ── live integration (requires ndt-client + opt-in) ───────────────────


@requires_ndt
def test_ndt_live_measurement():
    if os.environ.get("NETGENT_ALLOW_NDT_LIVE") != "1":
        pytest.skip("set NETGENT_ALLOW_NDT_LIVE=1 to run live M-Lab measurement")

    async def go():
        async with NdtService() as svc:
            return await svc.run(timeout="30s")

    outcome = _run(go())
    assert isinstance(outcome, ProcessOutcome)
    assert outcome.returncode == 0
    # ndt-client -format json emits NDJSON; first non-empty line should be JSON.
    first = next(
        (line for line in outcome.stdout.splitlines() if line.strip()), ""
    )
    assert first.startswith("{"), "expected JSON-line stdout from ndt-client"
