"""LLM package: registry of available models and the service that calls them."""

from .registry import LLMRegistry
from .service import LLMService, llm_service

__all__ = ["LLMRegistry", "LLMService", "llm_service"]
