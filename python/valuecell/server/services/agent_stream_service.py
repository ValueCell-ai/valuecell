"""
Agent stream service for handling streaming agent interactions.
"""

from typing import AsyncGenerator, Optional
from valuecell.core.coordinate.orchestrator import get_default_orchestrator
from valuecell.core.coordinate.tests.test_orchestrator import session_id
from valuecell.core.types import UserInput, UserInputMetadata
import logging

logger = logging.getLogger(__name__)


class AgentStreamService:
    """Service for handling streaming agent queries."""

    def __init__(self):
        """Initialize the agent stream service."""
        self.orchestrator = get_default_orchestrator()
        logger.info("Agent stream service initialized")

    async def stream_query_agent(
        self, query: str, agent_name: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream agent responses for a given query.

        Args:
            query: User query to process
            agent_name: Optional specific agent name to use. If provided, takes precedence over query parsing.

        Yields:
            str: Content chunks from the agent response
        """
        try:
            logger.info(f"Processing streaming query: {query[:100]}...")

            user_id = "default_user"
            desired_agent_name = agent_name
            session_id = agent_name + "_session_" + user_id

            user_input_meta = UserInputMetadata(user_id=user_id, session_id=session_id)

            user_input = UserInput(
                query=query, desired_agent_name=desired_agent_name, meta=user_input_meta
            )

            # Use the orchestrator's process_user_input method for streaming
            async for response_chunk in self.orchestrator.process_user_input(
                user_input
            ):
                if (
                    response_chunk
                    and response_chunk.content
                    and response_chunk.content.strip()
                ):
                    yield response_chunk.content

        except Exception as e:
            logger.error(f"Error in stream_query_agent: {str(e)}")
            yield f"Error processing query: {str(e)}"
