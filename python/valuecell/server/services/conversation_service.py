"""Conversation service for managing conversation data."""

from typing import Optional

from valuecell.core.conversation import (
    ConversationManager,
    SQLiteConversationStore,
    SQLiteItemStore,
)
from valuecell.core.coordinate.orchestrator import AgentOrchestrator
from valuecell.server.api.schemas.conversation import (
    ConversationDeleteData,
    ConversationHistoryData,
    ConversationHistoryItem,
    ConversationListData,
    ConversationListItem,
    MessageData,
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
                    extracted_name = latest_item.metadata.get("agent_name")
                    if extracted_name:
                        agent_name = extracted_name
                elif hasattr(latest_item, "agent_name") and latest_item.agent_name:
                    agent_name = latest_item.agent_name

            # Ensure agent_name is never None or empty
            if not agent_name or agent_name is None:
                agent_name = "unknown"

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

            # Convert payload to dict for JSON serialization
            payload_data = None
            if data.payload:
                try:
                    payload_data = (
                        data.payload.model_dump()
                        if hasattr(data.payload, "model_dump")
                        else str(data.payload)
                    )
                except Exception:
                    payload_data = str(data.payload)

            # Normalize event and role names
            event_str = self._normalize_event_name(str(response.event))
            role_str = self._normalize_role_name(str(data.role))

            # Create unified format: event and data at top level
            message_data_with_meta = MessageData(
                conversation_id=data.conversation_id,
                thread_id=data.thread_id,
                task_id=data.task_id,
                payload=payload_data,
                role=role_str,
                item_id=data.item_id,
            )

            history_item = ConversationHistoryItem(
                event=event_str, data=message_data_with_meta
            )

            history_items.append(history_item)

        return ConversationHistoryData(
            conversation_id=conversation_id, items=history_items
        )

    async def delete_conversation(self, conversation_id: str) -> ConversationDeleteData:
        """Delete a conversation and all its associated data."""
        # Check if conversation exists
        conversation = await self.conversation_manager.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        try:
            # Delete the conversation using the conversation manager
            await self.conversation_manager.delete_conversation(conversation_id)

            return ConversationDeleteData(conversation_id=conversation_id, deleted=True)
        except Exception:
            # If deletion fails, return False
            return ConversationDeleteData(
                conversation_id=conversation_id, deleted=False
            )

    def _normalize_role_name(self, role: str) -> str:
        """Normalize role name to match expected format."""
        role_lower = role.lower()
        if "user" in role_lower:
            return "user"
        elif "agent" in role_lower or "assistant" in role_lower:
            return "agent"
        elif "system" in role_lower:
            return "system"
        else:
            return "user"  # Default fallback

    def _normalize_event_name(self, event: str) -> str:
        """Normalize event name to match expected format."""
        event_lower = event.lower()

        # Map common event patterns to expected names
        if "message_chunk" in event_lower or "chunk" in event_lower:
            return "message_chunk"
        elif "reasoning" in event_lower:
            return "reasoning"
        elif "tool_call_completed" in event_lower or "tool_completed" in event_lower:
            return "tool_call_completed"
        elif "component_generator" in event_lower or "component" in event_lower:
            return "component_generator"
        elif "thread_started" in event_lower:
            return "thread_started"
        elif "task_started" in event_lower:
            return "task_started"
        else:
            # Extract the last part after the last dot or underscore
            parts = event.replace(".", "_").split("_")
            return "_".join(parts[-2:]).lower() if len(parts) > 1 else event.lower()


# Global service instance
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Get the global conversation service instance."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
