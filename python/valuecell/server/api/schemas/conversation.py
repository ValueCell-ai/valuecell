"""Conversation API schemas."""

from typing import Any, List, Optional

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


class ConversationHistoryItem(BaseModel):
    """Single message item in conversation history."""

    item_id: str = Field(..., description="Unique item identifier")
    conversation_id: str = Field(..., description="Conversation identifier")
    thread_id: Optional[str] = Field(None, description="Thread identifier")
    task_id: Optional[str] = Field(None, description="Task identifier")
    event: str = Field(..., description="Event type of the message")
    role: str = Field(..., description="Role of the message sender (user/agent/system)")
    agent_name: Optional[str] = Field(None, description="Name of the agent")
    content: Optional[str] = Field(None, description="Message content")
    payload: Optional[Any] = Field(None, description="Additional payload data")
    created_at: str = Field(..., description="Creation time in ISO format")


class ConversationHistoryData(BaseModel):
    """Data structure for conversation history response."""

    conversation_id: str = Field(..., description="Conversation identifier")
    messages: List[ConversationHistoryItem] = Field(
        ..., description="List of messages in chronological order"
    )
    total: int = Field(..., description="Total number of messages")


# Response type for conversation list
ConversationListResponse = SuccessResponse[ConversationListData]

# Response type for conversation history
ConversationHistoryResponse = SuccessResponse[ConversationHistoryData]
