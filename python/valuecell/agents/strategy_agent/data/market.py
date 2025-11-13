from collections import defaultdict
from typing import Dict, List, Optional

from loguru import logger

from ..models import Candle, InstrumentRef, MarketSnapShotType
from ..utils import get_exchange_cls, normalize_symbol
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
            exchange_cls = get_exchange_cls(self._exchange_id)
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
                                # quote_ccy="USD",
                            ),
                            open=float(open_v),
                            high=float(high_v),
                            low=float(low_v),
                            close=float(close_v),
                            volume=float(vol),
                            interval=interval,
                        )
                    )
            except Exception as exc:
                logger.error(
                    "Failed to fetch candles for {} from {}, return empty candles. Error: {}",
                    symbol,
                    self._exchange_id,
                    exc,
                )
        return candles

    async def get_market_snapshot(self, symbols: List[str]) -> MarketSnapShotType:
        """Fetch latest prices for the given symbols using exchange endpoints.

        The method tries to use the exchange's `fetch_ticker` (and optionally
        `fetch_open_interest` / `fetch_funding_rate` when available) to build
        a mapping symbol -> last price. On any failure for a symbol, it will
        fall back to `base_prices` if provided or omit the symbol.
        Example:
        ```
        "BTC/USDT": {
            "price": {
                "symbol": "BTC/USDT:USDT",
                "timestamp": 1762930517943,
                "datetime": "2025-11-12T06:55:17.943Z",
                "high": 105464.2,
                "low": 102400.0,
                "vwap": 103748.56,
                "open": 105107.1,
                "close": 103325.0,
                "last": 103325.0,
                "change": -1782.1,
                "percentage": -1.696,
                "average": 104216.0,
                "baseVolume": 105445.427,
                "quoteVolume": 10939811519.57,
                "info": {
                    "symbol": "BTCUSDT",
                    "priceChange": "-1782.10",
                    "priceChangePercent": "-1.696",
                    "weightedAvgPrice": "103748.56",
                    "lastPrice": "103325.00",
                    "lastQty": "0.002",
                    "openPrice": "105107.10",
                    "highPrice": "105464.20",
                    "lowPrice": "102400.00",
                    "volume": "105445.427",
                    "quoteVolume": "10939811519.57",
                    "openTime": 1762844100000,
                    "closeTime": 1762930517943,
                    "firstId": 6852533393,
                    "lastId": 6856484055,
                    "count": 3942419
                }
            },
            "open_interest": {
                "symbol": "BTC/USDT:USDT",
                "baseVolume": 85179.147,
                "openInterestAmount": 85179.147,
                "timestamp": 1762930517944,
                "datetime": "2025-11-12T06:55:17.944Z",
                "info": {
                    "symbol": "BTCUSDT",
                    "openInterest": "85179.147",
                    "time": 1762930517944
                }
            },
            "funding_rate": {
                "info": {
                    "symbol": "BTCUSDT",
                    "markPrice": "103325.10000000",
                    "indexPrice": "103382.54282609",
                    "estimatedSettlePrice": "103477.58650543",
                    "lastFundingRate": "0.00000967",
                    "interestRate": "0.00010000",
                    "nextFundingTime": 1762934400000,
                    "time": 1762930523000
                },
                "symbol": "BTC/USDT:USDT",
                "markPrice": 103325.1,
                "indexPrice": 103382.54282609,
                "interestRate": 0.0001,
                "estimatedSettlePrice": 103477.58650543,
                "timestamp": 1762930523000,
                "datetime": "2025-11-12T06:55:23.000Z",
                "fundingRate": 9.67e-06,
                "fundingTimestamp": 1762934400000,
                "fundingDatetime": "2025-11-12T08:00:00.000Z"
            }
        }
        ```
        """
        snapshot = defaultdict(dict)

        exchange_cls = get_exchange_cls(self._exchange_id)
        exchange = exchange_cls({"newUpdates": False, **self._ccxt_options})
        try:
            for symbol in symbols:
                sym = normalize_symbol(symbol)
                try:
                    ticker = await exchange.fetch_ticker(sym)
                    snapshot[symbol]["price"] = ticker

                    # best-effort: warm other endpoints (open interest / funding)
                    try:
                        oi = await exchange.fetch_open_interest(sym)
                        snapshot[symbol]["open_interest"] = oi
                    except Exception:
                        logger.exception(
                            "Failed to fetch open interest for {} at {}",
                            symbol,
                            self._exchange_id,
                        )

                    try:
                        fr = await exchange.fetch_funding_rate(sym)
                        snapshot[symbol]["funding_rate"] = fr
                    except Exception:
                        logger.exception(
                            "Failed to fetch funding rate for {} at {}",
                            symbol,
                            self._exchange_id,
                        )
                except Exception:
                    logger.exception(
                        "Failed to fetch market snapshot for {} at {}",
                        symbol,
                        self._exchange_id,
                    )
        finally:
            try:
                await exchange.close()
            except Exception:
                logger.exception(
                    "Failed to close exchange connection for {}",
                    self._exchange_id,
                )

        return dict(snapshot)
