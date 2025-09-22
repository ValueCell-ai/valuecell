"""Agent module initialization"""

# Core agent functionality
from .client import AgentClient
from .connect import RemoteConnections
from .registry import AgentRegistry

__all__ = [
    # Core agent exports
    "AgentClient",
    "RemoteConnections",
    "AgentRegistry",
]
