"""
TradingAgents Interactive Demo

This script demonstrates how to:
1. Connect to TradingAgents
2. Run an interactive conversation
3. Select LLM, analysts, and stock
4. Get trading analysis results
"""

import asyncio
import logging
from typing import Optional

from valuecell.core.agent.connect import RemoteConnections

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingAgentsDemo:
    """TradingAgents interactive demo class"""

    def __init__(self):
        self.connections = RemoteConnections()
        self.agent_name = "TradingAgentsAdapter"
        self.client: Optional[object] = None

    async def setup(self):
        """Set up connection"""
        try:
            # Connect to remote agent
            agent_url = await self.connections.connect_remote_agent(self.agent_name)
            logger.info(f"TradingAgents connected successfully: {agent_url}")

            # Get client connection
            self.client = await self.connections.get_client(self.agent_name)
            logger.info("Client connection established successfully")

            return True
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False

    async def interactive_session(self):
        """Interactive session"""
        print("\n" + "=" * 60)
        print("🚀 TradingAgents interactive demo")
        print("=" * 60)
        print("Enter 'help' to get help information")
        print("Enter 'quit' or 'exit' to exit")
        print("=" * 60 + "\n")

        while True:
            try:
                # Get user input
                user_input = input("💬 Please enter your query: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["quit", "exit", "exit"]:
                    print("👋 Bye!")
                    break

                # Send message and get streaming response
                print("\n🤖 TradingAgents response:")
                print("-" * 50)

                async for task, event in await self.client.send_message(
                    user_input,
                    streaming=True,
                ):
                    # Check artifact content (main response content)
                    if task and task.artifacts:
                        for artifact in task.artifacts:
                            if artifact.parts:
                                for part in artifact.parts:
                                    if hasattr(part.root, "text") and part.root.text:
                                        print(part.root.text, end="", flush=True)

                    # Check event content
                    elif event and hasattr(event, "content") and event.content:
                        print(event.content, end="", flush=True)

                print("\n" + "-" * 50 + "\n")

            except KeyboardInterrupt:
                print("\n👋 User interrupted, exiting...")
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                print(f"❌ Error: {e}\n")

    async def run_demo_queries(self):
        """Run preset demo queries"""
        demo_queries = [
            "help",  # Get help information
            "Analyze AAPL stock",  # Basic analysis
            "Use market and fundamentals analysts to analyze NVDA",  # Specify analysts
            "Use anthropic provider to analyze TSLA, date 2024-01-15",  # Specify LLM and date
            "Analyze SPY, use all analysts, enable debug mode",  # Full parameters
        ]

        print("\n" + "=" * 60)
        print("🎯 Run demo queries")
        print("=" * 60)

        for i, query in enumerate(demo_queries, 1):
            print(f"\n📝 Demo query {i}: {query}")
            print("-" * 50)

            try:
                async for task, event in await self.client.send_message(
                    query,
                    streaming=True,
                ):
                    # Check artifact content (main response content)
                    if task and task.artifacts:
                        for artifact in task.artifacts:
                            if artifact.parts:
                                for part in artifact.parts:
                                    if hasattr(part.root, "text") and part.root.text:
                                        print(part.root.text, end="", flush=True)

                    # Check event content
                    elif event and hasattr(event, "content") and event.content:
                        print(event.content, end="", flush=True)

                print("\n" + "-" * 50)

                # Wait for user to confirm continue
                if i < len(demo_queries):
                    input("\n⏸️  Press Enter to continue to the next demo...")

            except Exception as e:
                logger.error(f"Demo query failed: {e}")
                print(f"❌ Demo query failed: {e}\n")

    async def cleanup(self):
        """Clean up resources"""
        try:
            await self.connections.stop_all()
            logger.info("Resources cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up resources: {e}")


async def main():
    """Main function"""
    demo = TradingAgentsDemo()

    # Set up connection
    if not await demo.setup():
        print(
            "❌ Cannot connect to TradingAgents, please ensure the service is running"
        )
        return

    try:
        print("\nPlease select the running mode:")
        print("1. Interactive dialog mode")
        print("2. Run preset demo")

        choice = input("Please enter the choice (1 or 2): ").strip()

        if choice == "1":
            await demo.interactive_session()
        elif choice == "2":
            await demo.run_demo_queries()
        else:
            print("Invalid choice, default running interactive mode")
            await demo.interactive_session()

    except KeyboardInterrupt:
        print("\n👋 Program interrupted")
    finally:
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
