"""OKX exchange adapter for live trading (spot and contracts)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

from okx.Account import AccountAPI
from okx.MarketData import MarketAPI
from okx.PublicData import PublicAPI
from okx.Trade import TradeAPI

from .base_exchange import ExchangeBase, ExchangeType, Order, OrderStatus

logger = logging.getLogger(__name__)


class OKXExchangeError(RuntimeError):
    """Raised for recoverable OKX-related failures."""


class OKXExchange(ExchangeBase):
    """Exchange adapter for OKX via the official SDK.

    Supports both SPOT and CONTRACTS (e.g., SWAP). Default is contracts mode.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        passphrase: str,
        *,
        network: str = "paper",
        # Default to contracts trading mode (cross) instead of spot cash
        margin_mode: str = "cross",
        inst_type: str = "SWAP",
        use_server_time: bool = False,
        domain: str = "https://www.okx.com",
    ) -> None:
        super().__init__(ExchangeType.OKX)

        if not (api_key and api_secret and passphrase):
            raise OKXExchangeError("OKX API key/secret/passphrase must be provided")

        normalized_network = (network or "paper").lower()
        # OKX SDK flag semantics: "1" => demo/paper, "0" => live/mainnet
        self._flag = "1" if normalized_network in {"paper", "demo", "testnet"} else "0"
        self.margin_mode = (
            margin_mode or ("cash" if (inst_type or "").upper() == "SPOT" else "cross")
        ).lower()
        self.inst_type = (inst_type or "SWAP").upper()
        self.use_server_time = use_server_time
        self.domain = domain

        self._trade_client = TradeAPI(
            api_key,
            api_secret,
            passphrase,
            use_server_time=self.use_server_time,
            flag=self._flag,
            domain=self.domain,
        )
        self._account_client = AccountAPI(
            api_key,
            api_secret,
            passphrase,
            use_server_time=self.use_server_time,
            flag=self._flag,
            domain=self.domain,
        )
        self._market_client = MarketAPI(
            api_key,
            api_secret,
            passphrase,
            use_server_time=self.use_server_time,
            flag=self._flag,
            domain=self.domain,
        )
        self._public_client = PublicAPI(
            api_key,
            api_secret,
            passphrase,
            use_server_time=self.use_server_time,
            flag=self._flag,
            domain=self.domain,
        )

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        try:
            await asyncio.to_thread(self._account_client.get_account_balance)
            self.is_connected = True
            logger.info(
                "Connected to OKX (%s mode)", "paper" if self._flag == "1" else "live"
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to connect to OKX: %s", exc)
            raise OKXExchangeError("Unable to connect to OKX") from exc

    async def disconnect(self) -> bool:
        self.is_connected = False
        return True

    async def validate_connection(self) -> bool:
        try:
            await asyncio.to_thread(self._account_client.get_account_config)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("OKX connection validation failed: %s", exc)
            self.is_connected = False
            return False

    # ------------------------------------------------------------------
    # Account information
    # ------------------------------------------------------------------

    async def get_balance(self) -> Dict[str, float]:
        response = await asyncio.to_thread(self._account_client.get_account_balance)
        return self._parse_balance(response)

    async def get_asset_balance(self, asset: str) -> float:
        balances = await self.get_balance()
        return balances.get(asset.upper(), 0.0)

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    async def get_current_price(self, symbol: str) -> float:
        inst_id = self.normalize_symbol(symbol)
        response = await asyncio.to_thread(self._market_client.get_ticker, inst_id)
        data = self._extract_first(response)
        if not data:
            raise OKXExchangeError(f"No ticker data returned for {inst_id}")
        return float(data.get("last", data.get("lastPx", 0.0)))

    async def get_24h_ticker(self, symbol: str) -> Dict[str, Any]:
        inst_id = self.normalize_symbol(symbol)
        response = await asyncio.to_thread(self._market_client.get_ticker, inst_id)
        data = self._extract_first(response) or {}
        return {
            "symbol": inst_id,
            "last": self._safe_float(data.get("last", data.get("lastPx"))),
            "high_24h": self._safe_float(data.get("high24h")),
            "low_24h": self._safe_float(data.get("low24h")),
            "volume_24h": self._safe_float(data.get("vol24h")),
            "best_bid": self._safe_float(data.get("bidPx")),
            "best_ask": self._safe_float(data.get("askPx")),
        }

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        order_type: str = "limit",
        **kwargs: Any,
    ) -> Order:
        inst_id = self.normalize_symbol(symbol)
        cloid = kwargs.get("client_order_id") or uuid.uuid4().hex
        ord_type = "market" if order_type == "market" or price is None else "limit"
        px_value = "" if ord_type == "market" else f"{price:.8f}"

        payload = {
            "instId": inst_id,
            "tdMode": self.margin_mode,
            "side": side.lower(),
            "ordType": ord_type,
            "sz": f"{quantity:.8f}",
            "clOrdId": cloid,
        }
        # tgtCcy is only applicable for SPOT orders
        if self.inst_type == "SPOT":
            payload["tgtCcy"] = "base_ccy"
        if px_value:
            payload["px"] = px_value

        try:
            response = await asyncio.to_thread(
                self._trade_client.place_order, **payload
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("OKX order submission failed: %s", exc)
            raise OKXExchangeError("Order submission failed") from exc

        order_data = self._extract_first(response)
        if not order_data:
            logger.error("Invalid response from OKX place_order: %s", response)
            raise OKXExchangeError("Order submission returned no data")

        status = self._map_order_state(order_data.get("state"))
        filled_px = self._safe_float(order_data.get("avgPx")) or self._safe_float(
            px_value
        )

        order = Order(
            order_id=order_data.get("ordId", cloid),
            symbol=symbol,
            side=side.lower(),
            quantity=quantity,
            price=filled_px or 0.0,
            order_type=ord_type,
            trade_type=kwargs.get("trade_type"),
        )
        order.status = status
        if filled_px:
            order.filled_price = filled_px
            order.filled_quantity = quantity if status == OrderStatus.FILLED else 0.0
        self.orders[order.order_id] = order
        self.order_history.append(order)
        return order

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        inst_id = self.normalize_symbol(symbol)
        try:
            await asyncio.to_thread(
                self._trade_client.cancel_order, inst_id, ordId=order_id
            )
            if order_id in self.orders:
                self.orders[order_id].status = OrderStatus.CANCELLED
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to cancel OKX order %s: %s", order_id, exc)
            return False

    async def get_order_status(self, symbol: str, order_id: str) -> OrderStatus:
        inst_id = self.normalize_symbol(symbol)
        try:
            response = await asyncio.to_thread(
                self._trade_client.get_order, inst_id, ordId=order_id
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to query OKX order %s: %s", order_id, exc)
            return self.orders.get(
                order_id, Order(order_id, symbol, "buy", 0, 0)
            ).status

        order_data = self._extract_first(response)
        status = (
            self._map_order_state(order_data.get("state"))
            if order_data
            else OrderStatus.PENDING
        )
        if order_id in self.orders:
            self.orders[order_id].status = status
        return status

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        inst_id = self.normalize_symbol(symbol) if symbol else ""
        response = await asyncio.to_thread(
            self._trade_client.get_order_list, self.inst_type, instId=inst_id
        )
        orders: List[Order] = []
        for item in response.get("data", []):
            inst = item.get("instId")
            client_symbol = self._from_okx_symbol(inst)
            order = Order(
                order_id=item.get("ordId") or item.get("clOrdId", uuid.uuid4().hex),
                symbol=client_symbol,
                side=item.get("side", "buy"),
                quantity=self._safe_float(item.get("sz"), default=0.0),
                price=self._safe_float(item.get("px"), default=0.0),
            )
            order.status = self._map_order_state(item.get("state"))
            orders.append(order)
        return orders

    async def get_order_history(
        self, symbol: Optional[str] = None, limit: int = 100
    ) -> List[Order]:
        inst_id = self.normalize_symbol(symbol) if symbol else ""
        response = await asyncio.to_thread(
            self._trade_client.get_orders_history,
            self.inst_type,
            instId=inst_id,
            limit=str(limit),
        )
        orders: List[Order] = []
        for item in response.get("data", []):
            inst = item.get("instId")
            client_symbol = self._from_okx_symbol(inst)
            order = Order(
                order_id=item.get("ordId") or item.get("clOrdId", uuid.uuid4().hex),
                symbol=client_symbol,
                side=item.get("side", "buy"),
                quantity=self._safe_float(item.get("sz"), default=0.0),
                price=self._safe_float(
                    item.get("fillPx") or item.get("avgPx"), default=0.0
                ),
            )
            order.status = self._map_order_state(item.get("state"))
            order.filled_quantity = self._safe_float(item.get("accFillSz"), default=0.0)
            order.filled_price = self._safe_float(
                item.get("avgPx"), default=order.price
            )
            orders.append(order)
        return orders

    # ------------------------------------------------------------------
    # Position helpers
    # ------------------------------------------------------------------

    async def get_open_positions(
        self, symbol: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        # Contracts mode: query positions; Spot mode: derive from balances
        if self.inst_type != "SPOT":
            try:
                response = await asyncio.to_thread(
                    self._account_client.get_positions, self.inst_type
                )
                positions: Dict[str, Dict[str, Any]] = {}
                for item in response.get("data", []) or []:
                    inst = item.get("instId")
                    client_symbol = self._from_okx_symbol(inst)
                    if symbol and client_symbol != symbol:
                        continue
                    qty = (
                        self._safe_float(
                            item.get("pos")
                            or item.get("posSz")
                            or item.get("availPos"),
                            default=0.0,
                        )
                        or 0.0
                    )
                    entry_px = self._safe_float(item.get("avgPx"), default=0.0) or 0.0
                    unreal_pnl = self._safe_float(item.get("upl"), default=0.0) or 0.0
                    positions[client_symbol] = {
                        "quantity": qty,
                        "entry_price": entry_px,
                        "unrealized_pnl": unreal_pnl,
                    }
                return positions
            except Exception:  # noqa: BLE001 - fallback to spot-like behavior
                pass

        balances = await self.get_balance()
        # Spot balances act as positions for cash mode; return filtered view
        positions: Dict[str, Dict[str, Any]] = {}
        for asset, balance in balances.items():
            if asset in {"USD", "USDT", "USDC", "withdrawable_usd"}:
                continue
            client_symbol = f"{asset}-USDT"
            if symbol and client_symbol != symbol:
                continue
            positions[client_symbol] = {
                "quantity": balance,
                "entry_price": 0.0,
                "unrealized_pnl": 0.0,
            }
        return positions

    async def get_position_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        positions = await self.get_open_positions(symbol)
        return positions.get(symbol)

    async def execute_buy(
        self,
        symbol: str,
        quantity: float,
        price: Optional[float] = None,
        **kwargs: Any,
    ) -> Optional[Order]:
        order = await self.place_order(
            symbol=symbol,
            side="buy",
            quantity=quantity,
            price=price,
            order_type="market" if price is None else "limit",
            **kwargs,
        )
        return order

    async def execute_sell(
        self,
        symbol: str,
        quantity: float,
        price: Optional[float] = None,
        **kwargs: Any,
    ) -> Optional[Order]:
        order = await self.place_order(
            symbol=symbol,
            side="sell",
            quantity=quantity,
            price=price,
            order_type="market" if price is None else "limit",
            **kwargs,
        )
        return order

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def normalize_symbol(self, symbol: str) -> str:
        clean = symbol.replace("/", "-").upper()
        base, _, quote = clean.partition("-")
        if self.inst_type == "SPOT":
            if not quote:
                return clean
            if quote == "USD":
                quote = "USDT"
            return f"{base}-{quote}"
        # Contracts (default): map to USDT-margined perpetual swap by default
        return f"{base}-USDT-SWAP"

    def _from_okx_symbol(self, inst_id: Optional[str]) -> str:
        if not inst_id:
            return ""
        parts = inst_id.upper().split("-")
        if not parts:
            return ""
        base = parts[0]
        quote = parts[1] if len(parts) > 1 else "USD"
        # Strip contract suffix like SWAP/QUARTER/NEXT_QUARTER if present
        if len(parts) > 2:
            quote = parts[1]
        if quote == "USDT":
            quote = "USD"
        return f"{base}-{quote}"

    async def get_fee_tier(self) -> Dict[str, float]:
        try:
            response = await asyncio.to_thread(
                self._account_client.get_fee_rates, self.inst_type
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to fetch OKX fee rates: %s", exc)
            return {"maker": 0.0, "taker": 0.0}

        data = self._extract_first(response) or {}
        return {
            "maker": self._safe_float(data.get("maker"), default=0.0) or 0.0,
            "taker": self._safe_float(data.get("taker"), default=0.0) or 0.0,
        }

    async def get_trading_limits(self, symbol: str) -> Dict[str, float]:
        inst_id = self.normalize_symbol(symbol)
        try:
            response = await asyncio.to_thread(
                self._public_client.get_instruments, self.inst_type, instId=inst_id
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to fetch OKX instrument metadata: %s", exc)
            return {}

        data = self._extract_first(response) or {}
        min_sz = self._safe_float(data.get("minSz"))
        lot_sz = self._safe_float(data.get("lotSz"))
        return {
            "min_quantity": min_sz or 0.0,
            "lot_size": lot_sz or 0.0,
            "tick_size": self._safe_float(data.get("tickSz"), default=0.0) or 0.0,
        }

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_first(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        data = response.get("data") if isinstance(response, dict) else None
        if isinstance(data, list) and data:
            return data[0]
        return None

    @staticmethod
    def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        if value in (None, ""):
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _map_order_state(state: Optional[str]) -> OrderStatus:
        if not state:
            return OrderStatus.PENDING
        state = state.lower()
        if state in {"filled", "canceledfilled", "partially_filled"}:
            return OrderStatus.FILLED
        if state in {"live", "partially_filled_not_canceled"}:
            return OrderStatus.PENDING
        if state in {"canceled", "cancelled"}:
            return OrderStatus.CANCELLED
        if state in {"rejected"}:
            return OrderStatus.REJECTED
        return OrderStatus.PENDING

    def _parse_balance(self, response: Dict[str, Any]) -> Dict[str, float]:
        balances: Dict[str, float] = {}
        for account in response.get("data", []):
            total_eq = account.get("totalEq")
            if total_eq is not None:
                balances["USD"] = float(total_eq)
            for detail in account.get("details", []):
                currency = detail.get("ccy")
                if not currency:
                    continue
                total = detail.get("eq") or detail.get("cashBal") or "0"
                try:
                    balances[currency.upper()] = float(total)
                except (TypeError, ValueError):
                    continue
        return balances
