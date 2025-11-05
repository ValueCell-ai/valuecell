from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ..models import Candle, FeatureVector

# Contracts for feature computation (module-local abstract interfaces).
# Plain ABCs (not Pydantic) to keep implementations lightweight.


class FeatureComputer(ABC):
    """Computes feature vectors from raw market data (ticks/candles).

    Implementations may cache windows, offload CPU-heavy parts, or compose
    multiple feature families. The output should be per-instrument features.
    """

    @abstractmethod
    def compute_features(
        self,
        candles: Optional[List[Candle]] = None,
    ) -> List[FeatureVector]:
        """Build feature vectors from the given inputs.

        Args:
            candles: optional window of candles
        Returns:
            A list of FeatureVector items, one or more per instrument.
        """
        raise NotImplementedError
