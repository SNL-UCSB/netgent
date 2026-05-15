"""LLM model registry with pre-initialized instances."""

from __future__ import annotations

from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from core.config import Environment, settings
from core.logging import get_logger

logger = get_logger(__name__)

_ANTHROPIC_API_KEY = SecretStr(settings.ANTHROPIC_API_KEY or "")
_GOOGLE_API_KEY = SecretStr(settings.GOOGLE_API_KEY or "")


class LLMRegistry:
    """Registry of available LLM models with pre-initialized instances.

    This class maintains a list of LLM configurations and provides
    methods to retrieve them by name with optional argument overrides.
    """

    LLMS: list[dict[str, Any]] = [
        {
            "name": "claude-sonnet-4-6",
            "llm": ChatAnthropic(
                model_name="claude-sonnet-4-6",
                anthropic_api_key=_ANTHROPIC_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                default_request_timeout=60.0,
            ),
        },
        {
            "name": "claude-haiku-4-5",
            "llm": ChatAnthropic(
                model_name="claude-haiku-4-5",
                anthropic_api_key=_ANTHROPIC_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                default_request_timeout=60.0,
            ),
        },
        {
            "name": "gemini-3.1-flash-lite-preview",
            "llm": ChatGoogleGenerativeAI(
                model="gemini-3.1-flash-lite-preview",
                google_api_key=_GOOGLE_API_KEY,
                max_output_tokens=settings.MAX_TOKENS,
            ),
        },
        {
            "name": "gemini-2.5-pro",
            "llm": ChatGoogleGenerativeAI(
                model="gemini-2.5-pro",
                google_api_key=_GOOGLE_API_KEY,
                max_output_tokens=settings.MAX_TOKENS,
                temperature=(
                    0.2 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.5
                ),
            ),
        },
    ]

    @classmethod
    def get(cls, model_name: str, **kwargs: Any) -> BaseChatModel:
        """Get an LLM by name with optional argument overrides.

        When kwargs are provided a fresh instance is returned with those
        overrides applied, leaving the shared registry entry untouched.

        Args:
            model_name: Name of the model to retrieve.
            **kwargs: Optional arguments to override default model configuration.

        Returns:
            BaseChatModel instance.

        Raises:
            ValueError: If model_name is not found in LLMS.
        """
        entry = next((e for e in cls.LLMS if e["name"] == model_name), None)

        if not entry:
            available = ", ".join(e["name"] for e in cls.LLMS)
            raise ValueError(
                f"model '{model_name}' not found in registry. available models: {available}"
            )

        if kwargs:
            logger.debug(
                "creating LLM with custom args: model=%s overrides=%s",
                model_name,
                list(kwargs),
            )
            if model_name.startswith("claude"):
                return ChatAnthropic(
                    model_name=model_name,
                    anthropic_api_key=_ANTHROPIC_API_KEY,
                    **kwargs,
                )
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=_GOOGLE_API_KEY,
                **kwargs,
            )

        logger.debug("using default LLM instance: model=%s", model_name)
        return entry["llm"]

    @classmethod
    def get_all_names(cls) -> list[str]:
        """Return all registered model names in order."""
        return [e["name"] for e in cls.LLMS]

    @classmethod
    def get_model_at_index(cls, index: int) -> dict[str, Any]:
        """Return the model entry at a specific index, wrapping to 0 if out of range."""
        if 0 <= index < len(cls.LLMS):
            return cls.LLMS[index]
        return cls.LLMS[0]


__all__ = ["LLMRegistry"]
