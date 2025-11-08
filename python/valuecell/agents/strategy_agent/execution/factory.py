"""Factory for creating execution gateways based on configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import ExchangeConfig

from .ccxt_trading import CCXTExecutionGateway
from .interfaces import ExecutionGateway
from .paper_trading import PaperExecutionGateway


async def create_execution_gateway(config: ExchangeConfig) -> ExecutionGateway:
    """Create an execution gateway based on exchange configuration.

    Args:
        config: Exchange configuration with trading mode and credentials

    Returns:
        ExecutionGateway instance (paper or real CCXT gateway)

    Raises:
        ValueError: If configuration is invalid for the requested trading mode
    """
    from ..models import TradingMode

    # Virtual/paper trading mode
    if config.trading_mode == TradingMode.VIRTUAL:
        return PaperExecutionGateway(fee_bps=config.fee_bps)

    # Live trading mode requires exchange credentials
    if config.trading_mode == TradingMode.LIVE:
        if not config.exchange_id:
            raise ValueError(
                "exchange_id is required for live trading mode. "
                "Please specify an exchange (e.g., 'binance', 'okx', 'bybit')"
            )

        if not config.api_key or not config.secret_key:
            raise ValueError(
                f"API credentials are required for live trading on {config.exchange_id}. "
                "Please provide api_key and secret_key in ExchangeConfig."
            )

        # Create CCXT gateway with full configuration
        gateway = CCXTExecutionGateway(
            exchange_id=config.exchange_id,
            api_key=config.api_key,
            secret_key=config.secret_key,
            passphrase=config.passphrase,
            testnet=config.testnet,
            default_type=config.market_type.value,
            margin_mode=config.margin_mode.value,
        )

        # Initialize exchange connection
        await gateway._get_exchange()

        return gateway

    raise ValueError(f"Unsupported trading mode: {config.trading_mode}")


def create_execution_gateway_sync(config: ExchangeConfig) -> ExecutionGateway:
    """Synchronous version that returns paper gateway or raises for live mode.

    Use this when you need a gateway immediately without async initialization.
    For live trading, use the async create_execution_gateway instead.

    Args:
        config: Exchange configuration

    Returns:
        ExecutionGateway instance

    Raises:
        RuntimeError: If live trading is requested (requires async initialization)
    """
    from ..models import TradingMode

    if config.trading_mode == TradingMode.VIRTUAL:
        return PaperExecutionGateway(fee_bps=config.fee_bps)

    raise RuntimeError(
        "Live trading gateway requires async initialization. "
        "Use 'await create_execution_gateway(config)' instead."
    )
