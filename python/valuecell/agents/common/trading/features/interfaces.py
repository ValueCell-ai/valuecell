from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from valuecell.agents.common.trading.models import (
    Candle,
    FeaturesPipelineResult,
    FeatureVector,
)

# Contracts for feature computation (module-local abstract interfaces).
# Plain ABCs (not Pydantic) to keep implementations lightweight.


class CandleBasedFeatureComputer(ABC):
    """Computes feature vectors from raw market data (ticks/candles).

    Implementations may cache windows, offload CPU-heavy parts, or compose
    multiple feature families. The output should be per-instrument features.
    """

    @abstractmethod
    def compute_features(
        self,
        candles: Optional[List[Candle]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> List[FeatureVector]:
        """Build feature vectors from the given inputs.

        Args:
            candles: optional window of candles
            meta: optional metadata about the input window (e.g., interval,
                window_start_ts, window_end_ts, num_points). Implementations may
                use this to populate FeatureVector.meta.
        Returns:
            A list of FeatureVector items, one or more per instrument.
        """
        raise NotImplementedError


class BaseFeaturesPipeline(ABC):
    """Abstract pipeline that produces feature vectors (including market features)."""

    @abstractmethod
    async def build(self) -> FeaturesPipelineResult:
        """Compute feature vectors and return them.

        Implementations should use their configured request/inputs to determine
        which symbols to process; callers should not pass runtime parameters
        into this call.
        """
        raise NotImplementedError
