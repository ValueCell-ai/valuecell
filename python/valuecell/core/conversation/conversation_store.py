from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from .models import Conversation


class ConversationStore(ABC):
    """Conversation storage abstract base class - handles conversation metadata only.

    Items are stored separately using ItemStore implementations.
    """

    @abstractmethod
    async def save_conversation(self, conversation: Conversation) -> None:
        """Save conversation"""

    @abstractmethod
    async def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Load conversation"""

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation"""

    @abstractmethod
    async def list_conversations(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Conversation]:
        """List user conversations"""

    @abstractmethod
    async def conversation_exists(self, conversation_id: str) -> bool:
        """Check if conversation exists"""


class InMemoryConversationStore(ConversationStore):
    """In-memory conversation storage implementation"""

    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}

    async def save_conversation(self, conversation: Conversation) -> None:
        """Save conversation to memory"""
        self._conversations[conversation.conversation_id] = conversation

    async def load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Load conversation from memory"""
        return self._conversations.get(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation from memory"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False

    async def list_conversations(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Conversation]:
        """List user conversations"""
        user_conversations = [
            conversation
            for conversation in self._conversations.values()
            if conversation.user_id == user_id
        ]
        # Sort by creation time descending
        user_conversations.sort(key=lambda c: c.created_at, reverse=True)

        # Apply pagination
        start = offset
        end = offset + limit
        return user_conversations[start:end]

    async def conversation_exists(self, conversation_id: str) -> bool:
        """Check if conversation exists"""
        return conversation_id in self._conversations

    def clear_all(self) -> None:
        """Clear all conversations (for testing)"""
        self._conversations.clear()

    def get_conversation_count(self) -> int:
        """Get total conversation count (for debugging)"""
        return len(self._conversations)
