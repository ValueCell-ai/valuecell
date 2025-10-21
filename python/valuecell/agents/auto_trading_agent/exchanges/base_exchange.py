"""Abstract base class for exchange adapters"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..models import TradeType

logger = logging.getLogger(__name__)


class ExchangeType(str, Enum):
    """Supported exchange types"""

    PAPER = "paper"  # Simulated trading
    BINANCE = "binance"  # Binance exchange
    BYBIT = "bybit"  # Bybit exchange (future support)
    COINBASE = "coinbase"  # Coinbase (future support)


class OrderStatus(str, Enum):
    """Order execution status"""

    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Order:
    """Represents a single order"""

    def __init__(
        self,
        order_id: str,
        symbol: str,
        side: str,  # "buy" or "sell"
        quantity: float,
        price: float,
        order_type: str = "limit",  # "limit", "market", etc.
        trade_type: Optional[TradeType] = None,
    ):
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.order_type = order_type
        self.trade_type = trade_type
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0.0
        self.filled_price = 0.0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary"""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "order_type": self.order_type,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "created_at": self.created_at.isoformat(),
        }


class ExchangeBase(ABC):
    """
    Abstract base class for exchange adapters.

    All exchange implementations (Binance, Bybit, etc.) must inherit from this
    class and implement all abstract methods.
    """

    def __init__(self, exchange_type: ExchangeType):
        """
        Initialize exchange adapter.

        Args:
            exchange_type: Type of exchange (PAPER, BINANCE, etc.)
        """
        self.exchange_type = exchange_type
        self.is_connected = False
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []

    # ============ Connection Management ============

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to exchange (authenticate, validate credentials).

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from exchange gracefully.

        Returns:
            True if disconnection successful
        """
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate that connection is still active and valid.

        Returns:
            True if connection is valid
        """
        pass

    # ============ Account Information ============

    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """
        Get account balances across all assets.

        Returns:
            Dictionary mapping asset symbols to balances
            Example: {"USDT": 100000, "BTC": 1.5}
        """
        pass

    @abstractmethod
    async def get_asset_balance(self, asset: str) -> float:
        """
        Get balance for a specific asset.

        Args:
            asset: Asset symbol (e.g., "USDT", "BTC")

        Returns:
            Available balance
        """
        pass

    # ============ Market Data ============

    @abstractmethod
    async def get_current_price(self, symbol: str) -> float:
        """
        Get current market price for a symbol.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")

        Returns:
            Current price
        """
        pass

    @abstractmethod
    async def get_24h_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get 24-hour ticker data.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with price, volume, change data
        """
        pass

    # ============ Order Management ============

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        order_type: str = "limit",
        **kwargs,
    ) -> Order:
        """
        Place a new order.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            side: "buy" or "sell"
            quantity: Order quantity
            price: Order price (None for market orders)
            order_type: "limit" or "market"
            **kwargs: Exchange-specific parameters

        Returns:
            Order object with order_id
        """
        pass

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel an open order.

        Args:
            symbol: Trading symbol
            order_id: Order ID to cancel

        Returns:
            True if cancellation successful
        """
        pass

    @abstractmethod
    async def get_order_status(self, symbol: str, order_id: str) -> OrderStatus:
        """
        Get status of a specific order.

        Args:
            symbol: Trading symbol
            order_id: Order ID

        Returns:
            Order status
        """
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Get all open orders.

        Args:
            symbol: Optional symbol to filter by

        Returns:
            List of open Order objects
        """
        pass

    @abstractmethod
    async def get_order_history(
        self, symbol: Optional[str] = None, limit: int = 100
    ) -> List[Order]:
        """
        Get order history.

        Args:
            symbol: Optional symbol to filter by
            limit: Maximum number of orders to return

        Returns:
            List of Order objects
        """
        pass

    # ============ Position Management ============

    @abstractmethod
    async def get_open_positions(
        self, symbol: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get all open positions.

        Args:
            symbol: Optional symbol to filter by

        Returns:
            Dictionary with position details
            Example: {
                "BTC": {
                    "quantity": 1.5,
                    "entry_price": 45000,
                    "current_price": 46000,
                    "unrealized_pnl": 1500
                }
            }
        """
        pass

    @abstractmethod
    async def get_position_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get details for a specific position.

        Args:
            symbol: Trading symbol

        Returns:
            Position details or None if no position
        """
        pass

    # ============ Trade Execution ============

    @abstractmethod
    async def execute_buy(
        self,
        symbol: str,
        quantity: float,
        price: Optional[float] = None,
        **kwargs,
    ) -> Optional[Order]:
        """
        Execute a buy order.

        Args:
            symbol: Trading symbol
            quantity: Amount to buy
            price: Price (None for market order)
            **kwargs: Exchange-specific parameters

        Returns:
            Order object or None if execution failed
        """
        pass

    @abstractmethod
    async def execute_sell(
        self,
        symbol: str,
        quantity: float,
        price: Optional[float] = None,
        **kwargs,
    ) -> Optional[Order]:
        """
        Execute a sell order.

        Args:
            symbol: Trading symbol
            quantity: Amount to sell
            price: Price (None for market order)
            **kwargs: Exchange-specific parameters

        Returns:
            Order object or None if execution failed
        """
        pass

    # ============ Utilities ============

    @abstractmethod
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to exchange format.

        Args:
            symbol: Symbol to normalize (e.g., "BTC-USD")

        Returns:
            Exchange-formatted symbol (e.g., "BTCUSDT" for Binance)
        """
        pass

    @abstractmethod
    async def get_fee_tier(self) -> Dict[str, float]:
        """
        Get current trading fee tier.

        Returns:
            Dictionary with maker/taker fees
        """
        pass

    @abstractmethod
    async def get_trading_limits(self, symbol: str) -> Dict[str, float]:
        """
        Get trading limits for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with min/max quantities, precision, etc.
        """
        pass

    # ============ Error Handling ============

    async def handle_order_rejection(self, order: Order, reason: str) -> bool:
        """
        Handle order rejection (cleanup, logging, etc.).

        Args:
            order: Rejected order
            reason: Rejection reason

        Returns:
            True if handled successfully
        """
        logger.warning(f"Order {order.order_id} rejected: {reason}")
        order.status = OrderStatus.REJECTED
        return True

    async def handle_connection_error(self, error: Exception) -> bool:
        """
        Handle connection errors.

        Args:
            error: Connection error

        Returns:
            True if handled, False if critical
        """
        logger.error(f"Connection error: {error}")
        self.is_connected = False
        return False
