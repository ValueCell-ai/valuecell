from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List

from loguru import logger

from valuecell.utils.uuid import generate_uuid

from .data.interfaces import MarketDataSource
from .decision.interfaces import Composer
from .execution.interfaces import ExecutionGateway
from .features.interfaces import FeatureComputer
from .models import (
    ComposeContext,
    FeatureVector,
    HistoryRecord,
    MarketType,
    PortfolioView,
    StrategyStatus,
    StrategySummary,
    TradeDigest,
    TradeHistoryEntry,
    TradeInstruction,
    TradeSide,
    TradeType,
    TradingMode,
    TxResult,
    TxStatus,
    UserRequest,
)
from .portfolio.interfaces import PortfolioService
from .trading_history.interfaces import DigestBuilder, HistoryRecorder


@dataclass
class DecisionCycleResult:
    """Outcome of a single decision cycle."""

    compose_id: str
    timestamp_ms: int
    strategy_summary: StrategySummary
    instructions: List[TradeInstruction]
    trades: List[TradeHistoryEntry]
    history_records: List[HistoryRecord]
    digest: TradeDigest
    portfolio_view: PortfolioView


# Core interfaces for orchestration and portfolio service.
# Plain ABCs to avoid runtime dependencies on pydantic. Concrete implementations
# wire the pipeline: data -> features -> composer -> execution -> history/digest.


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
    async def run_once(self) -> DecisionCycleResult:
        """Execute one decision cycle and return the result."""
        raise NotImplementedError


def _default_clock() -> datetime:
    """Return current time in UTC."""

    return datetime.now(timezone.utc)


def _build_market_snapshot(features: List[FeatureVector]) -> Dict[str, float]:
    """Derive latest market snapshot from feature vectors."""

    snapshot: Dict[str, float] = {}
    for vector in features:
        price = vector.values.get("close")
        if price is not None:
            snapshot[vector.instrument.symbol] = float(price)
    return snapshot


class DefaultDecisionCoordinator(DecisionCoordinator):
    """Default implementation that wires the full decision pipeline."""

    def __init__(
        self,
        *,
        request: UserRequest,
        strategy_id: str,
        portfolio_service: PortfolioService,
        market_data_source: MarketDataSource,
        feature_computer: FeatureComputer,
        composer: Composer,
        execution_gateway: ExecutionGateway,
        history_recorder: HistoryRecorder,
        digest_builder: DigestBuilder,
        prompt_provider: Callable[[UserRequest], str],
        history_limit: int = 200,
    ) -> None:
        self._request = request
        self.strategy_id = strategy_id
        self._portfolio_service = portfolio_service
        self._market_data_source = market_data_source
        self._feature_computer = feature_computer
        self._composer = composer
        self._execution_gateway = execution_gateway
        self._history_recorder = history_recorder
        self._digest_builder = digest_builder
        self._history_limit = max(history_limit, 1)
        self._symbols = list(dict.fromkeys(request.trading_config.symbols))
        # prompt_provider is a required parameter (caller must supply a prompt builder)
        self._prompt_provider = prompt_provider
        # Use the default clock internally; clock is not a constructor parameter
        self._clock = _default_clock
        self._history_records: List[HistoryRecord] = []
        self._realized_pnl: float = 0.0
        self._unrealized_pnl: float = 0.0
        self._cycle_index: int = 0
        self._strategy_name = request.trading_config.strategy_name or strategy_id

    async def run_once(self) -> DecisionCycleResult:
        timestamp_ms = int(self._clock().timestamp() * 1000)
        compose_id = generate_uuid("compose")

        portfolio = self._portfolio_service.get_view()
        # LIVE mode: sync cash from exchange free balance; set buying power to cash
        try:
            if (
                self._request.exchange_config.trading_mode == TradingMode.LIVE
                and hasattr(self._execution_gateway, "fetch_balance")
            ):
                balance = await self._execution_gateway.fetch_balance()
                free_map = {}
                free_section = (
                    balance.get("free") if isinstance(balance, dict) else None
                )
                if isinstance(free_section, dict):
                    free_map = {
                        str(k).upper(): float(v or 0.0) for k, v in free_section.items()
                    }
                else:
                    # Handle nested per-currency dict shapes
                    iterable = balance.items() if isinstance(balance, dict) else []
                    for k, v in iterable:
                        if isinstance(v, dict) and "free" in v:
                            try:
                                free_map[str(k).upper()] = float(v.get("free") or 0.0)
                            except Exception:
                                continue
                # Derive quote currencies from symbols, fallback to common USD-stable quotes
                quotes = []
                for sym in self._symbols or []:
                    s = str(sym).upper()
                    if "/" in s and len(s.split("/")) == 2:
                        quotes.append(s.split("/")[1])
                    elif "-" in s and len(s.split("-")) == 2:
                        quotes.append(s.split("-")[1])
                # Deduplicate preserving order
                quotes = list(dict.fromkeys(quotes))
                free_cash = 0.0
                if quotes:
                    for q in quotes:
                        free_cash += float(free_map.get(q, 0.0) or 0.0)
                else:
                    for q in ("USDT", "USD", "USDC"):
                        free_cash += float(free_map.get(q, 0.0) or 0.0)
                portfolio.cash = float(free_cash)
                if self._request.exchange_config.market_type == MarketType.SPOT:
                    portfolio.buying_power = max(0.0, float(portfolio.cash))
        except Exception:
            # If syncing fails, continue with existing portfolio view
            pass
        # VIRTUAL mode: cash-only for spot; derivatives keep margin-based buying power
        if self._request.exchange_config.trading_mode == TradingMode.VIRTUAL:
            if self._request.exchange_config.market_type == MarketType.SPOT:
                portfolio.buying_power = max(0.0, float(portfolio.cash))

        # Use fixed 1-second interval and lookback of 3 minutes (60 * 3 seconds)
        candles = await self._market_data_source.get_recent_candles(
            self._symbols, "1s", 60 * 3
        )
        features = self._feature_computer.compute_features(candles=candles)
        market_snapshot = _build_market_snapshot(features)
        # Use fixed 1-minute interval and lookback of 4 hours (60 * 4 minutes)
        candles = await self._market_data_source.get_recent_candles(
            self._symbols, "1m", 60 * 4
        )
        features.extend(self._feature_computer.compute_features(candles=candles))

        digest = self._digest_builder.build(list(self._history_records))

        context = ComposeContext(
            ts=timestamp_ms,
            compose_id=compose_id,
            strategy_id=self.strategy_id,
            features=features,
            portfolio=portfolio,
            digest=digest,
            prompt_text=self._prompt_provider(self._request),
            market_snapshot=market_snapshot,
        )

        instructions = await self._composer.compose(context)
        logger.info(f"🔍 Composer returned {len(instructions)} instructions")
        for idx, inst in enumerate(instructions):
            logger.info(
                f"  📝 Instruction {idx}: {inst.instrument.symbol} {inst.side.value} qty={inst.quantity}"
            )

        # Execute instructions via async gateway to obtain execution results
        logger.info(
            f"🚀 Calling execution_gateway.execute() with {len(instructions)} instructions"
        )
        logger.info(
            f"  ExecutionGateway type: {type(self._execution_gateway).__name__}"
        )
        tx_results = await self._execution_gateway.execute(
            instructions, market_snapshot
        )
        logger.info(f"✅ ExecutionGateway returned {len(tx_results)} results")
        for idx, tx in enumerate(tx_results):
            logger.info(
                f"  📊 TxResult {idx}: {tx.instrument.symbol} status={tx.status.value} filled_qty={tx.filled_qty}"
            )

        trades = self._create_trades(tx_results, compose_id, timestamp_ms)
        self._portfolio_service.apply_trades(trades, market_snapshot)
        summary = self._build_summary(timestamp_ms, trades)

        history_records = self._create_history_records(
            timestamp_ms, compose_id, features, instructions, trades, summary
        )

        for record in history_records:
            self._history_recorder.record(record)

        self._history_records.extend(history_records)
        if len(self._history_records) > self._history_limit:
            self._history_records = self._history_records[-self._history_limit :]

        digest = self._digest_builder.build(list(self._history_records))
        self._cycle_index += 1

        portfolio = self._portfolio_service.get_view()
        return DecisionCycleResult(
            compose_id=compose_id,
            timestamp_ms=timestamp_ms,
            strategy_summary=summary,
            instructions=instructions,
            trades=trades,
            history_records=history_records,
            digest=digest,
            portfolio_view=portfolio,
        )

    def _create_trades(
        self,
        tx_results: List[TxResult],
        compose_id: str,
        timestamp_ms: int,
    ) -> List[TradeHistoryEntry]:
        trades: List[TradeHistoryEntry] = []
        # Current portfolio view (pre-apply) used to detect closes
        try:
            pre_view = self._portfolio_service.get_view()
        except Exception:
            pre_view = None

        for tx in tx_results:
            # Skip failed or rejected trades - only create history entries for successful fills
            # (including partial fills which may still have filled_qty > 0)
            if tx.status in (TxStatus.ERROR, TxStatus.REJECTED):
                continue

            qty = float(tx.filled_qty or 0.0)
            # Skip trades with zero filled quantity
            if qty == 0:
                continue

            price = float(tx.avg_exec_price or 0.0)
            notional = (price * qty) if price and qty else None
            # Immediate realized effect: fees are costs (negative PnL). Slippage already baked into exec price.
            fee = float(tx.fee_cost or 0.0)
            realized_pnl = -fee if notional else None

            # Determine if this trade fully closes an existing position for this symbol
            prev_pos = None
            prev_qty = 0.0
            try:
                if pre_view is not None:
                    prev_pos = pre_view.positions.get(tx.instrument.symbol)
                    prev_qty = float(prev_pos.quantity) if prev_pos is not None else 0.0
            except Exception:
                prev_pos = None
                prev_qty = 0.0

            eps = 1e-12
            is_full_close = False
            close_units = 0.0
            pos_dir_type: TradeType | None = None
            if prev_pos is not None:
                if prev_qty > 0 and tx.side == TradeSide.SELL:
                    close_units = min(qty, abs(prev_qty))
                    is_full_close = close_units >= abs(prev_qty) - eps
                    pos_dir_type = TradeType.LONG
                elif prev_qty < 0 and tx.side == TradeSide.BUY:
                    close_units = min(qty, abs(prev_qty))
                    is_full_close = close_units >= abs(prev_qty) - eps
                    pos_dir_type = TradeType.SHORT

            if (
                is_full_close
                and prev_pos is not None
                and prev_pos.avg_price is not None
            ):
                # Build a completed trade that ties back to the original open (avg_price/entry_ts)
                entry_px = float(prev_pos.avg_price or 0.0)
                entry_ts_prev = int(prev_pos.entry_ts) if prev_pos.entry_ts else None
                exit_px = price or None
                exit_ts = timestamp_ms
                qty_closed = float(close_units or 0.0)
                # Realized PnL on close (exclude prior fees; subtract this tx fee)
                core_pnl = None
                if entry_px and exit_px and qty_closed:
                    if pos_dir_type == TradeType.LONG:
                        core_pnl = (float(exit_px) - float(entry_px)) * qty_closed
                    else:  # SHORT
                        core_pnl = (float(entry_px) - float(exit_px)) * qty_closed
                realized_pnl = core_pnl if core_pnl is not None else None
                if realized_pnl is not None:
                    realized_pnl = float(realized_pnl) - fee
                notional_entry = (
                    (qty_closed * entry_px) if entry_px and qty_closed else None
                )
                notional_exit = (
                    (qty_closed * float(exit_px)) if exit_px and qty_closed else None
                )
                realized_pnl_pct = (
                    (realized_pnl / notional_entry)
                    if realized_pnl is not None and notional_entry
                    else None
                )

                trade = TradeHistoryEntry(
                    trade_id=generate_uuid("trade"),
                    compose_id=compose_id,
                    instruction_id=tx.instruction_id,
                    strategy_id=self.strategy_id,
                    instrument=tx.instrument,
                    side=tx.side,
                    type=pos_dir_type
                    or (
                        TradeType.LONG if tx.side == TradeSide.BUY else TradeType.SHORT
                    ),
                    quantity=qty_closed or qty,
                    entry_price=entry_px or None,
                    exit_price=exit_px,
                    notional_entry=notional_entry,
                    notional_exit=notional_exit,
                    entry_ts=entry_ts_prev or timestamp_ms,
                    exit_ts=exit_ts,
                    trade_ts=timestamp_ms,
                    holding_ms=(exit_ts - entry_ts_prev) if entry_ts_prev else None,
                    realized_pnl=realized_pnl,
                    realized_pnl_pct=realized_pnl_pct,
                    # For a full close, reflect the leverage of the closed position, not the closing instruction
                    leverage=(
                        float(prev_pos.leverage)
                        if getattr(prev_pos, "leverage", None) is not None
                        else tx.leverage
                    ),
                    fee_cost=fee or None,
                    note=(tx.meta.get("rationale") if tx.meta else None),
                )
            else:
                # Default behavior for opens/increases/reductions that are not full closes
                trade = TradeHistoryEntry(
                    trade_id=generate_uuid("trade"),
                    compose_id=compose_id,
                    instruction_id=tx.instruction_id,
                    strategy_id=self.strategy_id,
                    instrument=tx.instrument,
                    side=tx.side,
                    type=(
                        TradeType.LONG if tx.side == TradeSide.BUY else TradeType.SHORT
                    ),
                    quantity=qty,
                    entry_price=price or None,
                    exit_price=None,
                    notional_entry=notional or None,
                    notional_exit=None,
                    entry_ts=timestamp_ms,
                    exit_ts=None,
                    trade_ts=timestamp_ms,
                    holding_ms=None,
                    realized_pnl=realized_pnl,
                    realized_pnl_pct=(
                        ((realized_pnl or 0.0) / notional) if notional else None
                    ),
                    leverage=tx.leverage,
                    fee_cost=fee or None,
                    note=(tx.meta.get("rationale") if tx.meta else None),
                )

            # If reducing/closing but not a full close, try to annotate the most recent open trade
            is_closing = prev_pos is not None and (
                (prev_qty > 0 and tx.side == TradeSide.SELL)
                or (prev_qty < 0 and tx.side == TradeSide.BUY)
            )
            if is_closing and not is_full_close:
                # scan history records (most recent first) to find an open trade for this symbol
                paired_id = None
                for record in reversed(self._history_records):
                    if record.kind != "execution":
                        continue
                    trades_payload = record.payload.get("trades", []) or []
                    # iterate trades in reverse to find latest
                    for t in reversed(trades_payload):
                        try:
                            inst = t.get("instrument") or {}
                            if inst.get("symbol") != tx.instrument.symbol:
                                continue
                            # consider open if no exit_ts or exit_price present
                            if not t.get("exit_ts") and not t.get("exit_price"):
                                # annotate this historic trade dict with exit fields
                                t["exit_price"] = float(price) if price else None
                                t["exit_ts"] = timestamp_ms
                                entry_ts_prev = t.get("entry_ts") or t.get("trade_ts")
                                if entry_ts_prev:
                                    try:
                                        t["holding_ms"] = int(
                                            timestamp_ms - int(entry_ts_prev)
                                        )
                                    except Exception:
                                        t["holding_ms"] = None
                                t["notional_exit"] = (
                                    float(price * qty) if price and qty else None
                                )
                                paired_id = t.get("trade_id")
                                break
                        except Exception:
                            continue
                    if paired_id:
                        break

                # if we found a paired trade, record the pairing in the new trade's note
                if paired_id:
                    # preserve LLM rationale (if any) and append pairing info
                    existing = trade.note or ""
                    suffix = f"paired_exit_of:{paired_id}"
                    trade.note = f"{existing} {suffix}".strip()

            trades.append(trade)
        return trades

    def _build_summary(
        self,
        timestamp_ms: int,
        trades: List[TradeHistoryEntry],
    ) -> StrategySummary:
        realized_delta = sum(trade.realized_pnl or 0.0 for trade in trades)
        self._realized_pnl += realized_delta
        # Prefer authoritative unrealized PnL from the portfolio view when available.
        try:
            view = self._portfolio_service.get_view()
            unrealized = float(view.total_unrealized_pnl or 0.0)
            # In LIVE mode, treat equity as available cash (disallow financing)
            try:
                mode = getattr(self._request.exchange_config, "trading_mode", None)
            except Exception:
                mode = None
            if str(mode).upper() == "LIVE":
                equity = float(getattr(view, "cash", None) or 0.0)
            else:
                equity = float(view.total_value or 0.0)
        except Exception:
            # Fallback to internal tracking if portfolio service is unavailable
            unrealized = float(self._unrealized_pnl or 0.0)
            # Fallback equity uses initial capital when view is unavailable
            equity = float(self._request.trading_config.initial_capital or 0.0)

        # Keep internal state in sync (allow negative unrealized PnL)
        self._unrealized_pnl = float(unrealized)

        initial_capital = self._request.trading_config.initial_capital or 0.0
        pnl_pct = (
            (self._realized_pnl + self._unrealized_pnl) / initial_capital
            if initial_capital
            else None
        )

        # Strategy-level unrealized percent: percent of equity (if equity is available)
        unrealized_pnl_pct = (self._unrealized_pnl / equity * 100.0) if equity else None

        return StrategySummary(
            strategy_id=self.strategy_id,
            name=self._strategy_name,
            model_provider=self._request.llm_model_config.provider,
            model_id=self._request.llm_model_config.model_id,
            exchange_id=self._request.exchange_config.exchange_id,
            mode=self._request.exchange_config.trading_mode,
            status=StrategyStatus.RUNNING,
            realized_pnl=self._realized_pnl,
            unrealized_pnl=self._unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            pnl_pct=pnl_pct,
            last_updated_ts=timestamp_ms,
        )

    def _create_history_records(
        self,
        timestamp_ms: int,
        compose_id: str,
        features: List[FeatureVector],
        instructions: List[TradeInstruction],
        trades: List[TradeHistoryEntry],
        summary: StrategySummary,
    ) -> List[HistoryRecord]:
        feature_payload = [vector.model_dump(mode="json") for vector in features]
        instruction_payload = [inst.model_dump(mode="json") for inst in instructions]
        trade_payload = [trade.model_dump(mode="json") for trade in trades]

        return [
            HistoryRecord(
                ts=timestamp_ms,
                kind="features",
                reference_id=compose_id,
                payload={"features": feature_payload},
            ),
            HistoryRecord(
                ts=timestamp_ms,
                kind="compose",
                reference_id=compose_id,
                payload={
                    "prompt": self._prompt_provider(self._request),
                    "summary": summary.model_dump(mode="json"),
                },
            ),
            HistoryRecord(
                ts=timestamp_ms,
                kind="instructions",
                reference_id=compose_id,
                payload={"instructions": instruction_payload},
            ),
            HistoryRecord(
                ts=timestamp_ms,
                kind="execution",
                reference_id=compose_id,
                payload={"trades": trade_payload},
            ),
        ]
