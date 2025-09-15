"""Agent repository for ValueCell Server."""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..models.agent import Agent
from ...config.logging import get_logger

logger = get_logger(__name__)


class AgentRepository:
    """Repository for agent data access."""
    
    def __init__(self, db: Session):
        """Initialize agent repository."""
        self.db = db
    
    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        try:
            return self.db.query(Agent).filter(Agent.id == agent_id).first()
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}", exc_info=True)
            return None
    
    async def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name."""
        try:
            return self.db.query(Agent).filter(Agent.name == name).first()
        except Exception as e:
            logger.error(f"Error getting agent by name {name}", exc_info=True)
            return None
    
    async def list_agents(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        order_desc: bool = False,
    ) -> List[Agent]:
        """List agents with optional filtering and pagination."""
        try:
            query = self.db.query(Agent)
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if hasattr(Agent, key):
                        if isinstance(value, list):
                            query = query.filter(getattr(Agent, key).in_(value))
                        else:
                            query = query.filter(getattr(Agent, key) == value)
            
            # Apply ordering
            if hasattr(Agent, order_by):
                order_column = getattr(Agent, order_by)
                if order_desc:
                    query = query.order_by(order_column.desc())
                else:
                    query = query.order_by(order_column)
            
            # Apply pagination
            return query.offset(skip).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error listing agents", exc_info=True)
            return []
    
    async def create_agent(self, agent: Agent) -> Agent:
        """Create a new agent."""
        try:
            self.db.add(agent)
            self.db.commit()
            self.db.refresh(agent)
            logger.info(f"Created agent: {agent.id}")
            return agent
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating agent", exc_info=True)
            raise
    
    async def update_agent(self, agent: Agent) -> Agent:
        """Update an existing agent."""
        try:
            self.db.commit()
            self.db.refresh(agent)
            logger.info(f"Updated agent: {agent.id}")
            return agent
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating agent {agent.id}", exc_info=True)
            raise
    
    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        try:
            agent = await self.get_agent(agent_id)
            if agent:
                self.db.delete(agent)
                self.db.commit()
                logger.info(f"Deleted agent: {agent_id}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting agent {agent_id}", exc_info=True)
            return False
    
    async def search_agents(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Agent]:
        """Search agents by name or description."""
        try:
            db_query = self.db.query(Agent)
            
            # Text search
            search_filter = or_(
                Agent.name.ilike(f"%{query}%"),
                Agent.description.ilike(f"%{query}%")
            )
            db_query = db_query.filter(search_filter)
            
            # Apply additional filters
            if filters:
                for key, value in filters.items():
                    if hasattr(Agent, key):
                        if isinstance(value, list):
                            db_query = db_query.filter(getattr(Agent, key).in_(value))
                        else:
                            db_query = db_query.filter(getattr(Agent, key) == value)
            
            return db_query.limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error searching agents with query: {query}", exc_info=True)
            return []
    
    async def count_agents(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count agents with optional filtering."""
        try:
            query = self.db.query(Agent)
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if hasattr(Agent, key):
                        if isinstance(value, list):
                            query = query.filter(getattr(Agent, key).in_(value))
                        else:
                            query = query.filter(getattr(Agent, key) == value)
            
            return query.count()
            
        except Exception as e:
            logger.error(f"Error counting agents", exc_info=True)
            return 0