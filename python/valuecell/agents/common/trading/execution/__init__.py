"""Execution adapters for trading instructions."""

from .ccxt_trading import CCXTExecutionGateway, create_ccxt_gateway
from .factory import create_execution_gateway, create_execution_gateway_sync
from .interfaces import BaseExecutionGateway
from .paper_trading import PaperExecutionGateway

__all__ = [
    "BaseExecutionGateway",
    "PaperExecutionGateway",
    "CCXTExecutionGateway",
    "create_ccxt_gateway",
    "create_execution_gateway",
    "create_execution_gateway_sync",
]
