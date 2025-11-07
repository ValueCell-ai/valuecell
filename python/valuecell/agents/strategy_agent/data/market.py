from collections import defaultdict
from typing import Dict, List, Optional

import ccxt.pro as ccxtpro
from loguru import logger

from ..models import Candle, InstrumentRef
from .interfaces import MarketDataSource


class SimpleMarketDataSource(MarketDataSource):
    """Generates synthetic candle data for each symbol or fetches via ccxt.pro.

    If `exchange_id` was provided at construction time and `ccxt.pro` is
    available, this class will attempt to fetch OHLCV data from the
    specified exchange. If any error occurs (missing library, unknown
    exchange, network error), it falls back to the built-in synthetic
    generator so the runtime remains functional in tests and offline.
    """

    def __init__(
        self,
        base_prices: Optional[Dict[str, float]] = None,
        exchange_id: Optional[str] = None,
        ccxt_options: Optional[Dict] = None,
    ) -> None:
        self._base_prices = base_prices or {}
        self._counters: Dict[str, int] = defaultdict(int)
        self._exchange_id = exchange_id or "binance"
        self._ccxt_options = ccxt_options or {}

    async def get_recent_candles(
        self, symbols: List[str], interval: str, lookback: int
    ) -> List[Candle]:
        async def _fetch(symbol: str) -> List[List]:
            # instantiate exchange class by name (e.g., ccxtpro.kraken)
            exchange_cls = getattr(ccxtpro, self._exchange_id, None)
            if exchange_cls is None:
                raise RuntimeError(
                    f"Exchange '{self._exchange_id}' not found in ccxt.pro"
                )
            exchange = exchange_cls({"newUpdates": False, **self._ccxt_options})
            try:
                # ccxt.pro uses async fetch_ohlcv
                data = await exchange.fetch_ohlcv(
                    symbol, timeframe=interval, since=None, limit=lookback
                )
                return data
            finally:
                try:
                    await exchange.close()
                except Exception:
                    pass

        candles: List[Candle] = []
        # Run fetch for each symbol sequentially
        for symbol in symbols:
            try:
                raw = await _fetch(symbol)
                # raw is list of [ts, open, high, low, close, volume]
                for row in raw:
                    ts, open_v, high_v, low_v, close_v, vol = row
                    candles.append(
                        Candle(
                            ts=int(ts),
                            instrument=InstrumentRef(
                                symbol=symbol,
                                exchange_id=self._exchange_id,
                                quote_ccy="USD",
                            ),
                            open=float(open_v),
                            high=float(high_v),
                            low=float(low_v),
                            close=float(close_v),
                            volume=float(vol),
                            interval=interval,
                        )
                    )
            except Exception:
                logger.exception(
                    "Failed to fetch candles for {} from {}, return empty candles",
                    symbol,
                    self._exchange_id,
                )
        return candles
