"""Task API routes."""

from fastapi import APIRouter, HTTPException, Path

from valuecell.server.api.schemas.task import TaskCancelResponse
from valuecell.server.services.task_service import TaskApiService


def create_task_router() -> APIRouter:
    """Create task router."""
    router = APIRouter(prefix="/tasks", tags=["Tasks"])

    @router.post(
        "/{task_id}/cancel",
        response_model=TaskCancelResponse,
        summary="Cancel a task",
        description=(
            "Cancel a task by ID and update any corresponding scheduled_task_controller "
            "components in the conversation history to reflect the 'cancelled' status."
        ),
    )
    async def cancel_task(
        task_id: str = Path(..., description="The task ID to cancel"),
    ) -> TaskCancelResponse:
        try:
            service = TaskApiService()
            data = await service.cancel_and_update_component(task_id=task_id)
            if not data.success:
                # If the task could not be cancelled, return 400 with reason
                raise HTTPException(
                    status_code=400, detail="Task is not cancellable or not found"
                )
            return TaskCancelResponse.create(
                data=data, msg="Task cancelled successfully"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Internal server error: {str(e)}"
            )

    return router
