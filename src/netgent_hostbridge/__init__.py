"""
NetGent host bridge.

A small, dependency-light service that runs **natively on the user's macOS
machine** (never inside Docker) and lets the Dockerized NetGent orchestrator
observe and control desktop applications through the macOS Accessibility (AX)
API and PyAutoGUI.

This is intentionally a standalone top-level package (NOT a submodule of
``netgent``): importing it must never pull in the ``netgent`` package's heavy
orchestrator dependencies (pydantic, langchain, langgraph, seleniumbase, ...),
since the host bridge typically runs in its own minimal virtualenv, isolated
from those.

The orchestrator (state machine, state synthesis, agent) stays in the container
and talks to this bridge over HTTP; the bridge performs the actual perception
(AX tree) and actuation (mouse/keyboard) on the host's real screen.

Run it with:

    python -m netgent_hostbridge --port 8765

See ``README.md`` in this package for setup and required permissions.
"""

from .server import serve, main

__all__ = ["serve", "main"]
