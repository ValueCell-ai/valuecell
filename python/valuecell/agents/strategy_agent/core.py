from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from valuecell.utils.uuid import generate_uuid

from .data.interfaces import MarketDataSource
from .decision.interfaces import Composer
from .execution.interfaces import ExecutionGateway
from .features.interfaces import FeatureComputer
from .models import (
    ComposeContext,
    FeatureVector,
    HistoryRecord,
    PortfolioView,
    StrategyStatus,
    StrategySummary,
    TradeDigest,
    TradeHistoryEntry,
    TradeInstruction,
    TradeSide,
    TradeType,
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
        interval: str = "1m",
        lookback: int = 20,
        prompt_provider: Optional[Callable[[UserRequest], str]] = None,
        clock: Optional[Callable[[], datetime]] = None,
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
        self._interval = interval
        self._lookback = lookback
        self._history_limit = max(history_limit, 1)
        self._symbols = list(dict.fromkeys(request.trading_config.symbols))
        self._prompt_provider = (
            prompt_provider if prompt_provider is not None else self._default_prompt
        )
        self._clock = clock if clock is not None else _default_clock
        self._history_records: List[HistoryRecord] = []
        self._realized_pnl: float = 0.0
        self._unrealized_pnl: float = 0.0
        self._cycle_index: int = 0
        self._strategy_name = request.trading_config.strategy_name or strategy_id

    async def run_once(self) -> DecisionCycleResult:
        timestamp_ms = int(self._clock().timestamp() * 1000)
        compose_id = generate_uuid("compose")

        portfolio = self._portfolio_service.get_view()
        candles = await self._market_data_source.get_recent_candles(
            self._symbols, self._interval, self._lookback
        )
        features = self._feature_computer.compute_features(candles=candles)
        market_snapshot = _build_market_snapshot(features)
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
            constraints=None,
        )

        instructions = self._composer.compose(context)
        # Execution gateway may be sync; allow sync execute
        self._execution_gateway.execute(instructions)

        trades = self._create_trades(
            instructions, market_snapshot, compose_id, timestamp_ms
        )
        self._apply_trades_to_portfolio(trades, market_snapshot)
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

    def _default_prompt(self, request: UserRequest) -> str:
        custom_prompt = request.trading_config.custom_prompt
        if custom_prompt:
            return custom_prompt
        symbols = ", ".join(self._symbols)
        return f"Compose trading instructions for symbols: {symbols}."

    def _create_trades(
        self,
        instructions: List[TradeInstruction],
        market_snapshot: Dict[str, float],
        compose_id: str,
        timestamp_ms: int,
    ) -> List[TradeHistoryEntry]:
        trades: List[TradeHistoryEntry] = []
        for instruction in instructions:
            symbol = instruction.instrument.symbol
            price = market_snapshot.get(symbol, 0.0)
            notional = price * instruction.quantity
            realized_pnl = notional * (
                0.001 if instruction.side == TradeSide.SELL else -0.001
            )
            trades.append(
                TradeHistoryEntry(
                    trade_id=generate_uuid("trade"),
                    compose_id=compose_id,
                    instruction_id=instruction.instruction_id,
                    strategy_id=self.strategy_id,
                    instrument=instruction.instrument,
                    side=instruction.side,
                    type=TradeType.LONG
                    if instruction.side == TradeSide.BUY
                    else TradeType.SHORT,
                    quantity=instruction.quantity,
                    entry_price=price or None,
                    exit_price=None,
                    notional_entry=notional or None,
                    notional_exit=None,
                    entry_ts=timestamp_ms,
                    exit_ts=None,
                    trade_ts=timestamp_ms,
                    holding_ms=None,
                    realized_pnl=realized_pnl,
                    realized_pnl_pct=(realized_pnl / notional) if notional else None,
                    leverage=None,
                    note=None,
                )
            )
        return trades

    def _apply_trades_to_portfolio(
        self,
        trades: List[TradeHistoryEntry],
        market_snapshot: Dict[str, float],
    ) -> None:
        if not trades:
            return
        # PortfolioService now exposes apply_trades; call directly to update state
        try:
            self._portfolio_service.apply_trades(trades, market_snapshot)
        except NotImplementedError:
            # service may be read-only; ignore
            return

    def _build_summary(
        self,
        timestamp_ms: int,
        trades: List[TradeHistoryEntry],
    ) -> StrategySummary:
        realized_delta = sum(trade.realized_pnl or 0.0 for trade in trades)
        self._realized_pnl += realized_delta

        unrealized_delta = sum(
            (trade.notional_entry or 0.0) * 0.0001 for trade in trades
        )
        self._unrealized_pnl = max(self._unrealized_pnl + unrealized_delta, 0.0)

        initial_capital = self._request.trading_config.initial_capital or 0.0
        pnl_pct = (
            (self._realized_pnl + self._unrealized_pnl) / initial_capital
            if initial_capital
            else None
        )

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
