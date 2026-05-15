"""Test-suite-wide setup.

Inserts ``src/`` onto ``sys.path`` so tests can ``import services.ping``
etc. ``pyproject.toml`` declares ``pythonpath = ["src"]`` but pytest's
auto-prepend of the test rootdir can shadow same-named packages when a
test subdirectory has an ``__init__.py`` (e.g. ``tests/services/`` would
shadow ``src/services/``). Keeping this insert explicit prevents that
class of collision regardless of subdirectory layout.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
