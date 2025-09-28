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
from .watchlist import Watchlist, WatchlistItem

# Export all models
__all__ = [
    "Base",
    "Agent",
    "Asset",
    "Watchlist",
    "WatchlistItem",
]
