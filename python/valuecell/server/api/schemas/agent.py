"""
Agent API schemas for handling agent-related requests and responses.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from .base import SuccessResponse


class AgentCapabilities(BaseModel):
    """Agent capabilities model."""

    streaming: bool = Field(False, description="Whether the agent supports streaming")
    push_notifications: bool = Field(
        False, description="Whether the agent supports push notifications"
    )


class AgentMetadata(BaseModel):
    """Agent metadata model."""

    version: Optional[str] = Field(None, description="Agent version")
    author: Optional[str] = Field(None, description="Agent author")
    tags: Optional[List[str]] = Field(None, description="Agent tags")


class AgentData(BaseModel):
    """Data model for a single agent."""

    id: int = Field(..., description="Agent unique ID")
    agent_name: str = Field(..., description="Agent unique name/identifier")
    display_name: Optional[str] = Field(None, description="Human-readable display name")
    description: Optional[str] = Field(None, description="Agent description")
    version: Optional[str] = Field(None, description="Agent version")
    enabled: bool = Field(..., description="Whether the agent is enabled")
    icon_url: Optional[str] = Field(None, description="Agent icon URL")
    agent_metadata: Optional[Dict[str, Any]] = Field(None, description="Agent metadata")
    config: Optional[Dict[str, Any]] = Field(None, description="Agent configuration")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "agent_name": "MarketAnalystAgent",
                "display_name": "Market Analyst Agent",
                "description": "AI-powered market analysis agent",
                "version": "1.0.0",
                "enabled": True,
                "icon_url": "https://example.com/icons/market_analyst.png",
                "agent_metadata": {
                    "author": "ValueCell Team",
                    "tags": ["market", "analysis", "ai"],
                },
                "config": {},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }


class AgentListData(BaseModel):
    """Data model for agent list."""

    agents: List[AgentData] = Field(..., description="List of agents")
    total: int = Field(..., description="Total number of agents")
    enabled_count: int = Field(..., description="Number of enabled agents")

    class Config:
        json_schema_extra = {
            "example": {
                "agents": [
                    {
                        "id": 1,
                        "agent_name": "MarketAnalystAgent",
                        "display_name": "Market Analyst Agent",
                        "description": "AI-powered market analysis agent",
                        "version": "1.0.0",
                        "enabled": True,
                        "icon_url": "https://example.com/icons/market_analyst.png",
                        "agent_metadata": {
                            "author": "ValueCell Team",
                            "tags": ["market", "analysis", "ai"],
                        },
                        "config": {},
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                    }
                ],
                "total": 1,
                "enabled_count": 1,
            }
        }


class AgentQueryParams(BaseModel):
    """Query parameters for agent list."""

    enabled_only: Optional[bool] = Field(
        False, description="Filter only enabled agents"
    )
    name_filter: Optional[str] = Field(
        None, description="Filter by agent name (partial match)"
    )


# Type aliases for SuccessResponse
AgentResponse = SuccessResponse[AgentData]
AgentListResponse = SuccessResponse[AgentListData]
