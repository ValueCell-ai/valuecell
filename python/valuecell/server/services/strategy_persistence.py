from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from valuecell.agents.common.trading import models as agent_models
from valuecell.server.db.repositories.strategy_repository import (
    get_strategy_repository,
)


def persist_trade_history(
    strategy_id: str, trade: agent_models.TradeHistoryEntry
) -> Optional[dict]:
    """Persist a single TradeHistoryEntry into strategy_details via repository.

    Returns the inserted StrategyDetail-like dict on success, or None on failure.
    """
    repo = get_strategy_repository()
    try:
        # Skip if strategy does not exist (e.g., deleted)
        try:
            if repo.get_strategy_by_strategy_id(strategy_id) is None:
                logger.info(
                    "Skip persisting trade detail: strategy={} not found (possibly deleted)",
                    strategy_id,
                )
                return None
        except Exception:
            # If existence check fails, proceed but errors will be handled below
            pass
        # map direction and type
        ttype = trade.type.value if trade.type is not None else None
        side = trade.side.value if trade.side is not None else None

        # Prefer explicit entry/exit timestamps if provided; fall back to trade_ts
        if trade.entry_ts is not None:
            entry_time = datetime.fromtimestamp(
                trade.entry_ts / 1000.0, tz=timezone.utc
            )
        elif trade.trade_ts is not None:
            entry_time = datetime.fromtimestamp(
                trade.trade_ts / 1000.0, tz=timezone.utc
            )
        else:
            entry_time = None

        exit_time = (
            datetime.fromtimestamp(trade.exit_ts / 1000.0, tz=timezone.utc)
            if trade.exit_ts is not None
            else None
        )

        # Event time for repository: prefer entry_time, then exit_time, otherwise now
        event_time = entry_time or exit_time or datetime.now(timezone.utc)

        item = repo.add_detail_item(
            strategy_id=strategy_id,
            compose_id=trade.compose_id,
            trade_id=trade.trade_id,
            instruction_id=trade.instruction_id,
            symbol=trade.instrument.symbol,
            type=ttype or ("LONG" if (trade.quantity or 0) > 0 else "SHORT"),
            side=side or ("BUY" if (trade.quantity or 0) > 0 else "SELL"),
            leverage=float(trade.leverage) if trade.leverage is not None else None,
            quantity=abs(float(trade.quantity or 0.0)),
            entry_price=(
                float(trade.entry_price) if trade.entry_price is not None else None
            ),
            exit_price=(
                float(trade.exit_price) if trade.exit_price is not None else None
            ),
            avg_exec_price=(
                float(trade.avg_exec_price)
                if trade.avg_exec_price is not None
                else None
            ),
            unrealized_pnl=(
                float(trade.unrealized_pnl)
                if trade.unrealized_pnl is not None
                else (
                    float(trade.realized_pnl)
                    if trade.realized_pnl is not None
                    else None
                )
            ),
            realized_pnl=(
                float(trade.realized_pnl) if trade.realized_pnl is not None else None
            ),
            realized_pnl_pct=(
                float(trade.realized_pnl_pct)
                if trade.realized_pnl_pct is not None
                else None
            ),
            notional_entry=(
                float(trade.notional_entry)
                if trade.notional_entry is not None
                else None
            ),
            notional_exit=(
                float(trade.notional_exit) if trade.notional_exit is not None else None
            ),
            fee_cost=(float(trade.fee_cost) if trade.fee_cost is not None else None),
            # Note: store unrealized_pnl separately if available on the DTO
            # (some callers may populate unrealized vs realized differently)
            # Keep backward-compatibility: prefer trade.unrealized_pnl when present
            # If both present, the DTO should include both; StrategyDetail currently only stores unrealized_pnl.
            holding_ms=int(trade.holding_ms) if trade.holding_ms is not None else None,
            event_time=event_time,
            entry_time=entry_time,
            exit_time=exit_time,
            note=trade.note,
        )

        if item is None:
            logger.error(
                "Failed to persist trade detail for strategy={} trade={}",
                strategy_id,
                trade.trade_id,
            )
            return None

        return item.to_dict()
    except Exception:
        logger.exception(
            "persist_trade_history failed for {} {}",
            strategy_id,
            trade.trade_id,
        )
        return None


def persist_portfolio_view(view: agent_models.PortfolioView) -> bool:
    """Persist PortfolioView.positions into strategy_holdings (one row per symbol snapshot).

    Writes each position as a `StrategyHolding` snapshot with current timestamp if not provided.
    """
    repo = get_strategy_repository()
    strategy_id = view.strategy_id
    try:
        # Skip if strategy does not exist (e.g., deleted)
        try:
            if repo.get_strategy_by_strategy_id(strategy_id) is None:
                logger.info(
                    "Skip persisting portfolio view: strategy={} not found (possibly deleted)",
                    strategy_id,
                )
                return False
        except Exception:
            # If existence check fails, continue and let foreign key constraints guard writes
            pass
        if not strategy_id:
            logger.error("persist_portfolio_view missing strategy_id on view")
            return False

        snapshot_ts = (
            datetime.fromtimestamp(view.ts / 1000.0, tz=timezone.utc)
            if view.ts
            else None
        )

        cash = float(view.free_cash)
        total_value = float(view.total_value) if view.total_value is not None else cash
        total_unrealized = (
            float(view.total_unrealized_pnl)
            if view.total_unrealized_pnl is not None
            else None
        )
        total_realized = (
            float(view.total_realized_pnl)
            if view.total_realized_pnl is not None
            else None
        )
        gross_exposure = (
            float(view.gross_exposure) if view.gross_exposure is not None else None
        )
        net_exposure = (
            float(view.net_exposure) if view.net_exposure is not None else None
        )

        portfolio_item = repo.add_portfolio_snapshot(
            strategy_id=strategy_id,
            cash=cash,
            total_value=total_value,
            total_unrealized_pnl=total_unrealized,
            total_realized_pnl=total_realized,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            snapshot_ts=snapshot_ts,
        )
        if portfolio_item is None:
            logger.warning(
                "Failed to persist strategy portfolio snapshot for {}", strategy_id
            )

        for symbol, pos in view.positions.items():
            # pos is PositionSnapshot
            ttype = (
                pos.trade_type.value
                if pos.trade_type
                else ("LONG" if pos.quantity >= 0 else "SHORT")
            )
            repo.add_holding_item(
                strategy_id=strategy_id,
                symbol=symbol,
                type=ttype,
                leverage=float(pos.leverage) if pos.leverage is not None else None,
                entry_price=float(pos.avg_price) if pos.avg_price is not None else None,
                quantity=abs(float(pos.quantity)),
                unrealized_pnl=(
                    float(pos.unrealized_pnl)
                    if pos.unrealized_pnl is not None
                    else None
                ),
                unrealized_pnl_pct=(
                    float(pos.unrealized_pnl_pct)
                    if pos.unrealized_pnl_pct is not None
                    else None
                ),
                snapshot_ts=snapshot_ts,
            )
        return True
    except Exception:
        logger.exception("persist_portfolio_view failed for {}", strategy_id)
        return False


def persist_strategy_summary(summary: agent_models.StrategySummary) -> bool:
    """Persist a StrategySummary into the Strategy.strategy_metadata JSON.

    Returns True on success, False on failure.
    """
    repo = get_strategy_repository()
    strategy_id = summary.strategy_id
    try:
        # Only update existing strategies; do NOT recreate missing ones
        strategy = repo.get_strategy_by_strategy_id(strategy_id)
        if strategy is None:
            logger.info(
                "Skip persisting strategy summary: strategy={} not found (possibly deleted)",
                strategy_id,
            )
            return False

        existing_meta = strategy.strategy_metadata or {}
        meta = {
            **dict(existing_meta),
            **summary.model_dump(
                exclude_none=True,
                exclude={"strategy_id", "status"},
            ),
        }
        updated = repo.upsert_strategy(strategy_id, metadata=meta)
        return updated is not None
    except Exception:
        logger.exception("persist_strategy_summary failed for {}", strategy_id)
        return False


def strategy_running(strategy_id: str) -> bool:
    """Check if a strategy with the given strategy_id exists."""
    repo = get_strategy_repository()
    try:
        strategy = repo.get_strategy_by_strategy_id(strategy_id)
        return (
            strategy is not None
            and strategy.status == agent_models.StrategyStatus.RUNNING.value
        )
    except Exception:
        logger.exception("strategy_running check failed for {}", strategy_id)
        return False


def set_strategy_status(strategy_id: str, status: str) -> bool:
    """Set the status field for a strategy (convenience wrapper around upsert)."""
    repo = get_strategy_repository()
    try:
        # Only update if strategy exists; avoid recreating deleted strategies
        if repo.get_strategy_by_strategy_id(strategy_id) is None:
            logger.info(
                "Skip setting status for strategy={} to {}: strategy not found",
                strategy_id,
                status,
            )
            return False
        updated = repo.upsert_strategy(strategy_id, status=status)
        return updated is not None
    except Exception:
        logger.exception("set_strategy_status failed for {}", strategy_id)
        return False


def mark_strategy_stopped(strategy_id: str) -> bool:
    """Mark a strategy as stopped."""
    try:
        return set_strategy_status(
            strategy_id, agent_models.StrategyStatus.STOPPED.value
        )
    except Exception:
        logger.exception("mark_strategy_stopped failed for {}", strategy_id)
        return False


def persist_compose_cycle(
    strategy_id: str,
    compose_id: str,
    ts_ms: Optional[int],
    cycle_index: Optional[int],
    rationale: Optional[str],
) -> bool:
    """Persist a compose cycle metadata record.

    Does not store prompts, only timing and optional rationale.
    """
    repo = get_strategy_repository()
    try:
        compose_time = (
            datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
            if ts_ms is not None
            else None
        )
        item = repo.add_compose_cycle(
            strategy_id=strategy_id,
            compose_id=compose_id,
            compose_time=compose_time,
            cycle_index=cycle_index,
            rationale=rationale,
        )
        return item is not None
    except Exception:
        logger.exception(
            "persist_compose_cycle failed for {} {}", strategy_id, compose_id
        )
        return False


def persist_instructions(
    strategy_id: str,
    compose_id: str,
    instructions: list[agent_models.TradeInstruction],
) -> int:
    """Persist a list of TradeInstruction (including NOOP) for a compose cycle.

    Returns number of successfully inserted rows.
    """
    repo = get_strategy_repository()
    inserted = 0
    for ins in instructions:
        try:
            ok = repo.add_instruction(
                strategy_id=strategy_id,
                compose_id=compose_id,
                instruction_id=ins.instruction_id,
                symbol=ins.instrument.symbol,
                action=(ins.action.value if ins.action is not None else None),
                side=(ins.side.value if ins.side is not None else None),
                quantity=float(ins.quantity) if ins.quantity is not None else None,
                leverage=float(ins.leverage) if ins.leverage is not None else None,
                note=(ins.meta.get("rationale") if ins.meta else None),
            )
            if ok:
                inserted += 1
        except Exception:
            logger.warning(
                "Failed to persist instruction {} for {} {}",
                ins.instruction_id,
                strategy_id,
                compose_id,
            )
            continue
    return inserted


def update_initial_capital(strategy_id: str, new_initial_capital: float) -> bool:
    """Update `strategies.config.trading_config.initial_capital` for a strategy.

    This writes the provided value into the persisted strategy config so that
    downstream performance APIs that read from `strategies.config` reflect the
    actual initial capital used at runtime (e.g., LIVE mode free balance).

    Returns True on success, False on failure or if the strategy is missing.
    """
    repo = get_strategy_repository()
    try:
        strategy = repo.get_strategy_by_strategy_id(strategy_id)
        if strategy is None:
            logger.info(
                "Skip updating initial_capital: strategy={} not found (possibly deleted)",
                strategy_id,
            )
            return False

        # Ensure config and nested trading_config dict exist
        cfg = dict(strategy.config or {})
        tr = dict((cfg.get("trading_config") or {}) or {})

        try:
            tr["initial_capital"] = float(new_initial_capital)
        except Exception:
            # If conversion fails, keep raw value
            tr["initial_capital"] = new_initial_capital

        cfg["trading_config"] = tr

        updated = repo.upsert_strategy(strategy_id=strategy_id, config=cfg)
        if updated is None:
            logger.warning(
                "Failed to update initial_capital in config for strategy={}",
                strategy_id,
            )
            return False

        logger.info(
            "Updated strategies.config.trading_config.initial_capital to {} for strategy={}",
            tr.get("initial_capital"),
            strategy_id,
        )
        return True
    except Exception:
        logger.exception("update_initial_capital failed for {}", strategy_id)
        return False


def set_initial_capital_metadata(
    strategy_id: str,
    initial_capital: float,
    *,
    source: str | None = None,
    ts_ms: int | None = None,
) -> bool:
    """Record initial capital info into strategy.strategy_metadata.

    Fields stored:
    - initial_capital_live: float value used at start in LIVE mode
    - initial_capital_source: optional descriptor (e.g., 'live_snapshot_cash')
    - initial_capital_ts_ms: optional timestamp in milliseconds
    """
    repo = get_strategy_repository()
    try:
        strategy = repo.get_strategy_by_strategy_id(strategy_id)
        if strategy is None:
            logger.info(
                "Skip setting initial_capital metadata: strategy={} not found",
                strategy_id,
            )
            return False

        meta = dict(strategy.strategy_metadata or {})
        try:
            meta["initial_capital_live"] = float(initial_capital)
        except Exception:
            meta["initial_capital_live"] = initial_capital
        if source is not None:
            meta["initial_capital_source"] = source
        if ts_ms is not None:
            try:
                meta["initial_capital_ts_ms"] = int(ts_ms)
            except Exception:
                meta["initial_capital_ts_ms"] = ts_ms

        updated = repo.upsert_strategy(strategy_id=strategy_id, metadata=meta)
        if updated is None:
            logger.warning(
                "Failed to set initial_capital metadata for strategy={}",
                strategy_id,
            )
            return False

        logger.info(
            "Set initial_capital_live={} (source={}) in metadata for strategy={}",
            meta.get("initial_capital_live"),
            meta.get("initial_capital_source"),
            strategy_id,
        )
        return True
    except Exception:
        logger.exception("set_initial_capital_metadata failed for {}", strategy_id)
        return False
