"""Agent module initialization"""

# Core agent functionality
from .client import AgentClient
from .connect import RemoteConnections
from .decorator import serve
from .registry import AgentRegistry

# Import types from the unified types module
from ..types import BaseAgent, RemoteAgentResponse, StreamResponse


__all__ = [
    # Core agent exports
    "AgentClient",
    "RemoteConnections",
    "serve",
    "AgentRegistry",
    "BaseAgent",
    "RemoteAgentResponse",
    "StreamResponse",
]
