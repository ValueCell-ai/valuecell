"""Exchange adapters for different trading platforms

This module provides adapters for various cryptocurrency exchanges,
allowing the AutoTradingAgent to trade on both paper (simulated) and live (real) exchanges.

Adapters:
- ExchangeBase: Abstract base class defining the exchange interface
- PaperTrading: Simulated trading (default)
- BinanceExchange: Live trading on Binance (requires API keys)
"""

from .base_exchange import ExchangeBase, ExchangeType, Order, OrderStatus
from .okx_exchange import OKXExchange, OKXExchangeError
from .paper_trading import PaperTrading

__all__ = [
    "ExchangeBase",
    "ExchangeType",
    "Order",
    "OrderStatus",
    "OKXExchange",
    "OKXExchangeError",
    "PaperTrading",
]
