"""Conversation service for managing conversation data."""

from typing import Optional

from valuecell.core.conversation import ConversationManager, SQLiteItemStore
from valuecell.server.api.schemas.conversation import (
    ConversationListData,
    ConversationListItem,
)
from valuecell.utils import resolve_db_path


class ConversationService:
    """Service for managing conversation operations."""

    def __init__(self):
        """Initialize the conversation service."""
        # Use the existing database path resolver
        db_path = resolve_db_path()
        self.item_store = SQLiteItemStore(db_path=db_path)
        self.conversation_manager = ConversationManager(item_store=self.item_store)

    async def get_conversation_list(
        self, user_id: Optional[str] = None, limit: int = 10, offset: int = 0
    ) -> ConversationListData:
        """Get a list of conversations with optional filtering and pagination."""
        # Get conversations from the manager
        conversations = await self.conversation_manager.list_user_conversations(
            user_id=user_id
        )

        # Apply pagination
        total = len(conversations)
        paginated_conversations = conversations[offset : offset + limit]

        # Convert to response format
        conversation_items = []
        for conv in paginated_conversations:
            # Get the latest item to extract agent_name
            latest_items = await self.item_store.list_items(
                conversation_id=conv.conversation_id, limit=1
            )

            agent_name = "unknown"
            if latest_items:
                # Try to extract agent_name from the latest item's metadata
                latest_item = latest_items[0]
                if hasattr(latest_item, "metadata") and latest_item.metadata:
                    agent_name = latest_item.metadata.get("agent_name", "unknown")
                elif hasattr(latest_item, "agent_name"):
                    agent_name = latest_item.agent_name

            conversation_item = ConversationListItem(
                conversation_id=conv.conversation_id,
                title=conv.title or f"Conversation {conv.conversation_id}",
                agent_name=agent_name,
                update_time=conv.updated_at.isoformat()
                if conv.updated_at
                else conv.created_at.isoformat(),
            )
            conversation_items.append(conversation_item)

        return ConversationListData(conversations=conversation_items, total=total)


# Global service instance
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Get the global conversation service instance."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
