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
    MarketSnapShotType,
    PriceMode,
    TradeInstruction,
    TradeSide,
    TxResult,
    TxStatus,
    derive_side_from_action,
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
        default_type: str = "swap",
        margin_mode: str = "cross",
        position_mode: str = "oneway",
        ccxt_options: Optional[Dict] = None,
    ) -> None:
        """Initialize CCXT exchange gateway.

        Args:
            exchange_id: Exchange identifier (e.g., 'binance', 'okx', 'bybit')
            api_key: API key for authentication
            secret_key: Secret key for authentication
            passphrase: Optional passphrase (required for OKX)
            testnet: Whether to use testnet/sandbox mode
            default_type: Default market type ('spot', 'future', 'swap', "margin")
            margin_mode: Default margin mode ('isolated' or 'cross')
            position_mode: Position mode ('oneway' or 'hedged'), default 'oneway'
            ccxt_options: Additional CCXT exchange options
        """
        self.exchange_id = exchange_id.lower()
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.testnet = testnet
        self.default_type = default_type
        self.margin_mode = margin_mode
        self.position_mode = position_mode
        self._ccxt_options = ccxt_options or {}

        # Track leverage settings per symbol to avoid redundant calls
        self._leverage_cache: Dict[str, float] = {}
        self._margin_mode_cache: Dict[str, str] = {}

        # Exchange instance (lazy-initialized)
        self._exchange: Optional[ccxt.Exchange] = None

    def _choose_default_type_for_exchange(self) -> str:
        """Return a safe defaultType for the selected exchange.

        - Binance: map 'swap' to 'future' (USDT-M futures)
        - Others: keep configured default_type
        """
        if self.exchange_id == "binance" and self.default_type == "swap":
            return "future"
        return self.default_type

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
                "defaultType": self._choose_default_type_for_exchange(),
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

        # Optionally set position mode (oneway/hedged) for exchanges that support it
        try:
            if self._exchange.has.get("setPositionMode"):
                hedged = self.position_mode.lower() in ("hedged", "dual", "hedge")
                await self._exchange.set_position_mode(hedged)
        except Exception as e:
            logger.warning(
                f"⚠️ Could not set position mode ({self.position_mode}) on {self.exchange_id}: {e}"
            )

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
            BTC-USDT -> BTC/USDT:USDT (USDT futures on colon exchanges)
            ETH-USD -> ETH/USD:USD (USD futures on colon exchanges)

        Args:
            symbol: Symbol in format 'BTC-USD', 'BTC-USDT', etc.
            market_type: Optional market type override ('spot', 'future', 'swap')

        Returns:
            Normalized CCXT symbol
        """
        mtype = market_type or self.default_type

        # Replace dash with slash
        base_symbol = symbol.replace("-", "/")

        # For futures/swap, only append settlement currency for non-Binance exchanges
        if mtype in ("future", "swap") and self.exchange_id not in ("binance",):
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
            # Pass marginMode for exchanges that require it (e.g., OKX)
            params = {}
            if self.exchange_id == "okx":
                params["marginMode"] = self.margin_mode  # 'cross' or 'isolated'
            await exchange.set_leverage(int(leverage), symbol, params)
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

    def _sanitize_client_order_id(self, raw_id: str) -> str:
        """Sanitize client order id to satisfy exchange constraints.

        - Remove non-alphanumeric characters (safe for OKX 'clOrdId')
        - Truncate to 32 characters (common OKX limit)
        - If empty after sanitization, derive a short hash
        """
        safe = "".join(ch for ch in (raw_id or "") if ch.isalnum())
        if not safe:
            import hashlib

            safe = hashlib.sha1((raw_id or "").encode()).hexdigest()[:16]
        return safe[:32]

    def _build_order_params(self, inst: TradeInstruction, order_type: str) -> Dict:
        """Build exchange-specific order params with safe defaults.

        - Attach clientOrderId for idempotency where supported
        - Provide default time-in-force for limit orders
        - Provide reduceOnly defaults for derivatives
        - Provide tdMode for OKX if not specified
        """
        params: Dict = dict(inst.meta or {})

        exid = self.exchange_id

        # Idempotency / client order id (sanitize for OKX)
        raw_client_id = params.get("clientOrderId", inst.instruction_id)
        if raw_client_id:
            client_id = (
                self._sanitize_client_order_id(raw_client_id)
                if exid == "okx"
                else raw_client_id
            )
            params["clientOrderId"] = client_id

        # Default tdMode for OKX on all orders
        if exid == "okx":
            params.setdefault(
                "tdMode", "isolated" if self.margin_mode == "isolated" else "cross"
            )

        # Default time-in-force for limit orders
        if order_type == "limit":
            if exid == "binance":
                params.setdefault("timeInForce", "GTC")
            elif exid == "bybit":
                params.setdefault("time_in_force", "GoodTillCancel")

        # reduceOnly default for derivatives (oneway mode defaults to False)
        if exid in ("binance", "okx"):
            params.setdefault("reduceOnly", False)
        elif exid == "bybit":
            params.setdefault("reduce_only", False)

        # Enforce single-sided mode: strip positionSide/posSide if present
        try:
            mode = (self.position_mode or "oneway").lower()
            if mode in ("oneway", "single", "net"):
                removed = []
                if "positionSide" in params:
                    params.pop("positionSide", None)
                    removed.append("positionSide")
                if "posSide" in params:
                    params.pop("posSide", None)
                    removed.append("posSide")
                if removed:
                    logger.debug(
                        f"🧹 Oneway mode: stripped {removed} from order params"
                    )
        except Exception:
            pass

        return params

    async def _check_minimums(
        self,
        exchange: ccxt.Exchange,
        symbol: str,
        amount: float,
        price: Optional[float],
    ) -> Optional[str]:
        markets = getattr(exchange, "markets", {}) or {}
        market = markets.get(symbol, {})
        limits = market.get("limits") or {}

        # amount minimum
        min_amount = None
        amt_limits = limits.get("amount") or {}
        if amt_limits.get("min") is not None:
            try:
                min_amount = float(amt_limits["min"])
            except Exception:
                min_amount = None
        if min_amount is None:
            info = market.get("info") or {}
            min_sz = info.get("minSz")
            if min_sz is not None:
                try:
                    min_amount = float(min_sz)
                except Exception:
                    min_amount = None
        if min_amount is not None and amount < min_amount:
            return f"amount<{min_amount}"

        # notional minimum
        min_cost = None
        cost_limits = limits.get("cost") or {}
        if cost_limits.get("min") is not None:
            try:
                min_cost = float(cost_limits["min"])
            except Exception:
                min_cost = None
        if min_cost is not None:
            est_price = price
            if est_price is None and exchange.has.get("fetchTicker"):
                try:
                    ticker = await exchange.fetch_ticker(symbol)
                    est_price = float(
                        ticker.get("last")
                        or ticker.get("bid")
                        or ticker.get("ask")
                        or 0.0
                    )
                except Exception:
                    est_price = None
            if est_price and est_price > 0:
                notional = amount * est_price
                if notional < min_cost:
                    return f"notional<{min_cost}"
        return None

    async def _estimate_required_margin_okx(
        self,
        symbol: str,
        amount: float,
        price: Optional[float],
        leverage: Optional[float],
        exchange: ccxt.Exchange,
    ) -> Optional[float]:
        """Estimate initial margin required for an OKX derivatives open.

        If `symbol` is a derivatives contract and `amount` is in contracts (sz),
        multiply by the contract size (`contractSize` or `info.ctVal`) to convert
        to notional units before dividing by leverage.
        Falls back to ticker price when `price` is not provided.
        """
        try:
            lev = float(leverage or 1.0)
            if lev <= 0:
                lev = 1.0
            px = float(price or 0.0)
            if px <= 0:
                if exchange.has.get("fetchTicker"):
                    try:
                        ticker = await exchange.fetch_ticker(symbol)
                        px = float(
                            ticker.get("last")
                            or ticker.get("bid")
                            or ticker.get("ask")
                            or 0.0
                        )
                    except Exception:
                        px = 0.0
            if px <= 0:
                return None

            # Detect contract size if symbol is derivatives (OKX swap/futures)
            ct_val: Optional[float] = None
            try:
                market = (getattr(exchange, "markets", {}) or {}).get(symbol) or {}
                if market.get("contract"):
                    try:
                        ct_val = float(market.get("contractSize") or 0.0)
                    except Exception:
                        ct_val = None
                    if not ct_val:
                        info = market.get("info") or {}
                        try:
                            ct_val = float(info.get("ctVal") or 0.0)
                        except Exception:
                            ct_val = None
            except Exception:
                ct_val = None

            # If ct_val is present and amount is sz (contracts), convert to notional
            if ct_val and ct_val > 0:
                notional = amount * ct_val * px
            else:
                # Fallback: treat amount as base units
                notional = amount * px

            return notional / lev * 1.02
        except Exception:
            return None

    async def _get_free_usdt_okx(self, exchange: ccxt.Exchange) -> Optional[float]:
        """Read available USDT from OKX unified trading account.

        Explicitly queries trading balances and extracts free USDT.
        """
        try:
            bal = await exchange.fetch_balance({"type": "trading"})
            free = bal.get("free") or {}
            usdt = free.get("USDT")
            if usdt is None:
                # Fallback: some ccxt versions expose totals differently
                usdt = (bal.get("total") or {}).get("USDT")
            return float(usdt) if usdt is not None else 0.0
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch OKX trading balance: {e}")
            return None

    async def _estimate_required_margin_binance_linear(
        self,
        symbol: str,
        amount: float,
        price: Optional[float],
        leverage: Optional[float],
        exchange: ccxt.Exchange,
    ) -> Optional[float]:
        """Estimate initial margin for Binance USDT-M linear contracts.

        For USDT-M (linear), `amount` is base coin quantity.
        Approximation: notional = amount * price; initial_margin = notional / leverage.
        Adds a 2% buffer. If no price is provided, falls back to ticker last/bid/ask.
        """
        try:
            lev = float(leverage or 1.0)
            if lev <= 0:
                lev = 1.0
            px = float(price or 0.0)
            if px <= 0:
                if exchange.has.get("fetchTicker"):
                    try:
                        ticker = await exchange.fetch_ticker(symbol)
                        px = float(
                            ticker.get("last")
                            or ticker.get("bid")
                            or ticker.get("ask")
                            or 0.0
                        )
                    except Exception:
                        px = 0.0
            if px <= 0:
                return None
            notional = amount * px
            return notional / lev * 1.02
        except Exception:
            return None

    async def _get_free_usdt_binance(self, exchange: ccxt.Exchange) -> Optional[float]:
        """Fetch available USDT balance from Binance USDT-M futures account."""
        try:
            bal = await exchange.fetch_balance({"type": "future"})
            free = bal.get("free") or {}
            usdt = free.get("USDT")
            if usdt is None:
                usdt = (bal.get("total") or {}).get("USDT")
            return float(usdt) if usdt is not None else 0.0
        except Exception as e:
            logger.warning(f"Could not fetch Binance futures balance: {e}")
            return None

    async def execute(
        self,
        instructions: List[TradeInstruction],
        market_snapshot: Optional[MarketSnapShotType] = None,
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
            side = (
                getattr(inst, "side", None)
                or derive_side_from_action(getattr(inst, "action", None))
                or TradeSide.BUY
            )
            logger.info(
                f"  📤 Processing {inst.instrument.symbol} {side.value} qty={inst.quantity}"
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
                        side=side,
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
        # Dispatch by high-level action if provided (prefer structured field)
        action = (inst.action.value if getattr(inst, "action", None) else None) or str(
            (inst.meta or {}).get("action") or ""
        ).lower()
        if action == "open_long":
            return await self._exec_open_long(inst, exchange)
        if action == "open_short":
            return await self._exec_open_short(inst, exchange)
        if action == "close_long":
            return await self._exec_close_long(inst, exchange)
        if action == "close_short":
            return await self._exec_close_short(inst, exchange)
        if action == "noop":
            return await self._exec_noop(inst)

        # Fallback to generic submission
        return await self._submit_order(inst, exchange)

    async def _submit_order(
        self,
        inst: TradeInstruction,
        exchange: ccxt.Exchange,
        params_override: Optional[Dict] = None,
    ) -> TxResult:
        # Normalize symbol for CCXT
        symbol = self._normalize_symbol(inst.instrument.symbol)

        # Resolve symbol against loaded markets with simple fallbacks
        markets = getattr(exchange, "markets", {}) or {}
        if symbol not in markets:
            # Try alternate format without/with colon
            if ":" in symbol:
                alt = symbol.split(":")[0]
                if alt in markets:
                    symbol = alt
            else:
                parts = symbol.split("/")
                if len(parts) == 2:
                    base, quote = parts
                    alt = f"{base}/{quote}:{quote}"
                    if alt in markets:
                        symbol = alt
                    else:
                        # Try USD<->USDT swap
                        if quote in ("USD", "USDT"):
                            alt_quote = "USDT" if quote == "USD" else "USD"
                            alt2 = f"{base}/{alt_quote}"
                            alt3 = f"{base}/{alt_quote}:{alt_quote}"
                            if alt2 in markets:
                                symbol = alt2
                            elif alt3 in markets:
                                symbol = alt3

        # Setup leverage and margin mode
        await self._setup_leverage(symbol, inst.leverage, exchange)
        await self._setup_margin_mode(symbol, exchange)

        # Map instruction to CCXT parameters
        local_side = (
            getattr(inst, "side", None)
            or derive_side_from_action(getattr(inst, "action", None))
            or TradeSide.BUY
        )
        side = "buy" if local_side == TradeSide.BUY else "sell"
        order_type = "limit" if inst.price_mode == PriceMode.LIMIT else "market"
        amount = float(inst.quantity)
        price = float(inst.limit_price) if inst.limit_price else None

        # For OKX derivatives, amount must be in contracts; convert from base units if needed
        try:
            market = (getattr(exchange, "markets", {}) or {}).get(symbol) or {}
            if self.exchange_id == "okx" and market.get("contract"):
                try:
                    ct_val = float(market.get("contractSize") or 0.0)
                except Exception:
                    ct_val = None
                if not ct_val:
                    info = market.get("info") or {}
                    try:
                        ct_val = float(info.get("ctVal") or 0.0)
                    except Exception:
                        ct_val = None
                if ct_val and ct_val > 0:
                    amount = amount / ct_val
        except Exception:
            pass

        # Align precision if supported
        try:
            amount = float(exchange.amount_to_precision(symbol, amount))
        except Exception:
            pass
        if price is not None:
            try:
                price = float(exchange.price_to_precision(symbol, price))
            except Exception:
                pass

        # Reject orders below exchange minimums (do not lift to min)
        try:
            reject_reason = await self._check_minimums(exchange, symbol, amount, price)
        except Exception as e:
            logger.warning(f"⚠️ Minimum check failed for {symbol}: {e}")
            reject_reason = f"minimum_check_failed:{e}"
        if reject_reason is not None:
            logger.warning(f"  🚫 Skipping order due to {reject_reason}")
            return TxResult(
                instruction_id=inst.instruction_id,
                instrument=inst.instrument,
                side=local_side,
                requested_qty=float(inst.quantity),
                filled_qty=0.0,
                status=TxStatus.REJECTED,
                reason=reject_reason,
                meta=inst.meta,
            )

        # OKX trading account margin precheck for open orders
        if self.exchange_id == "okx":
            try:
                # Determine open vs close intent from default reduceOnly flags
                provisional = self._build_order_params(inst, order_type)
                is_close = bool(
                    provisional.get("reduceOnly") or provisional.get("reduce_only")
                )
                if not is_close:
                    required = await self._estimate_required_margin_okx(
                        symbol, amount, price, inst.leverage, exchange
                    )
                    free_usdt = await self._get_free_usdt_okx(exchange)
                    if (
                        required is not None
                        and free_usdt is not None
                        and free_usdt < required
                    ):
                        reject_reason = f"insufficient_margin:need~{required:.6f}USDT,free~{free_usdt:.6f}USDT"
                        logger.warning(f"  🚫 Skipping order due to {reject_reason}")
                        return TxResult(
                            instruction_id=inst.instruction_id,
                            instrument=inst.instrument,
                            side=local_side,
                            requested_qty=float(inst.quantity),
                            filled_qty=0.0,
                            status=TxStatus.REJECTED,
                            reason=reject_reason,
                            meta=inst.meta,
                        )
            except Exception as e:
                logger.warning(
                    f"⚠️ OKX margin precheck failed, proceeding without precheck: {e}"
                )

        # Binance USDT-M linear futures margin precheck for open orders
        if self.exchange_id == "binance":
            try:
                provisional = self._build_order_params(inst, order_type)
                is_close = bool(
                    provisional.get("reduceOnly") or provisional.get("reduce_only")
                )
                if not is_close:
                    market = (getattr(exchange, "markets", {}) or {}).get(symbol) or {}
                    is_contract = bool(market.get("contract"))
                    is_linear = bool(market.get("linear"))
                    if not is_linear:
                        settle = str(market.get("settle") or "").upper()
                        is_linear = bool(is_contract and settle == "USDT")
                    if is_contract and is_linear:
                        required = await self._estimate_required_margin_binance_linear(
                            symbol, amount, price, inst.leverage, exchange
                        )
                        free_usdt = await self._get_free_usdt_binance(exchange)
                        if (
                            required is not None
                            and free_usdt is not None
                            and free_usdt < required
                        ):
                            reject_reason = f"insufficient_margin_binance_usdtm:need~{required:.6f}USDT,free~{free_usdt:.6f}USDT"
                            logger.warning(
                                f"  🚫 Skipping order due to {reject_reason}"
                            )
                            return TxResult(
                                instruction_id=inst.instruction_id,
                                instrument=inst.instrument,
                                side=local_side,
                                requested_qty=float(inst.quantity),
                                filled_qty=0.0,
                                status=TxStatus.REJECTED,
                                reason=reject_reason,
                                meta=inst.meta,
                            )
            except Exception as e:
                logger.warning(
                    f"⚠️ Binance USDT-M margin precheck failed, proceeding without precheck: {e}"
                )

        # Build order params with exchange-specific defaults
        params = self._build_order_params(inst, order_type)
        if params_override:
            try:
                params.update(params_override)
            except Exception:
                pass

        # Enforce single-sided mode again after overrides
        try:
            mode = (self.position_mode or "oneway").lower()
            if mode in ("oneway", "single", "net"):
                removed = []
                if "positionSide" in params:
                    params.pop("positionSide", None)
                    removed.append("positionSide")
                if "posSide" in params:
                    params.pop("posSide", None)
                    removed.append("posSide")
                if removed:
                    logger.debug(
                        f"🧹 Oneway mode (post-override): stripped {removed} from order params"
                    )
        except Exception:
            pass

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
            side=local_side,
            requested_qty=amount,
            filled_qty=filled_qty,
            avg_exec_price=avg_price if avg_price > 0 else None,
            slippage_bps=slippage_bps,
            fee_cost=fee_cost if fee_cost > 0 else None,
            leverage=inst.leverage,
            status=status,
            reason=order.get("status") if status != TxStatus.FILLED else None,
            meta=inst.meta,
        )

    async def _exec_open_long(
        self, inst: TradeInstruction, exchange: ccxt.Exchange
    ) -> TxResult:
        # Ensure we do not mark reduceOnly on open
        overrides = {"reduceOnly": False, "reduce_only": False}
        return await self._submit_order(inst, exchange, overrides)

    async def _exec_open_short(
        self, inst: TradeInstruction, exchange: ccxt.Exchange
    ) -> TxResult:
        overrides = {"reduceOnly": False, "reduce_only": False}
        return await self._submit_order(inst, exchange, overrides)

    async def _exec_close_long(
        self, inst: TradeInstruction, exchange: ccxt.Exchange
    ) -> TxResult:
        # Force reduceOnly flags for closes
        overrides = {"reduceOnly": True, "reduce_only": True}
        return await self._submit_order(inst, exchange, overrides)

    async def _exec_close_short(
        self, inst: TradeInstruction, exchange: ccxt.Exchange
    ) -> TxResult:
        overrides = {"reduceOnly": True, "reduce_only": True}
        return await self._submit_order(inst, exchange, overrides)

    async def _exec_noop(self, inst: TradeInstruction) -> TxResult:
        # No-op: return a rejected result with reason
        side = (
            getattr(inst, "side", None)
            or derive_side_from_action(getattr(inst, "action", None))
            or TradeSide.BUY
        )
        return TxResult(
            instruction_id=inst.instruction_id,
            instrument=inst.instrument,
            side=side,
            requested_qty=float(inst.quantity),
            filled_qty=0.0,
            status=TxStatus.REJECTED,
            reason="noop",
            meta=inst.meta,
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
    market_type: str = "swap",
    margin_mode: str = "cross",
    position_mode: str = "oneway",
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
        position_mode: Optional position mode ('oneway' or 'hedged')
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
        ...     position_mode='oneway',
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
        position_mode=position_mode,
        ccxt_options=ccxt_options,
    )

    # Pre-load markets to validate connection
    await gateway._get_exchange()

    return gateway
