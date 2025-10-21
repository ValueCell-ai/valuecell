"""Auto Trading Agent - Modular architecture for automated crypto trading

Modules:
- agent: Main AutoTradingAgent orchestrator
- models: Data models and enumerations
- position_manager: Position and cash management
- market_data: Technical analysis and indicator retrieval
- trade_recorder: Trade history and statistics
- trading_executor: High-level trade execution facade
- technical_analysis: Backward-compatible technical analysis interface
- portfolio_decision_manager: Portfolio-level decision making
- formatters: Message formatting utilities
- constants: Configuration constants
"""

from .agent import AutoTradingAgent
from .market_data import MarketDataProvider, SignalGenerator
from .models import (
    AutoTradingConfig,
    CashManagement,
    PortfolioValueSnapshot,
    Position,
    PositionHistorySnapshot,
    TechnicalIndicators,
    TradeAction,
    TradeHistoryRecord,
    TradeType,
    TradingRequest,
)
from .portfolio_decision_manager import (
    AssetAnalysis,
    PortfolioDecision,
    PortfolioDecisionManager,
)
from .position_manager import PositionManager
from .technical_analysis import AISignalGenerator, TechnicalAnalyzer
from .trade_recorder import TradeRecorder
from .trading_executor import TradingExecutor

__all__ = [
    # Main agent
    "AutoTradingAgent",
    # Core modules
    "TradingExecutor",
    "PositionManager",
    "TradeRecorder",
    "MarketDataProvider",
    "SignalGenerator",
    "PortfolioDecisionManager",
    # Models
    "AutoTradingConfig",
    "TradingRequest",
    "Position",
    "CashManagement",
    "TechnicalIndicators",
    "TradeHistoryRecord",
    "PositionHistorySnapshot",
    "PortfolioValueSnapshot",
    "TradeAction",
    "TradeType",
    "AssetAnalysis",
    "PortfolioDecision",
    # Utilities
    "TechnicalAnalyzer",
    "AISignalGenerator",
]
