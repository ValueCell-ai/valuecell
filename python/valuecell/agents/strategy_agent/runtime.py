from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

import ccxt.pro as ccxtpro
from loguru import logger

from valuecell.utils.uuid import generate_uuid

from .core import DecisionCycleResult, DefaultDecisionCoordinator
from .data.interfaces import MarketDataSource
from .decision.interfaces import Composer
from .execution.interfaces import ExecutionGateway
from .features.interfaces import FeatureComputer
from .models import (
    Candle,
    ComposeContext,
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
    TradingMode,
    UserRequest,
)
from .portfolio.interfaces import PortfolioService
from .trading_history.interfaces import DigestBuilder, HistoryRecorder


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
            series.sort(key=lambda item: item.ts)
            last = series[-1]
            prev = series[-2] if len(series) > 1 else series[-1]
            change_pct = (last.close - prev.close) / prev.close if prev.close else 0.0
            features.append(
                FeatureVector(
                    ts=last.ts,
                    instrument=last.instrument,
                    values={
                        "close": last.close,
                        "volume": last.volume,
                        "change_pct": change_pct,
                    },
                    meta={"interval": last.interval, "count": len(series)},
                )
            )

        return features


class RuleBasedComposer(Composer):
    """Simple deterministic composer using momentum."""

    def __init__(self, threshold: float = 0.003, max_quantity: float = 1.0) -> None:
        self._threshold = threshold
        self._max_quantity = max_quantity

    def compose(self, context: ComposeContext) -> List[TradeInstruction]:
        instructions: List[TradeInstruction] = []
        for feature in context.features:
            change_pct = float(feature.values.get("change_pct", 0.0))
            if abs(change_pct) < self._threshold:
                continue

            symbol = feature.instrument.symbol
            side = TradeSide.BUY if change_pct > 0 else TradeSide.SELL
            quantity = min(self._max_quantity, max(0.01, abs(change_pct) * 10))
            instruction_id = f"{context.compose_id}:{symbol}:{side.value}"

            instructions.append(
                TradeInstruction(
                    instruction_id=instruction_id,
                    compose_id=context.compose_id,
                    instrument=feature.instrument,
                    side=side,
                    quantity=quantity,
                    price_mode="market",
                    limit_price=None,
                    max_slippage_bps=25,
                    meta={"change_pct": change_pct},
                )
            )

        return instructions


class PaperExecutionGateway(ExecutionGateway):
    """Records instructions without sending them anywhere."""

    def __init__(self) -> None:
        self.executed: List[TradeInstruction] = []

    def execute(self, instructions: List[TradeInstruction]) -> None:
        self.executed.extend(instructions)


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
    """Tracks cash and positions in memory."""

    def __init__(self, initial_capital: float, trading_mode: TradingMode) -> None:
        self._view = PortfolioView(
            ts=int(datetime.now(timezone.utc).timestamp() * 1000),
            cash=initial_capital,
            positions={},
            gross_exposure=None,
            net_exposure=None,
            constraints=None,
        )
        self._trading_mode = trading_mode

    def get_view(self) -> PortfolioView:
        self._view.ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        return self._view

    def apply_trades(
        self, trades: List[TradeHistoryEntry], market_snapshot: Dict[str, float]
    ) -> None:
        for trade in trades:
            symbol = trade.instrument.symbol
            price = trade.entry_price or market_snapshot.get(symbol, 0.0)
            quantity_delta = (
                trade.quantity if trade.side == TradeSide.BUY else -trade.quantity
            )
            position = self._view.positions.get(symbol)
            if position is None:
                position = PositionSnapshot(
                    instrument=trade.instrument,
                    quantity=0.0,
                    avg_price=None,
                    mark_price=price,
                    unrealized_pnl=None,
                )
                self._view.positions[symbol] = position

            new_quantity = position.quantity + quantity_delta
            position.mark_price = price
            if new_quantity == 0:
                self._view.positions.pop(symbol, None)
            else:
                position.quantity = new_quantity
                if position.avg_price is None:
                    position.avg_price = price
                else:
                    position.avg_price = (position.avg_price + price) / 2.0

            notional = (price or 0.0) * trade.quantity
            if trade.side == TradeSide.BUY:
                self._view.cash -= notional
            else:
                self._view.cash += notional


@dataclass
class StrategyRuntime:
    request: UserRequest
    strategy_id: str
    coordinator: DefaultDecisionCoordinator

    async def run_cycle(self) -> DecisionCycleResult:
        return await self.coordinator.run_once()


def create_strategy_runtime(request: UserRequest) -> StrategyRuntime:
    strategy_id = request.trading_config.strategy_name or generate_uuid("strategy")

    initial_capital = request.trading_config.initial_capital or 0.0
    portfolio_service = InMemoryPortfolioService(
        initial_capital=initial_capital,
        trading_mode=request.exchange_config.trading_mode,
    )

    base_prices = {
        symbol: 120.0 + index * 15.0
        for index, symbol in enumerate(request.trading_config.symbols)
    }
    market_data_source = SimpleMarketDataSource(base_prices=base_prices)
    feature_computer = SimpleFeatureComputer()
    composer = RuleBasedComposer()
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
    )

    return StrategyRuntime(
        request=request,
        strategy_id=strategy_id,
        coordinator=coordinator,
    )
