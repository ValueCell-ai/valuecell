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

from valuecell.agents.common.trading import models as agent_models
from valuecell.server.db.repositories.strategy_repository import get_strategy_repository
from valuecell.server.services import strategy_persistence
from valuecell.utils.ts import get_current_timestamp_ms

if TYPE_CHECKING:
    from valuecell.agents.common.trading._internal.coordinator import (
        DecisionCycleResult,
    )
    from valuecell.agents.common.trading._internal.runtime import StrategyRuntime


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
            # Check if this is the first-ever snapshot before persisting
            is_first_snapshot = not self.has_initial_state()
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

            # When running in LIVE mode, update DB config.initial_capital to exchange available balance
            # and record initial capital into strategy metadata for fast access by APIs.
            # Only perform this on the first snapshot to avoid overwriting user edits or restarts.
            try:
                trading_mode = getattr(
                    runtime.request.exchange_config, "trading_mode", None
                )
                is_live = trading_mode == agent_models.TradingMode.LIVE
                if is_live and is_first_snapshot:
                    initial_cash = getattr(initial_portfolio, "free_cash", None)
                    if initial_cash is None:
                        initial_cash = getattr(
                            initial_portfolio, "account_balance", None
                        )
                    if initial_cash is None:
                        initial_cash = getattr(
                            runtime.request.trading_config, "initial_capital", None
                        )

                    if initial_cash is not None:
                        if strategy_persistence.update_initial_capital(
                            self.strategy_id, float(initial_cash)
                        ):
                            logger.info(
                                "Updated DB initial_capital to {} for strategy={} (LIVE mode)",
                                initial_cash,
                                self.strategy_id,
                            )
                            try:
                                # Also persist metadata for initial capital to avoid repeated first-snapshot queries
                                strategy_persistence.set_initial_capital_metadata(
                                    strategy_id=self.strategy_id,
                                    initial_capital=float(initial_cash),
                                    source="live_snapshot_cash",
                                    ts_ms=timestamp_ms,
                                )
                                logger.info(
                                    "Recorded initial_capital_live={} (source=live_snapshot_cash) in metadata for strategy={}",
                                    initial_cash,
                                    self.strategy_id,
                                )
                            except Exception:
                                logger.exception(
                                    "Failed to set initial_capital metadata for {}",
                                    self.strategy_id,
                                )
                        else:
                            logger.warning(
                                "Failed to update DB initial_capital for strategy={} (LIVE mode)",
                                self.strategy_id,
                            )
            except Exception:
                logger.exception(
                    "Error while updating DB initial_capital from live balance for {}",
                    self.strategy_id,
                )
        except Exception:
            logger.exception(
                "Failed to persist initial portfolio/summary for {}", self.strategy_id
            )

    def has_initial_state(self) -> bool:
        """Return True if an initial portfolio snapshot already exists.

        This allows idempotent strategy restarts without duplicating the first snapshot.
        """
        try:
            repo = get_strategy_repository()
            snap = repo.get_latest_portfolio_snapshot(self.strategy_id)
            return snap is not None
        except Exception:
            logger.warning(
                "has_initial_state check failed for strategy {}", self.strategy_id
            )
            return False

    def get_latest_portfolio_snapshot(self):
        """Return the latest stored portfolio snapshot or None.

        This is a convenience wrapper around the repository call so callers
        can inspect persisted initial state (for resume semantics).
        """
        try:
            repo = get_strategy_repository()
            snap = repo.get_latest_portfolio_snapshot(self.strategy_id)
            return snap
        except Exception:
            logger.warning(
                "Failed to fetch latest portfolio snapshot for strategy {}",
                self.strategy_id,
            )
            return None

    def persist_cycle_results(self, result: DecisionCycleResult) -> None:
        """Persist trades, portfolio view, and strategy summary for a cycle.

        Errors are logged but not raised to keep the decision loop resilient.
        """
        try:
            # Persist compose cycle and instructions first (NOOP included)
            try:
                strategy_persistence.persist_compose_cycle(
                    strategy_id=self.strategy_id,
                    compose_id=result.compose_id,
                    ts_ms=result.timestamp_ms,
                    cycle_index=result.cycle_index,
                    rationale=result.rationale,
                )
            except Exception:
                logger.warning(
                    "Failed to persist compose cycle for strategy={} compose_id={}",
                    self.strategy_id,
                    result.compose_id,
                )

            try:
                strategy_persistence.persist_instructions(
                    strategy_id=self.strategy_id,
                    compose_id=result.compose_id,
                    instructions=list(result.instructions or []),
                )
            except Exception:
                logger.warning(
                    "Failed to persist compose instructions for strategy={} compose_id={}",
                    self.strategy_id,
                    result.compose_id,
                )

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

    def persist_portfolio_snapshot(self, runtime: StrategyRuntime) -> None:
        """Persist a final portfolio snapshot (used at shutdown).

        Mirrors portfolio part of cycle persistence but without trades or summary refresh.
        Errors are logged and swallowed.
        """
        try:
            view = runtime.coordinator.portfolio_service.get_view()
            try:
                view.strategy_id = self.strategy_id
            except Exception:
                pass
            ok = strategy_persistence.persist_portfolio_view(view)
            if ok:
                logger.info(
                    "Persisted final portfolio snapshot for strategy={}",
                    self.strategy_id,
                )
        except Exception:
            logger.exception(
                "Failed to persist final portfolio snapshot for {}", self.strategy_id
            )

    async def finalize(
        self,
        runtime: StrategyRuntime,
        reason: agent_models.StopReason | str = agent_models.StopReason.NORMAL_EXIT,
        reason_detail: str | None = None,
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

        # With simplified statuses, all terminal states map to STOPPED.
        # Preserve the detailed stop reason in strategy metadata for resume logic.
        final_status = agent_models.StrategyStatus.STOPPED.value

        # Mark strategy as stopped/error in persistence
        try:
            strategy_persistence.set_strategy_status(self.strategy_id, final_status)
            reason_value = getattr(reason, "value", reason)
            logger.info(
                "Marked strategy {} as {} (reason: {})",
                self.strategy_id,
                final_status,
                reason_value,
            )
        except Exception:
            logger.exception(
                "Failed to mark strategy {} for {} (reason: {})",
                final_status,
                self.strategy_id,
                getattr(reason, "value", reason),
            )
        self._record_stop_reason(reason, reason_detail)

    def is_running(self) -> bool:
        """Check if strategy is still running according to persistence layer."""
        try:
            return strategy_persistence.strategy_running(self.strategy_id)
        except Exception:
            logger.warning(
                "Error checking running status for strategy {}", self.strategy_id
            )
            return False

    def persist_trades(self, trades: list) -> None:
        """Persist a list of ad-hoc trades (e.g., from forced closure)."""
        if not trades:
            return
        try:
            for trade in trades:
                item = strategy_persistence.persist_trade_history(
                    self.strategy_id, trade
                )
                if item:
                    logger.info(
                        "Persisted ad-hoc trade {} for strategy={}",
                        trade.trade_id,
                        self.strategy_id,
                    )
        except Exception:
            logger.exception(
                "Error persisting ad-hoc trades for strategy {}", self.strategy_id
            )

    def _record_stop_reason(
        self, reason: agent_models.StopReason | str, reason_detail: str | None = None
    ) -> None:
        """Persist last stop reason inside strategy metadata for resume decisions.

        Accept either a StopReason enum or a raw string; store the normalized
        string value in the DB metadata.
        """
        try:
            repo = get_strategy_repository()
            strategy = repo.get_strategy_by_strategy_id(self.strategy_id)
            if strategy is None:
                return
            metadata = dict(strategy.strategy_metadata or {})
            metadata["stop_reason"] = getattr(reason, "value", reason)
            if reason_detail is not None:
                metadata["stop_reason_detail"] = reason_detail
            else:
                metadata.pop("stop_reason_detail", None)
            repo.upsert_strategy(strategy_id=self.strategy_id, metadata=metadata)
        except Exception:
            logger.warning(
                "Failed to record stop reason for strategy %s", self.strategy_id
            )
