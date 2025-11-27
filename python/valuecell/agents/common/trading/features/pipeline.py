"""Feature pipeline abstractions for the strategy agent.

This module encapsulates the data-fetch and feature-computation steps used by
strategy runtimes. Introducing a dedicated pipeline object means the decision
coordinator no longer needs direct access to the market data source or feature
computer—everything is orchestrated by the pipeline.
"""

from __future__ import annotations

import asyncio
import itertools
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
from .candle import SimpleCandleFeatureComputer
from .interfaces import (
    BaseFeaturesPipeline,
    CandleBasedFeatureComputer,
)
from .market_snapshot import MarketSnapshotFeatureComputer


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
    ) -> None:
        self._request = request
        self._market_data_source = market_data_source
        self._candle_feature_computer = candle_feature_computer
        self._symbols = list(dict.fromkeys(request.trading_config.symbols))
        self._market_snapshot_computer = market_snapshot_computer
        self._candle_configurations = candle_configurations
        self._candle_configurations = candle_configurations or [
            CandleConfig(interval="1s", lookback=60 * 3),
            CandleConfig(interval="1m", lookback=60 * 4),
        ]

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
        tasks = [
            _fetch_candles(config.interval, config.lookback)
            for config in self._candle_configurations
        ]
        tasks.append(_fetch_market_features())

        # results = [ [candle_features_1], [candle_features_2], ..., [market_features] ]
        results = await asyncio.gather(*tasks)
        logger.info("Concurrent data fetching complete.")

        market_features: List[FeatureVector] = results.pop()

        # Flatten the list of lists of candle features
        candle_features: List[FeatureVector] = list(
            itertools.chain.from_iterable(results)
        )

        candle_features.extend(market_features)

        return FeaturesPipelineResult(features=candle_features)

    @classmethod
    def from_request(cls, request: UserRequest) -> DefaultFeaturesPipeline:
        """Factory creating the default pipeline from a user request."""
        market_data_source = SimpleMarketDataSource(
            exchange_id=request.exchange_config.exchange_id
        )
        candle_feature_computer = SimpleCandleFeatureComputer()
        market_snapshot_computer = MarketSnapshotFeatureComputer()
        return cls(
            request=request,
            market_data_source=market_data_source,
            candle_feature_computer=candle_feature_computer,
            market_snapshot_computer=market_snapshot_computer,
        )
