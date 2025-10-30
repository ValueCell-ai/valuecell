"""News Agent core implementation."""

from typing import AsyncGenerator, Dict, Optional

from agno.agent import Agent
from loguru import logger

from valuecell.adapters.models import create_model_for_agent
from valuecell.config.manager import get_config_manager
from valuecell.core.agent.responses import streaming
from valuecell.core.types import BaseAgent, StreamResponse

from .prompts import NEWS_AGENT_INSTRUCTIONS
from .tools import get_breaking_news, get_financial_news, web_search


class NewsAgent(BaseAgent):
    """News Agent for fetching and analyzing news content."""

    def __init__(self):
        """Initialize the News Agent with news-related tools."""
        super().__init__()

        # Load agent configuration
        self.config_manager = get_config_manager()
        self.agent_config = self.config_manager.get_agent_config("news_agent")

        # Load tools based on configuration
        available_tools = []

        available_tools.extend([web_search, get_breaking_news, get_financial_news])

        # Create the knowledge news agent with configured model and tools
        # Use create_model_for_agent to load agent-specific configuration
        self.knowledge_news_agent = Agent(
            model=create_model_for_agent("news_agent"),
            tools=available_tools,
            instructions=NEWS_AGENT_INSTRUCTIONS,
        )

        logger.info("NewsAgent initialized with news tools")

    async def stream(
        self,
        query: str,
        conversation_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        """
        Stream news information based on the user query.

        Args:
            query: The user's news query
            conversation_id: Conversation ID for context
            task_id: Task ID
            dependencies: Optional dependencies

        Yields:
            StreamResponse: Streaming responses with proper event types
        """
        response_stream = self.knowledge_news_agent.arun(
            query,
            stream=True,
            stream_intermediate_steps=True,
            session_id=conversation_id,
        )
        async for event in response_stream:
            if event.event == "RunContent":
                yield streaming.message_chunk(event.content)
            elif event.event == "ToolCallStarted":
                yield streaming.tool_call_started(
                    event.tool.tool_call_id, event.tool.tool_name
                )
            elif event.event == "ToolCallCompleted":
                yield streaming.tool_call_completed(
                    event.tool.result, event.tool.tool_call_id, event.tool.tool_name
                )
        logger.info("News query processing completed")

        yield streaming.done()

    async def run(
        self, query: str, conversation_id: Optional[str] = None, **kwargs
    ) -> str:
        """
        Run news query and return the complete response.

        Args:
            query: The user's news query
            conversation_id: Optional conversation ID for context
            **kwargs: Additional parameters

        Returns:
            Complete news response as string
        """
        try:
            logger.info(f"Running news query: {query}")

            # Get the complete response from the knowledge news agent
            response = await self.knowledge_news_agent.arun(query)

            return response.content

        except Exception as e:
            logger.error(f"Error in NewsAgent run: {e}")
            return f"Error processing news query: {str(e)}"

    def get_capabilities(self) -> dict:
        """Get the capabilities and available tools of the News Agent."""
        # Get capabilities from configuration if available
        if self.agent_config:
            config_capabilities = self.agent_config.capabilities

            # Build tools list based on enabled capabilities
            enabled_tools = []
            if config_capabilities.get("web_search", {}).get("enabled", True):
                enabled_tools.append("web_search")
            if config_capabilities.get("breaking_news", {}).get("enabled", True):
                enabled_tools.append("get_breaking_news")
            if config_capabilities.get("financial_news", {}).get("enabled", True):
                enabled_tools.append("get_financial_news")

            # Build capabilities list based on configuration
            capabilities_list = []
            if config_capabilities.get("web_search", {}).get("enabled", True):
                capabilities_list.extend(
                    ["Real-time news search", "Topic-based news analysis"]
                )
            if config_capabilities.get("breaking_news", {}).get("enabled", True):
                capabilities_list.append("Categorized news retrieval")
            if config_capabilities.get("financial_news", {}).get("enabled", True):
                capabilities_list.extend(
                    [
                        "Comprehensive stock news analysis",
                        "Macroeconomic news",
                        "Industry sector news",
                        "Individual stock news analysis",
                    ]
                )
            if config_capabilities.get("languages", {}).get("enabled", True):
                capabilities_list.append("Multi-language support")
            if config_capabilities.get("analysis", {}).get("sentiment_analysis", True):
                capabilities_list.append("Intelligent news summarization")

            return {
                "name": "news_agent",
                "description": "Professional news query and analysis agent supporting multiple news sources and query types",
                "tools": enabled_tools,
                "capabilities": capabilities_list,
                "enabled": self.agent_config.enabled,
            }

        # Fallback to default capabilities if no config found
        return {
            "name": "news_agent",
            "description": "Professional news query and analysis agent supporting multiple news sources and query types",
            "tools": ["web_search", "get_breaking_news", "get_financial_news"],
            "capabilities": [
                "Real-time news search",
                "Categorized news retrieval",
                "Topic-based news analysis",
                "Comprehensive stock news analysis",
                "Macroeconomic news",
                "Industry sector news",
                "Individual stock news analysis",
                "Multi-language support",
                "Intelligent news summarization",
            ],
            "enabled": True,
        }
