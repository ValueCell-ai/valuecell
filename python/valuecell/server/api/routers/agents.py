"""Agents router for ValueCell Server."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...config.database import get_db
from ...services.agents.agent_service import AgentService
from ..schemas.agents import (
    AgentResponse,
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentExecutionRequest,
    AgentExecutionResponse,
)

router = APIRouter()


@router.get("/", response_model=List[AgentResponse])
async def list_agents(db: Session = Depends(get_db)):
    """List all available agents."""
    agent_service = AgentService(db)
    return await agent_service.list_agents()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get agent by ID."""
    agent_service = AgentService(db)
    agent = await agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    return agent


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new agent."""
    agent_service = AgentService(db)
    return await agent_service.create_agent(agent_data)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update an existing agent."""
    agent_service = AgentService(db)
    agent = await agent_service.update_agent(agent_id, agent_data)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, db: Session = Depends(get_db)):
    """Delete an agent."""
    agent_service = AgentService(db)
    success = await agent_service.delete_agent(agent_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )


@router.post("/{agent_id}/execute", response_model=AgentExecutionResponse)
async def execute_agent(
    agent_id: str,
    execution_request: AgentExecutionRequest,
    db: Session = Depends(get_db)
):
    """Execute an agent with given input."""
    agent_service = AgentService(db)
    result = await agent_service.execute_agent(agent_id, execution_request)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    return result