"""Stream controller for strategy agent lifecycle and persistence orchestration.

This module encapsulates the stream/persistence/lifecycle logic so that users
developing custom strategies only need to focus on decision logic, data sources,
and features.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from loguru import logger

from valuecell.server.services import strategy_persistence

from ..utils import get_current_timestamp_ms

if TYPE_CHECKING:
    from ..core import DecisionCycleResult
    from ..runtime import StrategyRuntime


class ControllerState(str, Enum):
    """Internal state machine for stream controller."""

    INITIALIZING = "INITIALIZING"
    WAITING_RUNNING = "WAITING_RUNNING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"


class StreamController:
    """Orchestrates strategy lifecycle, streaming, and persistence.

    This controller manages:
    - State transitions (INITIALIZING -> WAITING_RUNNING -> RUNNING -> STOPPED)
    - Persistence of initial state, cycle results, and finalization
    - Waiting for external "running" signal from persistence layer
    """

    def __init__(self, strategy_id: str, timeout_s: int = 300) -> None:
        self.strategy_id = strategy_id
        self.timeout_s = timeout_s
        self._state = ControllerState.INITIALIZING

    @property
    def state(self) -> ControllerState:
        """Current controller state."""
        return self._state

    def transition_to(self, new_state: ControllerState) -> None:
        """Transition to a new state."""
        logger.info(
            "StreamController for strategy={}: {} -> {}",
            self.strategy_id,
            self._state.value,
            new_state.value,
        )
        self._state = new_state

    async def wait_running(self) -> None:
        """Wait until persistence marks strategy as running or timeout.

        Transitions from WAITING_RUNNING to RUNNING when successful.
        Swallows exceptions to avoid nested error handling.
        """
        self.transition_to(ControllerState.WAITING_RUNNING)
        since = datetime.now()
        try:
            while not strategy_persistence.strategy_running(self.strategy_id):
                elapsed = (datetime.now() - since).total_seconds()
                if elapsed > self.timeout_s:
                    logger.warning(
                        "Timeout waiting for strategy_id={} to be marked as running ({}s)",
                        self.strategy_id,
                        self.timeout_s,
                    )
                    break
                await asyncio.sleep(1)
                logger.info(
                    "Waiting for strategy_id={} to be marked as running",
                    self.strategy_id,
                )
        except Exception:
            logger.exception(
                "Error while waiting for strategy {} to be marked running",
                self.strategy_id,
            )
        self.transition_to(ControllerState.RUNNING)

    def persist_initial_state(self, runtime: StrategyRuntime) -> None:
        """Persist initial portfolio snapshot and strategy summary.

        Logs and swallows errors to keep controller resilient.
        """
        try:
            initial_portfolio = runtime.coordinator.portfolio_service.get_view()
            try:
                initial_portfolio.strategy_id = self.strategy_id
            except Exception:
                pass

            ok = strategy_persistence.persist_portfolio_view(initial_portfolio)
            if ok:
                logger.info(
                    "Persisted initial portfolio view for strategy={}", self.strategy_id
                )

            timestamp_ms = get_current_timestamp_ms()
            initial_summary = runtime.coordinator.build_summary(timestamp_ms, [])
            ok = strategy_persistence.persist_strategy_summary(initial_summary)
            if ok:
                logger.info(
                    "Persisted initial strategy summary for strategy={}",
                    self.strategy_id,
                )
        except Exception:
            logger.exception(
                "Failed to persist initial portfolio/summary for {}", self.strategy_id
            )

    def persist_cycle_results(self, result: DecisionCycleResult) -> None:
        """Persist trades, portfolio view, and strategy summary for a cycle.

        Errors are logged but not raised to keep the decision loop resilient.
        """
        try:
            for trade in result.trades:
                item = strategy_persistence.persist_trade_history(
                    self.strategy_id, trade
                )
                if item:
                    logger.info(
                        "Persisted trade {} for strategy={}",
                        trade.trade_id,
                        self.strategy_id,
                    )

            ok = strategy_persistence.persist_portfolio_view(result.portfolio_view)
            if ok:
                logger.info(
                    "Persisted portfolio view for strategy={}", self.strategy_id
                )

            ok = strategy_persistence.persist_strategy_summary(result.strategy_summary)
            if ok:
                logger.info(
                    "Persisted strategy summary for strategy={}", self.strategy_id
                )
        except Exception:
            logger.exception("Error persisting cycle results for {}", self.strategy_id)

    async def finalize(
        self, runtime: StrategyRuntime, reason: str = "normal_exit"
    ) -> None:
        """Finalize strategy: close resources and mark as stopped.

        Args:
            runtime: The strategy runtime to finalize
            reason: Reason for stopping (e.g., 'normal_exit', 'cancelled', 'error')
        """
        self.transition_to(ControllerState.STOPPED)
        # Close runtime resources (e.g., CCXT exchange)
        try:
            await runtime.coordinator.close()
            logger.info(
                "Closed runtime coordinator resources for strategy {} (reason: {})",
                self.strategy_id,
                reason,
            )
        except Exception:
            logger.exception(
                "Failed to close runtime resources for strategy {}", self.strategy_id
            )

        # Mark strategy as stopped in persistence
        try:
            strategy_persistence.mark_strategy_stopped(self.strategy_id)
            logger.info(
                "Marked strategy {} as stopped (reason: {})", self.strategy_id, reason
            )
        except Exception:
            logger.exception(
                "Failed to mark strategy stopped for {} (reason: {})",
                self.strategy_id,
                reason,
            )

    def is_running(self) -> bool:
        """Check if strategy is still running according to persistence layer."""
        try:
            return strategy_persistence.strategy_running(self.strategy_id)
        except Exception:
            logger.warning(
                "Error checking running status for strategy {}", self.strategy_id
            )
            return False
