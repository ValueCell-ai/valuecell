from dataclasses import dataclass
from typing import Optional

from valuecell.utils.uuid import generate_uuid

from .core import DecisionCycleResult, DefaultDecisionCoordinator
from .data.market import SimpleMarketDataSource
from .decision.composer import LlmComposer
from .execution.factory import create_execution_gateway, create_execution_gateway_sync
from .execution.interfaces import ExecutionGateway
from .features.simple import SimpleFeatureComputer
from .models import Constraints, TradingMode, UserRequest
from .portfolio.in_memory import InMemoryPortfolioService
from .trading_history.digest import RollingDigestBuilder
from .trading_history.recorder import InMemoryHistoryRecorder


def _simple_prompt_provider(request: UserRequest) -> str:
    """Return a resolved prompt text by fusing custom_prompt and prompt_text.

    Fusion logic:
    - If custom_prompt exists, use it as base
    - If prompt_text also exists, append it after custom_prompt
    - If only prompt_text exists, use it
    - Fallback: simple generated mention of symbols
    """
    custom = request.trading_config.custom_prompt
    prompt = request.trading_config.prompt_text
    if custom and prompt:
        return f"{prompt}\n\n{custom}"
    elif custom:
        return custom
    elif prompt:
        return prompt
    symbols = ", ".join(request.trading_config.symbols)
    return f"Compose trading instructions for symbols: {symbols}."


@dataclass
class StrategyRuntime:
    request: UserRequest
    strategy_id: str
    coordinator: DefaultDecisionCoordinator

    async def run_cycle(self) -> DecisionCycleResult:
        return await self.coordinator.run_once()


def create_strategy_runtime(
    request: UserRequest,
    execution_gateway: Optional[ExecutionGateway] = None,
) -> StrategyRuntime:
    """Create a strategy runtime with synchronous initialization.

    Note: This function only supports paper trading by default. For live trading,
    use create_strategy_runtime_async() instead, which properly initializes
    the CCXT exchange connection.

    Args:
        request: User request with strategy configuration
        execution_gateway: Optional pre-initialized execution gateway.
                          If None, will be created based on request.exchange_config.

    Returns:
        StrategyRuntime instance

    Raises:
        RuntimeError: If live trading is requested without providing a gateway
    """
    strategy_id = generate_uuid("strategy")
    initial_capital = request.trading_config.initial_capital or 0.0
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

    base_prices = {
        symbol: 120.0 + index * 15.0
        for index, symbol in enumerate(request.trading_config.symbols)
    }
    market_data_source = SimpleMarketDataSource(
        base_prices=base_prices, exchange_id=request.exchange_config.exchange_id
    )
    feature_computer = SimpleFeatureComputer()
    composer = LlmComposer(request=request)

    # Create execution gateway if not provided
    if execution_gateway is None:
        if request.exchange_config.trading_mode == TradingMode.LIVE:
            raise RuntimeError(
                "Live trading requires async initialization. "
                "Use create_strategy_runtime_async() or provide a pre-initialized gateway."
            )
        execution_gateway = create_execution_gateway_sync(request.exchange_config)

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
        prompt_provider=_simple_prompt_provider,
    )

    return StrategyRuntime(
        request=request,
        strategy_id=strategy_id,
        coordinator=coordinator,
    )


async def create_strategy_runtime_async(request: UserRequest) -> StrategyRuntime:
    """Create a strategy runtime with async initialization (supports live trading).

    This function properly initializes CCXT exchange connections for live trading.
    It can also be used for paper trading.

    In LIVE mode, it fetches the exchange balance and sets the
    initial capital to the available (free) cash for the strategy's
    quote currencies. Opening positions will therefore draw down cash
    and cannot borrow (no financing).

    Args:
        request: User request with strategy configuration

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
        >>> runtime = await create_strategy_runtime_async(request)
    """
    # Create execution gateway asynchronously
    execution_gateway = await create_execution_gateway(request.exchange_config)

    # In LIVE mode, fetch exchange balance and set initial capital from free cash
    try:
        if request.exchange_config.trading_mode == TradingMode.LIVE and hasattr(
            execution_gateway, "fetch_balance"
        ):
            balance = await execution_gateway.fetch_balance()
            free_map = {}
            # ccxt balance may be shaped as: {'free': {...}, 'used': {...}, 'total': {...}}
            try:
                free_section = (
                    balance.get("free") if isinstance(balance, dict) else None
                )
            except Exception:
                free_section = None
            if isinstance(free_section, dict):
                free_map = {
                    str(k).upper(): float(v or 0.0) for k, v in free_section.items()
                }
            else:
                # fallback: per-ccy dicts: balance['USDT'] = {'free': x, 'used': y, 'total': z}
                for k, v in balance.items() if isinstance(balance, dict) else []:
                    if isinstance(v, dict) and "free" in v:
                        try:
                            free_map[str(k).upper()] = float(v.get("free") or 0.0)
                        except Exception:
                            continue
            # collect quote currencies from configured symbols
            quotes: list[str] = []
            for sym in request.trading_config.symbols or []:
                s = str(sym).upper()
                if "/" in s:
                    parts = s.split("/")
                    if len(parts) == 2:
                        quotes.append(parts[1])
                elif "-" in s:
                    parts = s.split("-")
                    if len(parts) == 2:
                        quotes.append(parts[1])
            quotes = list(dict.fromkeys(quotes))  # unique order-preserving
            free_cash = 0.0
            if quotes:
                for q in quotes:
                    free_cash += float(free_map.get(q, 0.0) or 0.0)
            else:
                # fallback to common stablecoins
                for q in ("USDT", "USD", "USDC"):
                    free_cash += float(free_map.get(q, 0.0) or 0.0)
            # Set initial capital to exchange free cash
            request.trading_config.initial_capital = float(free_cash)
    except Exception:
        # Do not fail runtime creation if balance fetch or parsing fails
        pass

    # Use the sync function with the pre-initialized gateway
    return create_strategy_runtime(request, execution_gateway=execution_gateway)
