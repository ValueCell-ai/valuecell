"""Conversation API schemas."""

from typing import List

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


# Response type for conversation list
ConversationListResponse = SuccessResponse[ConversationListData]
