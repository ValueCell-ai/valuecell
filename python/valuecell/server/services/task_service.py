"""Task API service: bridges TaskService and conversation item updates."""

from __future__ import annotations

import json
from typing import List

from valuecell.core.task.locator import get_task_service
from valuecell.core.types import CommonResponseEvent, ComponentType
from valuecell.server.api.schemas.task import TaskCancelData
from valuecell.server.services.conversation_service import get_conversation_service


class TaskApiService:
    """Orchestrates task cancellation and related conversation component updates."""

    def __init__(self) -> None:
        # Use core conversation service instead of direct store access
        self.conversation_service = get_conversation_service().core_conversation_service
        self.task_service = get_task_service()

    async def cancel_and_update_component(self, task_id: str) -> TaskCancelData:
        """Cancel a task and update any matching scheduled_task_controller components.

        Steps:
        - Attempt to cancel the task using TaskService
        - Find component_generator items of type scheduled_task_controller with matching task_id
        - Update the nested content.task_status to 'cancelled' and persist
        """

        cancelled = await self.task_service.cancel_task(task_id)

        updated_ids: List[str] = []
        if cancelled:
            # Fetch all controller components, filter by task_id, update payload
            items = await self.conversation_service.get_conversation_items(
                event=CommonResponseEvent.COMPONENT_GENERATOR.value,
                component_type=ComponentType.SCHEDULED_TASK_CONTROLLER.value,
            )

            for item in items:
                if item.task_id != task_id:
                    # As a fallback, inspect payload content if task_id column isn't set
                    try:
                        payload_obj = json.loads(item.payload or "{}")
                        content_raw = payload_obj.get("content")
                        if content_raw and isinstance(content_raw, str):
                            content_obj = json.loads(content_raw)
                            embedded_id = content_obj.get("task_id")
                            if embedded_id != task_id:
                                continue
                        else:
                            # If no content, skip
                            continue
                    except Exception:
                        continue

                # We have a match; update content.task_status to 'cancelled'
                try:
                    payload_obj = json.loads(item.payload or "{}")
                    content_raw = payload_obj.get("content")
                    if isinstance(content_raw, str):
                        content_obj = json.loads(content_raw)
                    else:
                        content_obj = {}

                    content_obj["task_status"] = "cancelled"
                    payload_obj["content"] = json.dumps(content_obj, ensure_ascii=False)

                    # Save back via core conversation service using same item_id
                    # Preserve metadata by parsing original string into dict
                    try:
                        metadata_dict = (
                            json.loads(item.metadata) if item.metadata else None
                        )
                    except Exception:
                        metadata_dict = None

                    await self.conversation_service.add_item(
                        role=item.role,
                        event=item.event,
                        conversation_id=item.conversation_id,
                        thread_id=item.thread_id,
                        task_id=item.task_id,
                        payload=json.dumps(payload_obj, ensure_ascii=False),
                        item_id=item.item_id,
                        agent_name=item.agent_name,
                        metadata=metadata_dict,
                    )
                    updated_ids.append(item.item_id)
                except Exception:
                    # Skip broken payloads; continue updating others
                    continue

        return TaskCancelData(
            task_id=task_id,
            success=cancelled,
            updated_component_ids=updated_ids,
        )
