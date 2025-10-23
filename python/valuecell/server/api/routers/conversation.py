"""Conversation API routes."""

from typing import Optional

from fastapi import APIRouter, Query

from valuecell.server.services.conversation_service import get_conversation_service

from ..schemas.conversation import ConversationListResponse


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

    return router
