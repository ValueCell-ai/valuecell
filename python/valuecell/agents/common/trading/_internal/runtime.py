from dataclasses import dataclass
from typing import Optional

from loguru import logger

from valuecell.server.db.repositories.strategy_repository import get_strategy_repository
from valuecell.utils.uuid import generate_uuid

from ..decision import BaseComposer, LlmComposer
from ..execution import BaseExecutionGateway
from ..execution.factory import create_execution_gateway
from ..features import DefaultFeaturesPipeline
from ..features.interfaces import BaseFeaturesPipeline
from ..history import (
    InMemoryHistoryRecorder,
    RollingDigestBuilder,
)
from ..models import Constraints, DecisionCycleResult, TradingMode, UserRequest
from ..portfolio.in_memory import InMemoryPortfolioService
from ..utils import fetch_free_cash_from_gateway
from .coordinator import DefaultDecisionCoordinator


async def _create_execution_gateway(request: UserRequest) -> BaseExecutionGateway:
    """Create execution gateway asynchronously, handling LIVE mode balance fetching."""
    execution_gateway = await create_execution_gateway(request.exchange_config)

    # In LIVE mode, fetch exchange balance and set initial capital from free cash
    try:
        if request.exchange_config.trading_mode == TradingMode.LIVE:
            free_cash, _ = await fetch_free_cash_from_gateway(
                execution_gateway, request.trading_config.symbols
            )
            request.trading_config.initial_capital = float(free_cash)
    except Exception:
        # Log the error but continue - user might have set initial_capital manually
        logger.exception(
            "Failed to fetch exchange balance for LIVE mode. Will use configured initial_capital instead."
        )

    # Validate initial capital for LIVE mode
    if request.exchange_config.trading_mode == TradingMode.LIVE:
        initial_cap = request.trading_config.initial_capital or 0.0
        if initial_cap <= 0:
            logger.error(
                f"LIVE trading mode has initial_capital={initial_cap}. "
                "This usually means balance fetch failed or account has no funds. "
                "Strategy will not be able to trade without capital."
            )

    return execution_gateway


@dataclass
class StrategyRuntime:
    request: UserRequest
    strategy_id: str
    coordinator: DefaultDecisionCoordinator

    async def run_cycle(self) -> DecisionCycleResult:
        return await self.coordinator.run_once()


async def create_strategy_runtime(
    request: UserRequest,
    composer: Optional[BaseComposer] = None,
    features_pipeline: Optional[BaseFeaturesPipeline] = None,
    strategy_id_override: Optional[str] = None,
) -> StrategyRuntime:
    """Create a strategy runtime with async initialization (supports both paper and live trading).

    This function properly initializes CCXT exchange connections for live trading
    and can also be used for paper trading.

    In LIVE mode, it fetches the exchange balance and sets the
    initial capital to the available (free) cash for the strategy's
    quote currencies. Opening positions will therefore draw down cash
    and cannot borrow (no financing).

    Args:
        request: User request with strategy configuration
        composer: Optional custom decision composer. If None, uses LlmComposer.
        features_pipeline: Optional custom features pipeline. If None, uses
            `DefaultFeaturesPipeline`.

    Returns:
        StrategyRuntime instance with initialized execution gateway

    Example:
        >>> request = UserRequest(
        ...     exchange_config=ExchangeConfig(
        ...         exchange_id='binance',
        ...         trading_mode=TradingMode.LIVE,
        ...         api_key='YOUR_KEY',
        ...         secret_key='YOUR_SECRET',
        ...         market_type=MarketType.SWAP,
        ...         margin_mode=MarginMode.ISOLATED,
        ...         testnet=True,
        ...     ),
        ...     trading_config=TradingConfig(
        ...         symbols=['BTC-USDT', 'ETH-USDT'],
        ...         initial_capital=10000.0,
        ...         max_leverage=10.0,
        ...         max_positions=5,
        ...     )
        ... )
        >>> runtime = await create_strategy_runtime(request)
    """
    # Create execution gateway asynchronously
    execution_gateway = await _create_execution_gateway(request)

    # Create strategy runtime components
    strategy_id = strategy_id_override or generate_uuid("strategy")

    # If an initial capital override wasn't provided, and this is a resume
    # of an existing strategy, attempt to initialize from the persisted
    # portfolio snapshot so the in-memory portfolio starts with the
    # previously recorded equity.
    initial_capital_override = None
    if strategy_id_override:
        try:
            repo = get_strategy_repository()
            snap = repo.get_latest_portfolio_snapshot(strategy_id_override)
            if snap is not None:
                initial_capital_override = float(snap.total_value or snap.cash or 0.0)
                logger.info(
                    "Initialized runtime initial_capital from persisted snapshot for strategy_id=%s",
                    strategy_id_override,
                )
        except Exception:
            logger.exception(
                "Failed to initialize initial_capital from persisted snapshot for strategy_id=%s",
                strategy_id_override,
            )

    initial_capital = (
        initial_capital_override or request.trading_config.initial_capital or 0.0
    )
    constraints = Constraints(
        max_positions=request.trading_config.max_positions,
        max_leverage=request.trading_config.max_leverage,
    )
    portfolio_service = InMemoryPortfolioService(
        initial_capital=initial_capital,
        trading_mode=request.exchange_config.trading_mode,
        market_type=request.exchange_config.market_type,
        constraints=constraints,
        strategy_id=strategy_id,
    )

    # Use custom composer if provided, otherwise default to LlmComposer
    if composer is None:
        composer = LlmComposer(request=request)

    if features_pipeline is None:
        features_pipeline = DefaultFeaturesPipeline.from_request(request)

    history_recorder = InMemoryHistoryRecorder()
    digest_builder = RollingDigestBuilder()

    coordinator = DefaultDecisionCoordinator(
        request=request,
        strategy_id=strategy_id,
        portfolio_service=portfolio_service,
        features_pipeline=features_pipeline,
        composer=composer,
        execution_gateway=execution_gateway,
        history_recorder=history_recorder,
        digest_builder=digest_builder,
    )

    # If resuming an existing strategy, initialize coordinator cycle index
    # from the latest persisted compose cycle so the in-memory coordinator
    # continues numbering without overlap.
    if strategy_id_override:
        try:
            repo = get_strategy_repository()
            cycles = repo.get_cycles(strategy_id, limit=1)
            if cycles:
                latest = cycles[0]
                if latest.cycle_index is not None:
                    coordinator.cycle_index = int(latest.cycle_index)
        except Exception:
            logger.exception(
                "Failed to initialize coordinator cycle_index from DB for strategy_id=%s",
                strategy_id,
            )

    return StrategyRuntime(
        request=request,
        strategy_id=strategy_id,
        coordinator=coordinator,
    )
