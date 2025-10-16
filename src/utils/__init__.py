"""
NetGent Utilities

Common utilities and data structures used throughout the NetGent framework.

This module provides:
- Pydantic models for type-safe message passing
- Formatting functions for LLM context
- State representation classes
- Serialization helpers

Main Classes:
    Message: Base class for all message types
    Element: Represents a DOM element with properties
    ActionOutput: Structured output from LLM for action generation
    StatePrompt: High-level state definition for workflows
    Metadata: Captures page state at a specific point in time
    
Main Functions:
    format_context: Format message history for LLM consumption
    save_context_to_file: Save message context to JSON
    load_context_from_file: Load message context from JSON
"""

from .message import (
    Message,
    Element,
    Toolcall,
    ActionOutput,
    Decision,
    Reflection,
    Metadata,
    ExecutedState,
    StatePrompt,
    format_context,
    format_context_without_reflection,
    save_context_to_file,
    load_context_from_file,
)

__all__ = [
    "Message",
    "Element",
    "Toolcall",
    "ActionOutput",
    "Decision",
    "Reflection",
    "Metadata",
    "ExecutedState",
    "StatePrompt",
    "format_context",
    "format_context_without_reflection",
    "save_context_to_file",
    "load_context_from_file",
]

__version__ = "0.1.0"

