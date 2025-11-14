import os
from typing import Dict, Optional

import ccxt.pro as ccxtpro
import httpx
from loguru import logger


def extract_price_map(market_snapshot: Dict) -> Dict[str, float]:
    """Extract a simple symbol -> price mapping from market snapshot structure.

    The market snapshot structure is:
    {
      "BTC/USDT:USDT": {
        "price": {ticker dict with "last", "close", etc.},
        "open_interest": {...},
        "funding_rate": {...}
      }
    }

    Returns:
        Dict[symbol, last_price] for internal use in quantity normalization.
    """
    price_map: Dict[str, float] = {}
    for symbol, data in market_snapshot.items():
        if not isinstance(data, dict):
            continue
        price_obj = data.get("price")
        if isinstance(price_obj, dict):
            # Prefer "last" over "close" for real-time pricing
            last_price = price_obj.get("last") or price_obj.get("close")
            if last_price is not None:
                try:
                    price_map[symbol] = float(last_price)
                except (ValueError, TypeError):
                    logger.warning(
                        "Failed to parse price for {}: {}", symbol, last_price
                    )
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
