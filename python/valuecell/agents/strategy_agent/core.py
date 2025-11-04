from __future__ import annotations

# Core interfaces for orchestration and portfolio service.
# Plain ABCs to avoid runtime dependencies on pydantic. Concrete implementations
# wire the pipeline: data -> features -> composer -> execution -> history/digest.

from abc import ABC, abstractmethod
from typing import Optional

from .models import PortfolioView


class PortfolioService(ABC):
    """Provides current portfolio state to decision modules."""

    @abstractmethod
    def get_view(self) -> PortfolioView:
        """Return the latest portfolio view (positions, cash, optional constraints)."""
        raise NotImplementedError


class DecisionCoordinator(ABC):
    """Coordinates a single decision cycle end-to-end.

    A typical run performs:
        1) fetch portfolio view
        2) pull data and compute features
        3) build compose context (prompt_text, digest, constraints)
        4) compose (LLM + guardrails) -> trade instructions
        5) execute instructions
        6) record checkpoints and update digest
    """

    @abstractmethod
    def run_once(self) -> None:
        """Execute one decision cycle."""
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
