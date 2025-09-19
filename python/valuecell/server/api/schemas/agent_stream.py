"""
Agent stream API schemas for handling streaming agent queries.
"""

from pydantic import BaseModel, Field


class AgentStreamRequest(BaseModel):
    """Request model for agent streaming queries."""

    query: str = Field(..., description="User query to send to the agent")
    agent_name: str = Field(
        None, description="Specific agent name to use for the query"
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
