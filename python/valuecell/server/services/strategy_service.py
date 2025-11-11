from datetime import datetime
from typing import List, Optional

from valuecell.server.api.schemas.strategy import (
    PositionHoldingItem,
    StrategyDetailItem,
    StrategyHoldingData,
)
from valuecell.server.db.repositories import get_strategy_repository


class StrategyService:
    @staticmethod
    async def get_strategy_holding(strategy_id: str) -> Optional[StrategyHoldingData]:
        repo = get_strategy_repository()
        holdings = repo.get_latest_holdings(strategy_id)
        if not holdings:
            return None

        snapshot_ts = holdings[0].snapshot_ts
        ts_ms = (
            int(snapshot_ts.timestamp() * 1000)
            if snapshot_ts
            else int(datetime.utcnow().timestamp() * 1000)
        )

        positions: List[PositionHoldingItem] = []
        for h in holdings:
            try:
                t = h.type
                if h.quantity is None or h.quantity == 0.0:
                    # Skip fully closed positions
                    continue
                qty = float(h.quantity)
                positions.append(
                    PositionHoldingItem(
                        symbol=h.symbol,
                        exchange_id=None,
                        quantity=qty if t == "LONG" else -qty if t == "SHORT" else qty,
                        avg_price=float(h.entry_price)
                        if h.entry_price is not None
                        else None,
                        mark_price=None,
                        unrealized_pnl=float(h.unrealized_pnl)
                        if h.unrealized_pnl is not None
                        else None,
                        unrealized_pnl_pct=float(h.unrealized_pnl_pct)
                        if h.unrealized_pnl_pct is not None
                        else None,
                        notional=None,
                        leverage=float(h.leverage) if h.leverage is not None else None,
                        entry_ts=None,
                        trade_type=t,
                    )
                )
            except Exception:
                continue

        return StrategyHoldingData(
            strategy_id=strategy_id,
            ts=ts_ms,
            cash=0.0,
            positions=positions,
            total_value=None,
            total_unrealized_pnl=None,
            available_cash=None,
        )

    @staticmethod
    async def get_strategy_detail(
        strategy_id: str,
    ) -> Optional[List[StrategyDetailItem]]:
        repo = get_strategy_repository()
        details = repo.get_details(strategy_id)
        if not details:
            return None

        items: List[StrategyDetailItem] = []
        for d in details:
            try:
                items.append(
                    StrategyDetailItem(
                        trade_id=d.trade_id,
                        symbol=d.symbol,
                        type=d.type,
                        side=d.side,
                        leverage=float(d.leverage) if d.leverage is not None else None,
                        quantity=float(d.quantity) if d.quantity is not None else 0.0,
                        unrealized_pnl=float(d.unrealized_pnl)
                        if d.unrealized_pnl is not None
                        else None,
                        entry_price=float(d.entry_price)
                        if d.entry_price is not None
                        else None,
                        exit_price=float(d.exit_price)
                        if d.exit_price is not None
                        else None,
                        holding_ms=int(d.holding_ms)
                        if d.holding_ms is not None
                        else None,
                        time=d.event_time.isoformat() if d.event_time else None,
                        note=d.note,
                    )
                )
            except Exception:
                continue

        return items
