"""Execution adapters for trading instructions."""

from .ccxt_trading import CCXTExecutionGateway, create_ccxt_gateway
from .factory import create_execution_gateway, create_execution_gateway_sync
from .interfaces import ExecutionGateway
from .paper_trading import PaperExecutionGateway

__all__ = [
    "ExecutionGateway",
    "PaperExecutionGateway",
    "CCXTExecutionGateway",
    "create_ccxt_gateway",
    "create_execution_gateway",
    "create_execution_gateway_sync",
]
