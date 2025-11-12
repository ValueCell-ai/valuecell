import ccxt.pro as ccxtpro


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
