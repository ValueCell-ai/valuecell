"""Default strategy agent implementation with standard behavior.

This module provides a concrete implementation of StrategyAgent that uses
the default feature computation and LLM-based decision making. Users can
extend this class or StrategyAgent directly for custom strategies.
"""

from __future__ import annotations

from valuecell.agents.common.trading.base_agent import BaseStrategyAgent
from valuecell.agents.common.trading.decision import BaseComposer, LlmComposer
from valuecell.agents.common.trading.features import (
    BaseFeaturesPipeline,
    DefaultFeaturesPipeline,
)
from valuecell.agents.common.trading.models import UserRequest


class PromptBasedStrategyAgent(BaseStrategyAgent):
    """Default strategy agent with standard feature computation and LLM composer.

    This implementation uses:
    - SimpleFeatureComputer for feature extraction
    - LlmComposer for decision making
    - Default data sources and execution

    Users can subclass this to customize specific aspects while keeping
    other defaults, or subclass StrategyAgent directly for full control.

    Example:
        # Use the default agent directly
        agent = DefaultStrategyAgent()

        # Or customize just the features
        class MyCustomAgent(DefaultStrategyAgent):
            def _build_features_pipeline(self, request):
                # Custom feature pipeline encapsulating data + features
                return MyCustomPipeline(request)
    """

    async def _build_features_pipeline(
        self, request: UserRequest
    ) -> BaseFeaturesPipeline | None:
        """Use the default features pipeline built from the user request."""

        return DefaultFeaturesPipeline.from_request(request)

    async def _create_decision_composer(
        self, request: UserRequest
    ) -> BaseComposer | None:
        """Use default LLM-based composer."""

        return LlmComposer(request=request)
