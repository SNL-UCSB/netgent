"""LLM service with retries, circular fallback, and optional structured output."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any, TypeVar, overload

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import BaseMessage
from pydantic import BaseModel
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import settings
from core.logging import get_logger
from .registry import LLMRegistry

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def _build_retryable_exceptions() -> tuple[type[BaseException], ...]:
    """Collect provider-specific transient errors that warrant a retry.

    Imported lazily and best-effort: if a provider lib isn't installed its
    exceptions just aren't added. Falls back to ``Exception`` only when no
    provider hooks are available, since blindly retrying every error class
    would mask real bugs.
    """
    excs: list[type[BaseException]] = []
    try:
        import anthropic  # type: ignore[import-not-found]

        excs.extend(
            [
                anthropic.APIConnectionError,
                anthropic.APITimeoutError,
                anthropic.APIError,
                anthropic.RateLimitError,
            ]
        )
    except ImportError:
        pass
    try:
        from google.api_core import exceptions as gexc  # type: ignore[import-not-found]

        excs.extend(
            [
                gexc.DeadlineExceeded,
                gexc.ResourceExhausted,
                gexc.ServiceUnavailable,
                gexc.InternalServerError,
            ]
        )
    except ImportError:
        pass
    return tuple(excs) or (Exception,)


_RETRYABLE_EXCS = _build_retryable_exceptions()


class LLMService:
    """LLM calls with retries and circular fallback across the registry.

    Two distinct execution paths:

    - **Default path** (no ``model_name`` / ``response_format`` /
      ``model_kwargs``): uses ``self._llm`` which is the tool-bound agent
      model. Circular fallback updates ``self._llm`` in place so tool
      bindings survive switching models on retry.

    - **One-off path** (any override provided): resolves a fresh, local
      ``Runnable`` for the call without touching ``self._llm``, so
      concurrent default-path calls are never affected.
    """

    def __init__(self) -> None:
        self._llm: Any = None
        self._current_model_index: int = 0
        self._bound_tools: list[Any] = []

        names = LLMRegistry.get_all_names()
        try:
            self._current_model_index = names.index(settings.DEFAULT_LLM_MODEL)
            self._llm = LLMRegistry.get(settings.DEFAULT_LLM_MODEL)
            logger.info(
                "LLMService initialized: default_model=%s index=%s total=%s env=%s",
                settings.DEFAULT_LLM_MODEL,
                self._current_model_index,
                len(names),
                settings.ENVIRONMENT.value,
            )
        except Exception as exc:
            self._current_model_index = 0
            self._llm = LLMRegistry.LLMS[0]["llm"]
            logger.warning(
                "default model not found; using first: requested=%s using=%s error=%s",
                settings.DEFAULT_LLM_MODEL,
                names[0] if names else "<none>",
                exc,
            )

    # ── Public API ────────────────────────────────────────────────────────────

    @overload
    async def call(
        self,
        messages: LanguageModelInput,
        model_name: str | None = ...,
        response_format: None = ...,
        **model_kwargs: Any,
    ) -> BaseMessage: ...

    @overload
    async def call(
        self,
        messages: LanguageModelInput,
        model_name: str | None = ...,
        *,
        response_format: type[T],
        **model_kwargs: Any,
    ) -> T: ...

    async def call(
        self,
        messages: LanguageModelInput,
        model_name: str | None = None,
        response_format: type[BaseModel] | None = None,
        **model_kwargs: Any,
    ) -> BaseMessage | BaseModel:
        """Call the LLM with retries and circular fallback.

        Args:
            messages: Conversation messages to send.
            model_name: Override the model. ``None`` uses the current default.
            response_format: Pydantic schema for structured output. When
                provided the call chains ``.with_structured_output(schema)``
                and returns a validated instance of that schema instead of a
                raw ``BaseMessage``.
            **model_kwargs: Extra kwargs forwarded to ``LLMRegistry.get``
                when constructing a one-off model instance.

        Raises:
            RuntimeError: when all models fail after retries or the total
                timeout is exceeded.
        """
        try:
            return await asyncio.wait_for(
                self._call_with_fallback(
                    messages, model_name, response_format, model_kwargs
                ),
                timeout=settings.LLM_TOTAL_TIMEOUT,
            )
        except TimeoutError:
            logger.exception(
                "LLM total timeout exceeded after %ss", settings.LLM_TOTAL_TIMEOUT
            )
            raise RuntimeError(
                f"llm call timed out after {settings.LLM_TOTAL_TIMEOUT}s total budget"
            ) from None

    def get_llm(self) -> Any:
        return self._llm

    def bind_tools(self, tools: list[Any]) -> LLMService:
        if self._llm is not None:
            self._bound_tools = tools
            self._llm = self._llm.bind_tools(tools)
            logger.debug("tools bound to LLM: count=%s", len(tools))
        return self

    # ── Internal helpers ─────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(settings.MAX_LLM_CALL_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(_RETRYABLE_EXCS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _invoke_with_retry(
        self, llm: Any, messages: LanguageModelInput
    ) -> Any:
        try:
            response = await llm.ainvoke(messages)
            logger.debug("LLM call succeeded")
            return response
        except _RETRYABLE_EXCS as exc:
            logger.warning(
                "LLM call failed, retrying: type=%s error=%s",
                type(exc).__name__,
                exc,
            )
            raise

    def _switch_to_next_model(self) -> bool:
        """Advance the default model to the next entry (circular).

        Mutates ``self._llm`` and ``self._current_model_index`` so tool
        bindings survive model switches on the default agent path.
        """
        try:
            next_index = (self._current_model_index + 1) % len(LLMRegistry.LLMS)
            next_entry = LLMRegistry.get_model_at_index(next_index)
            logger.warning(
                "switching to next model: from_index=%s to_index=%s to_model=%s",
                self._current_model_index,
                next_index,
                next_entry["name"],
            )
            self._current_model_index = next_index
            self._llm = next_entry["llm"]
            if self._bound_tools:
                self._llm = self._llm.bind_tools(self._bound_tools)
            logger.info(
                "model switched: new_model=%s new_index=%s",
                next_entry["name"],
                next_index,
            )
            return True
        except Exception as exc:
            logger.error("model switch failed: %s", exc)
            return False

    async def _call_with_fallback(
        self,
        messages: LanguageModelInput,
        model_name: str | None,
        response_format: type[BaseModel] | None,
        model_kwargs: dict[str, Any],
    ) -> BaseMessage | BaseModel:
        """Build path-specific strategies and delegate to the shared loop."""

        def _override_target(idx: int) -> Any:
            base = LLMRegistry.get(LLMRegistry.LLMS[idx]["name"], **model_kwargs)
            return (
                base.with_structured_output(response_format)
                if response_format
                else base
            )

        def _default_target(_: int) -> Any:
            return self._llm

        def _default_advance(_: int) -> int | None:
            return (
                self._current_model_index if self._switch_to_next_model() else None
            )

        if model_name or response_format or model_kwargs:
            names = LLMRegistry.get_all_names()
            if model_name and model_name not in names:
                logger.error("requested model not found: %s", model_name)
                raise ValueError(
                    f"model '{model_name}' not found in registry. "
                    f"available models: {', '.join(names)}"
                )

            start = (
                names.index(model_name)
                if model_name
                else self._current_model_index
            )
            total = len(LLMRegistry.LLMS)

            def _override_advance(idx: int) -> int | None:
                return (idx + 1) % total

            get_target: Callable[[int], Any] = _override_target
            advance: Callable[[int], int | None] = _override_advance
        else:
            start = self._current_model_index
            get_target = _default_target
            advance = _default_advance

        return await self._fallback_loop(messages, start, get_target, advance)

    async def _fallback_loop(
        self,
        messages: LanguageModelInput,
        start: int,
        get_target: Callable[[int], Any],
        advance: Callable[[int], int | None],
    ) -> Any:
        total = len(LLMRegistry.LLMS)
        current = start
        models_tried = 0
        last_error: BaseException | None = None

        for models_tried in range(1, total + 1):
            current_name = LLMRegistry.LLMS[current]["name"]
            try:
                return await self._invoke_with_retry(get_target(current), messages)
            except _RETRYABLE_EXCS as exc:
                last_error = exc
                logger.error(
                    "LLM call failed after retries: model=%s tried=%s/%s error=%s",
                    current_name,
                    models_tried,
                    total,
                    exc,
                )
                if models_tried >= total:
                    logger.error(
                        "all models failed: tried=%s starting_model=%s",
                        models_tried,
                        LLMRegistry.LLMS[start]["name"],
                    )
                    break
                next_idx = advance(current)
                if next_idx is None:
                    logger.error("failed to switch to next model")
                    break
                current = next_idx

        raise RuntimeError(
            f"failed to get response from llm after trying {models_tried} models. "
            f"last error: {last_error}"
        )


llm_service = LLMService()


__all__ = ["LLMService", "llm_service"]
