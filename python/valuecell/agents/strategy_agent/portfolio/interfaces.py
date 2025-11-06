from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..models import PortfolioView, TradeHistoryEntry


class PortfolioService(ABC):
    """Provides current portfolio state to decision modules.

    Keep this as a read-only service used by DecisionCoordinator and Composer.
    """

    @abstractmethod
    def get_view(self) -> PortfolioView:
        """Return the latest portfolio view (positions, cash, optional constraints)."""
        raise NotImplementedError

    def apply_trades(
        self, trades: List[TradeHistoryEntry], market_snapshot: Dict[str, float]
    ) -> None:
        """Apply executed trades to the portfolio view (optional).

        Implementations that support state changes (paper trading, backtests)
        should update their internal view accordingly. This method is optional
        for read-only portfolio services, but providing it here makes the
        contract explicit to callers.
        """
        raise NotImplementedError


class PortfolioSnapshotStore(ABC):
    """Persist/load portfolio snapshots (optional for paper/backtest modes)."""

    @abstractmethod
    def load_latest(self) -> Optional[PortfolioView]:
        """Load the latest persisted portfolio snapshot, if any."""
        raise NotImplementedError

    @abstractmethod
    def save(self, view: PortfolioView) -> None:
        """Persist the provided portfolio view as a snapshot."""
        raise NotImplementedError
