"""Application configuration management.

Handles environment detection, .env file discovery, and env-specific overrides.
Shape mirrors `amyconnects-infra/backend/src/app/core/config.py` but trimmed to
NetGent's env vars.

Env-file priority (first hit wins):
    .env.{environment}.local
    .env.{environment}
    .env.local
    .env
"""

from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Environment detection ─────────────────────────────────────────────────────


class Environment(StrEnum):
    """Runtime environment for the service."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


def _get_environment() -> Environment:
    """Resolve the current environment from NETGENT_ENV. Accepts shorthand."""
    match os.getenv("NETGENT_ENV", "development").lower():
        case "production" | "prod":
            return Environment.PRODUCTION
        case "staging" | "stage":
            return Environment.STAGING
        case "test":
            return Environment.TEST
        case _:
            return Environment.DEVELOPMENT


def _discover_env_file() -> str | None:
    """Walk the env-file priority list and return the first that exists.

    Project root is two levels up from this file (`src/core/config.py`).
    """
    env = _get_environment().value
    base_dir = Path(__file__).resolve().parents[2]
    candidates = [
        base_dir / f".env.{env}.local",
        base_dir / f".env.{env}",
        base_dir / ".env.local",
        base_dir / ".env",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


# ── Settings ──────────────────────────────────────────────────────────────────


class Settings(BaseSettings):
    """Typed, validated application settings.

    Env-specific overrides (DEBUG, LOG_LEVEL, LOG_FORMAT) are applied in
    `_apply_environment_overrides` and only take effect when the corresponding
    env var is *not* explicitly set — so an env value always wins over the
    built-in default.
    """

    model_config = SettingsConfigDict(
        env_file=_discover_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ── Application ───────────────────────────────────────────────────────────

    PROJECT_NAME: str = "NetGent"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: Environment = Field(default_factory=_get_environment)

    # ── Logging ───────────────────────────────────────────────────────────────

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "console"

    # ── Execution (substrate worker namespace) ───────────────────────────────

    # When True, actions execute in the local process. When False, they're
    # wrapped in `nsenter ... ip netns exec <ns>` so traffic flows through
    # the dedicated worker network namespace (see client/execution.py).
    USE_LOCAL: bool = True
    LINUX_NAMESPACE: str = "ns1"

    # ── LLM providers ────────────────────────────────────────────────────────

    NETGENT_LLM_PROVIDER: Literal["anthropic", "gemini"] = "gemini"
    ANTHROPIC_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    # Default model name resolved against `LLMRegistry.LLMS`. The LLM service
    # falls back to `LLMS[0]` if this name isn't found.
    DEFAULT_LLM_MODEL: str = "gemini-3.1-flash-lite"
    # Per-call cap. Forwarded to the chat model where supported.
    MAX_TOKENS: int = 2000
    # Per-model retry budget; the LLM service uses tenacity to retry on
    # rate-limit / timeout / transient API errors before falling back to the
    # next model in the registry.
    MAX_LLM_CALL_RETRIES: int = 3
    # Wall-clock cap for the entire call_with_fallback budget (across retries
    # and model fallbacks). Bounds the worst case so callers don't block
    # indefinitely on a misbehaving provider.
    LLM_TOTAL_TIMEOUT: int = 60

    # ── Browser-use / Playwright ─────────────────────────────────────────────

    BROWSER_USE_HEADLESS: bool = True
    BROWSER_USE_MAX_STEPS: int = 30
    BROWSER_USE_MAX_REPAIR_ATTEMPTS: int = 2
    # Disables Playwright stealth patches — useful when diagnosing whether a
    # site break is caused by anti-bot evasion vs. real bugs.
    NETGENT_DISABLE_STEALTH: bool = False
    # When set, browser actions connect to a remote Browserless instance over
    # CDP instead of launching a local Chromium.
    BROWSERLESS_WS_ENDPOINT: str | None = None

    # ── Env-specific overrides ───────────────────────────────────────────────

    @model_validator(mode="after")
    def _apply_environment_overrides(self) -> Settings:
        """Dev defaults to DEBUG + console logs; prod tightens to WARNING + json.

        An override only fires when the env var wasn't explicitly set — so any
        value in `.env` always wins.
        """
        overrides: dict[Environment, dict[str, Any]] = {
            Environment.DEVELOPMENT: {
                "DEBUG": True,
                "LOG_LEVEL": "DEBUG",
                "LOG_FORMAT": "console",
            },
            Environment.STAGING: {
                "DEBUG": False,
                "LOG_LEVEL": "INFO",
                "LOG_FORMAT": "json",
            },
            Environment.PRODUCTION: {
                "DEBUG": False,
                "LOG_LEVEL": "WARNING",
                "LOG_FORMAT": "json",
            },
            Environment.TEST: {
                "DEBUG": True,
                "LOG_LEVEL": "DEBUG",
                "LOG_FORMAT": "console",
            },
        }
        for key, value in overrides.get(self.ENVIRONMENT, {}).items():
            if key not in os.environ:
                setattr(self, key, value)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
