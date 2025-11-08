from dataclasses import dataclass
from pathlib import Path
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
        prompt_provider=_make_prompt_provider(),
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

    # Use the sync function with the pre-initialized gateway
    return create_strategy_runtime(request, execution_gateway=execution_gateway)
