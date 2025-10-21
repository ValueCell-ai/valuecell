"""
Auto Trading Agent Module

A modular automated crypto trading agent with technical analysis and position management.

Main components:
- agent: Main AutoTradingAgent class
- models: Data models and enumerations
- technical_analysis: Technical indicators and AI signal generation
- trading_executor: Trade execution and position management
- formatters: Message formatting utilities
- constants: Configuration constants
"""

from .agent import AutoTradingAgent
from .constants import (
    DEFAULT_CHECK_INTERVAL,
    DEFAULT_INITIAL_CAPITAL,
    MAX_SYMBOLS,
    PORTFOLIO_COMPONENT_TYPE,
    TRADING_COMPONENT_TYPE,
)
from .models import (
    AutoTradingConfig,
    Position,
    TechnicalIndicators,
    TradeAction,
    TradeType,
    TradingRequest,
)

__all__ = [
    # Main agent
    "AutoTradingAgent",
    # Models
    "AutoTradingConfig",
    "Position",
    "TechnicalIndicators",
    "TradeAction",
    "TradeType",
    "TradingRequest",
    # Constants
    "DEFAULT_CHECK_INTERVAL",
    "DEFAULT_INITIAL_CAPITAL",
    "MAX_SYMBOLS",
    "PORTFOLIO_COMPONENT_TYPE",
    "TRADING_COMPONENT_TYPE",
]
