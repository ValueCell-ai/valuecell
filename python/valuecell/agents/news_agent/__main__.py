"""Main entry point for the News Agent."""

import asyncio

from valuecell.core.agent.decorator import create_wrapped_agent

from .core import NewsAgent


async def main():
    """Main function to run the News Agent."""
    agent = create_wrapped_agent(NewsAgent)

    # Example queries for testing
    test_queries = [
        "What's the latest news today?",
        "Any breaking news right now?",
        "What's happening in the financial markets?",
        "Latest technology news and AI developments",
        "News about climate change in the past week",
    ]

    print("News Agent is ready! Try these example queries:")
    for i, query in enumerate(test_queries, 1):
        print(f"{i}. {query}")

    print("\nEnter your news query (or 'quit' to exit):")

    while True:
        try:
            user_input = input("\n> ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            if not user_input:
                continue

            print("\nFetching news...")

            # Stream the response
            async for chunk in agent.stream(user_input):
                if chunk.get("type") == "message":
                    print(chunk.get("content", ""), end="", flush=True)
                elif chunk.get("type") == "tool_call_start":
                    tool_name = chunk.get("tool_name", "")
                    print(f"\n[Using tool: {tool_name}]")
                elif chunk.get("type") == "error":
                    print(f"\nError: {chunk.get('content', '')}")

            print("\n" + "=" * 50)

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
