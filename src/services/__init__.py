"""Services for the application.

Top-level package keeps eager imports light. Heavier subpackages (e.g.
`services.llm`, which pulls langchain) should be imported directly when
needed.
"""

from . import iperf, ndt, ping
from .iperf import IPerf3ProcessError
from .ndt import NDT7ProcessError
from .ping import PingProcessError

__all__ = [
    "IPerf3ProcessError",
    "NDT7ProcessError",
    "PingProcessError",
    "iperf",
    "ndt",
    "ping",
]
