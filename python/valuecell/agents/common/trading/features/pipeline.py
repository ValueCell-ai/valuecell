"""Feature pipeline abstractions for the strategy agent.

This module encapsulates the data-fetch and feature-computation steps used by
strategy runtimes. Introducing a dedicated pipeline object means the decision
coordinator no longer needs direct access to the market data source or feature
computer—everything is orchestrated by the pipeline.
"""

from __future__ import annotations

from typing import List

from valuecell.agents.common.trading.models import (
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
        micro_interval: str = "1s",
        micro_lookback: int = 60 * 3,
        medium_interval: str = "1m",
        medium_lookback: int = 60 * 4,
    ) -> None:
        self._request = request
        self._market_data_source = market_data_source
        self._candle_feature_computer = candle_feature_computer
        self._micro_interval = micro_interval
        self._micro_lookback = micro_lookback
        self._medium_interval = medium_interval
        self._medium_lookback = medium_lookback
        self._symbols = list(dict.fromkeys(request.trading_config.symbols))
        self._market_snapshot_computer = market_snapshot_computer

    async def build(self) -> FeaturesPipelineResult:
        """Fetch candles, compute feature vectors, and append market features."""
        # Determine symbols from the configured request so caller doesn't pass them
        candles_micro = await self._market_data_source.get_recent_candles(
            self._symbols, self._micro_interval, self._micro_lookback
        )
        micro_features = self._candle_feature_computer.compute_features(
            candles=candles_micro
        )

        candles_medium = await self._market_data_source.get_recent_candles(
            self._symbols, self._medium_interval, self._medium_lookback
        )
        medium_features = self._candle_feature_computer.compute_features(
            candles=candles_medium
        )

        features: List[FeatureVector] = []
        features.extend(medium_features or [])
        features.extend(micro_features or [])

        market_snapshot = await self._market_data_source.get_market_snapshot(
            self._symbols
        )
        market_snapshot = market_snapshot or {}

        market_features = self._market_snapshot_computer.build(
            market_snapshot, self._request.exchange_config.exchange_id
        )
        features.extend(market_features)

        return FeaturesPipelineResult(features=features)

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
