import asyncio
import json
import os
from pprint import pprint

from valuecell.agents.strategy_agent.agent import StrategyAgent


# @pytest.mark.asyncio
async def strategy_agent_basic_stream():
    """Test basic functionality of StrategyAgent stream method."""
    agent = StrategyAgent()

    # Prepare a valid JSON query based on UserRequest structure
    query = json.dumps(
        {
            "llm_model_config": {
                "provider": "openrouter",
                "model_id": "deepseek/deepseek-v3.1-terminus",
                "api_key": os.getenv("OPENROUTER_API_KEY"),
            },
            "exchange_config": {
                "exchange_id": "binance",
                "trading_mode": "virtual",
                "api_key": "test-exchange-key",
                "secret_key": "test-secret-key",
            },
            "trading_config": {
                "strategy_name": "Test Strategy",
                "initial_capital": 10000.0,
                "max_leverage": 5.0,
                "max_positions": 5,
                "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
                "decide_interval": 60,
                "template_id": "aggressive",
                "custom_prompt": "no custom prompt",
            },
        }
    )

    async for response in agent.stream(query, "test-conversation", "test-task"):
        pprint(response.metadata)
        pprint(json.loads(response.content))
        print("\n\n")


asyncio.run(strategy_agent_basic_stream())
