import json
from typing import Literal

from langchain.tools import tool

from clients.netgent.src.adapters.iperf import (
    IPerf3BinaryNotFoundError,
    IPerf3Error,
)
from clients.netgent.src.adapters.ndt import (
    NDT7BinaryNotFoundError,
    NDT7Error,
)
from clients.netgent.src.adapters.ping import (
    PingBinaryNotFoundError,
    PingError,
)
from clients.netgent.src.agent.subagents.shell.schema import (
    RunIPerf3Tool,
    RunNDT7Tool,
    RunPingTool,
)
from clients.netgent.src.services import iperf, ndt, ping


@tool(args_schema=RunIPerf3Tool)
async def run_iperf3(
    host: str,
    port: int | None = None,
    duration_seconds: int | None = None,
    interval_seconds: int | None = None,
    omit_seconds: int | None = None,
    udp: bool = False,
    reverse: bool = False,
    bitrate: str | None = None,
    parallel: int | None = None,
) -> str:
    """Run an iperf3 test against a remote server."""

    try:
        result = await iperf.run(
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
    except IPerf3BinaryNotFoundError as exc:
        return json.dumps(
            {
                "success": False,
                "message": "IPerf3 Binary Not Found. Ensure that iperf3 is installed and available on PATH. Exeception: "
                + str(exc),
            }
        )
    except IPerf3Error as exc:
        return json.dumps(
            {
                "success": False,
                "message": str(exc),
            }
        )

    return json.dumps(
        {
            "success": True,
            "message": "IPerf3 Tools Ran Successfully Without Any Errors.",
            "output": {
                "command": result.command,
                "protocol": result.protocol,
                "bits_per_second": result.bits_per_second,
                "jitter_ms": result.jitter_ms,
                "packet_loss_percent": result.packet_loss_percent,
                "summary": result.summary,
                "interval_count": len(result.intervals),
            },
        }
    )


@tool(args_schema=RunPingTool)
async def run_ping(
    host: str,
    count: int | None = None,
    interval_seconds: float | None = None,
    timeout_seconds: int | None = None,
    packet_size: int | None = None,
) -> str:
    """Run a ping test against a remote host."""

    try:
        result = await ping.run(
            host,
            count=count,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
            packet_size=packet_size,
        )
    except PingBinaryNotFoundError as exc:
        return json.dumps(
            {
                "success": False,
                "message": "Ping Binary Not Found. Ensure that ping is installed and available on PATH. Exeception: "
                + str(exc),
            }
        )
    except PingError as exc:
        return json.dumps(
            {
                "success": False,
                "message": str(exc),
            }
        )

    return json.dumps(
        {
            "success": True,
            "message": "Ping Tools Ran Successfully Without Any Errors.",
            "output": {
                "command": result.command,
                "host": result.host,
                "resolved_ip": result.resolved_ip,
                "packet_loss_percent": result.packet_loss_percent,
                "avg_latency_ms": result.avg_latency_ms,
                "jitter_ms": result.jitter_ms,
                "reply_count": len(result.replies),
                "statistics": (
                    result.statistics.model_dump(mode="json")
                    if result.statistics is not None
                    else None
                ),
            },
        }
    )


@tool(args_schema=RunNDT7Tool)
async def run_ndt7(
    timeout: str | None = None,
    download: bool = True,
    upload: bool = True,
    server: str | None = None,
    service_url: str | None = None,
    scheme: Literal["ws", "wss"] | None = None,
    no_verify: bool = False,
    client_name: str | None = None,
) -> str:
    """Run an NDT7 throughput test."""

    if not download and not upload:
        return json.dumps(
            {
                "success": False,
                "message": "At least one of download or upload must be true.",
            }
        )

    try:
        result = await ndt.run(
            timeout=timeout,
            download=download,
            upload=upload,
            server=server,
            service_url=service_url,
            scheme=scheme,
            no_verify=no_verify,
            client_name=client_name,
        )
    except NDT7BinaryNotFoundError as exc:
        return json.dumps(
            {
                "success": False,
                "message": "NDT7 Binary Not Found. Ensure that ndt7 is installed and available on PATH. Exeception: "
                + str(exc),
            }
        )
    except NDT7Error as exc:
        return json.dumps(
            {
                "success": False,
                "message": str(exc),
            }
        )

    return json.dumps(
        {
            "success": True,
            "message": "NDT7 Tools Ran Successfully Without Any Errors.",
            "output": {
                "command": result.command,
                "completed_tests": result.completed_tests,
                "error_count": len(result.errors),
                "measurement_count": len(result.measurements),
                "download_measurement_count": len(result.download_measurements),
                "upload_measurement_count": len(result.upload_measurements),
                "summary": result.summary,
            },
        }
    )


TOOLS = [run_iperf3, run_ndt7, run_ping]


__all__ = ["TOOLS", "run_iperf3", "run_ndt7", "run_ping"]
