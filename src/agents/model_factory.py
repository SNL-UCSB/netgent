"""Factory functions for the chat models the agents drive.

Two consumers, two model abstractions:

* :func:`get_langchain_model` — used by the shell decide step. Returns a
  LangChain ``BaseChatModel`` (so ``model.bind_tools(...)`` works).
* :func:`get_browser_use_model` — used by ``browser_use.Agent(llm=...)``.
  browser-use 0.5.x rejects plain LangChain models and requires its own
  ``browser_use.llm.BaseChatModel`` subclass (``ChatGoogle`` /
  ``ChatAnthropic``).
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel as LangChainBaseChatModel

from core.config import settings
from services.llm.registry import LLMRegistry


def get_langchain_model() -> LangChainBaseChatModel:
    """Return the configured default LangChain chat model."""
    return LLMRegistry.get(settings.DEFAULT_LLM_MODEL)


def get_browser_use_model():
    """Return a native ``browser_use.llm`` model for ``Agent(llm=...)``.

    Selected by ``settings.NETGENT_LLM_PROVIDER``. browser-use ships its
    own provider-specific chat classes; LangChain models are rejected
    with ``invalid llm, must be from browser_use.llm``.
    """
    if settings.NETGENT_LLM_PROVIDER == "anthropic":
        from browser_use.llm.anthropic.chat import ChatAnthropic

        return ChatAnthropic(
            model=settings.DEFAULT_LLM_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            max_tokens=settings.MAX_TOKENS,
        )

    # Default: gemini
    from browser_use.llm.google.chat import ChatGoogle

    return ChatGoogle(
        model=settings.DEFAULT_LLM_MODEL,
        api_key=settings.GOOGLE_API_KEY,
    )


__all__ = ["get_browser_use_model", "get_langchain_model"]
