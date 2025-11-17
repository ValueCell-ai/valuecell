from datetime import datetime
from typing import List, Optional

from valuecell.server.api.schemas.strategy import (
    PositionHoldingItem,
    StrategyActionCard,
    StrategyCycleDetail,
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
                entry_ts = None
                exit_ts = None
                if d and d.entry_price:
                    entry_ts = int(d.entry_time.timestamp() * 1000)
                if d and d.exit_time:
                    exit_ts = int(d.exit_time.timestamp() * 1000)

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
                        entry_ts=entry_ts,
                        exit_ts=exit_ts,
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

            ts_ms = int((c.compose_time or datetime.utcnow()).timestamp() * 1000)
            cycle_details.append(
                StrategyCycleDetail(
                    compose_id=c.compose_id,
                    ts=ts_ms,
                    rationale=c.rationale,
                    actions=cards,
                )
            )

        return cycle_details
