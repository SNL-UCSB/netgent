from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langchain_core.messages import ToolMessage

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
from clients.netgent.src.services import iperf, ndt, ping

if TYPE_CHECKING:
    from clients.netgent.src.agent.subagents.shell.agent import ShellRunAgentState


def bad_tool_name(state: ShellRunAgentState) -> dict[str, list[ToolMessage]]:
    tool_call = state["messages"][-1].tool_calls[0]
    message = f"Could not find tool with name `{tool_call['name']}`. Make sure you are calling one of the allowed tools!"
    last_message = state["messages"][-1]
    last_message.tool_calls[0]["name"] = last_message.tool_calls[0]["name"].replace(
        ":",
        "",
    )
    return {
        "messages": [
            last_message,
            ToolMessage(content=message, tool_call_id=tool_call["id"]),
        ]
    }


async def run_iperf3(
    state: ShellRunAgentState,
) -> dict[str, list[ToolMessage]]:
    """Run an iperf3 test against a remote server."""

    tool_call = state["messages"][-1].tool_calls[0]
    tool_args = tool_call.get("args", {})
    if isinstance(tool_args, str):
        tool_args = json.loads(tool_args)

    host = tool_args["host"]
    port = tool_args.get("port")
    duration_seconds = tool_args.get("duration_seconds")
    interval_seconds = tool_args.get("interval_seconds")
    omit_seconds = tool_args.get("omit_seconds")
    udp = tool_args.get("udp", False)
    reverse = tool_args.get("reverse", False)
    bitrate = tool_args.get("bitrate")
    parallel = tool_args.get("parallel")

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
        return {
            "messages": [
                ToolMessage(
                    content=json.dumps(
                        {
                            "success": False,
                            "message": "IPerf3 Binary Not Found. Ensure that iperf3 is installed and available on PATH. Exeception: "
                            + str(exc),
                        }
                    ),
                    tool_call_id=tool_call["id"],
                )
            ]
        }

    except IPerf3Error as exc:
        return {
            "messages": [
                ToolMessage(
                    content=json.dumps(
                        {
                            "success": False,
                            "message": str(exc),
                        }
                    ),
                    tool_call_id=tool_call["id"],
                )
            ]
        }

    return {
        "messages": [
            ToolMessage(
                content=json.dumps(
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
                ),
                tool_call_id=tool_call["id"],
            )
        ]
    }


async def run_ping(
    state: ShellRunAgentState,
) -> dict[str, list[ToolMessage]]:
    """Run a ping test against a remote host."""

    tool_call = state["messages"][-1].tool_calls[0]
    tool_args = tool_call.get("args", {})
    if isinstance(tool_args, str):
        tool_args = json.loads(tool_args)

    host = tool_args["host"]
    count = tool_args.get("count")
    interval_seconds = tool_args.get("interval_seconds")
    timeout_seconds = tool_args.get("timeout_seconds")
    packet_size = tool_args.get("packet_size")

    try:
        result = await ping.run(
            host,
            count=count,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
            packet_size=packet_size,
        )
    except PingBinaryNotFoundError as exc:
        return {
            "messages": [
                ToolMessage(
                    content=json.dumps(
                        {
                            "success": False,
                            "message": "Ping Binary Not Found. Ensure that ping is installed and available on PATH. Exeception: "
                            + str(exc),
                        }
                    ),
                    tool_call_id=tool_call["id"],
                )
            ]
        }
    except PingError as exc:
        return {
            "messages": [
                ToolMessage(
                    content=json.dumps(
                        {
                            "success": False,
                            "message": str(exc),
                        }
                    ),
                    tool_call_id=tool_call["id"],
                )
            ]
        }

    return {
        "messages": [
            ToolMessage(
                content=json.dumps(
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
                ),
                tool_call_id=tool_call["id"],
            )
        ]
    }


def send_message(state: ShellRunAgentState) -> dict[str, list[ToolMessage]]:
    tool_call = state["messages"][-1].tool_calls[0]
    tool_args = tool_call.get("args", {})
    if isinstance(tool_args, str):
        tool_args = json.loads(tool_args)

    success = tool_args.get("success", False)
    reason = tool_args.get("reason", "")

    return {
        "messages": [
            ToolMessage(
                content=json.dumps({"success": success, "reason": reason}),
                tool_call_id=tool_call["id"],
            )
        ]
    }


async def run_ndt7(
    state: ShellRunAgentState,
) -> dict[str, list[ToolMessage]]:
    """Run an NDT7 throughput test."""

    tool_call = state["messages"][-1].tool_calls[0]
    tool_args = tool_call.get("args", {})
    if isinstance(tool_args, str):
        tool_args = json.loads(tool_args)

    timeout = tool_args.get("timeout")
    download = tool_args.get("download", True)
    upload = tool_args.get("upload", True)
    server = tool_args.get("server")
    service_url = tool_args.get("service_url")
    scheme = tool_args.get("scheme")
    no_verify = tool_args.get("no_verify", False)
    client_name = tool_args.get("client_name")

    if not download and not upload:
        return {
            "messages": [
                ToolMessage(
                    content=json.dumps(
                        {
                            "success": False,
                            "message": "At least one of download or upload must be true.",
                        }
                    ),
                    tool_call_id=tool_call["id"],
                )
            ]
        }

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
        return {
            "messages": [
                ToolMessage(
                    content=json.dumps(
                        {
                            "success": False,
                            "message": "NDT7 Binary Not Found. Ensure that ndt7 is installed and available on PATH. Exeception: "
                            + str(exc),
                        }
                    ),
                    tool_call_id=tool_call["id"],
                )
            ]
        }
    except NDT7Error as exc:
        return {
            "messages": [
                ToolMessage(
                    content=json.dumps(
                        {
                            "success": False,
                            "message": str(exc),
                        }
                    ),
                    tool_call_id=tool_call["id"],
                )
            ]
        }

    return {
        "messages": [
            ToolMessage(
                content=json.dumps(
                    {
                        "success": True,
                        "message": "NDT7 Tools Ran Successfully Without Any Errors.",
                        "output": {
                            "command": result.command,
                            "completed_tests": result.completed_tests,
                            "error_count": len(result.errors),
                            "measurement_count": len(result.measurements),
                            "download_measurement_count": len(
                                result.download_measurements
                            ),
                            "upload_measurement_count": len(result.upload_measurements),
                            "summary": result.summary,
                        },
                    }
                ),
                tool_call_id=tool_call["id"],
            )
        ]
    }
