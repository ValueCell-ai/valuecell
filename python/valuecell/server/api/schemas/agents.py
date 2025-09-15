"""Agent schemas for ValueCell Server."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class AgentBase(BaseModel):
    """Base agent model."""
    
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    agent_type: str = Field(..., description="Type of agent (e.g., 'sec_13f', 'calculator')")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")
    is_active: bool = Field(True, description="Whether the agent is active")


class AgentCreateRequest(AgentBase):
    """Request model for creating an agent."""
    pass


class AgentUpdateRequest(BaseModel):
    """Request model for updating an agent."""
    
    name: Optional[str] = Field(None, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    config: Optional[Dict[str, Any]] = Field(None, description="Agent configuration")
    is_active: Optional[bool] = Field(None, description="Whether the agent is active")


class AgentResponse(AgentBase):
    """Response model for agent data."""
    
    id: str = Field(..., description="Agent ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "agent_123",
                "name": "SEC 13F Analyzer",
                "description": "Analyzes SEC 13F filings for institutional holdings",
                "agent_type": "sec_13f",
                "config": {
                    "model": "gpt-4",
                    "temperature": 0.7
                },
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }


class AgentExecutionRequest(BaseModel):
    """Request model for agent execution."""
    
    input_data: Dict[str, Any] = Field(..., description="Input data for the agent")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Execution parameters")
    
    class Config:
        schema_extra = {
            "example": {
                "input_data": {
                    "query": "Analyze Berkshire Hathaway's latest 13F filing",
                    "ticker": "BRK.A"
                },
                "parameters": {
                    "streaming": True,
                    "timeout": 300
                }
            }
        }


class AgentExecutionResponse(BaseModel):
    """Response model for agent execution."""
    
    execution_id: str = Field(..., description="Execution ID")
    agent_id: str = Field(..., description="Agent ID")
    status: str = Field(..., description="Execution status")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution completion time")
    
    class Config:
        schema_extra = {
            "example": {
                "execution_id": "exec_456",
                "agent_id": "agent_123",
                "status": "completed",
                "result": {
                    "content": "Analysis of Berkshire Hathaway's 13F filing...",
                    "is_task_complete": True
                },
                "error": None,
                "started_at": "2024-01-01T00:00:00Z",
                "completed_at": "2024-01-01T00:05:00Z"
            }
        }