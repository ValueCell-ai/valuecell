"""Conversation service for managing conversation data."""

from typing import Optional

from valuecell.core.conversation import (
    ConversationManager,
    SQLiteConversationStore,
    SQLiteItemStore,
)
from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.server.api.schemas.conversation import (
    ConversationHistoryData,
    ConversationHistoryItem,
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
        conversation_store = SQLiteConversationStore(db_path=db_path)
        self.conversation_manager = ConversationManager(
            conversation_store=conversation_store, item_store=self.item_store
        )
        self.orchestrator = AgentOrchestrator()

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
            latest_items = await self.item_store.get_items(
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

    async def get_conversation_history(
        self, conversation_id: str
    ) -> ConversationHistoryData:
        """Get conversation history for a specific conversation."""
        # Check if conversation exists
        conversation = await self.conversation_manager.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Get conversation history using orchestrator's method
        base_responses = await self.orchestrator.get_conversation_history(
            conversation_id=conversation_id
        )

        # Convert BaseResponse objects to ConversationHistoryItem objects
        history_items = []
        for response in base_responses:
            data = response.data

            # Extract content from payload
            content = None
            payload_data = None
            if data.payload:
                if hasattr(data.payload, "content"):
                    content = data.payload.content
                # Convert payload to dict for JSON serialization
                try:
                    payload_data = (
                        data.payload.model_dump()
                        if hasattr(data.payload, "model_dump")
                        else str(data.payload)
                    )
                except Exception:
                    payload_data = str(data.payload)

            history_item = ConversationHistoryItem(
                item_id=data.item_id,
                conversation_id=data.conversation_id,
                thread_id=data.thread_id,
                task_id=data.task_id,
                event=str(response.event),
                role=str(data.role),
                agent_name=data.agent_name,
                content=content,
                payload=payload_data,
                created_at="",  # Will be filled from database if available
            )
            history_items.append(history_item)

        # Get creation timestamps from the database
        conversation_items = await self.conversation_manager.get_conversation_items(
            conversation_id=conversation_id
        )

        # Create a mapping of item_id to created_at
        item_timestamps = {
            item.item_id: item.created_at.isoformat()
            if hasattr(item, "created_at") and item.created_at
            else ""
            for item in conversation_items
        }

        # Update history items with timestamps
        for history_item in history_items:
            if history_item.item_id in item_timestamps:
                history_item.created_at = item_timestamps[history_item.item_id]

        return ConversationHistoryData(
            conversation_id=conversation_id,
            messages=history_items,
            total=len(history_items),
        )


# Global service instance
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Get the global conversation service instance."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
