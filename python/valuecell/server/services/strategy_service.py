from datetime import datetime
from typing import List, Optional

from valuecell.server.api.schemas.strategy import (
    PositionHoldingItem,
    StrategyActionCard,
    StrategyCycleDetail,
    StrategyHoldingData,
    StrategyPortfolioSummaryData,
)
from valuecell.server.db.repositories import get_strategy_repository


def _to_optional_float(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


class StrategyService:
    @staticmethod
    async def get_strategy_holding(strategy_id: str) -> Optional[StrategyHoldingData]:
        repo = get_strategy_repository()
        holdings = repo.get_latest_holdings(strategy_id)
        if not holdings:
            return None

        snapshot = repo.get_latest_portfolio_snapshot(strategy_id)
        snapshot_ts = snapshot.snapshot_ts if snapshot else None
        holding_ts = holdings[0].snapshot_ts if holdings else None

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
                        avg_price=(
                            float(h.entry_price) if h.entry_price is not None else None
                        ),
                        mark_price=None,
                        unrealized_pnl=(
                            float(h.unrealized_pnl)
                            if h.unrealized_pnl is not None
                            else None
                        ),
                        unrealized_pnl_pct=(
                            float(h.unrealized_pnl_pct)
                            if h.unrealized_pnl_pct is not None
                            else None
                        ),
                        notional=None,
                        leverage=float(h.leverage) if h.leverage is not None else None,
                        entry_ts=None,
                        trade_type=t,
                    )
                )
            except Exception:
                continue

        ts_source = snapshot_ts or holding_ts
        ts_ms = (
            int(ts_source.timestamp() * 1000)
            if ts_source
            else int(datetime.utcnow().timestamp() * 1000)
        )

        cash_value = _to_optional_float(snapshot.cash) if snapshot else None
        cash = cash_value if cash_value is not None else 0.0
        gross_exposure = (
            _to_optional_float(snapshot.gross_exposure) if snapshot else None
        )
        net_exposure = _to_optional_float(snapshot.net_exposure) if snapshot else None

        return StrategyHoldingData(
            strategy_id=strategy_id,
            ts=ts_ms,
            cash=cash,
            positions=positions,
            total_value=_to_optional_float(snapshot.total_value) if snapshot else None,
            total_unrealized_pnl=(
                _to_optional_float(snapshot.total_unrealized_pnl) if snapshot else None
            ),
            total_realized_pnl=(
                _to_optional_float(snapshot.total_realized_pnl) if snapshot else None
            ),
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            available_cash=cash,
        )

    @staticmethod
    async def get_strategy_portfolio_summary(
        strategy_id: str,
    ) -> Optional[StrategyPortfolioSummaryData]:
        repo = get_strategy_repository()
        snapshot = repo.get_latest_portfolio_snapshot(strategy_id)
        if not snapshot:
            return None

        ts = snapshot.snapshot_ts or datetime.utcnow()

        return StrategyPortfolioSummaryData(
            strategy_id=strategy_id,
            ts=int(ts.timestamp() * 1000),
            cash=_to_optional_float(snapshot.cash),
            total_value=_to_optional_float(snapshot.total_value),
            total_pnl=StrategyService._combine_realized_unrealized(snapshot),
            gross_exposure=_to_optional_float(
                getattr(snapshot, "gross_exposure", None)
            ),
            net_exposure=_to_optional_float(getattr(snapshot, "net_exposure", None)),
        )

    @staticmethod
    def _combine_realized_unrealized(snapshot) -> Optional[float]:
        realized = _to_optional_float(getattr(snapshot, "total_realized_pnl", None))
        unrealized = _to_optional_float(getattr(snapshot, "total_unrealized_pnl", None))
        if realized is None and unrealized is None:
            return None
        return (realized or 0.0) + (unrealized or 0.0)

    @staticmethod
    async def get_strategy_detail(
        strategy_id: str,
    ) -> Optional[List[StrategyCycleDetail]]:
        repo = get_strategy_repository()
        cycles = repo.get_cycles(strategy_id)
        if not cycles:
            return None

        cycle_details: List[StrategyCycleDetail] = []
        for c in cycles:
            # fetch instructions for this cycle
            instrs = repo.get_instructions_by_compose(strategy_id, c.compose_id)
            instr_ids = [i.instruction_id for i in instrs if i.instruction_id]
            details = repo.get_details_by_instruction_ids(strategy_id, instr_ids)
            detail_map = {d.instruction_id: d for d in details if d.instruction_id}

            cards: List[StrategyActionCard] = []
            for i in instrs:
                d = detail_map.get(i.instruction_id)
                # Construct card combining instruction (always present) with optional execution detail
                entry_at: Optional[datetime] = None
                exit_at: Optional[datetime] = None
                holding_time_ms: Optional[int] = None
                if d:
                    entry_at = d.entry_time
                    exit_at = d.exit_time
                    if d.holding_ms is not None:
                        holding_time_ms = int(d.holding_ms)
                    elif entry_at and exit_at:
                        try:
                            delta_ms = int((exit_at - entry_at).total_seconds() * 1000)
                        except TypeError:
                            delta_ms = None
                        if delta_ms is not None:
                            holding_time_ms = max(delta_ms, 0)

                # Human-friendly display label for the action
                action_display = i.action
                if action_display is not None:
                    # canonicalize values like 'open_long' -> 'OPEN LONG'
                    action_display = str(i.action).replace("_", " ").upper()

                cards.append(
                    StrategyActionCard(
                        instruction_id=i.instruction_id,
                        symbol=i.symbol,
                        action=i.action,
                        action_display=action_display,
                        side=i.side,
                        quantity=float(i.quantity) if i.quantity is not None else None,
                        leverage=(
                            float(i.leverage) if i.leverage is not None else None
                        ),
                        avg_exec_price=(
                            float(d.avg_exec_price)
                            if (d and d.avg_exec_price is not None)
                            else None
                        ),
                        entry_price=(
                            float(d.entry_price)
                            if (d and d.entry_price is not None)
                            else None
                        ),
                        exit_price=(
                            float(d.exit_price)
                            if (d and d.exit_price is not None)
                            else None
                        ),
                        entry_at=entry_at,
                        exit_at=exit_at,
                        holding_time_ms=holding_time_ms,
                        notional_entry=(
                            float(d.notional_entry)
                            if (d and d.notional_entry is not None)
                            else None
                        ),
                        notional_exit=(
                            float(d.notional_exit)
                            if (d and d.notional_exit is not None)
                            else None
                        ),
                        fee_cost=(
                            float(d.fee_cost)
                            if (d and d.fee_cost is not None)
                            else None
                        ),
                        realized_pnl=(
                            float(d.realized_pnl)
                            if (d and d.realized_pnl is not None)
                            else None
                        ),
                        realized_pnl_pct=(
                            float(d.realized_pnl_pct)
                            if (d and d.realized_pnl_pct is not None)
                            else None
                        ),
                        rationale=i.note,
                    )
                )

            created_at = c.compose_time or datetime.utcnow()
            cycle_details.append(
                StrategyCycleDetail(
                    compose_id=c.compose_id,
                    cycle_index=c.cycle_index,
                    created_at=created_at,
                    rationale=c.rationale,
                    actions=cards,
                )
            )

        return cycle_details
