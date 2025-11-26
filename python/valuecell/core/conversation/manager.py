import json
from datetime import datetime
from typing import List, Optional

from loguru import logger

from valuecell.core.types import (
    ComponentType,
    ConversationItem,
    ConversationItemEvent,
    ResponseMetadata,
    ResponsePayload,
    Role,
)
from valuecell.utils.uuid import generate_conversation_id, generate_item_id

from .conversation_store import ConversationStore, InMemoryConversationStore
from .item_store import InMemoryItemStore, ItemStore
from .models import Conversation, ConversationStatus


class ConversationManager:
    """High-level manager coordinating conversation metadata and items.

    Conversation metadata is delegated to a ConversationStore while message
    items are delegated to an ItemStore. This class exposes convenience
    methods for creating conversations, adding items, and querying state.
    """

    def __init__(
        self,
        conversation_store: Optional[ConversationStore] = None,
        item_store: Optional[ItemStore] = None,
    ):
        self.conversation_store = conversation_store or InMemoryConversationStore()
        self.item_store = item_store or InMemoryItemStore()

    async def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None,
        conversation_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> Conversation:
        """Create new conversation"""
        conversation = Conversation(
            conversation_id=conversation_id or generate_conversation_id(),
            user_id=user_id,
            title=title,
            agent_name=agent_name,
        )
        await self.conversation_store.save_conversation(conversation)
        return conversation

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation metadata"""
        return await self.conversation_store.load_conversation(conversation_id)

    async def update_conversation(self, conversation: Conversation) -> None:
        """Update conversation metadata"""
        conversation.updated_at = datetime.now()
        await self.conversation_store.save_conversation(conversation)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation and all its items"""
        # First delete all items for this conversation
        await self.item_store.delete_conversation_items(conversation_id)

        # Then delete the conversation metadata
        return await self.conversation_store.delete_conversation(conversation_id)

    async def list_user_conversations(
        self, user_id: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Conversation]:
        """List conversations. If user_id is None, return all conversations."""
        return await self.conversation_store.list_conversations(user_id, limit, offset)

    async def conversation_exists(self, conversation_id: str) -> bool:
        """Check if conversation exists"""
        return await self.conversation_store.conversation_exists(conversation_id)

    async def add_item(
        self,
        role: Role,
        event: ConversationItemEvent,
        conversation_id: str,
        thread_id: Optional[str] = None,
        task_id: Optional[str] = None,
        payload: Optional[ResponsePayload] = None,
        item_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        metadata: Optional[ResponseMetadata] = None,
    ) -> Optional[ConversationItem]:
        """Add item to conversation

        Args:
            conversation_id: Conversation ID to add item to
            role: Item role (USER, AGENT, SYSTEM)
            event: Item event
            thread_id: Thread ID (optional)
            task_id: Associated task ID (optional)
            payload: Item payload
            item_id: Item ID (optional)
            agent_name: Agent name (optional)
            metadata: Additional metadata as dict (optional)
        """
        # Verify conversation exists
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return None

        # Create item
        # Serialize payload to JSON string if it's a pydantic model
        payload_str = None
        if payload is not None:
            try:
                # pydantic BaseModel supports model_dump_json
                payload_str = payload.model_dump_json(exclude_none=True)
            except Exception:
                try:
                    payload_str = str(payload)
                except Exception:
                    payload_str = None

        # Serialize metadata to JSON string
        metadata_str = None
        if metadata is not None:
            try:
                metadata_str = json.dumps(metadata, default=str)
            except Exception:
                metadata_str = "{}"
        metadata_str = metadata_str or "{}"

        item = ConversationItem(
            item_id=item_id or generate_item_id(),
            role=role,
            event=event,
            conversation_id=conversation_id,
            thread_id=thread_id,
            task_id=task_id,
            payload=payload_str,
            agent_name=agent_name,
            metadata=metadata_str,
        )

        # Save item directly to item store
        await self.item_store.save_item(item)

        # Update conversation timestamp
        conversation.touch()
        await self.conversation_store.save_conversation(conversation)

        return item

    async def get_conversation_items(
        self,
        conversation_id: Optional[str] = None,
        event: Optional[ConversationItemEvent] = None,
        component_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ConversationItem]:
        """Get items for a conversation with optional filtering and pagination

        Args:
            conversation_id: Conversation ID
            event: Filter by specific event (optional)
            component_type: Filter by component type (optional)
            limit: Maximum number of items to return (optional, default: all)
            offset: Number of items to skip (optional, default: 0)
        """
        return await self.item_store.get_items(
            conversation_id=conversation_id,
            event=event,
            component_type=component_type,
            limit=limit,
            offset=offset or 0,
        )

    async def get_latest_item(self, conversation_id: str) -> Optional[ConversationItem]:
        """Get latest item in a conversation"""
        return await self.item_store.get_latest_item(conversation_id)

    async def get_item(self, item_id: str) -> Optional[ConversationItem]:
        """Get a specific item by ID"""
        return await self.item_store.get_item(item_id)

    async def get_item_count(self, conversation_id: str) -> int:
        """Get total item count for a conversation"""
        return await self.item_store.get_item_count(conversation_id)

    async def get_items_by_role(
        self, conversation_id: str, role: Role
    ) -> List[ConversationItem]:
        """Get items filtered by role"""
        return await self.item_store.get_items(conversation_id, role=role)

    async def deactivate_conversation(self, conversation_id: str) -> bool:
        """Deactivate conversation"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False

        conversation.deactivate()
        await self.conversation_store.save_conversation(conversation)
        return True

    async def activate_conversation(self, conversation_id: str) -> bool:
        """Activate conversation"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False

        conversation.activate()
        await self.conversation_store.save_conversation(conversation)
        return True

    async def set_conversation_status(
        self, conversation_id: str, status: ConversationStatus
    ) -> bool:
        """Set conversation status"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False

        conversation.set_status(status)
        await self.conversation_store.save_conversation(conversation)
        return True

    async def require_user_input(self, conversation_id: str) -> bool:
        """Mark conversation as requiring user input"""
        return await self.set_conversation_status(
            conversation_id, ConversationStatus.REQUIRE_USER_INPUT
        )

    async def update_task_component_status(
        self,
        task_id: str,
        status: str,
        error_reason: Optional[str] = None,
    ) -> None:
        """Update persisted scheduled task controller component's status and error reason.

        For a given task_id, find the persisted conversation item with
        component_type='scheduled_task_controller', update its payload's
        task_status field, and set error_reason in metadata if provided.

        Args:
            task_id: The task identifier to search for.
            status: New task status value (e.g., 'failed').
            error_reason: Optional error details to store in metadata.
        """
        items = await self.item_store.get_items(task_id=task_id)
        for item in items:
            # Check if this is a scheduled_task_controller component
            if not item.payload:
                continue
            try:
                payload_obj = json.loads(item.payload)
                if (
                    payload_obj.get("component_type")
                    != ComponentType.SCHEDULED_TASK_CONTROLLER
                ):
                    continue
            except Exception:
                continue

            # Update task_status in payload and error_reason in metadata
            try:
                payload_obj = json.loads(item.payload)
                content = payload_obj.get("content") or "{}"
                content_obj = json.loads(content)
                content_obj["task_status"] = status
                payload_obj["content"] = json.dumps(content_obj)
                item.payload = json.dumps(payload_obj)

                # Update metadata with error reason if provided
                metadata_obj = json.loads(item.metadata or "{}")
                if error_reason:
                    metadata_obj["error_reason"] = error_reason
                item.metadata = json.dumps(metadata_obj, default=str)

                await self.item_store.save_item(item)
            except Exception as e:
                logger.warning(
                    f"Failed to update task component status for task {task_id}: {e}"
                )

    async def get_conversations_by_status(
        self,
        user_id: str,
        status: ConversationStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Conversation]:
        """Get user conversations filtered by status"""
        # Get all user conversations and filter by status
        # Note: This could be optimized by adding status filtering to the store interface
        all_conversations = await self.conversation_store.list_conversations(
            user_id, limit * 2, offset
        )
        return [
            conversation
            for conversation in all_conversations
            if conversation.status == status
        ][:limit]
