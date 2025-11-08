"""CCXT-based real exchange execution gateway.

Supports:
- Spot trading
- Futures/Perpetual contracts (USDT-margined, coin-margined)
- Leverage trading (cross/isolated margin)
- Multiple exchanges via CCXT unified API
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

import ccxt.async_support as ccxt
from loguru import logger

from ..models import (
    PriceMode,
    TradeInstruction,
    TradeSide,
    TxResult,
    TxStatus,
)
from .interfaces import ExecutionGateway


class CCXTExecutionGateway(ExecutionGateway):
    """Async execution gateway using CCXT unified API for real exchanges.

    Features:
    - Supports spot, futures, and perpetual contracts
    - Automatic leverage and margin mode setup
    - Symbol format normalization (BTC-USD -> BTC/USD:USD for futures)
    - Proper error handling and partial fill support
    - Fee tracking from exchange responses
    """

    def __init__(
        self,
        exchange_id: str,
        api_key: str,
        secret_key: str,
        passphrase: Optional[str] = None,
        testnet: bool = False,
        default_type: str = "spot",
        margin_mode: str = "isolated",
        ccxt_options: Optional[Dict] = None,
    ) -> None:
        """Initialize CCXT exchange gateway.

        Args:
            exchange_id: Exchange identifier (e.g., 'binance', 'okx', 'bybit')
            api_key: API key for authentication
            secret_key: Secret key for authentication
            passphrase: Optional passphrase (required for OKX)
            testnet: Whether to use testnet/sandbox mode
            default_type: Default market type ('spot', 'future', 'swap')
            margin_mode: Default margin mode ('isolated' or 'cross')
            ccxt_options: Additional CCXT exchange options
        """
        self.exchange_id = exchange_id.lower()
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.testnet = testnet
        self.default_type = default_type
        self.margin_mode = margin_mode
        self._ccxt_options = ccxt_options or {}

        # Track leverage settings per symbol to avoid redundant calls
        self._leverage_cache: Dict[str, float] = {}
        self._margin_mode_cache: Dict[str, str] = {}

        # Exchange instance (lazy-initialized)
        self._exchange: Optional[ccxt.Exchange] = None

    async def _get_exchange(self) -> ccxt.Exchange:
        """Get or create the CCXT exchange instance."""
        if self._exchange is not None:
            return self._exchange

        # Get exchange class by name
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
        except AttributeError:
            raise ValueError(
                f"Exchange '{self.exchange_id}' not supported by CCXT. "
                f"Available: {', '.join(ccxt.exchanges)}"
            )

        # Build configuration
        config = {
            "apiKey": self.api_key,
            "secret": self.secret_key,
            "enableRateLimit": True,  # Respect rate limits
            "options": {
                "defaultType": self.default_type,
                **self._ccxt_options,
            },
        }

        # Add passphrase if provided (required for OKX)
        if self.passphrase:
            config["password"] = self.passphrase

        # Create exchange instance
        self._exchange = exchange_class(config)

        # Enable sandbox/testnet mode if requested
        if self.testnet:
            self._exchange.set_sandbox_mode(True)

        # Load markets
        try:
            await self._exchange.load_markets()
        except Exception as e:
            raise RuntimeError(
                f"Failed to load markets for {self.exchange_id}: {e}"
            ) from e

        return self._exchange

    def _normalize_symbol(self, symbol: str, market_type: Optional[str] = None) -> str:
        """Normalize symbol format for CCXT.

        Examples:
            BTC-USD -> BTC/USD (spot)
            BTC-USDT -> BTC/USDT:USDT (USDT futures)
            ETH-USD -> ETH/USD:USD (USD futures)

        Args:
            symbol: Symbol in format 'BTC-USD', 'BTC-USDT', etc.
            market_type: Optional market type override ('spot', 'future', 'swap')

        Returns:
            Normalized CCXT symbol
        """
        mtype = market_type or self.default_type

        # Replace dash with slash
        base_symbol = symbol.replace("-", "/")

        # For futures/swap, append settlement currency
        if mtype in ("future", "swap"):
            # If symbol is like BTC/USDT, make it BTC/USDT:USDT
            if ":" not in base_symbol:
                parts = base_symbol.split("/")
                if len(parts) == 2:
                    base_symbol = f"{parts[0]}/{parts[1]}:{parts[1]}"

        return base_symbol

    async def _setup_leverage(
        self, symbol: str, leverage: Optional[float], exchange: ccxt.Exchange
    ) -> None:
        """Set leverage for a symbol if needed and supported.

        Args:
            symbol: CCXT normalized symbol
            leverage: Desired leverage (None means 1x)
            exchange: CCXT exchange instance
        """
        if leverage is None:
            leverage = 1.0

        # Check if already set to avoid redundant calls
        if self._leverage_cache.get(symbol) == leverage:
            return

        # Check if exchange supports setting leverage
        if not exchange.has.get("setLeverage"):
            return

        try:
            await exchange.set_leverage(int(leverage), symbol)
            self._leverage_cache[symbol] = leverage
        except Exception as e:
            # Some exchanges don't support leverage on certain symbols
            # Log but don't fail the trade
            print(f"Warning: Could not set leverage for {symbol}: {e}")

    async def _setup_margin_mode(self, symbol: str, exchange: ccxt.Exchange) -> None:
        """Set margin mode for a symbol if needed and supported.

        Args:
            symbol: CCXT normalized symbol
            exchange: CCXT exchange instance
        """
        # Check if already set
        if self._margin_mode_cache.get(symbol) == self.margin_mode:
            return

        # Check if exchange supports setting margin mode
        if not exchange.has.get("setMarginMode"):
            return

        try:
            await exchange.set_margin_mode(self.margin_mode, symbol)
            self._margin_mode_cache[symbol] = self.margin_mode
        except Exception as e:
            # Log but don't fail
            print(f"Warning: Could not set margin mode for {symbol}: {e}")

    async def execute(
        self,
        instructions: List[TradeInstruction],
        market_snapshot: Optional[Dict[str, float]] = None,
    ) -> List[TxResult]:
        """Execute trade instructions on the real exchange via CCXT.

        Args:
            instructions: List of trade instructions to execute
            market_snapshot: Optional market snapshot (not used for real execution)

        Returns:
            List of transaction results with fill details
        """
        if not instructions:
            logger.warning("⚠️ CCXTExecutionGateway: No instructions to execute")
            return []

        logger.info(
            f"💰 CCXTExecutionGateway: Executing {len(instructions)} instructions"
        )
        exchange = await self._get_exchange()
        results: List[TxResult] = []

        for inst in instructions:
            logger.info(
                f"  📤 Processing {inst.instrument.symbol} {inst.side.value} qty={inst.quantity}"
            )
            try:
                result = await self._execute_single(inst, exchange)
                results.append(result)
            except Exception as e:
                # Create error result for failed instruction
                results.append(
                    TxResult(
                        instruction_id=inst.instruction_id,
                        instrument=inst.instrument,
                        side=inst.side,
                        requested_qty=float(inst.quantity),
                        filled_qty=0.0,
                        status=TxStatus.ERROR,
                        reason=str(e),
                        meta=inst.meta,
                    )
                )

        return results

    async def _execute_single(
        self, inst: TradeInstruction, exchange: ccxt.Exchange
    ) -> TxResult:
        """Execute a single trade instruction.

        Args:
            inst: Trade instruction to execute
            exchange: CCXT exchange instance

        Returns:
            Transaction result with execution details
        """
        # Normalize symbol for CCXT
        symbol = self._normalize_symbol(inst.instrument.symbol)

        # Setup leverage and margin mode
        await self._setup_leverage(symbol, inst.leverage, exchange)
        await self._setup_margin_mode(symbol, exchange)

        # Map instruction to CCXT parameters
        side = "buy" if inst.side == TradeSide.BUY else "sell"
        order_type = "limit" if inst.price_mode == PriceMode.LIMIT else "market"
        amount = float(inst.quantity)
        price = float(inst.limit_price) if inst.limit_price else None

        # Build order params
        params = {}
        if inst.meta:
            # Pass through any exchange-specific parameters
            params.update(inst.meta)

        # Create order
        try:
            logger.info(
                f"  🔨 Creating {order_type} order: {side} {amount} {symbol} @ {price if price else 'market'}"
            )
            order = await exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params,
            )
            logger.info(
                f"  ✓ Order created: id={order.get('id')}, status={order.get('status')}, filled={order.get('filled')}"
            )
        except Exception as e:
            logger.error(f"  ❌ ERROR creating order for {symbol}: {e}")
            raise RuntimeError(f"Failed to create order for {symbol}: {e}") from e

        # For market orders, wait for fill and fetch final order status
        # Many exchanges don't immediately return filled quantities for market orders
        if order_type == "market":
            order_id = order.get("id")
            if order_id and exchange.has.get("fetchOrder"):
                try:
                    # Wait a short time for market order to fill
                    logger.info(
                        f"  ⏳ Waiting 0.5s for market order {order_id} to fill..."
                    )
                    await asyncio.sleep(0.5)

                    # Fetch updated order status
                    order = await exchange.fetch_order(order_id, symbol)
                    logger.info(
                        f"  📈 Order status after fetch: filled={order.get('filled')}, average={order.get('average')}, status={order.get('status')}"
                    )
                except Exception as e:
                    # If fetch fails, use original order response
                    logger.warning(
                        f"  ⚠️ Could not fetch order status for {symbol}: {e}"
                    )

        # Parse order response
        filled_qty = float(order.get("filled", 0.0))
        avg_price = float(order.get("average") or 0.0)
        fee_cost = 0.0

        logger.info(
            f"  📊 Final parsed: filled_qty={filled_qty}, avg_price={avg_price}"
        )

        # Extract fee information
        if "fee" in order and order["fee"]:
            fee_info = order["fee"]
            fee_cost = float(fee_info.get("cost", 0.0))

        # Calculate slippage if applicable
        slippage_bps = None
        if avg_price and inst.limit_price and inst.price_mode == PriceMode.LIMIT:
            expected = float(inst.limit_price)
            slippage = abs(avg_price - expected) / expected * 10000.0
            slippage_bps = slippage

        # Determine status
        status = TxStatus.FILLED
        if filled_qty < amount * 0.99:  # Allow 1% tolerance
            status = TxStatus.PARTIAL
        if filled_qty == 0:
            status = TxStatus.REJECTED

        return TxResult(
            instruction_id=inst.instruction_id,
            instrument=inst.instrument,
            side=inst.side,
            requested_qty=amount,
            filled_qty=filled_qty,
            avg_exec_price=avg_price if avg_price > 0 else None,
            slippage_bps=slippage_bps,
            fee_cost=fee_cost if fee_cost > 0 else None,
            leverage=inst.leverage,
            status=status,
            reason=order.get("status") if status != TxStatus.FILLED else None,
            meta={
                "order_id": order.get("id"),
                "exchange_symbol": symbol,
                **(inst.meta or {}),
            },
        )

    async def close(self) -> None:
        """Close the exchange connection and cleanup resources."""
        if self._exchange is not None:
            await self._exchange.close()
            self._exchange = None

    async def fetch_balance(self) -> Dict:
        """Fetch account balance from exchange.

        Returns:
            Balance dictionary with free, used, and total amounts per currency
        """
        exchange = await self._get_exchange()
        return await exchange.fetch_balance()

    async def fetch_positions(self, symbols: Optional[List[str]] = None) -> List[Dict]:
        """Fetch current positions from exchange.

        Args:
            symbols: Optional list of symbols to fetch positions for

        Returns:
            List of position dictionaries
        """
        exchange = await self._get_exchange()

        # Check if exchange supports fetching positions
        if not exchange.has.get("fetchPositions"):
            return []

        # Normalize symbols if provided
        normalized_symbols = None
        if symbols:
            normalized_symbols = [self._normalize_symbol(s) for s in symbols]

        try:
            positions = await exchange.fetch_positions(normalized_symbols)
            return positions
        except Exception as e:
            print(f"Warning: Could not fetch positions: {e}")
            return []

    async def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """Cancel an open order.

        Args:
            order_id: Order ID to cancel
            symbol: Symbol of the order

        Returns:
            Cancellation result dictionary
        """
        exchange = await self._get_exchange()
        normalized_symbol = self._normalize_symbol(symbol)
        return await exchange.cancel_order(order_id, normalized_symbol)

    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Fetch open orders from exchange.

        Args:
            symbol: Optional symbol to filter orders

        Returns:
            List of open order dictionaries
        """
        exchange = await self._get_exchange()
        normalized_symbol = self._normalize_symbol(symbol) if symbol else None
        return await exchange.fetch_open_orders(normalized_symbol)

    def __repr__(self) -> str:
        mode = "testnet" if self.testnet else "live"
        return (
            f"CCXTExecutionGateway(exchange={self.exchange_id}, "
            f"type={self.default_type}, margin={self.margin_mode}, mode={mode})"
        )


async def create_ccxt_gateway(
    exchange_id: str,
    api_key: str,
    secret_key: str,
    passphrase: Optional[str] = None,
    testnet: bool = False,
    market_type: str = "spot",
    margin_mode: str = "isolated",
    **ccxt_options,
) -> CCXTExecutionGateway:
    """Factory function to create and initialize a CCXT execution gateway.

    Args:
        exchange_id: Exchange identifier (e.g., 'binance', 'okx', 'bybit')
        api_key: API key for authentication
        secret_key: Secret key for authentication
        passphrase: Optional passphrase (required for OKX)
        testnet: Whether to use testnet/sandbox mode
        market_type: Market type ('spot', 'future', 'swap')
        margin_mode: Margin mode ('isolated' or 'cross')
        **ccxt_options: Additional CCXT exchange options

    Returns:
        Initialized CCXT execution gateway

    Example:
        >>> gateway = await create_ccxt_gateway(
        ...     exchange_id='binance',
        ...     api_key='YOUR_KEY',
        ...     secret_key='YOUR_SECRET',
        ...     market_type='swap',  # For perpetual futures
        ...     margin_mode='isolated',
        ...     testnet=True
        ... )
    """
    gateway = CCXTExecutionGateway(
        exchange_id=exchange_id,
        api_key=api_key,
        secret_key=secret_key,
        passphrase=passphrase,
        testnet=testnet,
        default_type=market_type,
        margin_mode=margin_mode,
        ccxt_options=ccxt_options,
    )

    # Pre-load markets to validate connection
    await gateway._get_exchange()

    return gateway
