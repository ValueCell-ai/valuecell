"""
Agent API router for handling agent-related endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from valuecell.server.api.schemas.agent import (
    AgentEnableRequest,
    AgentEnableResponse,
    AgentEnableSuccessResponse,
    AgentListResponse,
    AgentResponse,
)
from valuecell.server.api.schemas.base import SuccessResponse
from valuecell.server.db import get_db
from valuecell.server.services.agent_service import AgentService


def create_agent_router() -> APIRouter:
    """Create and configure the agent router."""

    router = APIRouter(
        prefix="/agents",
        tags=["agents"],
        responses={404: {"description": "Not found"}},
    )

    @router.get(
        "/",
        response_model=AgentListResponse,
        summary="Get all agents",
        description="Get a list of all agents in the system, including basic information",
    )
    async def get_agents(
        enabled_only: bool = Query(False, description="Return only enabled agents"),
        name_filter: Optional[str] = Query(
            None, description="Filter agents by name (supports fuzzy matching)"
        ),
        db: Session = Depends(get_db),
    ) -> AgentListResponse:
        """
        Get all agents list.

        - **enabled_only**: If True, return only enabled agents
        - **name_filter**: Filter by agent name or display name with fuzzy matching

        Returns a response containing the agent list and statistics.
        """
        try:
            agent_list_data = AgentService.get_all_agents(
                db=db, enabled_only=enabled_only, name_filter=name_filter
            )
            return SuccessResponse.create(
                data=agent_list_data,
                msg=f"Successfully retrieved {agent_list_data.total} agents",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve agent list: {str(e)}"
            )

    @router.get(
        "/{agent_id}",
        response_model=AgentResponse,
        summary="Get agent by ID",
        description="Get detailed information of an agent by its ID",
    )
    async def get_agent_by_id(
        agent_id: int = Path(..., description="Unique identifier of the agent"),
        db: Session = Depends(get_db),
    ) -> AgentResponse:
        """
        Get detailed information of a specific agent by ID.

        - **agent_id**: Unique identifier of the agent

        Returns detailed agent information, or 404 error if agent doesn't exist.
        """
        try:
            agent = AgentService.get_agent_by_id(db=db, agent_id=agent_id)
            if not agent:
                raise HTTPException(
                    status_code=404, detail=f"Agent with ID {agent_id} not found"
                )
            return SuccessResponse.create(
                data=agent, msg="Successfully retrieved agent information"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve agent information: {str(e)}",
            )

    @router.get(
        "/by-name/{agent_name}",
        response_model=AgentResponse,
        summary="Get agent by name",
        description="Get detailed information of an agent by its name",
    )
    async def get_agent_by_name(
        agent_name: str = Path(..., description="Name of the agent"),
        db: Session = Depends(get_db),
    ) -> AgentResponse:
        """
        Get detailed information of a specific agent by name.

        - **agent_name**: Name of the agent

        Returns detailed agent information, or 404 error if agent doesn't exist.
        """
        try:
            agent = AgentService.get_agent_by_name(db=db, agent_name=agent_name)
            if not agent:
                raise HTTPException(
                    status_code=404, detail=f"Agent with name '{agent_name}' not found"
                )
            return SuccessResponse.create(
                data=agent, msg="Successfully retrieved agent information"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve agent information: {str(e)}",
            )

    @router.post(
        "/{agent_name}/enable",
        response_model=AgentEnableSuccessResponse,
        summary="Update agent enable status",
        description="Enable or disable an agent by its name",
    )
    async def update_agent_enable_status(
        agent_name: str = Path(..., description="Name of the agent"),
        request: AgentEnableRequest = ...,
        db: Session = Depends(get_db),
    ) -> AgentEnableSuccessResponse:
        """
        Update the enabled status of a specific agent by name.

        - **agent_name**: Name of the agent to update
        - **enabled**: Whether to enable (true) or disable (false) the agent

        Returns updated agent status information, or 404 error if agent doesn't exist.
        """
        try:
            updated_agent = AgentService.update_agent_enabled(
                db=db, agent_name=agent_name, enabled=request.enabled
            )
            if not updated_agent:
                raise HTTPException(
                    status_code=404, detail=f"Agent with name '{agent_name}' not found"
                )

            response_data = AgentEnableResponse(
                agent_name=updated_agent.agent_name,
                enabled=updated_agent.enabled,
                message=f"Agent '{agent_name}' has been {'enabled' if request.enabled else 'disabled'} successfully",
            )

            return SuccessResponse.create(
                data=response_data,
                msg=f"Successfully {'enabled' if request.enabled else 'disabled'} agent '{agent_name}'",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update agent status: {str(e)}",
            )

    return router
