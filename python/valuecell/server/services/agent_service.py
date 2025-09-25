"""
Agent service layer for handling agent-related business logic.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from valuecell.server.db.models.agent import Agent
from valuecell.server.api.schemas.agent import AgentData, AgentListData


class AgentService:
    """Service class for agent-related operations."""

    @staticmethod
    def get_all_agents(
        db: Session, enabled_only: bool = False, name_filter: Optional[str] = None
    ) -> AgentListData:
        """
        Get all agents from database with optional filters.

        Args:
            db: Database session
            enabled_only: Filter only enabled agents
            name_filter: Filter by agent name (partial match)

        Returns:
            AgentListData with agents list and statistics
        """
        # Build query with filters
        query = db.query(Agent)

        filters = []
        if enabled_only:
            filters.append(Agent.enabled)
        if name_filter:
            filters.append(
                or_(
                    Agent.name.ilike(f"%{name_filter}%"),
                    Agent.display_name.ilike(f"%{name_filter}%"),
                )
            )

        if filters:
            query = query.filter(and_(*filters))

        # Execute query
        agents = query.order_by(Agent.created_at.desc()).all()

        # Convert to data models
        agent_data_list = [
            AgentData(
                id=agent.id,
                agent_name=agent.name,
                display_name=agent.display_name,
                description=agent.description,
                version=agent.version,
                enabled=agent.enabled,
                icon_url=agent.icon_url,
                agent_metadata=agent.agent_metadata,
                config=agent.config,
                created_at=agent.created_at,
                updated_at=agent.updated_at,
            )
            for agent in agents
        ]

        # Calculate statistics
        total_count = len(agent_data_list)
        enabled_count = sum(1 for agent in agent_data_list if agent.enabled)

        return AgentListData(
            agents=agent_data_list, total=total_count, enabled_count=enabled_count
        )

    @staticmethod
    def get_agent_by_id(db: Session, agent_id: int) -> Optional[AgentData]:
        """
        Get a specific agent by ID.

        Args:
            db: Database session
            agent_id: Agent ID

        Returns:
            AgentData if found, None otherwise
        """
        agent = db.query(Agent).filter(Agent.id == agent_id).first()

        if not agent:
            return None

        return AgentData(
            id=agent.id,
            agent_name=agent.name,
            display_name=agent.display_name,
            description=agent.description,
            version=agent.version,
            enabled=agent.enabled,
            icon_url=agent.icon_url,
            agent_metadata=agent.agent_metadata,
            config=agent.config,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )

    @staticmethod
    def get_agent_by_name(db: Session, agent_name: str) -> Optional[AgentData]:
        """
        Get a specific agent by name.

        Args:
            db: Database session
            agent_name: Agent name

        Returns:
            AgentData if found, None otherwise
        """
        agent = db.query(Agent).filter(Agent.name == agent_name).first()

        if not agent:
            return None

        return AgentData(
            id=agent.id,
            agent_name=agent.name,
            display_name=agent.display_name,
            description=agent.description,
            version=agent.version,
            enabled=agent.enabled,
            icon_url=agent.icon_url,
            agent_metadata=agent.agent_metadata,
            config=agent.config,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )
