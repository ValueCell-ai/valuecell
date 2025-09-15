"""Agent service for ValueCell Server."""

import time
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from ...db.repositories.agent_repository import AgentRepository
from ...db.models.agent import Agent
from ...api.schemas.agents import (
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentExecutionRequest,
    AgentExecutionResponse,
)
from ...config.logging import get_logger

logger = get_logger(__name__)


class AgentService:
    """Service for managing agents."""
    
    def __init__(self, db: Session):
        """Initialize agent service."""
        self.db = db
        self.repository = AgentRepository(db)
    
    async def list_agents(
        self,
        skip: int = 0,
        limit: int = 100,
        agent_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[Agent]:
        """List agents with optional filtering."""
        logger.info(f"Listing agents: skip={skip}, limit={limit}, type={agent_type}")
        
        filters = {}
        if agent_type:
            filters["agent_type"] = agent_type
        if is_active is not None:
            filters["is_active"] = is_active
        
        return await self.repository.list_agents(
            skip=skip,
            limit=limit,
            filters=filters
        )
    
    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        logger.info(f"Getting agent: {agent_id}")
        return await self.repository.get_agent(agent_id)
    
    async def create_agent(self, agent_data: AgentCreateRequest) -> Agent:
        """Create a new agent."""
        logger.info(f"Creating agent: {agent_data.name}")
        
        agent = Agent(
            name=agent_data.name,
            description=agent_data.description,
            agent_type=agent_data.agent_type,
            config=agent_data.config,
            is_active=agent_data.is_active,
        )
        
        return await self.repository.create_agent(agent)
    
    async def update_agent(
        self,
        agent_id: str,
        agent_data: AgentUpdateRequest
    ) -> Optional[Agent]:
        """Update an existing agent."""
        logger.info(f"Updating agent: {agent_id}")
        
        agent = await self.repository.get_agent(agent_id)
        if not agent:
            return None
        
        # Update fields
        update_data = agent_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(agent, field, value)
        
        return await self.repository.update_agent(agent)
    
    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        logger.info(f"Deleting agent: {agent_id}")
        return await self.repository.delete_agent(agent_id)
    
    async def execute_agent(
        self,
        agent_id: str,
        execution_request: AgentExecutionRequest
    ) -> AgentExecutionResponse:
        """Execute an agent with given parameters."""
        logger.info(f"Executing agent: {agent_id}")
        
        agent = await self.repository.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        if not agent.is_active:
            raise ValueError(f"Agent {agent_id} is not active")
        
        try:
            # TODO: Implement actual agent execution logic
            # This would integrate with the existing agent execution framework
            
            # For now, return a mock response
            result = {
                "status": "completed",
                "message": f"Agent {agent.name} executed successfully",
                "data": execution_request.parameters,
            }
            
            logger.info(f"Agent execution completed: {agent_id}")
            
            return AgentExecutionResponse(
                agent_id=agent_id,
                execution_id=f"exec_{agent_id}_{int(time.time())}",
                status="completed",
                result=result,
                error=None,
            )
            
        except Exception as e:
            logger.error(f"Agent execution failed: {agent_id}", exc_info=True)
            
            return AgentExecutionResponse(
                agent_id=agent_id,
                execution_id=f"exec_{agent_id}_{int(time.time())}",
                status="failed",
                result=None,
                error=str(e),
            )