"""Grid strategy agent following the same abstraction as the prompt agent.

This agent reuses:
- Default features pipeline `DefaultFeaturesPipeline`
- Rule-based decision composer `GridComposer`

Usage:
    from valuecell.agents.strategy_agent.grid_agent import GridStrategyAgent
    agent = GridStrategyAgent()
    await agent.stream(request)
"""

from __future__ import annotations

from .agent import BaseStrategyAgent
from .decision.grid_composer import GridComposer
from .decision.interfaces import Composer
from .features.pipeline import DefaultFeaturesPipeline, FeaturesPipeline
from .models import UserRequest


class GridStrategyAgent(BaseStrategyAgent):
    """Grid trading agent: default features + rule-based grid composer.

    - Spot: long-only grid add/reduce.
    - Perpetual/derivatives: bi-directional grid; add short on up moves,
      add long on down moves; reduce on reversals.
    """

    def _build_features_pipeline(self, request: UserRequest) -> FeaturesPipeline | None:
        return DefaultFeaturesPipeline.from_request(request)

    def _create_decision_composer(self, request: UserRequest) -> Composer | None:
        # Adjust step_pct / max_steps / base_fraction as needed
        return GridComposer(
            request=request,
            step_pct=0.005,  # ~0.5% per step
            max_steps=3,  # up to 3 steps per cycle
            base_fraction=0.08,  # base order size = equity * 8%
        )
