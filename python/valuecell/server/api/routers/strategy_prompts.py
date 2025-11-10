"""Strategy Prompts API Router

Provides minimal endpoints to list and create strategy prompts.
Design: simple, no versioning, permissions, or pagination.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from valuecell.server.api.schemas.base import SuccessResponse
from valuecell.server.api.schemas.strategy import (
    PromptCreateRequest,
    PromptCreateResponse,
    PromptItem,
    PromptListResponse,
)
from valuecell.server.db import get_db
from valuecell.server.db.repositories import get_strategy_repository


def create_strategy_prompts_router() -> APIRouter:
    router = APIRouter(
        prefix="/strategies/prompts",
        tags=["strategies"],  # keep under strategy namespace
        responses={404: {"description": "Not found"}},
    )

    @router.get(
        "/",
        response_model=PromptListResponse,
        summary="List strategy prompts",
        description="Return all available strategy prompts (unordered by recency).",
    )
    async def list_prompts(db: Session = Depends(get_db)) -> PromptListResponse:
        try:
            repo = get_strategy_repository(db_session=db)
            items = repo.list_prompts()
            prompt_items = [PromptItem(**p.to_dict()) for p in items]
            return SuccessResponse.create(
                data=prompt_items, msg=f"Fetched {len(prompt_items)} prompts"
            )
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Failed to list prompts: {e}")

    @router.post(
        "/create",
        response_model=PromptCreateResponse,
        summary="Create a strategy prompt",
        description="Create a new strategy prompt with name and content.",
    )
    async def create_prompt(
        payload: PromptCreateRequest, db: Session = Depends(get_db)
    ) -> PromptCreateResponse:
        try:
            repo = get_strategy_repository(db_session=db)
            item = repo.create_prompt(name=payload.name, content=payload.content)
            if item is None:
                raise HTTPException(status_code=500, detail="Failed to create prompt")
            return SuccessResponse.create(
                data=PromptItem(**item.to_dict()), msg="Prompt created"
            )
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Failed to create prompt: {e}")

    return router
