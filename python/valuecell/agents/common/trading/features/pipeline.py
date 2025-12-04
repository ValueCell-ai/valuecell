"""Feature pipeline abstractions for the strategy agent.

This module encapsulates the data-fetch and feature-computation steps used by
strategy runtimes. Introducing a dedicated pipeline object means the decision
coordinator no longer needs direct access to the market data source or feature
computer—everything is orchestrated by the pipeline.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Optional

from loguru import logger

from valuecell.agents.common.trading.models import (
    CandleConfig,
    FeaturesPipelineResult,
    FeatureVector,
    UserRequest,
)

from ..data.interfaces import BaseMarketDataSource
from ..data.market import SimpleMarketDataSource
from ..data.screenshot import AggrScreenshotDataSource, PlaywrightScreenshotDataSource
from ..models import InstrumentRef
from .candle import SimpleCandleFeatureComputer
from .image import MLLMImageFeatureComputer
from .interfaces import (
    BaseFeaturesPipeline,
    CandleBasedFeatureComputer,
)
from .market_snapshot import MarketSnapshotFeatureComputer
from .prompts import AGGR_PROMPT


class DefaultFeaturesPipeline(BaseFeaturesPipeline):
    """Default pipeline using the simple data source and feature computer."""

    def __init__(
        self,
        *,
        request: UserRequest,
        market_data_source: BaseMarketDataSource,
        candle_feature_computer: CandleBasedFeatureComputer,
        market_snapshot_computer: MarketSnapshotFeatureComputer,
        candle_configurations: Optional[List[CandleConfig]] = None,
        screenshot_data_source: Optional[PlaywrightScreenshotDataSource] = None,
        image_feature_computer: Optional[MLLMImageFeatureComputer] = None,
    ) -> None:
        self._request = request
        self._market_data_source = market_data_source
        self._candle_feature_computer = candle_feature_computer
        self._symbols = list(dict.fromkeys(request.trading_config.symbols))
        self._market_snapshot_computer = market_snapshot_computer
        self._screenshot_data_source = screenshot_data_source
        self._image_feature_computer = image_feature_computer
        self._candle_configurations = candle_configurations or [
            CandleConfig(interval="1m", lookback=60 * 4),
        ]

    async def open(self) -> None:
        """Open any long-lived resources needed by the pipeline."""

        if self._screenshot_data_source is not None:
            await self._screenshot_data_source.open()

    async def build(self) -> FeaturesPipelineResult:
        """
        Fetch candles and market snapshot, compute feature vectors concurrently,
        and combine results.
        """

        async def _fetch_candles(interval: str, lookback: int) -> List[FeatureVector]:
            """Fetches candles and computes features for a single (interval, lookback) pair."""
            _candles = await self._market_data_source.get_recent_candles(
                self._symbols, interval, lookback
            )
            return self._candle_feature_computer.compute_features(candles=_candles)

        async def _fetch_market_features() -> List[FeatureVector]:
            """Fetches market snapshot for all symbols and computes features."""
            market_snapshot = await self._market_data_source.get_market_snapshot(
                self._symbols
            )
            market_snapshot = market_snapshot or {}
            return self._market_snapshot_computer.build(
                market_snapshot, self._request.exchange_config.exchange_id
            )

        logger.info(
            f"Starting concurrent data fetching for {len(self._candle_configurations)} candle sets and markets snapshot..."
        )

        # Create named tasks so we don't depend on result ordering.
        tasks_map: dict[str, asyncio.Task] = {}

        for idx, config in enumerate(self._candle_configurations):
            name = f"candles:{config.interval}:{idx}"
            coro = _fetch_candles(config.interval, config.lookback)
            tasks_map[name] = asyncio.create_task(coro)

        # market snapshot task
        tasks_map["market"] = asyncio.create_task(_fetch_market_features())

        # Optionally fetch and compute image-based features if providers are set
        if (
            self._screenshot_data_source is not None
            and self._image_feature_computer is not None
        ):

            async def _fetch_image_features() -> List[FeatureVector]:
                try:
                    images = await self._screenshot_data_source.capture()
                    return await self._image_feature_computer.compute_features(
                        images=images
                    )
                except Exception as e:
                    logger.error(f"Failed to capture screenshot: {e}")
                    return []

            tasks_map["image"] = asyncio.create_task(_fetch_image_features())

        # Await all tasks and then collect results by name
        await asyncio.gather(*tasks_map.values())
        logger.info("Concurrent data fetching complete.")

        results_map: dict[str, List[FeatureVector]] = {
            name: task.result() for name, task in tasks_map.items()
        }

        # Flatten candle features from all candle tasks
        candle_features: List[FeatureVector] = []
        for name, feats in results_map.items():
            if name.startswith("candles:"):
                candle_features.extend(feats)

        # Append market features if available
        market_features: List[FeatureVector] = results_map.get("market", [])

        # Append image-derived features if available
        image_features: List[FeatureVector] = results_map.get("image", [])

        candle_features.extend(market_features)
        candle_features.extend(image_features)

        return FeaturesPipelineResult(features=candle_features)

    async def close(self) -> None:
        """Close any long-lived resources created by the pipeline."""
        if self._screenshot_data_source is not None:
            await self._screenshot_data_source.close()

    @classmethod
    def from_request(cls, request: UserRequest) -> DefaultFeaturesPipeline:
        """Factory creating the default pipeline from a user request."""
        market_data_source = SimpleMarketDataSource(
            exchange_id=request.exchange_config.exchange_id
        )
        candle_feature_computer = SimpleCandleFeatureComputer()
        market_snapshot_computer = MarketSnapshotFeatureComputer()

        try:
            image_feature_computer = MLLMImageFeatureComputer.from_request(
                request, prompt=AGGR_PROMPT
            )
            charts_json = (
                Path(__file__).parent.parent
                / "data"
                / "configs"
                / "aggr"
                / "charts.json"
            )
            screenshot_data_source = AggrScreenshotDataSource(
                target_url="https://aggr.trade",
                file_path=str(charts_json),
                instrument=InstrumentRef(symbol="BTCUSD"),
            )
        except Exception as e:
            logger.warning(
                f"Image feature computer could not be initialized: {e}. Proceeding without image features."
            )
            image_feature_computer = None
            screenshot_data_source = None

        return cls(
            request=request,
            market_data_source=market_data_source,
            candle_feature_computer=candle_feature_computer,
            market_snapshot_computer=market_snapshot_computer,
            image_feature_computer=image_feature_computer,
            screenshot_data_source=screenshot_data_source,
        )
