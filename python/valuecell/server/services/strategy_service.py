from datetime import datetime
from typing import List, Optional

from valuecell.server.api.schemas.strategy import (
    PositionHoldingItem,
    StrategyActionCard,
    StrategyCycleDetail,
    StrategyHoldingData,
    StrategyPerformanceData,
    StrategyPortfolioSummaryData,
    StrategyType,
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

        first_snapshot = repo.get_first_portfolio_snapshot(strategy_id)
        if not first_snapshot:
            return None

        ts = snapshot.snapshot_ts or datetime.now(datetime.timezone.utc)
        total_value = _to_optional_float(snapshot.total_value)
        total_pnl = StrategyService._combine_realized_unrealized(snapshot)
        total_pnl_pct = (
            total_pnl / (total_value - total_pnl) if total_pnl is not None else 0.0
        )
        if baseline := _to_optional_float(first_snapshot.total_value):
            total_pnl = total_value - baseline
            total_pnl_pct = total_pnl / baseline

        return StrategyPortfolioSummaryData(
            strategy_id=strategy_id,
            ts=int(ts.timestamp() * 1000),
            cash=_to_optional_float(snapshot.cash),
            total_value=total_value,
            total_pnl=total_pnl,
            total_pnl_pct=_to_optional_float(total_pnl_pct) * 100.0,
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
    def _normalize_strategy_type(meta: dict, cfg: dict) -> Optional[StrategyType]:
        try:
            from valuecell.server.api.schemas.strategy import StrategyType as ST
        except Exception:
            return None

        val = meta.get("strategy_type")
        if not val:
            val = (cfg.get("trading_config", {}) or {}).get("strategy_type")
        if val is None:
            agent_name = str(meta.get("agent_name") or "").lower()
            if "prompt" in agent_name:
                return ST.PROMPT
            if "grid" in agent_name:
                return ST.GRID
            return None

        raw = str(val).strip().lower()
        if raw.startswith("strategytype."):
            raw = raw.split(".", 1)[1]
        raw_compact = "".join(ch for ch in raw if ch.isalnum())

        if raw in ("prompt based strategy", "grid strategy"):
            return ST.PROMPT if raw.startswith("prompt") else ST.GRID
        if raw_compact in ("promptbasedstrategy", "gridstrategy"):
            return ST.PROMPT if raw_compact.startswith("prompt") else ST.GRID
        if raw in ("prompt", "grid"):
            return ST.PROMPT if raw == "prompt" else ST.GRID

        agent_name = str(meta.get("agent_name") or "").lower()
        if "prompt" in agent_name:
            return ST.PROMPT
        if "grid" in agent_name:
            return ST.GRID
        return None

    @staticmethod
    async def get_strategy_performance(
        strategy_id: str,
    ) -> Optional[StrategyPerformanceData]:
        repo = get_strategy_repository()
        strategy = repo.get_strategy_by_strategy_id(strategy_id)
        if not strategy:
            return None

        snapshot = repo.get_latest_portfolio_snapshot(strategy_id)
        # Reference timestamp no longer included in performance response

        # Extract flattened config fields from original config/meta
        cfg = strategy.config or {}
        meta = strategy.strategy_metadata or {}

        llm = cfg.get("llm_model_config") or {}
        ex = cfg.get("exchange_config") or {}
        tr = cfg.get("trading_config") or {}

        llm_provider = (
            llm.get("provider") or meta.get("provider") or meta.get("llm_provider")
        )
        llm_model_id = (
            llm.get("model_id") or meta.get("model_id") or meta.get("llm_model_id")
        )
        exchange_id = ex.get("exchange_id") or meta.get("exchange_id")
        strategy_type = StrategyService._normalize_strategy_type(meta, cfg)
        # Determine initial capital source: in LIVE mode, prefer metadata (initial_capital_live),
        # falling back to first snapshot cash only when metadata is missing; non-LIVE uses config.
        trading_mode_raw = str(ex.get("trading_mode") or "").strip().lower()
        if trading_mode_raw.startswith("tradingmode."):
            trading_mode_raw = trading_mode_raw.split(".", 1)[1]
        is_live_mode = trading_mode_raw == "live"

        if is_live_mode:
            # Fast path: read from metadata set on first LIVE snapshot
            initial_capital = _to_optional_float(meta.get("initial_capital_live"))
            if initial_capital is None:
                # Rare path: metadata missing (older strategies); query first snapshot once
                try:
                    first_snapshot = repo.get_first_portfolio_snapshot(strategy_id)
                    initial_capital = (
                        _to_optional_float(getattr(first_snapshot, "cash", None))
                        if first_snapshot
                        else None
                    )
                except Exception:
                    initial_capital = None
        else:
            initial_capital = _to_optional_float(tr.get("initial_capital"))
        max_leverage = _to_optional_float(tr.get("max_leverage"))
        symbols = tr.get("symbols") if tr.get("symbols") is not None else None
        # Resolve final prompt strictly via template_id from strategy_prompts (no fallback)
        template_id = (
            tr.get("template_id") if tr.get("template_id") is not None else None
        )
        final_prompt: Optional[str] = None
        if template_id:
            try:
                prompt_item = repo.get_prompt_by_id(template_id)
                if prompt_item and getattr(prompt_item, "content", None):
                    final_prompt = prompt_item.content
            except Exception:
                # Strict mode: do not fallback; leave final_prompt as None
                final_prompt = None

        total_value = (
            _to_optional_float(getattr(snapshot, "total_value", None))
            if snapshot
            else None
        )

        return_rate_pct: Optional[float] = None
        try:
            if initial_capital and initial_capital > 0 and total_value is not None:
                return_rate_pct = (
                    (total_value - initial_capital) / initial_capital
                ) * 100.0
        except Exception:
            return_rate_pct = None

        return StrategyPerformanceData(
            strategy_id=strategy_id,
            initial_capital=initial_capital,
            return_rate_pct=return_rate_pct,
            llm_provider=llm_provider,
            llm_model_id=llm_model_id,
            exchange_id=exchange_id,
            strategy_type=strategy_type,
            max_leverage=max_leverage,
            symbols=symbols,
            prompt=final_prompt,
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
