from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from valuecell.agents.common.trading.models import (
    Candle,
    FeaturesPipelineResult,
    FeatureVector,
)

if TYPE_CHECKING:
    # Only for type hints to avoid hard dependency at runtime
    from agno.media import Image

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


class ImageBasedFeatureComputer(ABC):
    """Abstract base for image-based feature computers.

    Implementations consume one or more images (screenshots, dashboard panes)
    and return domain FeatureVector objects. The concrete implementations may
    call external vision/LLM services.
    """

    @abstractmethod
    async def compute_features(
        self,
        images: Optional[List["Image"]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> List[FeatureVector]:
        """Build feature vectors from the provided images.

        Args:
            images: list of image objects. Implementations expect `agno.media.Image`.
            meta: optional metadata such as instrument or timestamps.
        Returns:
            A list of `FeatureVector` items.
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

    @abstractmethod
    async def open(self) -> None:
        """Optional one-time initialization for long-lived resources.

        Implementations may open network/browser sessions or warm caches here.
        This method will be called by the runtime when available; callers may
        ignore if not needed.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Optional cleanup for resources allocated in `open()`.

        Called by the runtime during shutdown to release resources (e.g., close
        browser, stop background tasks). Implementations should make this idempotent.
        """
        pass
