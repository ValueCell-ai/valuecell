"""
Agent stream API schemas for handling streaming agent queries.
"""

from typing import Optional

from pydantic import BaseModel, Field


class AgentStreamRequest(BaseModel):
    """Request model for agent streaming queries."""

    query: str = Field(..., description="User query to send to the agent")
    agent_name: Optional[str] = Field(
        None, description="Specific agent name to use for the query"
    )
    conversation_id: Optional[str] = Field(
        None, description="Optional conversation ID for context tracking"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is the current market trend?",
                "agent_name": "MarketAnalystAgent",
            }
        }


class StreamChunk(BaseModel):
    """Response chunk model for streaming data."""

    content: str = Field(..., description="Content chunk from the agent response")
    is_final: bool = Field(False, description="Whether this is the final chunk")

    class Config:
        json_schema_extra = {
            "example": {"content": "The current market shows...", "is_final": False}
        }
