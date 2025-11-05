"""Schemas for StrategyAgent API requests."""

from typing import Optional

from pydantic import Field

from valuecell.agents.strategy_agent.models import (
    ModelConfig,
    ExchangeConfig,
    TradingConfig,
    UserRequest,
)


class StrategyAgentCreateRequest(UserRequest):
    """Request body for creating a strategy via StrategyAgent.

    Inherits fields from UserRequest and adds optional conversation_id
    to bind the request to an existing conversation.
    """

    conversation_id: Optional[str] = Field(
        default=None, description="Conversation ID for correlating the stream"
    )