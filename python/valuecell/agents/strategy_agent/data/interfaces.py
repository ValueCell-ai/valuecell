from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import Candle

# Contracts for market data sources (module-local abstract interfaces).
# These are plain ABCs (not Pydantic models) so implementations can be
# synchronous or asynchronous without runtime overhead.


class MarketDataSource(ABC):
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
            symbols: list of symbols (e.g., ["BTCUSDT", "ETHUSDT"])
            interval: candle interval string (e.g., "1m", "5m")
            lookback: number of bars to retrieve
        """
        raise NotImplementedError
