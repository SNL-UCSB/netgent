from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langchain_core.messages import ToolMessage

from adapters.iperf import IPerf3BinaryNotFoundError, IPerf3Error
from adapters.ndt import NDT7BinaryNotFoundError, NDT7Error
from adapters.ping import PingBinaryNotFoundError, PingError
from services.iperf import IperfService
from services.ndt import NdtService
from services.ping import PingService

if TYPE_CHECKING:
    from agents.subagents.shell.agent import ShellRunAgentState


# Output sent back to the LLM is the raw subprocess outcome — stdout /
# stderr / returncode / command. Parsing was removed from the services
# layer; the LLM reads the raw output and reasons about it directly.
def _outcome_payload(outcome) -> dict:
    return {
        "command": outcome.command,
        "returncode": outcome.returncode,
        "stdout": outcome.stdout,
        "stderr": outcome.stderr,
    }


def _error_message(tool_call_id: str, message: str) -> dict:
    return {
        "messages": [
            ToolMessage(
                content=json.dumps({"success": False, "message": message}),
                tool_call_id=tool_call_id,
            )
        ]
    }


def _success_message(tool_call_id: str, label: str, outcome) -> dict:
    return {
        "messages": [
            ToolMessage(
                content=json.dumps(
                    {
                        "success": True,
                        "message": f"{label} Ran Successfully Without Errors.",
                        "output": _outcome_payload(outcome),
                    }
                ),
                tool_call_id=tool_call_id,
            )
        ]
    }


def bad_tool_name(state: ShellRunAgentState) -> dict[str, list[ToolMessage]]:
    tool_call = state["messages"][-1].tool_calls[0]
    message = (
        f"Could not find tool with name `{tool_call['name']}`. "
        "Make sure you are calling one of the allowed tools!"
    )
    last_message = state["messages"][-1]
    last_message.tool_calls[0]["name"] = last_message.tool_calls[0]["name"].replace(":", "")
    return {
        "messages": [
            last_message,
            ToolMessage(content=message, tool_call_id=tool_call["id"]),
        ]
    }


async def run_iperf3(state: ShellRunAgentState) -> dict[str, list[ToolMessage]]:
    """Run an iperf3 test against a remote server."""
    tool_call = state["messages"][-1].tool_calls[0]
    args = tool_call.get("args", {})
    if isinstance(args, str):
        args = json.loads(args)

    try:
        async with IperfService() as svc:
            outcome = await svc.run(
                args["host"],
                port=args.get("port"),
                duration_seconds=args.get("duration_seconds"),
                interval_seconds=args.get("interval_seconds"),
                omit_seconds=args.get("omit_seconds"),
                udp=args.get("udp", False),
                reverse=args.get("reverse", False),
                bitrate=args.get("bitrate"),
                parallel=args.get("parallel"),
            )
    except IPerf3BinaryNotFoundError as exc:
        return _error_message(
            tool_call["id"],
            f"iperf3 binary not found. Ensure iperf3 is installed on PATH: {exc}",
        )
    except IPerf3Error as exc:
        return _error_message(tool_call["id"], str(exc))

    return _success_message(tool_call["id"], "iperf3", outcome)


async def run_ping(state: ShellRunAgentState) -> dict[str, list[ToolMessage]]:
    """Run a ping test against a remote host."""
    tool_call = state["messages"][-1].tool_calls[0]
    args = tool_call.get("args", {})
    if isinstance(args, str):
        args = json.loads(args)

    try:
        async with PingService() as svc:
            outcome = await svc.run(
                args["host"],
                count=args.get("count"),
                interval_seconds=args.get("interval_seconds"),
                timeout_seconds=args.get("timeout_seconds"),
                packet_size=args.get("packet_size"),
            )
    except PingBinaryNotFoundError as exc:
        return _error_message(
            tool_call["id"],
            f"ping binary not found. Ensure ping is installed on PATH: {exc}",
        )
    except PingError as exc:
        return _error_message(tool_call["id"], str(exc))

    return _success_message(tool_call["id"], "Ping", outcome)


def send_message(state: ShellRunAgentState) -> dict[str, list[ToolMessage]]:
    tool_call = state["messages"][-1].tool_calls[0]
    args = tool_call.get("args", {})
    if isinstance(args, str):
        args = json.loads(args)

    return {
        "messages": [
            ToolMessage(
                content=json.dumps(
                    {
                        "success": args.get("success", False),
                        "reason": args.get("reason", ""),
                    }
                ),
                tool_call_id=tool_call["id"],
            )
        ]
    }


async def run_ndt7(state: ShellRunAgentState) -> dict[str, list[ToolMessage]]:
    """Run an NDT7 throughput test."""
    tool_call = state["messages"][-1].tool_calls[0]
    args = tool_call.get("args", {})
    if isinstance(args, str):
        args = json.loads(args)

    download = args.get("download", True)
    upload = args.get("upload", True)
    if not download and not upload:
        return _error_message(tool_call["id"], "At least one of download or upload must be true.")

    try:
        async with NdtService() as svc:
            outcome = await svc.run(
                timeout=args.get("timeout"),
                download=download,
                upload=upload,
                server=args.get("server"),
                service_url=args.get("service_url"),
                scheme=args.get("scheme"),
                no_verify=args.get("no_verify", False),
                client_name=args.get("client_name"),
            )
    except NDT7BinaryNotFoundError as exc:
        return _error_message(
            tool_call["id"],
            f"ndt-client binary not found. Ensure ndt-client is installed on PATH: {exc}",
        )
    except NDT7Error as exc:
        return _error_message(tool_call["id"], str(exc))

    return _success_message(tool_call["id"], "NDT7", outcome)
