import asyncio
import logging
from valuecell.core.agent.decorator import serve
from valuecell.core.agent.connect import RemoteConnections

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Demo agents using the @serve decorator
@serve(name="Calculator Agent")
class CalculatorAgent:
    """A calculator agent that can do basic math"""

    def __init__(self):
        logger.info("Initializing CalculatorAgent")
        self.agent_name = "CalculatorAgent"

    async def stream(self, query, session_id, task_id):
        """Process math queries"""
        logger.info(f"Calculator processing: {query}")

        yield {"is_task_complete": False, "content": f"🧮 Calculating: {query}"}
        await asyncio.sleep(0.5)

        try:
            # Simple math evaluation (in real world, use safe parsing)
            if any(op in query for op in ["+", "-", "*", "/", "(", ")"]):
                # For demo, just respond with a mock calculation
                result = "42"  # Mock result
                yield {"is_task_complete": False, "content": "💭 Computing result..."}
                await asyncio.sleep(0.5)
                yield {"is_task_complete": True, "content": f"✅ Result: {result}"}
            else:
                yield {
                    "is_task_complete": True,
                    "content": "❓ I can help with math calculations. Try something like '2 + 3'",
                }
        except Exception as e:
            yield {
                "is_task_complete": True,
                "content": f"❌ Error in calculation: {str(e)}",
            }


@serve(name="Weather Agent", port=9101, description="Provides weather information")
class WeatherAgent:
    """A weather information agent"""

    def __init__(self):
        logger.info("Initializing WeatherAgent")
        self.agent_name = "WeatherAgent"

    async def stream(self, query, session_id, task_id):
        """Process weather queries"""
        logger.info(f"Weather processing: {query}")

        yield {"is_task_complete": False, "content": f"🌤️ Checking weather for: {query}"}
        await asyncio.sleep(0.8)

        if "weather" in query.lower():
            yield {
                "is_task_complete": False,
                "content": "🌡️ Fetching current conditions...",
            }
            await asyncio.sleep(0.5)
            yield {
                "is_task_complete": False,
                "content": "📊 Analyzing forecast data...",
            }
            await asyncio.sleep(0.5)
            yield {
                "is_task_complete": True,
                "content": f"☀️ Weather report: Sunny, 22°C. Perfect day! (for query: {query})",
            }
        else:
            yield {
                "is_task_complete": True,
                "content": "🌍 I provide weather information. Ask me about the weather in any location!",
            }


@serve(name="Simple Agent", streaming=False, push_notifications=False)
class SimpleAgent:
    """A simple non-streaming agent"""

    async def stream(self, query, session_id, task_id):
        """Simple response"""
        yield {"is_task_complete": True, "content": f"Simple response to: {query}"}


async def demo_complete_system():
    """Complete demonstration of the decorator system"""
    logger.info("🚀 Starting Complete A2A Decorator System Demo")

    # Create connections manager
    connections = RemoteConnections()

    try:
        # Show available agents from registry
        available = connections.list_available_agents()
        logger.info(f"📋 Available agents from registry: {available}")

        # Start multiple agents
        logger.info("▶️  Starting multiple agents...")

        calc_url = await connections.start_agent("CalculatorAgent")
        weather_url = await connections.start_agent("WeatherAgent")
        simple_url = await connections.start_agent("SimpleAgent")

        logger.info(f"🧮 Calculator Agent: {calc_url}")
        logger.info(f"🌤️ Weather Agent: {weather_url}")
        logger.info(f"📝 Simple Agent: {simple_url}")

        # Wait for all agents to fully start
        await asyncio.sleep(3)

        # Show running agents
        running = connections.list_running_agents()
        logger.info(f"🏃 Running agents: {running}")

        # Test Calculator Agent
        logger.info("🧪 Testing Calculator Agent...")
        client = await connections.get_client("CalculatorAgent")
        task, event = await client.send_message("What is 15 + 27?")
        logger.info(f"Calculator result: {task.status}")

        # # Test Weather Agent
        logger.info("🧪 Testing Weather Agent...")
        client = await connections.get_client("WeatherAgent")
        task, event = await client.send_message(
            "What's the weather like in San Francisco?"
        )
        logger.info(f"Weather result: {task.status}")

        # Test Simple Agent
        logger.info("🧪 Testing Simple Agent...")
        client = await connections.get_client("SimpleAgent")
        task, event = await client.send_message("Hello simple agent")
        logger.info(f"Simple agent result: {task.status}")

        await asyncio.sleep(10)
        # Show agent information
        for agent_name in running:
            info = connections.get_agent_info(agent_name)
            if info:
                logger.info(
                    f"ℹ️  {agent_name}: {info['url']} (running: {info['running']})"
                )

        logger.info("✅ All tests completed successfully!")

    except Exception as e:
        logger.error(f"❌ Error in demo: {e}")
        import traceback

        traceback.print_exc()
        raise

    finally:
        # Clean up
        logger.info("🧹 Stopping all agents...")
        await connections.stop_all()
        logger.info("✅ Demo completed and cleaned up")


if __name__ == "__main__":
    asyncio.run(demo_complete_system())
