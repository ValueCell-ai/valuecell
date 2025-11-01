"""Conversation API schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import SuccessResponse


class ConversationListItem(BaseModel):
    """Single conversation item in the list."""

    conversation_id: str = Field(..., description="Unique conversation identifier")
    title: str = Field(..., description="Conversation title")
    agent_name: str = Field(
        ..., description="Name of the agent associated with this conversation"
    )
    update_time: str = Field(..., description="Last update time in ISO format")


class ConversationListData(BaseModel):
    """Data structure for conversation list response."""

    conversations: List[ConversationListItem] = Field(
        ..., description="List of conversations"
    )
    total: int = Field(..., description="Total number of conversations")


class MessageData(BaseModel):
    """Data structure for message events."""

    conversation_id: str = Field(..., description="Conversation ID")
    thread_id: str = Field(..., description="Thread ID")
    task_id: Optional[str] = Field(None, description="Task ID")
    payload: Optional[Dict[str, Any]] = Field(None, description="Message payload")
    role: Optional[str] = Field(None, description="Role for simple event format")
    item_id: Optional[str] = Field(None, description="Item ID for simple event format")
    agent_name: Optional[str] = Field(None, description="Name of the agent")
    metadata: Optional[Dict[str, str | int | float]] = Field(
        None, description="Metadata"
    )


class MessageEvent(BaseModel):
    """Message event structure."""

    event: str = Field(..., description="Event type")
    data: MessageData = Field(..., description="Event data")


class ConversationHistoryItem(BaseModel):
    """A single item in conversation history."""

    # Unified format: event and data at top level
    event: str = Field(..., description="Event type")
    data: MessageData = Field(..., description="Event data")


class ConversationHistoryData(BaseModel):
    """Data structure for conversation history response."""

    conversation_id: str = Field(..., description="Conversation identifier")
    items: List[ConversationHistoryItem] = Field(
        ..., description="List of conversation items"
    )


class ConversationDeleteData(BaseModel):
    """Data structure for conversation deletion response."""

    conversation_id: str = Field(..., description="Deleted conversation identifier")
    deleted: bool = Field(
        ..., description="Whether the conversation was successfully deleted"
    )


class AgentScheduledTaskResults(BaseModel):
    """Scheduled task results for a specific agent."""

    agent_name: str = Field(..., description="Name of the agent")
    results: List[ConversationHistoryItem] = Field(
        ..., description="List of scheduled task results for this agent"
    )
    update_time: Optional[datetime] = Field(
        None, description="Timestamp of the latest message from this agent"
    )


class AllConversationsScheduledTaskData(BaseModel):
    """Data structure for all conversations scheduled task results."""

    agents: List[AgentScheduledTaskResults] = Field(
        ..., description="List of agents with their scheduled task results"
    )


# Response type for conversation list
ConversationListResponse = SuccessResponse[ConversationListData]

# Response type for conversation history
ConversationHistoryResponse = SuccessResponse[ConversationHistoryData]

# Response type for conversation deletion
ConversationDeleteResponse = SuccessResponse[ConversationDeleteData]

# Response type for all conversations scheduled task results
AllConversationsScheduledTaskResponse = SuccessResponse[
    AllConversationsScheduledTaskData
]
