from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RunIPerf3Tool(BaseModel):
    """Run an iperf3 test against a remote server."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(
        ...,
        description="Short explanation for choosing iperf3.",
    )

    host: str = Field(
        ...,
        description="Hostname or IP Address of the IPerf3 Server.",
    )
    port: int | None = Field(
        default=None,
        ge=1,
        le=65535,
        description="Server Port. Defaults to the client's configured iperf3 port.",
    )
    duration_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Test duration in seconds. Defaults to the client's configured duration.",
    )
    interval_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Optional reporting interval in seconds.",
    )
    omit_seconds: int | None = Field(
        default=None,
        ge=0,
        description="Optional warm-up period to omit from the final result, in seconds.",
    )
    udp: bool = Field(
        default=False,
        description="Run the test in UDP mode instead of TCP.",
    )
    reverse: bool = Field(
        default=False,
        description="Run the test in reverse mode so the server sends traffic back to the client.",
    )
    bitrate: str | None = Field(
        default=None,
        description="Optional target bitrate such as '20M', mainly for UDP tests.",
    )
    parallel: int | None = Field(
        default=None,
        ge=1,
        description="Number of parallel client streams.",
    )


class RunPingTool(BaseModel):
    """Run a ping test against a remote host."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(
        ...,
        description="Short explanation for choosing ping.",
    )

    host: str = Field(
        ...,
        description="Hostname or IP Address to ping.",
    )
    count: int | None = Field(
        default=None,
        ge=1,
        description="Number of echo requests to send. Defaults to the client's configured count.",
    )
    interval_seconds: float | None = Field(
        default=None,
        gt=0,
        description="Optional interval between ping packets in seconds.",
    )
    timeout_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Optional per-packet timeout in seconds.",
    )
    packet_size: int | None = Field(
        default=None,
        ge=1,
        description="Optional ICMP payload size in bytes.",
    )


class RunNDT7Tool(BaseModel):
    """Run an NDT7 network throughput test."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(
        ...,
        description="Short explanation for choosing NDT7.",
    )

    timeout: str | None = Field(
        default=None,
        description="Optional timeout such as '55s'. Defaults to the client's configured timeout.",
    )
    download: bool = Field(
        default=True,
        description="Whether to run the download test.",
    )
    upload: bool = Field(
        default=True,
        description="Whether to run the upload test.",
    )
    server: str | None = Field(
        default=None,
        description="Optional NDT server hostname.",
    )
    service_url: str | None = Field(
        default=None,
        description="Optional explicit NDT service URL.",
    )
    scheme: Literal["ws", "wss"] | None = Field(
        default=None,
        description="Optional websocket scheme override.",
    )
    no_verify: bool = Field(
        default=False,
        description="Disable TLS certificate verification when using secure websocket connections.",
    )


class SendMessage(BaseModel):
    """Send a message to the user."""

    success: bool = Field(
        default=True,
        description="Whether the message was sent successfully.",
    )
    reason: str | None = Field(
        default=None,
        description="Reason for the success or failure.",
    )


__all__ = ["RunIPerf3Tool", "RunPingTool", "RunNDT7Tool", "SendMessage"]
