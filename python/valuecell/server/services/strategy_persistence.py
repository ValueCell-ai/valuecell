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
            entry_price=float(trade.entry_price)
            if trade.entry_price is not None
            else None,
            exit_price=float(trade.exit_price)
            if trade.exit_price is not None
            else None,
            unrealized_pnl=float(trade.realized_pnl)
            if trade.realized_pnl is not None
            else None,
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


def persist_portfolio_view(strategy_id: str, view: agent_models.PortfolioView) -> bool:
    """Persist PortfolioView.positions into strategy_holdings (one row per symbol snapshot).

    Writes each position as a `StrategyHolding` snapshot with current timestamp if not provided.
    """
    repo = get_strategy_repository()
    try:
        snapshot_ts = (
            datetime.fromtimestamp(view.ts / 1000.0, tz=timezone.utc)
            if view.ts
            else None
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
                unrealized_pnl=float(pos.unrealized_pnl)
                if pos.unrealized_pnl is not None
                else None,
                unrealized_pnl_pct=float(pos.unrealized_pnl_pct)
                if pos.unrealized_pnl_pct is not None
                else None,
                snapshot_ts=snapshot_ts,
            )
        return True
    except Exception:
        logger.exception("persist_portfolio_view failed for {}", strategy_id)
        return False


def build_strategy_summary(strategy_id: str) -> Optional[agent_models.StrategySummary]:
    """Build a StrategySummary by aggregating holdings and details.

    This is a simple implementation: sums realized_pnl from details and
    unrealized from latest holdings. It does not attempt to compute pnl_pct
    precisely (depends on how you define denominator); this function can be
    extended to use initial capital or last known equity.
    """
    repo = get_strategy_repository()
    try:
        details = repo.get_details(strategy_id, limit=1000) or []
        holdings = repo.get_latest_holdings(strategy_id) or []

        realized = 0.0
        for d in details:
            try:
                # if stored realized_pnl exists on detail (not all rows may have), sum
                if getattr(d, "realized_pnl", None) is not None:
                    realized += float(d.realized_pnl)
            except Exception:
                continue

        unreal = 0.0
        for h in holdings:
            try:
                if h.unrealized_pnl is not None:
                    unreal += float(h.unrealized_pnl)
            except Exception:
                continue

        # Build minimal StrategySummary DTO. More fields can be filled from Strategy model.
        summary = agent_models.StrategySummary(
            strategy_id=strategy_id,
            realized_pnl=realized,
            unrealized_pnl=unreal,
            last_updated_ts=int(datetime.now(timezone.utc).timestamp() * 1000),
        )
        return summary
    except Exception:
        logger.exception("build_strategy_summary failed for {}", strategy_id)
        return None
