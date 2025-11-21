"""
Agent service layer for handling agent-related business logic.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from valuecell.server.api.schemas.agent import AgentData, AgentListData
from valuecell.server.db.models.agent import Agent


class AgentService:
    """Service class for agent-related operations."""

    @staticmethod
    def get_all_agents(
        db: Session,
        enabled_only: bool = False,
        name_filter: Optional[str] = None,
        exclude_hidden: bool = True,
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
        agent_data_list = []
        # Agents that are hidden by default unless explicitly enabled
        HIDE_UNLESS_ENABLED = {"research_agent", "news_agent"}
        for _agent_entity in agents:
            if (
                _agent_entity.agent_metadata
                and exclude_hidden
                and _agent_entity.agent_metadata.get("hidden", False)
            ):
                continue

            # Hide research/news agents by default when not enabled
            if (
                exclude_hidden
                and (_agent_entity.name in HIDE_UNLESS_ENABLED)
                and (not _agent_entity.enabled)
            ):
                continue

            agent = AgentData(
                id=_agent_entity.id,
                agent_name=_agent_entity.name,
                display_name=_agent_entity.display_name,
                description=_agent_entity.description,
                version=_agent_entity.version,
                enabled=_agent_entity.enabled,
                icon_url=_agent_entity.icon_url,
                agent_metadata=_agent_entity.agent_metadata,
                config=_agent_entity.config,
                created_at=_agent_entity.created_at,
                updated_at=_agent_entity.updated_at,
            )
            agent_data_list.append(agent)

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
    def update_agent_enabled(
        db: Session, agent_name: str, enabled: bool
    ) -> Optional[AgentData]:
        """
        Update the enabled status of an agent by name.

        Args:
            db: Database session
            agent_name: Name of the agent to update
            enabled: New enabled status

        Returns:
            Updated AgentData if found and updated, None if agent not found
        """
        agent = db.query(Agent).filter(Agent.name == agent_name).first()

        if not agent:
            return None

        # Update the enabled status and timestamp
        agent.enabled = enabled
        agent.updated_at = datetime.utcnow()

        # Commit the changes
        db.commit()
        db.refresh(agent)

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
