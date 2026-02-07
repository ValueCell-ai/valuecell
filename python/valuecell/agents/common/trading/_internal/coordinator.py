from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from loguru import logger

from valuecell.utils.ts import get_current_timestamp_ms
from valuecell.utils.uuid import generate_uuid

from ..decision import BaseComposer
from ..execution import BaseExecutionGateway
from ..features.interfaces import BaseFeaturesPipeline
from ..history import (
    BaseDigestBuilder,
    BaseHistoryRecorder,
)
from ..models import (
    ComposeContext,
    DecisionCycleResult,
    FeatureVector,
    HistoryRecord,
    MarketType,
    PriceMode,
    StrategyStatus,
    StrategySummary,
    TradeDecisionAction,
    TradeHistoryEntry,
    TradeInstruction,
    TradeSide,
    TradeType,
    TradingMode,
    TxResult,
    TxStatus,
    UserRequest,
)
from ..portfolio.interfaces import BasePortfolioService
from ..utils import (
    extract_market_snapshot_features,
    fetch_free_cash_from_gateway,
    standardize_symbol_key,
    sync_positions_from_gateway,
    fetch_positions_from_gateway,
)

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

    @abstractmethod
    async def close_all_positions(self) -> None:
        """Close all open positions for this strategy."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Release any held resources."""
        raise NotImplementedError


class DefaultDecisionCoordinator(DecisionCoordinator):
    """Default implementation that wires the full decision pipeline."""

    def __init__(
        self,
        *,
        request: UserRequest,
        strategy_id: str,
        portfolio_service: BasePortfolioService,
        features_pipeline: BaseFeaturesPipeline,
        composer: BaseComposer,
        execution_gateway: BaseExecutionGateway,
        history_recorder: BaseHistoryRecorder,
        digest_builder: BaseDigestBuilder,
    ) -> None:
        self._request = request
        self.strategy_id = strategy_id
        self.portfolio_service = portfolio_service
        self._features_pipeline = features_pipeline
        self._composer = composer
        self._execution_gateway = execution_gateway
        self._history_recorder = history_recorder
        self._digest_builder = digest_builder
        self._symbols = list(dict.fromkeys(request.trading_config.symbols))
        self._realized_pnl: float = 0.0
        self._unrealized_pnl: float = 0.0
        self.cycle_index: int = 0
        self._strategy_name = request.trading_config.strategy_name or strategy_id

    async def run_once(self) -> DecisionCycleResult:
        timestamp_ms = get_current_timestamp_ms()
        compose_id = generate_uuid("compose")

        portfolio = self.portfolio_service.get_view()
        # LIVE mode: sync cash and positions from exchange
        try:
            if self._request.exchange_config.trading_mode == TradingMode.LIVE:
                # 1. Sync balance
                free_cash, total_cash = await fetch_free_cash_from_gateway(
                    self._execution_gateway, self._symbols
                )
                portfolio.account_balance = float(free_cash)
                if self._request.exchange_config.market_type == MarketType.SPOT:
                    # Spot: Account Balance is Cash (Free). Buying Power is Cash.
                    portfolio.account_balance = float(free_cash)
                    portfolio.buying_power = max(0.0, float(portfolio.account_balance))
                else:
                    # Derivatives: Account Balance should be Wallet Balance or Equity.
                    # We use total_cash (Equity) as the best approximation for account_balance
                    # to ensure InMemoryPortfolioService calculates Equity correctly (Equity + Unrealized).
                    # Note: If total_cash IS Equity, adding Unrealized PnL again in InMemoryService
                    # (Equity = Balance + Unreal) would double count PnL.
                    # However, separating Wallet Balance from Equity is exchange-specific.
                    # For now, we set account_balance = total_cash and rely on the fixed
                    # InMemoryPortfolioService to handle it (assuming Balance ~= Equity for initial sync).
                    portfolio.account_balance = float(total_cash)
                    # Buying Power is explicit Free Margin
                    portfolio.buying_power = float(free_cash)
                    # Also update free_cash field in view if it exists
                    portfolio.free_cash = float(free_cash)

                # 2. Sync positions from exchange (for derivatives only)
                if self._request.exchange_config.market_type != MarketType.SPOT:
                    exchange_positions = await sync_positions_from_gateway(
                        self._execution_gateway, self._symbols
                    )
                    
                    # CRITICAL: Exchange data is source of truth!
                    # Strategy: 
                    # 1. Update/create positions that exist on exchange
                    # 2. Clear positions that don't exist on exchange (set qty=0)
                    
                    # ✅ FIX: Build set of standardized symbols (not raw exchange symbols)
                    exchange_symbols = set()
                    
                    # Step 1: Update or create positions from exchange
                    for exchange_symbol, pos_data in exchange_positions.items():
                        # Standardize symbol to internal format (BASE/QUOTE)
                        # e.g., "SOL/USDT:USDT" -> "SOL/USDT", "SOL-USDT" -> "SOL/USDT"
                        symbol = standardize_symbol_key(exchange_symbol)
                        exchange_symbols.add(symbol)  # ✅ Collect standardized symbol
                        
                        contracts = pos_data.get("contracts", 0.0)
                        side = pos_data.get("side", "long")
                        # Convert contracts to signed quantity (positive for long, negative for short)
                        signed_qty = contracts if side == "long" else -contracts
                        entry_price = pos_data.get("entryPrice", 0.0)
                        mark_price = pos_data.get("markPrice", 0.0)
                        unrealized_pnl = pos_data.get("unrealizedPnl", 0.0)
                        leverage = pos_data.get("leverage", 1.0)
                        notional = pos_data.get("notional", 0.0)
                        
                        # Update existing or create new position
                        if symbol in portfolio.positions:
                            # Update existing position with exchange data
                            portfolio.positions[symbol].quantity = signed_qty
                            portfolio.positions[symbol].avg_price = entry_price
                            portfolio.positions[symbol].mark_price = mark_price
                            portfolio.positions[symbol].unrealized_pnl = unrealized_pnl
                            portfolio.positions[symbol].leverage = leverage
                            portfolio.positions[symbol].notional = notional
                            logger.debug(
                                f"📝 Updated position {symbol} from exchange: qty={signed_qty}, "
                                f"lev={leverage:.1f}, pnl={unrealized_pnl:.2f}"
                            )
                        else:
                            # Create new position from exchange data
                            # This can happen if position was opened outside this strategy
                            # or if local cache is stale
                            from valuecell.agents.common.trading.models import PositionSnapshot, InstrumentRef
                            portfolio.positions[symbol] = PositionSnapshot(
                                instrument=InstrumentRef(
                                    symbol=symbol,
                                    exchange_id=self._request.exchange_config.exchange_id,
                                ),
                                quantity=signed_qty,
                                avg_price=entry_price,
                                mark_price=mark_price,
                                unrealized_pnl=unrealized_pnl,
                                leverage=leverage,
                                notional=notional,
                            )
                            logger.warning(f"➕ Created missing position {symbol} from exchange: qty={signed_qty}")
                    
                    # Step 2: Clear positions that don't exist on exchange anymore
                    for symbol in list(portfolio.positions.keys()):
                        if symbol not in exchange_symbols:
                            # Position exists locally but not on exchange - mark as closed
                            old_qty = portfolio.positions[symbol].quantity
                            if old_qty != 0:
                                logger.warning(
                                    f"🧹 Clearing stale position {symbol}: local_qty={old_qty} but not on exchange"
                                )
                                portfolio.positions[symbol].quantity = 0.0
                                portfolio.positions[symbol].unrealized_pnl = 0.0
                                portfolio.positions[symbol].mark_price = 0.0


                    # Update portfolio totals after syncing positions
                    total_unrealized_pnl = sum(
                        pos.unrealized_pnl or 0.0
                        for pos in portfolio.positions.values()
                        if pos.quantity != 0
                    )
                    portfolio.total_unrealized_pnl = total_unrealized_pnl
                    if total_cash > 0:
                        portfolio.total_value = total_cash + total_unrealized_pnl
        except Exception:
            # If syncing fails, continue with existing portfolio view
            logger.warning(
                "Failed to sync balance/positions from exchange in LIVE mode, using cached portfolio view",
                exc_info=True,
            )
        # VIRTUAL mode: cash-only for spot; derivatives keep margin-based buying power
        if self._request.exchange_config.trading_mode == TradingMode.VIRTUAL:
            if self._request.exchange_config.market_type == MarketType.SPOT:
                portfolio.buying_power = max(0.0, float(portfolio.account_balance))

        pipeline_result = await self._features_pipeline.build()
        features = list(pipeline_result.features or [])
        market_features = extract_market_snapshot_features(features)
        digest = self._digest_builder.build(self._history_recorder.get_records())

        context = ComposeContext(
            ts=timestamp_ms,
            compose_id=compose_id,
            strategy_id=self.strategy_id,
            features=features,
            portfolio=portfolio,
            digest=digest,
        )

        compose_result = await self._composer.compose(context)
        instructions = compose_result.instructions
        rationale = compose_result.rationale
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
        tx_results = await self.execute_instructions(
            instructions, market_features=market_features
        )
        logger.info(f"✅ ExecutionGateway returned {len(tx_results)} results")

        # Filter out failed instructions and append reasons to rationale
        failed_ids = set()
        failure_msgs = []
        for idx, tx in enumerate(tx_results):
            logger.info(
                f"  📊 TxResult {idx}: {tx.instrument.symbol} status={tx.status.value} filled_qty={tx.filled_qty}"
            )
            if tx.status in (TxStatus.REJECTED, TxStatus.ERROR):
                failed_ids.add(tx.instruction_id)
                reason = tx.reason or "Unknown error"
                # Format failure message with clear details
                msg = f"❌ Skipped {tx.instrument.symbol} {tx.side.value} qty={tx.requested_qty}: {reason}"
                failure_msgs.append(msg)
                logger.warning(f"  ⚠️ Order rejected: {msg}")

        if failure_msgs:
            # Append failure reasons to AI rationale for frontend display
            prefix = "\n\n**Execution Warnings:**\n"
            rationale = (
                (rationale or "")
                + prefix
                + "\n".join(f"- {msg}" for msg in failure_msgs)
            )

        if failed_ids:
            # Remove failed instructions so they don't appear in history/UI
            instructions = [
                inst for inst in instructions if inst.instruction_id not in failed_ids
            ]

        trades = self._create_trades(tx_results, compose_id, timestamp_ms)
        self.portfolio_service.apply_trades(trades, market_features)
        summary = self.build_summary(timestamp_ms, trades)

        history_records = self._create_history_records(
            timestamp_ms, compose_id, features, instructions, trades, summary
        )

        for record in history_records:
            self._history_recorder.record(record)

        digest = self._digest_builder.build(self._history_recorder.get_records())
        self.cycle_index += 1

        portfolio = self.portfolio_service.get_view()
        
        # Debug logging for should_stop flag
        logger.info(
            f"🔍 Strategy {self.strategy_id} compose_result.should_stop={compose_result.should_stop}, summary.status={summary.status.value}"
        )
        
        if compose_result.should_stop:
            logger.warning(f"🛑 Strategy {self.strategy_id} requested STOP via composer")
            summary.status = StrategyStatus.STOPPED
            
            # Detect stop reason from rationale
            from valuecell.agents.common.trading.models import StopReason
            stop_reason = StopReason.NORMAL_EXIT  # Default
            stop_reason_detail = None
            
            rationale = compose_result.rationale or ""
            if "Stop Loss triggered" in rationale or "STOP LOSS" in rationale:
                stop_reason = StopReason.STOP_LOSS
                stop_reason_detail = "Stop loss threshold exceeded"
                logger.warning(f"🛑 Detected STOP_LOSS from rationale: {rationale[:200]}")
            
            # Record stop reason in summary metadata (will be persisted by caller)
            if not hasattr(summary, 'metadata'):
                summary.metadata = {}
            summary.metadata = summary.metadata or {}
            summary.metadata["stop_reason"] = stop_reason.value
            if stop_reason_detail:
                summary.metadata["stop_reason_detail"] = stop_reason_detail

        return DecisionCycleResult(
            compose_id=compose_id,
            timestamp_ms=timestamp_ms,
            cycle_index=self.cycle_index,
            rationale=rationale,
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
            pre_view = self.portfolio_service.get_view()
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
                    avg_exec_price=(
                        float(tx.avg_exec_price)
                        if tx.avg_exec_price is not None
                        else (exit_px or None)
                    ),
                    exit_price=exit_px,
                    notional_entry=notional_entry,
                    notional_exit=notional_exit,
                    entry_ts=entry_ts_prev or timestamp_ms,
                    exit_ts=exit_ts,
                    trade_ts=timestamp_ms,
                    holding_ms=(exit_ts - entry_ts_prev) if entry_ts_prev else None,
                    unrealized_pnl=0.0,
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
                    avg_exec_price=(
                        float(tx.avg_exec_price)
                        if tx.avg_exec_price is not None
                        else (price or None)
                    ),
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
                for record in reversed(self._history_recorder.get_records()):
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

    def build_summary(
        self,
        timestamp_ms: int,
        trades: List[TradeHistoryEntry],
    ) -> StrategySummary:
        realized_delta = sum(trade.realized_pnl or 0.0 for trade in trades)
        self._realized_pnl += realized_delta
        # Prefer authoritative unrealized PnL from the portfolio view when available.
        try:
            view = self.portfolio_service.get_view()
            unrealized = float(view.total_unrealized_pnl or 0.0)
            # Use the portfolio view's total_value which now correctly reflects Equity
            # (whether simulated or synced from exchange)
            equity = float(view.total_value or 0.0)
        except Exception:
            # Fallback to internal tracking if portfolio service is unavailable
            unrealized = float(self._unrealized_pnl or 0.0)
            # Fallback equity uses initial capital when view is unavailable
            equity = float(
                (self._request.trading_config.initial_capital + unrealized)
                if self._request.trading_config.initial_capital is not None
                else 0.0
            )

        # Keep internal state in sync (allow negative unrealized PnL)
        self._unrealized_pnl = float(unrealized)

        initial_capital = self._request.trading_config.initial_capital or 0.0
        pnl_pct = (
            (self._realized_pnl + self._unrealized_pnl) / equity if equity else None
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
            total_value=equity,
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

    async def execute_instructions(
        self,
        instructions: List[TradeInstruction],
        *,
        market_features: Optional[List[FeatureVector]] = None,
    ) -> List[TxResult]:
        """Execute a list of instructions directly via the gateway."""
        if not instructions:
            return []
        return await self._execution_gateway.execute(
            instructions, market_features=market_features
        )

    async def close_all_positions(self) -> List[TradeHistoryEntry]:
        """Close all open positions for the strategy.

        Generates and executes market orders to close all existing positions found
        in the current portfolio view. Returns the list of executed trades.
        """
        try:
            logger.info("Closing all positions for strategy {}", self.strategy_id)

            # Get current positions
            portfolio = self.portfolio_service.get_view()

            if not portfolio.positions:
                logger.info(
                    "No open positions to close for strategy {}", self.strategy_id
                )
                return []

            instructions = []
            compose_id = generate_uuid("close_all")
            timestamp_ms = get_current_timestamp_ms()

            for symbol, pos in portfolio.positions.items():
                quantity = float(pos.quantity)
                if quantity == 0:
                    continue

                # Determine side and action
                side = TradeSide.SELL if quantity > 0 else TradeSide.BUY
                action = (
                    TradeDecisionAction.CLOSE_LONG
                    if quantity > 0
                    else TradeDecisionAction.CLOSE_SHORT
                )

                # Create instruction with reduceOnly flag for closing
                inst = TradeInstruction(
                    instruction_id=generate_uuid("inst"),
                    compose_id=compose_id,
                    instrument=pos.instrument,
                    action=action,
                    side=side,
                    quantity=abs(quantity),
                    price_mode=PriceMode.MARKET,
                    meta={
                        "rationale": "Strategy stopped: closing all positions",
                        "reduceOnly": True,
                    },
                )
                instructions.append(inst)

            if not instructions:
                return []

            logger.info("Executing {} close instructions", len(instructions))

            # Fetch market features for pricing if possible
            market_features: List[FeatureVector] = []
            if self._request.exchange_config.trading_mode == TradingMode.VIRTUAL:
                try:
                    pipeline_result = await self._features_pipeline.build()
                    market_features = extract_market_snapshot_features(
                        pipeline_result.features or []
                    )
                except Exception:
                    logger.exception(
                        "Failed to build market features for closing positions"
                    )

            # Execute instructions
            tx_results = await self.execute_instructions(
                instructions, market_features=market_features
            )

            # Create trades and apply to portfolio
            trades = self._create_trades(tx_results, compose_id, timestamp_ms)
            self.portfolio_service.apply_trades(trades, market_features=[])

            # Record to in-memory history
            for trade in trades:
                self._history_recorder.record(
                    HistoryRecord(
                        ts=timestamp_ms,
                        kind="execution",
                        reference_id=compose_id,
                        payload={"trades": [trade.model_dump(mode="json")]},
                    )
                )

            logger.info(
                "Successfully closed all positions, generated {} trades", len(trades)
            )
            return trades

        except Exception:
            logger.exception(
                "Failed to close all positions for strategy {}", self.strategy_id
            )
            return []

    def _sync_portfolio_positions_with_exchange(
        self, portfolio, exchange_positions: Dict[str, Dict]
    ) -> None:
        """Sync portfolio positions with real positions from exchange.

        This method reconciles the local portfolio state with the actual positions
        on the exchange to prevent drift caused by failed requests or manual operations.

        Args:
            portfolio: Current portfolio view (will be modified in place)
            exchange_positions: Dict of positions from exchange (symbol -> position_data)
        """
        from datetime import datetime, timezone

        from valuecell.agents.common.trading.models import (
            Instrument,
            PositionSnapshot,
            TradeType,
        )

        if not exchange_positions:
            logger.debug("📭 No exchange positions to sync")
            return

        # Build normalized symbol map for matching
        # Exchange may return symbols in different formats (e.g., BTC/USDT:USDT vs BTC-USDT)
        symbol_map = {}
        for sym in self._symbols:
            # Try multiple format variations
            normalized = sym.replace("-", "/")
            if ":" not in normalized:
                parts = normalized.split("/")
                if len(parts) == 2:
                    normalized = f"{parts[0]}/{parts[1]}:{parts[1]}"
            symbol_map[normalized] = sym

        synced_count = 0
        for exchange_symbol, pos_data in exchange_positions.items():
            # Find matching local symbol
            local_symbol = symbol_map.get(exchange_symbol) or exchange_symbol

            contracts = float(pos_data.get("contracts", 0.0))
            side = pos_data.get("side", "").lower()
            entry_price = float(pos_data.get("entryPrice", 0.0))
            mark_price = float(pos_data.get("markPrice", 0.0))
            leverage = float(pos_data.get("leverage", 1.0))
            unrealized_pnl = float(pos_data.get("unrealizedPnl", 0.0))

            # Determine quantity with sign (long=positive, short=negative)
            if side == "short":
                quantity = -abs(contracts)
                trade_type = TradeType.SHORT
            else:
                quantity = abs(contracts)
                trade_type = TradeType.LONG

            # Get or create position in portfolio
            position = portfolio.positions.get(local_symbol)
            if position is None:
                # Create new position from exchange data
                position = PositionSnapshot(
                    instrument=Instrument(symbol=local_symbol),
                    quantity=quantity,
                    avg_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=unrealized_pnl,
                    leverage=leverage,
                    trade_type=trade_type,
                )
                portfolio.positions[local_symbol] = position
                logger.info(
                    f"  ➕ Added missing position from exchange: {local_symbol} {trade_type.value} {abs(quantity)}"
                )
            else:
                # Update existing position with exchange data
                local_qty = float(position.quantity or 0.0)
                exchange_qty = quantity

                # Check for significant divergence (>1% difference)
                qty_diff = abs(local_qty - exchange_qty)
                qty_tolerance = max(abs(local_qty), abs(exchange_qty)) * 0.01
                if qty_diff > qty_tolerance:
                    logger.warning(
                        f"  ⚠️ Position quantity mismatch for {local_symbol}: "
                        f"local={local_qty:.4f}, exchange={exchange_qty:.4f}, diff={qty_diff:.4f}"
                    )

                # Always update with exchange data as source of truth
                position.quantity = exchange_qty
                position.avg_price = entry_price if entry_price > 0 else position.avg_price
                position.mark_price = mark_price if mark_price > 0 else position.mark_price
                position.unrealized_pnl = unrealized_pnl
                position.leverage = leverage if leverage > 0 else position.leverage
                position.trade_type = trade_type

                # Recalculate unrealized PnL percentage
                if entry_price > 0 and abs(exchange_qty) > 0:
                    notional = abs(exchange_qty) * entry_price
                    position.unrealized_pnl_pct = (unrealized_pnl / notional) * 100.0 if notional else None
                    position.pnl_pct = position.unrealized_pnl_pct  # Keep legacy field

            synced_count += 1

        # Check for positions in local portfolio that don't exist on exchange
        # (possibly closed manually or via other means)
        local_symbols = set(portfolio.positions.keys())
        exchange_symbols = set(symbol_map.get(sym, sym) for sym in exchange_positions.keys())

        orphaned_symbols = local_symbols - exchange_symbols
        for sym in orphaned_symbols:
            pos = portfolio.positions.get(sym)
            if pos and abs(float(pos.quantity or 0.0)) > 1e-6:
                logger.warning(
                    f"  ⚠️ Local position exists but not found on exchange: {sym} qty={pos.quantity:.4f} "
                    f"(may have been closed manually or outside this system)"
                )
                # Mark as closed rather than removing immediately
                pos.quantity = 0.0
                pos.unrealized_pnl = 0.0
                pos.unrealized_pnl_pct = None
                pos.closed_ts = int(datetime.now(timezone.utc).timestamp() * 1000)

        logger.info(f"✅ Synced {synced_count} positions with exchange")

    async def close(self) -> None:
        """Release resources for the execution gateway if it supports closing."""
        try:
            close_fn = getattr(self._execution_gateway, "close", None)
            if callable(close_fn):
                await close_fn()
        except Exception:
            # Avoid bubbling cleanup errors
            pass
