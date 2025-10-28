"""Conversation API routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query

from valuecell.server.services.conversation_service import get_conversation_service

from ..schemas.conversation import (
    ConversationDeleteResponse,
    ConversationHistoryResponse,
    ConversationListResponse,
)


def create_conversation_router() -> APIRouter:
    """Create conversation router."""
    router = APIRouter(prefix="/conversations", tags=["Conversations"])

    @router.get(
        "/",
        response_model=ConversationListResponse,
        summary="Get conversation list",
        description="Get a list of conversations with optional filtering and pagination",
    )
    async def get_conversations(
        user_id: Optional[str] = Query(None, description="Filter by user ID"),
        limit: int = Query(
            10, ge=1, le=100, description="Number of conversations to return"
        ),
        offset: int = Query(0, ge=0, description="Number of conversations to skip"),
    ) -> ConversationListResponse:
        """Get conversation list."""
        service = get_conversation_service()
        data = await service.get_conversation_list(
            user_id=user_id, limit=limit, offset=offset
        )
        return ConversationListResponse.create(
            data=data, msg="Conversations retrieved successfully"
        )

    @router.get(
        "/{conversation_id}/history",
        response_model=ConversationHistoryResponse,
        summary="Get conversation history",
        description="Get the complete message history for a specific conversation",
    )
    async def get_conversation_history(
        conversation_id: str = Path(..., description="The conversation ID"),
    ) -> ConversationHistoryResponse:
        """Get conversation history."""
        try:
            service = get_conversation_service()
            data = await service.get_conversation_history(
                conversation_id=conversation_id
            )
            return ConversationHistoryResponse.create(
                data=data, msg="Conversation history retrieved successfully"
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Internal server error: {str(e)}"
            )

    @router.get(
        "/{conversation_id}/scheduled-task-results",
        response_model=ConversationHistoryResponse,
        summary="Get conversation scheduled task results",
        description="Get scheduled task results for a specific conversation",
    )
    async def get_conversation_scheduled_task_results(
        conversation_id: str = Path(..., description="The conversation ID"),
    ) -> ConversationHistoryResponse:
        """Get conversation scheduled task results."""
        try:
            service = get_conversation_service()
            data = await service.get_conversation_scheduled_task_results(
                conversation_id=conversation_id
            )
            return ConversationHistoryResponse.create(
                data=data,
                msg="Conversation scheduled task results retrieved successfully",
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Internal server error: {str(e)}"
            )

    @router.delete(
        "/{conversation_id}",
        response_model=ConversationDeleteResponse,
        summary="Delete conversation",
        description="Delete a specific conversation and all its associated data",
    )
    async def delete_conversation(
        conversation_id: str = Path(..., description="The conversation ID to delete"),
    ) -> ConversationDeleteResponse:
        """Delete conversation."""
        try:
            service = get_conversation_service()
            data = await service.delete_conversation(conversation_id=conversation_id)

            if data.deleted:
                return ConversationDeleteResponse.create(
                    data=data, msg="Conversation deleted successfully"
                )
            else:
                raise HTTPException(
                    status_code=500, detail="Failed to delete conversation"
                )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Internal server error: {str(e)}"
            )

    return router
