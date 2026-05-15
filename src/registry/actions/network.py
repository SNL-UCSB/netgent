from __future__ import annotations

from typing import Literal

from clients.netgent.src.registry.actions.base import action
from clients.netgent.src.registry.actions.exception import ActionError
from clients.netgent.src.schema import ProcessOutcome
from clients.netgent.src.services.iperf import IperfService
from clients.netgent.src.services.ndt import NdtService
from clients.netgent.src.services.ping import PingService


@action(name="iperf")
async def run_iperf(
    host: str,
    port: int | None = None,
    duration_seconds: int | None = None,
    interval_seconds: int | None = None,
    omit_seconds: int | None = None,
    udp: bool = False,
    reverse: bool = False,
    bitrate: str | None = None,
    parallel: int | None = None,
) -> ProcessOutcome:
    async with IperfService() as svc:
        return await svc.run(
            host,
            port=port,
            duration_seconds=duration_seconds,
            interval_seconds=interval_seconds,
            omit_seconds=omit_seconds,
            udp=udp,
            reverse=reverse,
            bitrate=bitrate,
            parallel=parallel,
        )


@action(name="ndt")
async def run_ndt(
    timeout: str | None = None,
    download: bool = True,
    upload: bool = True,
    server: str | None = None,
    service_url: str | None = None,
    scheme: Literal["ws", "wss"] | None = None,
    no_verify: bool = False,
    client_name: str | None = None,
) -> ProcessOutcome:
    if not download and not upload:
        raise ActionError("At least one of download or upload must be true")

    async with NdtService() as svc:
        return await svc.run(
            timeout=timeout,
            download=download,
            upload=upload,
            server=server,
            service_url=service_url,
            scheme=scheme,
            no_verify=no_verify,
            client_name=client_name,
        )


@action(name="ping")
async def run_ping(
    host: str,
    count: int | None = None,
    interval_seconds: float | None = None,
    timeout_seconds: int | None = None,
    packet_size: int | None = None,
) -> ProcessOutcome:
    if count is not None:
        count = int(count)

    async with PingService() as svc:
        return await svc.run(
            host,
            count=count,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
            packet_size=packet_size,
        )


NETWORK_ACTIONS = (run_iperf, run_ndt, run_ping)


__all__ = ["NETWORK_ACTIONS", "run_iperf", "run_ndt", "run_ping"]
