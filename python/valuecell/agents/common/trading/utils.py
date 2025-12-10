import asyncio
import os
import random
from typing import Dict, List, Optional, Tuple

import ccxt.pro as ccxtpro
import httpx
from loguru import logger

from valuecell.agents.common.trading.constants import (
    FEATURE_GROUP_BY_KEY,
    FEATURE_GROUP_BY_MARKET_SNAPSHOT,
)
from valuecell.agents.common.trading.models import (
    FeatureVector,
    InstrumentRef,
    PositionSnapshot,
    TradeType,
)


async def fetch_free_cash_from_gateway(
    execution_gateway, symbols: list[str], retry_cnt: int = 0, max_retries: int = 3
) -> Tuple[float, float]:
    """Fetch exchange balance via `execution_gateway.fetch_balance()` and
    aggregate free cash for the given `symbols` (quote currencies).

    Returns aggregated free cash as float. Returns 0.0 on error or when
    balance shape cannot be parsed.
    """
    logger.info("Fetching exchange balance for LIVE trading mode")
    try:
        if not hasattr(execution_gateway, "fetch_balance"):
            raise AttributeError(
                f"Execution gateway {execution_gateway.__class__.__name__} "
                "does not implement the required 'fetch_balance' method."
            )
        balance = await execution_gateway.fetch_balance()
    except Exception as e:
        if retry_cnt < max_retries:
            logger.warning(
                f"Failed to fetch free cash from exchange, retrying... ({retry_cnt + 1}/{max_retries})"
            )
            await asyncio.sleep(
                random.uniform(retry_cnt, retry_cnt + 1)
            )  # jitter to prevent mass retry at the same time
            return await fetch_free_cash_from_gateway(
                execution_gateway, symbols, retry_cnt + 1, max_retries
            )
        # Propagate after exhausting retries so upstream can keep cached portfolio
        logger.error(
            f"Failed to fetch free cash from exchange after {max_retries} retries.",
            exception=e,
        )
        raise

    logger.info(f"Raw balance response: {balance}")
    free_map: dict[str, float] = {}
    # ccxt balance may be shaped as: {'free': {...}, 'used': {...}, 'total': {...}}
    try:
        free_section = balance.get("free") if isinstance(balance, dict) else None
    except Exception:
        free_section = None

    if isinstance(free_section, dict):
        free_map = {str(k).upper(): float(v or 0.0) for k, v in free_section.items()}
    else:
        # fallback: per-ccy dicts: balance['USDT'] = {'free': x, 'used': y, 'total': z}
        iterable = balance.items() if isinstance(balance, dict) else []
        for k, v in iterable:
            if isinstance(v, dict) and "free" in v:
                try:
                    free_map[str(k).upper()] = float(v.get("free") or 0.0)
                except Exception:
                    continue

    # If balance structure is unrecognized, avoid returning zeros silently
    if not isinstance(balance, dict) or (not free_map and free_section is None):
        raise ValueError("Unrecognized balance response shape from exchange")

    logger.info(f"Parsed free balance map: {free_map}")
    # Derive quote currencies from symbols, fallback to common USD-stable quotes
    quotes: list[str] = []
    for sym in symbols or []:
        s = str(sym).upper()
        if "/" in s and len(s.split("/")) == 2:
            quotes.append(s.split("/")[1])
        elif "-" in s and len(s.split("-")) == 2:
            quotes.append(s.split("-")[1])

    # Deduplicate preserving order
    quotes = list(dict.fromkeys(quotes))
    logger.info(f"Quote currencies from symbols: {quotes}")

    free_cash = 0.0
    total_cash = 0.0

    # Sum up free and total cash from relevant quote currencies
    if quotes:
        for q in quotes:
            free_cash += float(free_map.get(q, 0.0) or 0.0)
            # Try to find total/equity in balance if available (often 'total' dict in CCXT)
            # Hyperliquid/CCXT structure: balance[q]['total']
            q_data = balance.get(q)
            if isinstance(q_data, dict):
                total_cash += float(q_data.get("total", 0.0) or 0.0)
            else:
                # Fallback if structure is flat or missing
                total_cash += float(free_map.get(q, 0.0) or 0.0)
    else:
        for q in ("USDT", "USD", "USDC"):
            free_cash += float(free_map.get(q, 0.0) or 0.0)
            q_data = balance.get(q)
            if isinstance(q_data, dict):
                total_cash += float(q_data.get("total", 0.0) or 0.0)
            else:
                total_cash += float(free_map.get(q, 0.0) or 0.0)

    logger.debug(
        f"Synced balance from exchange: free_cash={free_cash}, total_cash={total_cash}, quotes={quotes}"
    )

    return float(free_cash), float(total_cash)


async def fetch_positions_from_gateway(
    execution_gateway, retry_cnt: int = 0, max_retries: int = 3
) -> Dict[str, PositionSnapshot]:
    """Fetch positions from exchange."""
    logger.info("Fetching positions for LIVE trading mode")
    try:
        if not hasattr(execution_gateway, "fetch_positions"):
            raise AttributeError(
                f"Execution gateway {execution_gateway.__class__.__name__} "
                "does not implement the required 'fetch_positions' method."
            )
        raw_positions = await execution_gateway.fetch_positions()
    except Exception as e:
        if retry_cnt < max_retries:
            logger.warning(
                f"Failed to fetch positions from exchange, retrying... ({retry_cnt + 1}/{max_retries})"
            )
            await asyncio.sleep(
                random.uniform(retry_cnt, retry_cnt + 1)
            )  # jitter to prevent mass retry at the same time
            return await fetch_positions_from_gateway(
                execution_gateway, retry_cnt + 1, max_retries
            )
        logger.error(
            f"Failed to fetch positions from exchange after {max_retries} retries.",
            exception=e,
        )
        raise e

    logger.debug(f"Raw positions response: {raw_positions}")
    positions = {}
    for position in raw_positions:
        if "symbol" in position:
            symbol = position.get("symbol").split(":")[0]
            position = PositionSnapshot(
                instrument=InstrumentRef(
                    exchange_id=execution_gateway.exchange_id,
                    symbol=symbol,
                ),
                quantity=(
                    position.get("contracts")
                    if position.get("side") == "long"
                    else -position.get("contracts")
                ),
                avg_price=position.get("entryPrice"),
                mark_price=position.get("markPrice"),
                unrealized_pnl=position.get("unrealizedPnl"),
                notional=position.get("notional"),
                leverage=position.get("leverage") or 1,
                entry_ts=position.get("timestamp"),
                trade_type=(
                    TradeType.LONG
                    if position.get("side") == "long"
                    else TradeType.SHORT
                ),
            )
            if position.notional is not None and position.notional != 0:
                position.unrealized_pnl_pct = (
                    position.unrealized_pnl / position.notional
                )
            positions[symbol] = position
    logger.info(f"Fetched positions: {positions}")

    return positions


def extract_market_snapshot_features(
    features: List[FeatureVector],
) -> List[FeatureVector]:
    """Extract market snapshot feature vectors for a specific exchange.

    Args:
        features: List of FeatureVector objects.
    Returns:
        List of FeatureVector objects filtered by market snapshot group.
    """
    snapshot_features: List[FeatureVector] = []

    for item in features:
        if not isinstance(item, FeatureVector):
            continue

        meta = item.meta or {}
        group_key = meta.get(FEATURE_GROUP_BY_KEY)
        if group_key != FEATURE_GROUP_BY_MARKET_SNAPSHOT:
            continue

        snapshot_features.append(item)

    return snapshot_features


def extract_price_map(features: List[FeatureVector]) -> Dict[str, float]:
    """Extract symbol -> price map from market snapshot feature vectors."""

    price_map: Dict[str, float] = {}

    for item in features:
        if not isinstance(item, FeatureVector):
            continue

        meta = item.meta or {}
        group_key = meta.get(FEATURE_GROUP_BY_KEY)
        if group_key != FEATURE_GROUP_BY_MARKET_SNAPSHOT:
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


def prune_none(obj):
    """Recursively remove None, empty dict, and empty list values."""
    if isinstance(obj, dict):
        pruned = {k: prune_none(v) for k, v in obj.items() if v is not None}
        return {k: v for k, v in pruned.items() if v not in (None, {}, [])}
    if isinstance(obj, list):
        pruned = [prune_none(v) for v in obj]
        return [v for v in pruned if v not in (None, {}, [])]
    return obj


def extract_market_section(market_data: List[Dict]) -> Dict:
    """Extract decision-critical metrics from market feature entries."""

    compact: Dict[str, Dict] = {}
    for item in market_data:
        symbol = (item.get("instrument") or {}).get("symbol")
        if not symbol:
            continue

        values = item.get("values") or {}
        entry: Dict[str, float] = {}

        for feature_key, alias in (
            ("price.last", "last"),
            ("price.close", "close"),
            ("price.open", "open"),
            ("price.high", "high"),
            ("price.low", "low"),
            ("price.bid", "bid"),
            ("price.ask", "ask"),
            ("price.change_pct", "change_pct"),
            ("price.volume", "volume"),
        ):
            if feature_key in values and values[feature_key] is not None:
                entry[alias] = values[feature_key]

        if values.get("open_interest") is not None:
            entry["open_interest"] = values["open_interest"]

        if values.get("funding.rate") is not None:
            entry["funding_rate"] = values["funding.rate"]
        if values.get("funding.mark_price") is not None:
            entry["mark_price"] = values["funding.mark_price"]

        normalized = {k: v for k, v in entry.items() if v is not None}
        if normalized:
            compact[symbol] = normalized

    return compact


def group_features(features: List[FeatureVector]) -> Dict:
    """Organize features by grouping metadata and trim payload noise.

    Prefers the FeatureVector.meta group_by_key when present, otherwise
    falls back to the interval tag. This allows callers to introduce
    ad-hoc groupings (e.g., market snapshots) without overloading the
    interval field.
    """
    grouped: Dict[str, List] = {}

    for fv in features:
        data = fv.model_dump(mode="json")
        meta = data.get("meta") or {}
        group_key = meta.get(FEATURE_GROUP_BY_KEY)

        if not group_key:
            continue

        grouped.setdefault(group_key, []).append(data)

    return grouped
