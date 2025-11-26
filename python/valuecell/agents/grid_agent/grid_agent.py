"""Grid strategy agent following the same abstraction as the prompt agent.

This agent reuses:
- Default features pipeline `DefaultFeaturesPipeline`
- Rule-based decision composer `GridComposer`

Usage:
    from valuecell.agents.grid_agent.grid_agent import GridStrategyAgent
    agent = GridStrategyAgent()
    await agent.stream(request)
"""

from __future__ import annotations

from valuecell.agents.common.trading.base_agent import BaseStrategyAgent
from valuecell.agents.common.trading.decision.grid_composer.grid_composer import (
    GridComposer,
)
from valuecell.agents.common.trading.decision.interfaces import BaseComposer
from valuecell.agents.common.trading.features.interfaces import BaseFeaturesPipeline
from valuecell.agents.common.trading.features.pipeline import DefaultFeaturesPipeline
from valuecell.agents.common.trading.models import UserRequest


class GridStrategyAgent(BaseStrategyAgent):
    """Grid trading agent: default features + rule-based grid composer.

    - Spot: long-only grid add/reduce.
    - Perpetual/derivatives: bi-directional grid; add short on up moves,
      add long on down moves; reduce on reversals.
    """

    async def _build_features_pipeline(
        self, request: UserRequest
    ) -> BaseFeaturesPipeline | None:
        return DefaultFeaturesPipeline.from_request(request)

    async def _create_decision_composer(
        self, request: UserRequest
    ) -> BaseComposer | None:
        # Adjust step_pct / max_steps / base_fraction as needed
        return GridComposer(
            request=request,
            step_pct=0.001,  # 0.1% per step (more sensitive)
            max_steps=3,
            base_fraction=0.08,
            use_llm_params=True,
        )
