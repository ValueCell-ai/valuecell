"""
Test and example usage for AutoTradingAgent
"""

import asyncio
import json

import pytest

from valuecell.agents.auto_trading_agent import (
    AutoTradingAgent,
    AutoTradingConfig,
)


class TestAutoTradingAgent:
    """Test cases for AutoTradingAgent"""

    @pytest.fixture
    def agent(self):
        """Create agent instance for testing"""
        return AutoTradingAgent()

    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing"""
        return AutoTradingConfig(
            initial_capital=100000,
            crypto_symbols=["BTC-USD"],
            check_interval=60,
            risk_per_trade=0.02,
            max_positions=3,
            agent_model="TestModel",
        )

    def test_agent_initialization(self, agent):
        """Test agent initializes correctly"""
        assert agent is not None
        assert agent.config is None
        assert agent.current_capital == 0.0
        assert len(agent.positions) == 0

    def test_config_validation(self):
        """Test configuration validation"""
        # Valid config
        config = AutoTradingConfig(
            initial_capital=50000, crypto_symbols=["BTC-USD", "ETH-USD"]
        )
        assert config.initial_capital == 50000
        assert len(config.crypto_symbols) == 2

        # Invalid config - no symbols
        with pytest.raises(ValueError):
            AutoTradingConfig(initial_capital=50000, crypto_symbols=[])

        # Invalid config - too many symbols
        with pytest.raises(ValueError):
            AutoTradingConfig(
                initial_capital=50000,
                crypto_symbols=[f"SYM{i}-USD" for i in range(11)],
            )

    def test_calculate_indicators(self, agent, sample_config):
        """Test technical indicator calculation"""
        agent.config = sample_config

        # Calculate indicators for BTC-USD
        indicators = agent._calculate_technical_indicators("BTC-USD")

        if indicators is not None:
            # Check that all expected fields are present
            assert indicators.symbol == "BTC-USD"
            assert indicators.close_price > 0
            assert indicators.volume >= 0
            # Note: Some indicators may be None if insufficient data
            assert hasattr(indicators, "macd")
            assert hasattr(indicators, "rsi")
            assert hasattr(indicators, "ema_12")

    def test_portfolio_value_calculation(self, agent, sample_config):
        """Test portfolio value calculation"""
        agent.config = sample_config
        agent.current_capital = 50000

        # Initially should equal current capital
        portfolio_value = agent._get_portfolio_value()
        assert portfolio_value == 50000

    def test_stop_trading(self, agent):
        """Test stop trading functionality"""
        session_id = "test_session_001"
        agent.trading_active[session_id] = True

        result = agent.stop_trading(session_id)
        assert result is True
        assert agent.trading_active[session_id] is False

    def test_get_portfolio_summary(self, agent, sample_config):
        """Test portfolio summary generation"""
        agent.config = sample_config
        agent.current_capital = 75000

        summary = agent.get_portfolio_summary()
        assert "capital" in summary
        assert "portfolio_value" in summary
        assert "positions" in summary
        assert summary["capital"] == 75000


# Example usage functions
async def example_setup_agent():
    """Example: Setup the agent with configuration"""
    print("=" * 60)
    print("Example 1: Setup AutoTradingAgent")
    print("=" * 60)

    agent = AutoTradingAgent()

    # Configuration as JSON
    config_json = json.dumps(
        {
            "initial_capital": 100000,
            "crypto_symbols": ["BTC-USD", "ETH-USD"],
            "check_interval": 60,
            "risk_per_trade": 0.02,
            "max_positions": 3,
            "agent_model": "DeepSeek Chat V3.1",
        }
    )

    print(f"\n📝 Configuration:\n{config_json}\n")

    # Setup agent via stream method
    async for response in agent.stream(
        query=config_json, session_id="example_001", task_id="task_001"
    ):
        print(f"Response: {response.content}")

    print("\n✅ Agent setup complete!\n")


async def example_trading_cycle():
    """Example: Run a few trading cycles"""
    print("=" * 60)
    print("Example 2: Run Trading Cycles")
    print("=" * 60)

    agent = AutoTradingAgent()

    # Configuration
    config_json = json.dumps(
        {
            "initial_capital": 50000,
            "crypto_symbols": ["BTC-USD"],
            "check_interval": 10,  # Faster for demo
            "risk_per_trade": 0.02,
            "max_positions": 2,
            "agent_model": "DemoAgent",
        }
    )

    print(f"\n📝 Configuration:\n{config_json}\n")
    print("🚀 Starting trading cycles (will run 3 cycles then stop)...\n")

    session_id = "example_002"
    cycle_count = 0
    max_cycles = 3

    # Start trading
    async for notification in agent.notify(
        query=config_json, session_id=session_id, task_id="task_002"
    ):
        print("\n📊 Notification received:")
        print(f"   Event: {notification.event}")
        if notification.content:
            print(f"   Content preview: {notification.content[:100]}...")

        cycle_count += 1
        if cycle_count >= max_cycles:
            print("\n⏹️  Stopping after 3 cycles...")
            agent.stop_trading(session_id)
            break

    print("\n✅ Trading cycles complete!\n")


async def example_portfolio_monitoring():
    """Example: Monitor portfolio status"""
    print("=" * 60)
    print("Example 3: Portfolio Monitoring")
    print("=" * 60)

    agent = AutoTradingAgent()

    # Setup agent
    agent.config = AutoTradingConfig(
        initial_capital=100000,
        crypto_symbols=["BTC-USD", "ETH-USD"],
        agent_model="MonitoringAgent",
    )
    agent.current_capital = 100000

    print("\n📊 Initial Portfolio Status:")
    summary = agent.get_portfolio_summary()
    print(f"   Capital: ${summary['capital']:,.2f}")
    print(f"   Portfolio Value: ${summary['portfolio_value']:,.2f}")
    print(f"   Open Positions: {summary['positions']}")

    print("\n✅ Monitoring example complete!\n")


async def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("AutoTradingAgent Examples")
    print("=" * 60 + "\n")

    # Example 1: Setup
    await example_setup_agent()

    print("\n" + "-" * 60 + "\n")

    # Example 2: Trading (commented out as it takes time)
    # Uncomment to run actual trading cycles
    # await example_trading_cycle()

    # Example 3: Portfolio monitoring
    await example_portfolio_monitoring()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())

    # To run pytest tests:
    # pytest test_auto_trading_agent.py -v
