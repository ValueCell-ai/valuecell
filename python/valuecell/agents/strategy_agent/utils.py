from typing import Dict

import ccxt.pro as ccxtpro
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
