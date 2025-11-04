from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..models import PortfolioView


class PortfolioService(ABC):
    """Provides current portfolio state to decision modules.

    Keep this as a read-only service used by DecisionCoordinator and Composer.
    """

    @abstractmethod
    def get_view(self) -> PortfolioView:
        """Return the latest portfolio view (positions, cash, optional constraints)."""
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
