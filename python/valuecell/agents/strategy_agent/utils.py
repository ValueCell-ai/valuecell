import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import ccxt.pro as ccxtpro
import httpx
from loguru import logger

from .models import FeatureVector


def get_current_timestamp_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


async def fetch_free_cash_from_gateway(execution_gateway, symbols: list[str]) -> float:
    """Fetch exchange balance via `execution_gateway.fetch_balance()` and
    aggregate free cash for the given `symbols` (quote currencies).

    Returns aggregated free cash as float. Returns 0.0 on error or when
    balance shape cannot be parsed.
    """
    try:
        if not hasattr(execution_gateway, "fetch_balance"):
            return 0.0
        balance = await execution_gateway.fetch_balance()
    except Exception:
        return 0.0

    free_map: dict[str, float] = {}
    try:
        free_section = balance.get("free") if isinstance(balance, dict) else None
    except Exception:
        free_section = None

    if isinstance(free_section, dict):
        free_map = {str(k).upper(): float(v or 0.0) for k, v in free_section.items()}
    else:
        iterable = balance.items() if isinstance(balance, dict) else []
        for k, v in iterable:
            if isinstance(v, dict) and "free" in v:
                try:
                    free_map[str(k).upper()] = float(v.get("free") or 0.0)
                except Exception:
                    continue

    # collect quote currencies from configured symbols
    quotes: list[str] = []
    for sym in symbols or []:
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

    return float(free_cash)


def extract_price_map(features: List[FeatureVector]) -> Dict[str, float]:
    """Extract symbol -> price map from market snapshot feature vectors."""

    price_map: Dict[str, float] = {}

    for item in features:
        if not isinstance(item, FeatureVector):
            continue

        meta = item.meta or {}
        group_key = meta.get("group_by_key")
        if group_key != "market_snapshot":
            continue

        instrument = getattr(item, "instrument", None)
        symbol = getattr(instrument, "symbol", None)
        if not symbol:
            continue

        values = item.values or {}
        price = (
            values.get("price.last")
            or values.get("price.close")
            or values.get("price.mark")
            or values.get("funding.mark_price")
        )
        if price is None:
            continue

        try:
            price_map[symbol] = float(price)
        except (TypeError, ValueError):
            logger.warning("Failed to parse feature price for {}", symbol)

    return price_map


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol format for CCXT.

    Examples:
        BTC-USD -> BTC/USD:USD (spot)
        BTC-USDT -> BTC/USDT:USDT (USDT futures on colon exchanges)
        ETH-USD -> ETH/USD:USD (USD futures on colon exchanges)

    Args:
        symbol: Symbol in format 'BTC-USD', 'BTC-USDT', etc.

    Returns:
        Normalized CCXT symbol
    """
    # Replace dash with slash
    base_symbol = symbol.replace("-", "/")

    if ":" not in base_symbol:
        parts = base_symbol.split("/")
        if len(parts) == 2:
            base_symbol = f"{parts[0]}/{parts[1]}:{parts[1]}"

    return base_symbol


def get_exchange_cls(exchange_id: str):
    """Get CCXT exchange class by exchange ID."""

    exchange_cls = getattr(ccxtpro, exchange_id, None)
    if exchange_cls is None:
        raise RuntimeError(f"Exchange '{exchange_id}' not found in ccxt.pro")
    return exchange_cls


async def send_discord_message(
    content: str,
    webhook_url: Optional[str] = None,
    *,
    raise_for_status: bool = True,
    timeout: float = 10.0,
) -> str:
    """Send a message to Discord via webhook asynchronously.

    Reads the webhook URL from the environment variable
    `STRATEGY_AGENT_DISCORD_WEBHOOK_URL` when `webhook_url` is not provided.

    Args:
        content: The message content to send.
        webhook_url: Optional webhook URL to override the environment variable.
        raise_for_status: If True, raise on non-2xx responses.
        timeout: Request timeout in seconds.

    Returns:
        The response body as text.

    Raises:
        ValueError: If no webhook URL is provided or available in env.
        ImportError: If `httpx` is not installed.
        httpx.HTTPStatusError: If `raise_for_status` is True and the response is an HTTP error.
    """
    if webhook_url is None:
        webhook_url = os.getenv("STRATEGY_AGENT_DISCORD_WEBHOOK_URL")

    if not webhook_url:
        raise ValueError(
            "Discord webhook URL not provided and STRATEGY_AGENT_DISCORD_WEBHOOK_URL is not set"
        )

    headers = {
        "Accept": "text",
        "Content-Type": "application/json",
    }
    payload = {"content": content}

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(webhook_url, headers=headers, json=payload)
        if raise_for_status:
            resp.raise_for_status()
        return resp.text
