"""High-level service wrapper for conversation operations."""

from __future__ import annotations

from typing import List, Optional, Tuple

from valuecell.core.conversation.manager import ConversationManager
from valuecell.core.conversation.models import Conversation, ConversationStatus
from valuecell.core.types import (
    ConversationItem,
    ConversationItemEvent,
    ResponseMetadata,
    ResponsePayload,
    Role,
)


class ConversationService:
    """Expose conversation operations without tying them to the orchestrator."""

    def __init__(self, manager: ConversationManager) -> None:
        self._manager = manager

    @property
    def manager(self) -> ConversationManager:
        return self._manager

    async def ensure_conversation(
        self,
        user_id: str,
        conversation_id: str,
        title: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> Tuple[Conversation, bool]:
        """Return the conversation, creating it if it does not exist."""

        conversation = await self._manager.get_conversation(conversation_id)
        created = False
        if conversation is None:
            conversation = await self._manager.create_conversation(
                user_id=user_id,
                title=title,
                conversation_id=conversation_id,
                agent_name=agent_name,
            )
            created = True
        return conversation, created

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return await self._manager.get_conversation(conversation_id)

    async def activate(self, conversation_id: str) -> bool:
        conversation = await self._manager.get_conversation(conversation_id)
        if not conversation:
            return False
        conversation.activate()
        await self._manager.update_conversation(conversation)
        return True

    async def require_user_input(self, conversation_id: str) -> bool:
        conversation = await self._manager.get_conversation(conversation_id)
        if not conversation:
            return False
        conversation.require_user_input()
        await self._manager.update_conversation(conversation)
        return True

    async def set_status(
        self, conversation_id: str, status: ConversationStatus
    ) -> bool:
        conversation = await self._manager.get_conversation(conversation_id)
        if not conversation:
            return False
        conversation.set_status(status)
        await self._manager.update_conversation(conversation)
        return True

    async def add_item(
        self,
        *,
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
        """Persist a conversation item via the underlying manager.

        Args:
            role: Item role (USER, AGENT, SYSTEM)
            event: Item event
            conversation_id: Conversation ID
            thread_id: Thread ID (optional)
            task_id: Task ID (optional)
            payload: Item payload
            item_id: Item ID (optional)
            agent_name: Agent name (optional)
            metadata: Additional metadata as dict (optional)
        """

        return await self._manager.add_item(
            role=role,
            event=event,
            conversation_id=conversation_id,
            thread_id=thread_id,
            task_id=task_id,
            payload=payload,
            item_id=item_id,
            agent_name=agent_name,
            metadata=metadata,
        )

    async def get_conversation_items(
        self,
        conversation_id: Optional[str] = None,
        event: Optional[ConversationItemEvent] = None,
        component_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ConversationItem]:
        """Load conversation items with optional filtering and pagination.

        Args:
            conversation_id: Filter by conversation ID (optional)
            event: Filter by event type (optional)
            component_type: Filter by component type (optional)
            limit: Maximum number of items to return (optional, default: all)
            offset: Number of items to skip (optional, default: 0)
        """

        return await self._manager.get_conversation_items(
            conversation_id=conversation_id,
            event=event,
            component_type=component_type,
            limit=limit,
            offset=offset,
        )

    async def update_task_component_status(
        self,
        task_id: str,
        status: str,
        error_reason: Optional[str] = None,
    ) -> None:
        """Update persisted scheduled task component's status and error.

        Args:
            task_id: The task identifier.
            status: New status (e.g., 'failed').
            error_reason: Optional error reason for metadata.
        """
        return await self._manager.update_task_component_status(
            task_id=task_id,
            status=status,
            error_reason=error_reason,
        )
