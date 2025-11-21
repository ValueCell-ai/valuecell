"""Conversation service for managing conversation data."""

from typing import Optional

from valuecell.core.conversation import (
    ConversationManager,
    SQLiteConversationStore,
    SQLiteItemStore,
)
from valuecell.core.conversation.service import (
    ConversationService as CoreConversationService,
)
from valuecell.core.event.factory import ResponseFactory
from valuecell.core.types import CommonResponseEvent, ComponentType
from valuecell.server.api.schemas.conversation import (
    AgentScheduledTaskResults,
    AllConversationsScheduledTaskData,
    ConversationDeleteData,
    ConversationHistoryData,
    ConversationHistoryItem,
    ConversationListData,
    ConversationListItem,
    MessageData,
)
from valuecell.utils import resolve_db_path

# Agent names used by strategy creation flows; conversations from these agents
# should be excluded from the general conversation list returned to clients.
# Keep this set small and focused; extend if new strategy agents are added.
STRATEGY_AGENT_NAMES = {
    "PromptBasedStrategyAgent",
    "GridStrategyAgent",
}


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
        self.core_conversation_service = CoreConversationService(
            manager=self.conversation_manager
        )
        self.response_factory = ResponseFactory()

    async def get_conversation_list(
        self, user_id: Optional[str] = None, limit: int = 10, offset: int = 0
    ) -> ConversationListData:
        """Get a list of conversations with optional filtering and pagination."""
        # Get conversations from the manager
        conversations = await self.conversation_manager.list_user_conversations(
            user_id=user_id
        )

        # Exclude conversations initiated by strategy agents from general listing.
        # We match by known names and a conservative substring check to future-proof.
        conversations = [
            conv
            for conv in conversations
            if not (
                (conv.agent_name or "") in STRATEGY_AGENT_NAMES
                or (
                    (conv.agent_name or "")
                    and "StrategyAgent" in (conv.agent_name or "")
                )
            )
        ]

        # Apply pagination
        total = len(conversations)

        # Convert to response format
        conversation_items = []
        for conv in conversations:
            conversation_item = ConversationListItem(
                conversation_id=conv.conversation_id,
                title=conv.title or f"Conversation {conv.conversation_id}",
                agent_name=conv.agent_name,
                update_time=(
                    conv.updated_at.isoformat()
                    if conv.updated_at
                    else conv.created_at.isoformat()
                ),
            )
            conversation_items.append(conversation_item)

        return ConversationListData(conversations=conversation_items, total=total)

    async def _validate_conversation_exists(self, conversation_id: str) -> None:
        """Validate that a conversation exists, raise ValueError if not found."""
        conversation = await self.conversation_manager.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

    def _convert_response_to_history_item(self, response) -> ConversationHistoryItem:
        """Convert a BaseResponse to ConversationHistoryItem."""
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
        if data.agent_name:
            message_data_with_meta.agent_name = data.agent_name
        if data.metadata:
            message_data_with_meta.metadata = data.metadata

        return ConversationHistoryItem(event=event_str, data=message_data_with_meta)

    async def get_conversation_history(
        self, conversation_id: str
    ) -> ConversationHistoryData:
        """Get conversation history for a specific conversation."""
        # Check if conversation exists
        await self._validate_conversation_exists(conversation_id)

        # Retrieve persisted conversation items and rebuild responses
        conversation_items = (
            await self.core_conversation_service.get_conversation_items(
                conversation_id=conversation_id,
            )
        )

        base_responses = []
        for item in conversation_items:
            resp = self.response_factory.from_conversation_item(item)
            # Exclude scheduled task results from general history
            if (
                resp.event == CommonResponseEvent.COMPONENT_GENERATOR.value
                and resp.data.payload
                and getattr(resp.data.payload, "component_type", None)
                == ComponentType.SCHEDULED_TASK_RESULT.value
            ):
                continue  # Skip scheduled task results in general history

            base_responses.append(resp)

        # Convert BaseResponse objects to ConversationHistoryItem objects
        history_items = [
            self._convert_response_to_history_item(response)
            for response in base_responses
        ]

        return ConversationHistoryData(
            conversation_id=conversation_id, items=history_items
        )

    async def get_conversation_scheduled_task_results(
        self, conversation_id: str
    ) -> ConversationHistoryData:
        """Get scheduled task results for a specific conversation."""
        # Check if conversation exists
        await self._validate_conversation_exists(conversation_id)

        # Retrieve persisted conversation items and rebuild responses
        conversation_items = (
            await self.core_conversation_service.get_conversation_items(
                conversation_id=conversation_id,
                event=CommonResponseEvent.COMPONENT_GENERATOR.value,
                component_type=ComponentType.SCHEDULED_TASK_RESULT.value,
            )
        )

        base_responses = [
            self.response_factory.from_conversation_item(item)
            for item in conversation_items
        ]

        # Convert BaseResponse objects to ConversationHistoryItem objects
        history_items = [
            self._convert_response_to_history_item(response)
            for response in base_responses
        ]

        return ConversationHistoryData(
            conversation_id=conversation_id, items=history_items
        )

    async def get_all_conversations_scheduled_task_results(
        self, user_id: Optional[str] = None
    ) -> AllConversationsScheduledTaskData:
        """Get scheduled task results from all conversations, grouped by agent name."""
        # Get all conversations
        conversations = await self.conversation_manager.list_user_conversations(
            user_id=user_id
        )

        # Dictionary to group results by agent name and track latest message times
        agent_results = {}
        agent_latest_times = {}

        # Process each conversation
        for conversation in conversations:
            # Get conversation items
            conversation_items = await self.conversation_manager.get_conversation_items(
                conversation.conversation_id
            )

            # Filter for scheduled task results
            # Note: ConversationItem.payload is a JSON string, not an object
            scheduled_task_items = []
            for item in conversation_items:
                if (
                    hasattr(item, "event")
                    and item.event == CommonResponseEvent.COMPONENT_GENERATOR
                ):
                    # Parse the payload JSON string to check component_type
                    try:
                        import json

                        payload_data = json.loads(item.payload)
                        if (
                            payload_data.get("component_type")
                            == ComponentType.SCHEDULED_TASK_RESULT
                        ):
                            scheduled_task_items.append(item)
                    except (json.JSONDecodeError, AttributeError):
                        # Skip items with invalid payload
                        continue

            # Convert to history items and group by agent
            for item in scheduled_task_items:
                # Convert ConversationItem to BaseResponse first
                response = self.response_factory.from_conversation_item(item)
                history_item = self._convert_response_to_history_item(response)
                agent_name = conversation.agent_name or "Unknown Agent"

                if agent_name not in agent_results:
                    agent_results[agent_name] = []
                    agent_latest_times[agent_name] = None

                agent_results[agent_name].append(history_item)

                # Get the latest message time for this agent from the conversation
                # We'll use the conversation's updated_at as a proxy for the latest message time
                if (
                    agent_latest_times[agent_name] is None
                    or conversation.updated_at > agent_latest_times[agent_name]
                ):
                    agent_latest_times[agent_name] = conversation.updated_at

        # Convert to response format with latest message times
        agents = [
            AgentScheduledTaskResults(
                agent_name=agent_name,
                results=results,
                update_time=agent_latest_times[agent_name],
            )
            for agent_name, results in agent_results.items()
        ]

        return AllConversationsScheduledTaskData(agents=agents)

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
