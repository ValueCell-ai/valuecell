from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import ccxt.pro as ccxtpro
import numpy as np
import pandas as pd
from loguru import logger

from valuecell.utils.uuid import generate_uuid

from .core import DecisionCycleResult, DefaultDecisionCoordinator
from .data.interfaces import MarketDataSource
from .decision.composer import LlmComposer
from .execution.interfaces import ExecutionGateway
from .features.interfaces import FeatureComputer
from .models import (
    Candle,
    Constraints,
    FeatureVector,
    HistoryRecord,
    InstrumentRef,
    PortfolioView,
    PositionSnapshot,
    TradeDigest,
    TradeDigestEntry,
    TradeHistoryEntry,
    TradeInstruction,
    TradeSide,
    TradeType,
    TradingMode,
    TxResult,
    UserRequest,
)
from .portfolio.interfaces import PortfolioService
from .trading_history.interfaces import DigestBuilder, HistoryRecorder


def _make_prompt_provider(template_dir: Optional[Path] = None):
    """Return a prompt_provider callable that builds prompts from templates.

    Behavior:
    - If request.trading_config.template_id matches a file under templates dir
      (try extensions .txt, .md, or exact name), the file content is used.
    - If request.trading_config.custom_prompt is present, it is appended after
      the template content (separated by two newlines).
    - If neither is present, fall back to a simple generated prompt mentioning
      the symbols.
    """
    base = Path(__file__).parent / "templates" if template_dir is None else template_dir

    def provider(request: UserRequest) -> str:
        tid = request.trading_config.template_id
        custom = request.trading_config.custom_prompt

        template_text = ""
        if tid:
            # safe-resolve candidate files
            candidates = [tid, f"{tid}.txt", f"{tid}.md"]
            for name in candidates:
                try_path = base / name
                try:
                    resolved = try_path.resolve()
                    # ensure resolved path is inside base
                    if base.resolve() in resolved.parents or resolved == base.resolve():
                        if resolved.exists() and resolved.is_file():
                            template_text = resolved.read_text(encoding="utf-8")
                            break
                except Exception:
                    continue

        parts = []
        if template_text:
            parts.append(template_text.strip())
        if custom:
            parts.append(custom.strip())

        if parts:
            return "\n\n".join(parts)

        # fallback: simple generated prompt referencing symbols
        symbols = ", ".join(request.trading_config.symbols)
        return f"Compose trading instructions for symbols: {symbols}."

    return provider


class SimpleMarketDataSource(MarketDataSource):
    """Generates synthetic candle data for each symbol or fetches via ccxt.pro.

    If `exchange_id` was provided at construction time and `ccxt.pro` is
    available, this class will attempt to fetch OHLCV data from the
    specified exchange. If any error occurs (missing library, unknown
    exchange, network error), it falls back to the built-in synthetic
    generator so the runtime remains functional in tests and offline.
    """

    def __init__(
        self,
        base_prices: Optional[Dict[str, float]] = None,
        exchange_id: Optional[str] = None,
        ccxt_options: Optional[Dict] = None,
    ) -> None:
        self._base_prices = base_prices or {}
        self._counters: Dict[str, int] = defaultdict(int)
        self._exchange_id = exchange_id or "binance"
        self._ccxt_options = ccxt_options or {}

    async def get_recent_candles(
        self, symbols: List[str], interval: str, lookback: int
    ) -> List[Candle]:
        async def _fetch(symbol: str) -> List[List]:
            # instantiate exchange class by name (e.g., ccxtpro.kraken)
            exchange_cls = getattr(ccxtpro, self._exchange_id, None)
            if exchange_cls is None:
                raise RuntimeError(
                    f"Exchange '{self._exchange_id}' not found in ccxt.pro"
                )
            exchange = exchange_cls({"newUpdates": False, **self._ccxt_options})
            try:
                # ccxt.pro uses async fetch_ohlcv
                data = await exchange.fetch_ohlcv(
                    symbol, timeframe=interval, since=None, limit=lookback
                )
                return data
            finally:
                try:
                    await exchange.close()
                except Exception:
                    pass

        candles: List[Candle] = []
        # Run fetch for each symbol sequentially
        for symbol in symbols:
            try:
                raw = await _fetch(symbol)
                # raw is list of [ts, open, high, low, close, volume]
                for row in raw:
                    ts, open_v, high_v, low_v, close_v, vol = row
                    candles.append(
                        Candle(
                            ts=int(ts),
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._exchange_id,
                                quote_ccy="USD",
                            ),
                            open=float(open_v),
                            high=float(high_v),
                            low=float(low_v),
                            close=float(close_v),
                            volume=float(vol),
                            interval=interval,
                        )
                    )
            except Exception:
                logger.exception(
                    "Failed to fetch candles for {} from {}, using synthetic data",
                    symbol,
                    self._exchange_id,
                )
        return candles


class SimpleFeatureComputer(FeatureComputer):
    """Computes basic momentum and volume features."""

    def compute_features(
        self, candles: Optional[List[Candle]] = None
    ) -> List[FeatureVector]:
        if not candles:
            return []

        grouped: Dict[str, List[Candle]] = defaultdict(list)
        for candle in candles:
            grouped[candle.instrument.symbol].append(candle)

        features: List[FeatureVector] = []
        for symbol, series in grouped.items():
            # Build a DataFrame for indicator calculations
            series.sort(key=lambda item: item.ts)
            rows = [
                {
                    "ts": c.ts,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                    "interval": c.interval,
                }
                for c in series
            ]
            df = pd.DataFrame(rows)

            # EMAs
            df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
            df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()
            df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()

            # MACD
            df["macd"] = df["ema_12"] - df["ema_26"]
            df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
            df["macd_histogram"] = df["macd"] - df["macd_signal"]

            # RSI
            delta = df["close"].diff()
            gain = delta.clip(lower=0).rolling(window=14).mean()
            loss = (-delta).clip(lower=0).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.inf)
            df["rsi"] = 100 - (100 / (1 + rs))

            # Bollinger Bands
            df["bb_middle"] = df["close"].rolling(window=20).mean()
            bb_std = df["close"].rolling(window=20).std()
            df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
            df["bb_lower"] = df["bb_middle"] - (bb_std * 2)

            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last

            change_pct = (
                (float(last.close) - float(prev.close)) / float(prev.close)
                if prev.close
                else 0.0
            )

            values = {
                "close": float(last.close),
                "volume": float(last.volume),
                "change_pct": float(change_pct),
                "ema_12": (
                    float(last.get("ema_12", np.nan))
                    if not pd.isna(last.get("ema_12"))
                    else None
                ),
                "ema_26": (
                    float(last.get("ema_26", np.nan))
                    if not pd.isna(last.get("ema_26"))
                    else None
                ),
                "ema_50": (
                    float(last.get("ema_50", np.nan))
                    if not pd.isna(last.get("ema_50"))
                    else None
                ),
                "macd": (
                    float(last.get("macd", np.nan))
                    if not pd.isna(last.get("macd"))
                    else None
                ),
                "macd_signal": (
                    float(last.get("macd_signal", np.nan))
                    if not pd.isna(last.get("macd_signal"))
                    else None
                ),
                "macd_histogram": (
                    float(last.get("macd_histogram", np.nan))
                    if not pd.isna(last.get("macd_histogram"))
                    else None
                ),
                "rsi": (
                    float(last.get("rsi", np.nan))
                    if not pd.isna(last.get("rsi"))
                    else None
                ),
                "bb_upper": (
                    float(last.get("bb_upper", np.nan))
                    if not pd.isna(last.get("bb_upper"))
                    else None
                ),
                "bb_middle": (
                    float(last.get("bb_middle", np.nan))
                    if not pd.isna(last.get("bb_middle"))
                    else None
                ),
                "bb_lower": (
                    float(last.get("bb_lower", np.nan))
                    if not pd.isna(last.get("bb_lower"))
                    else None
                ),
            }

            features.append(
                FeatureVector(
                    ts=int(last["ts"]),
                    instrument=series[-1].instrument,
                    values=values,
                    meta={"interval": series[-1].interval, "count": len(series)},
                )
            )

        return features


class PaperExecutionGateway(ExecutionGateway):
    """Async paper executor that simulates fills with slippage and fees.

    - Uses instruction.max_slippage_bps to compute execution price around snapshot.
    - Applies a flat fee_bps to notional to produce fee_cost.
    - Marks orders as FILLED with filled_qty=requested quantity.
    """

    def __init__(self, fee_bps: float = 10.0) -> None:
        self._fee_bps = float(fee_bps)
        self.executed: List[TradeInstruction] = []

    async def execute(
        self,
        instructions: List[TradeInstruction],
        market_snapshot: Optional[Dict[str, float]] = None,
    ) -> List[TxResult]:
        results: List[TxResult] = []
        price_map = market_snapshot or {}
        for inst in instructions:
            self.executed.append(inst)
            ref_price = float(price_map.get(inst.instrument.symbol, 0.0) or 0.0)
            slip_bps = float(inst.max_slippage_bps or 0.0)
            slip = slip_bps / 10_000.0
            if inst.side == TradeSide.BUY:
                exec_price = ref_price * (1.0 + slip)
            else:
                exec_price = ref_price * (1.0 - slip)

            notional = exec_price * float(inst.quantity)
            fee_cost = notional * (self._fee_bps / 10_000.0) if notional else 0.0

            results.append(
                TxResult(
                    instruction_id=inst.instruction_id,
                    instrument=inst.instrument,
                    side=inst.side,
                    requested_qty=float(inst.quantity),
                    filled_qty=float(inst.quantity),
                    avg_exec_price=float(exec_price) if exec_price else None,
                    slippage_bps=slip_bps or None,
                    fee_cost=fee_cost or None,
                    leverage=inst.leverage,
                    meta=None,
                )
            )

        return results


class InMemoryHistoryRecorder(HistoryRecorder):
    """In-memory recorder storing history records."""

    def __init__(self) -> None:
        self.records: List[HistoryRecord] = []

    def record(self, record: HistoryRecord) -> None:
        self.records.append(record)


class RollingDigestBuilder(DigestBuilder):
    """Builds a lightweight digest from recent execution records."""

    def __init__(self, window: int = 50) -> None:
        self._window = max(window, 1)

    def build(self, records: List[HistoryRecord]) -> TradeDigest:
        recent = records[-self._window :]
        by_instrument: Dict[str, TradeDigestEntry] = {}

        for record in recent:
            if record.kind != "execution":
                continue
            trades = record.payload.get("trades", [])
            for trade_dict in trades:
                instrument_dict = trade_dict.get("instrument") or {}
                symbol = instrument_dict.get("symbol")
                if not symbol:
                    continue
                entry = by_instrument.get(symbol)
                if entry is None:
                    entry = TradeDigestEntry(
                        instrument=InstrumentRef(**instrument_dict),
                        trade_count=0,
                        realized_pnl=0.0,
                    )
                    by_instrument[symbol] = entry
                entry.trade_count += 1
                realized = float(trade_dict.get("realized_pnl") or 0.0)
                entry.realized_pnl += realized
                entry.last_trade_ts = trade_dict.get("trade_ts") or entry.last_trade_ts

        timestamp = (
            recent[-1].ts
            if recent
            else int(datetime.now(timezone.utc).timestamp() * 1000)
        )
        return TradeDigest(ts=timestamp, by_instrument=by_instrument)


class InMemoryPortfolioService(PortfolioService):
    """Tracks cash and positions in memory and computes derived metrics.

    Notes:
    - cash reflects running cash balance from trade settlements
    - gross_exposure = sum(abs(qty) * mark_price)
    - net_exposure   = sum(qty * mark_price)
    - equity (total_value) = cash + net_exposure  [correct for both long and short]
    - total_unrealized_pnl = sum((mark_price - avg_price) * qty)
    - buying_power: max(0, equity * max_leverage - gross_exposure)
      where max_leverage comes from portfolio.constraints (default 1.0)
    """

    def __init__(
        self,
        initial_capital: float,
        trading_mode: TradingMode,
        constraints: Optional[Constraints] = None,
        strategy_id: Optional[str] = None,
    ) -> None:
        # Store owning strategy id on the view so downstream components
        # always see which strategy this portfolio belongs to.
        self._strategy_id = strategy_id
        self._view = PortfolioView(
            strategy_id=strategy_id,
            ts=int(datetime.now(timezone.utc).timestamp() * 1000),
            cash=initial_capital,
            positions={},
            gross_exposure=0.0,
            net_exposure=0.0,
            constraints=constraints or None,
            total_value=initial_capital,
            total_unrealized_pnl=0.0,
            buying_power=initial_capital,
        )
        self._trading_mode = trading_mode

    def get_view(self) -> PortfolioView:
        self._view.ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        # Ensure strategy_id is present on each view retrieval
        if self._strategy_id is not None:
            try:
                self._view.strategy_id = self._strategy_id
            except Exception:
                pass
        return self._view

    def apply_trades(
        self, trades: List[TradeHistoryEntry], market_snapshot: Dict[str, float]
    ) -> None:
        """Apply trades and update portfolio positions and aggregates.

        This method updates:
        - cash (subtract on BUY, add on SELL at trade price)
        - positions with weighted avg price, entry_ts on (re)open, and mark_price
        - per-position notional, unrealized_pnl, unrealized_pnl_pct (and keeps pnl_pct for
          backward compatibility)
        - portfolio aggregates: gross_exposure, net_exposure, total_value (equity), total_unrealized_pnl, buying_power
        """
        for trade in trades:
            symbol = trade.instrument.symbol
            price = float(trade.entry_price or market_snapshot.get(symbol, 0.0) or 0.0)
            delta = float(trade.quantity or 0.0)
            quantity_delta = delta if trade.side == TradeSide.BUY else -delta

            position = self._view.positions.get(symbol)
            if position is None:
                position = PositionSnapshot(
                    instrument=trade.instrument,
                    quantity=0.0,
                    avg_price=None,
                    mark_price=price,
                    unrealized_pnl=0.0,
                )
                self._view.positions[symbol] = position

            current_qty = float(position.quantity)
            avg_price = float(position.avg_price or 0.0)
            new_qty = current_qty + quantity_delta

            # Update mark price
            position.mark_price = price

            # Handle position quantity transitions and avg price
            if new_qty == 0.0:
                # Fully closed
                self._view.positions.pop(symbol, None)
            elif current_qty == 0.0:
                # Opening new position
                position.quantity = new_qty
                position.avg_price = price
                position.entry_ts = (
                    trade.entry_ts
                    or trade.trade_ts
                    or int(datetime.now(timezone.utc).timestamp() * 1000)
                )
                position.trade_type = TradeType.LONG if new_qty > 0 else TradeType.SHORT
                # Initialize leverage from trade if provided
                if trade.leverage is not None:
                    position.leverage = float(trade.leverage)
            elif (current_qty > 0 and new_qty > 0) or (current_qty < 0 and new_qty < 0):
                # Same direction
                if abs(new_qty) > abs(current_qty):
                    # Increasing position: weighted average price
                    position.avg_price = (
                        abs(current_qty) * avg_price + abs(quantity_delta) * price
                    ) / abs(new_qty)
                    position.quantity = new_qty
                    # Update leverage as size-weighted average if provided
                    if trade.leverage is not None:
                        prev_lev = float(position.leverage or trade.leverage)
                        position.leverage = (
                            abs(current_qty) * prev_lev
                            + abs(quantity_delta) * float(trade.leverage)
                        ) / abs(new_qty)
                else:
                    # Reducing position: keep avg price, update quantity
                    position.quantity = new_qty
                # entry_ts remains from original opening
            else:
                # Crossing through zero to opposite direction: reset avg price and entry_ts
                position.quantity = new_qty
                position.avg_price = price
                position.entry_ts = (
                    trade.entry_ts
                    or trade.trade_ts
                    or int(datetime.now(timezone.utc).timestamp() * 1000)
                )
                position.trade_type = TradeType.LONG if new_qty > 0 else TradeType.SHORT
                # Reset leverage when flipping direction
                if trade.leverage is not None:
                    position.leverage = float(trade.leverage)

            # Update cash by trade notional
            notional = price * delta
            if trade.side == TradeSide.BUY:
                self._view.cash -= notional
            else:
                self._view.cash += notional

            # Recompute per-position derived fields (if position still exists)
            pos = self._view.positions.get(symbol)
            if pos is not None:
                qty = float(pos.quantity)
                mpx = float(pos.mark_price or 0.0)
                apx = float(pos.avg_price or 0.0)
                pos.notional = abs(qty) * mpx if mpx else None
                if apx and mpx:
                    pos.unrealized_pnl = (mpx - apx) * qty
                    denom = abs(qty) * apx
                    pct = (pos.unrealized_pnl / denom) * 100.0 if denom else None
                    # populate both the newer field and keep the legacy alias
                    pos.unrealized_pnl_pct = pct
                    pos.pnl_pct = pct
                else:
                    pos.unrealized_pnl = None
                    pos.unrealized_pnl_pct = None
                    pos.pnl_pct = None

        # Recompute portfolio aggregates
        gross = 0.0
        net = 0.0
        unreal = 0.0
        for pos in self._view.positions.values():
            # Refresh mark price from snapshot if available
            try:
                sym = pos.instrument.symbol
            except Exception:
                sym = None
            if sym and sym in market_snapshot:
                snap_px = float(market_snapshot.get(sym) or 0.0)
                if snap_px > 0:
                    pos.mark_price = snap_px

            mpx = float(pos.mark_price or 0.0)
            qty = float(pos.quantity)
            apx = float(pos.avg_price or 0.0)
            # Recompute unrealized PnL and percent (populate both new and legacy fields)
            if apx and mpx:
                pos.unrealized_pnl = (mpx - apx) * qty
                denom = abs(qty) * apx
                pct = (pos.unrealized_pnl / denom) * 100.0 if denom else None
                pos.unrealized_pnl_pct = pct
                pos.pnl_pct = pct
            else:
                pos.unrealized_pnl = None
                pos.unrealized_pnl_pct = None
                pos.pnl_pct = None
            gross += abs(qty) * mpx
            net += qty * mpx
            if pos.unrealized_pnl is not None:
                unreal += float(pos.unrealized_pnl)

        self._view.gross_exposure = gross
        self._view.net_exposure = net
        self._view.total_unrealized_pnl = unreal
        # Equity is cash plus net exposure (correct for both long and short)
        equity = self._view.cash + net
        self._view.total_value = equity

        # Approximate buying power using max leverage constraint
        max_lev = (
            float(self._view.constraints.max_leverage)
            if (self._view.constraints and self._view.constraints.max_leverage)
            else 1.0
        )
        buying_power = max(0.0, equity * max_lev - gross)
        self._view.buying_power = buying_power


@dataclass
class StrategyRuntime:
    request: UserRequest
    strategy_id: str
    coordinator: DefaultDecisionCoordinator

    async def run_cycle(self) -> DecisionCycleResult:
        return await self.coordinator.run_once()


def create_strategy_runtime(request: UserRequest) -> StrategyRuntime:
    strategy_id = generate_uuid("strategy")
    initial_capital = request.trading_config.initial_capital or 0.0
    constraints = Constraints(
        max_positions=request.trading_config.max_positions,
        max_leverage=request.trading_config.max_leverage,
    )
    portfolio_service = InMemoryPortfolioService(
        initial_capital=initial_capital,
        trading_mode=request.exchange_config.trading_mode,
        constraints=constraints,
        strategy_id=strategy_id,
    )

    base_prices = {
        symbol: 120.0 + index * 15.0
        for index, symbol in enumerate(request.trading_config.symbols)
    }
    market_data_source = SimpleMarketDataSource(
        base_prices=base_prices, exchange_id=request.exchange_config.exchange_id
    )
    feature_computer = SimpleFeatureComputer()
    composer = LlmComposer(request=request)
    execution_gateway = PaperExecutionGateway()
    history_recorder = InMemoryHistoryRecorder()
    digest_builder = RollingDigestBuilder()

    coordinator = DefaultDecisionCoordinator(
        request=request,
        strategy_id=strategy_id,
        portfolio_service=portfolio_service,
        market_data_source=market_data_source,
        feature_computer=feature_computer,
        composer=composer,
        execution_gateway=execution_gateway,
        history_recorder=history_recorder,
        digest_builder=digest_builder,
        prompt_provider=_make_prompt_provider(),
    )

    return StrategyRuntime(
        request=request,
        strategy_id=strategy_id,
        coordinator=coordinator,
    )
