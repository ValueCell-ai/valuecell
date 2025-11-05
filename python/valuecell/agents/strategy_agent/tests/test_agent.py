import asyncio
import json

import pytest

from valuecell.agents.strategy_agent.agent import StrategyAgent


@pytest.mark.asyncio
async def test_strategy_agent_basic_stream():
    """Test basic functionality of StrategyAgent stream method."""
    agent = StrategyAgent()

    # Prepare a valid JSON query based on UserRequest structure
    query = json.dumps(
        {
            "llm_model_config": {
                "provider": "test-provider",
                "model_id": "test-model",
                "api_key": "test-api-key",
            },
            "exchange_config": {
                "exchange_id": "binance",
                "trading_mode": "virtual",
                "api_key": "test-exchange-key",
                "secret_key": "test-secret-key",
            },
            "trading_config": {
                "strategy_name": "Test Strategy",
                "initial_capital": 1000.0,
                "max_leverage": 1.0,
                "max_positions": 5,
                "symbols": ["BTC/USDT"],
                "decide_interval": 60,
            },
        }
    )

    try:
        async for response in agent.stream(query, "test-conversation", "test-task"):
            print(response)
    except asyncio.CancelledError:
        pass  # Expected if we cancel
