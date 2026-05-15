from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProcessOutcome(BaseModel):
    """Raw subprocess result returned by execution adapters."""

    model_config = ConfigDict(extra="forbid")

    command: list[str]
    stdout: str
    stderr: str
    returncode: int


# ── Ping ──────────────────────────────────────────────────────────────────


class PingReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bytes: int
    source: str
    icmp_seq: int
    ttl: int | None = None
    time_ms: float
    raw: str


class PingStatistics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transmitted: int
    received: int
    packet_loss_percent: float
    total_time_ms: int | None = None
    min_ms: float | None = None
    avg_ms: float | None = None
    max_ms: float | None = None
    jitter_ms: float | None = None


class PingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: list[str]
    stdout: str
    stderr: str
    returncode: int
    host: str | None = None
    resolved_ip: str | None = None
    replies: list[PingReply] = Field(default_factory=list)
    statistics: PingStatistics | None = None

    @property
    def packet_loss_percent(self) -> float | None:
        if self.statistics is None:
            return None
        return self.statistics.packet_loss_percent

    @property
    def avg_latency_ms(self) -> float | None:
        if self.statistics is None:
            return None
        return self.statistics.avg_ms

    @property
    def jitter_ms(self) -> float | None:
        if self.statistics is None:
            return None
        return self.statistics.jitter_ms


# ── iperf3 ────────────────────────────────────────────────────────────────


class IPerf3Result(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: list[str]
    data: dict[str, Any]
    stdout: str
    stderr: str
    returncode: int

    @property
    def error(self) -> str | None:
        error = self.data.get("error")
        return error if isinstance(error, str) else None

    @property
    def protocol(self) -> str | None:
        protocol = self.data.get("start", {}).get("test_start", {}).get("protocol")
        return protocol if isinstance(protocol, str) else None

    @property
    def end(self) -> dict[str, Any]:
        end = self.data.get("end")
        return end if isinstance(end, dict) else {}

    @property
    def intervals(self) -> list[dict[str, Any]]:
        intervals = self.data.get("intervals")
        if not isinstance(intervals, list):
            return []
        return [interval for interval in intervals if isinstance(interval, dict)]

    @property
    def sent_summary(self) -> dict[str, Any]:
        summary = self.end.get("sum_sent")
        return summary if isinstance(summary, dict) else {}

    @property
    def received_summary(self) -> dict[str, Any]:
        summary = self.end.get("sum_received")
        return summary if isinstance(summary, dict) else {}

    @property
    def summary(self) -> dict[str, Any]:
        fallback = self.end.get("sum", {})
        if not isinstance(fallback, dict):
            fallback = {}
        return self.received_summary or self.sent_summary or fallback

    @property
    def bits_per_second(self) -> float | None:
        value = self.summary.get("bits_per_second")
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @property
    def jitter_ms(self) -> float | None:
        value = self.summary.get("jitter_ms")
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @property
    def packet_loss_percent(self) -> float | None:
        value = self.summary.get("lost_percent")
        if isinstance(value, (int, float)):
            return float(value)
        return None


# ── ndt7 ──────────────────────────────────────────────────────────────────

NDT7TestName = Literal["download", "upload"]


class NDT7Event(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    key: str = Field(validation_alias="Key")
    value: dict[str, Any] = Field(validation_alias="Value")

    @property
    def test(self) -> str | None:
        test = self.value.get("Test")
        return test if isinstance(test, str) else None


class NDT7Result(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: list[str]
    events: list[NDT7Event]
    summary: dict[str, Any] | None = None
    stdout: str
    stderr: str
    returncode: int

    def events_for(self, key: str, *, test: str | None = None) -> list[NDT7Event]:
        return [
            event
            for event in self.events
            if event.key == key and (test is None or event.test == test)
        ]

    @property
    def measurements(self) -> list[dict[str, Any]]:
        return [event.value for event in self.events_for("measurement")]

    @property
    def download_measurements(self) -> list[dict[str, Any]]:
        return [
            event.value for event in self.events_for("measurement", test="download")
        ]

    @property
    def upload_measurements(self) -> list[dict[str, Any]]:
        return [
            event.value for event in self.events_for("measurement", test="upload")
        ]

    @property
    def errors(self) -> list[dict[str, Any]]:
        return [event.value for event in self.events_for("error")]

    @property
    def completed_tests(self) -> list[str]:
        tests: list[str] = []
        for event in self.events_for("complete"):
            if event.test is not None:
                tests.append(event.test)
        return tests


__all__ = [
    "IPerf3Result",
    "NDT7Event",
    "NDT7Result",
    "NDT7TestName",
    "PingReply",
    "PingResult",
    "PingStatistics",
    "ProcessOutcome",
]
