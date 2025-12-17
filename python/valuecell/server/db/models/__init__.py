"""
ValueCell Server - Database Models

This package contains all database models for the ValueCell server.
All models are automatically imported to ensure they are registered with SQLAlchemy.
"""

# Import all models to ensure they are registered with SQLAlchemy
from .agent import Agent
from .asset import Asset

# Import base model
from .base import Base
from .strategy import Strategy
from .strategy_compose_cycle import StrategyComposeCycle
from .strategy_detail import StrategyDetail
from .strategy_holding import StrategyHolding
from .strategy_instruction import StrategyInstruction
from .strategy_portfolio import StrategyPortfolioView
from .user_profile import ProfileCategory, UserProfile
from .watchlist import Watchlist, WatchlistItem

# Export all models
__all__ = [
    "Base",
    "Agent",
    "Asset",
    "Strategy",
    "Watchlist",
    "WatchlistItem",
    "UserProfile",
    "ProfileCategory",
    "StrategyHolding",
    "StrategyDetail",
    "StrategyPortfolioView",
    "StrategyComposeCycle",
    "StrategyInstruction",
]
