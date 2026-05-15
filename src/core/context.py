from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

Source = Literal["api", "webhook", "worker", "agent", "cli", "mcp", "test"]
Actor = Literal["user", "agent", "system"]


@dataclass(frozen=True)
class ExecutionContext:
    """Immutable identity for one logical operation.

    Fields:
        correlation_id   propagates end-to-end across systems (UUID)
        source           where the operation entered the system
        actor            who initiated it (user, agent, system)
        environment      runtime environment, copied from settings at creation
        user_id          the user the operation acts on, when known
        coordination_id  the coordination the operation is part of, when known
        request_id       == str(correlation_id) when source == "api" / "webhook"
        run_id           LangGraph run id when source == "agent"
        thread_id        LangGraph thread id when source == "agent"
        started_at       wall-clock UTC at creation; events may stamp their own
    """

    correlation_id: UUID
    source: Source
    actor: Actor
    environment: str
    coordination_id: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    # When True, the TransactionManager opens transactions under the
    # `amy_admin` Postgres role (BYPASSRLS). Use for system paths that
    # legitimately need cross-user reads — relay-worker phone-number
    # lookups before a user is resolved, migration backfills, operator
    # CLI commands. Normal request paths leave this False; the
    # transaction runs under `amy_app` (NOBYPASSRLS) with `amy.user_id`
    # set to the request's user, so RLS policies enforce isolation.
    is_system: bool = False

    @classmethod
    def from_api(
        cls,
        *,
        environment: str,
        correlation_id: UUID | None = None,
        coordination_id: str | None = None,
        actor: Actor = "user",
    ) -> ExecutionContext:
        return cls(
            correlation_id=correlation_id or uuid4(),
            source="api",
            actor=actor,
            environment=environment,
            coordination_id=coordination_id,
        )

    @classmethod
    def from_webhook(
        cls,
        *,
        environment: str,
        correlation_id: UUID | None = None,
        coordination_id: str | None = None,
    ) -> ExecutionContext:
        return cls(
            correlation_id=correlation_id or uuid4(),
            source="webhook",
            actor="system",
            environment=environment,
            coordination_id=coordination_id,
            is_system=True,
        )

    @classmethod
    def from_worker(
        cls,
        *,
        environment: str,
        correlation_id: UUID | None = None,
        coordination_id: str | None = None,
        is_system: bool = True,
    ) -> ExecutionContext:
        return cls(
            correlation_id=correlation_id or uuid4(),
            source="worker",
            actor="system",
            environment=environment,
            coordination_id=coordination_id,
            is_system=is_system,
        )

    @classmethod
    def from_agent(
        cls,
        *,
        environment: str,
        correlation_id: UUID | None = None,
        coordination_id: str | None = None,
    ) -> ExecutionContext:
        return cls(
            correlation_id=correlation_id or uuid4(),
            source="agent",
            actor="agent",
            environment=environment,
            coordination_id=coordination_id,
        )

    @classmethod
    def from_cli(
        cls,
        *,
        environment: str,
        correlation_id: UUID | None = None,
        coordination_id: str | None = None,
        is_system: bool = False,
    ) -> ExecutionContext:
        return cls(
            correlation_id=correlation_id or uuid4(),
            source="cli",
            actor="user",
            environment=environment,
            coordination_id=coordination_id,
            is_system=is_system,
        )

    @classmethod
    def from_mcp(
        cls,
        *,
        environment: str,
        correlation_id: UUID | None = None,
        coordination_id: str | None = None,
        actor: Actor = "agent",
    ) -> ExecutionContext:
        return cls(
            correlation_id=correlation_id or uuid4(),
            source="mcp",
            actor=actor,
            environment=environment,
            coordination_id=coordination_id,
        )

    @classmethod
    def from_test(
        cls,
        *,
        environment: str = "test",
        correlation_id: UUID | None = None,
        coordination_id: str | None = None,
        actor: Actor = "system",
    ) -> ExecutionContext:
        return cls(
            correlation_id=correlation_id or uuid4(),
            source="test",
            actor=actor,
            environment=environment,
            coordination_id=coordination_id,
        )


__all__ = ["Actor", "ExecutionContext", "Source"]
