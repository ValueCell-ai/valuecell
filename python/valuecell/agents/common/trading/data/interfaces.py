from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from valuecell.agents.common.trading.models import Candle, MarketSnapShotType

# Contracts for market data sources (module-local abstract interfaces).
# These are plain ABCs (not Pydantic models) so implementations can be
# synchronous or asynchronous without runtime overhead.


class BaseMarketDataSource(ABC):
    """Abstract market data access used by feature computation.

    Implementations should fetch recent ticks or candles for the requested
    symbols and intervals. Caching and batching policies are left to the
    concrete classes.
    """

    @abstractmethod
    async def get_recent_candles(
        self, symbols: List[str], interval: str, lookback: int
    ) -> List[Candle]:
        """Return recent candles (OHLCV) for the given symbols/interval.

        Args:
            symbols: list of symbols (e.g., ["BTC/USDT", "ETH/USDT"])
            interval: candle interval string (e.g., "1m", "5m")
            lookback: number of bars to retrieve
        """
        raise NotImplementedError

    @abstractmethod
    async def get_market_snapshot(self, symbols: List[str]) -> MarketSnapShotType:
        """Return a lightweight market snapshot mapping symbol -> price.

        Implementations may call exchange endpoints (ticker, funding, open
        interest) to build an authoritative latest-price mapping. The return
        value should be a dict where keys are symbol strings and values are
        latest price floats (or absent if not available).
        """

        raise NotImplementedError
