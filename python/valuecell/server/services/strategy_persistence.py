from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from valuecell.agents.strategy_agent import models as agent_models
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
        # map direction and type
        ttype = trade.type.value if getattr(trade, "type", None) is not None else None
        side = trade.side.value if getattr(trade, "side", None) is not None else None

        event_time = (
            datetime.fromtimestamp(trade.trade_ts / 1000.0, tz=timezone.utc)
            if trade.trade_ts
            else None
        )

        item = repo.add_detail_item(
            strategy_id=strategy_id,
            trade_id=trade.trade_id,
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
            unrealized_pnl=(
                float(trade.unrealized_pnl)
                if getattr(trade, "unrealized_pnl", None) is not None
                else (
                    float(trade.realized_pnl)
                    if getattr(trade, "realized_pnl", None) is not None
                    else None
                )
            ),
            # Note: store unrealized_pnl separately if available on the DTO
            # (some callers may populate unrealized vs realized differently)
            # Keep backward-compatibility: prefer trade.unrealized_pnl when present
            # If both present, the DTO should include both; StrategyDetail currently only stores unrealized_pnl.
            holding_ms=int(trade.holding_ms) if trade.holding_ms is not None else None,
            event_time=event_time,
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
            getattr(trade, "trade_id", None),
        )
        return None


def persist_portfolio_view(view: agent_models.PortfolioView) -> bool:
    """Persist PortfolioView.positions into strategy_holdings (one row per symbol snapshot).

    Writes each position as a `StrategyHolding` snapshot with current timestamp if not provided.
    """
    repo = get_strategy_repository()
    strategy_id = view.strategy_id
    try:
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

        portfolio_item = repo.add_portfolio_snapshot(
            strategy_id=strategy_id,
            cash=cash,
            total_value=total_value,
            total_unrealized_pnl=total_unrealized,
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
        strategy = repo.get_strategy_by_strategy_id(strategy_id)
        existing_meta = (
            (strategy.strategy_metadata or {}) if strategy is not None else {}
        )
        meta = {**dict(existing_meta), **summary.model_dump(exclude_none=True)}
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
