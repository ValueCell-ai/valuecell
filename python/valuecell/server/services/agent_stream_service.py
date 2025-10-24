"""
Agent stream service for handling streaming agent interactions.
"""

import logging
from typing import AsyncGenerator, Optional

from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.core.types import UserInput, UserInputMetadata
from valuecell.utils.uuid import generate_conversation_id

logger = logging.getLogger(__name__)


class AgentStreamService:
    """Service for handling streaming agent queries."""

    def __init__(self):
        """Initialize the agent stream service."""
        self.orchestrator = AgentOrchestrator()
        logger.info("Agent stream service initialized")

    async def stream_query_agent(
        self,
        query: str,
        agent_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream agent responses for a given query.

        Args:
            query: User query to process
            agent_name: Optional specific agent name to use. If provided, takes precedence over query parsing.
            conversation_id: Optional conversation ID for context tracking.

        Yields:
            str: Content chunks from the agent response
        """
        try:
            logger.info(f"Processing streaming query: {query[:100]}...")

            user_id = "default_user"
            target_agent_name = agent_name

            conversation_id = conversation_id or generate_conversation_id()

            user_input_meta = UserInputMetadata(
                user_id=user_id, conversation_id=conversation_id
            )

            user_input = UserInput(
                query=query, target_agent_name=target_agent_name, meta=user_input_meta
            )

            # Use the orchestrator's process_user_input method for streaming
            async for response_chunk in self.orchestrator.process_user_input(
                user_input
            ):
                yield response_chunk.model_dump(exclude_none=True)

        except Exception as e:
            logger.error(f"Error in stream_query_agent: {str(e)}")
            yield f"Error processing query: {str(e)}"
