"""
ValueCell Server - Agent Models

This module defines the database models for agents in the ValueCell system.
"""

from typing import Dict, Any
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func

from .base import Base


class Agent(Base):
    """
    Agent model representing an AI agent in the ValueCell system.

    This table stores information about available agents, their capabilities,
    configuration, and metadata.
    """

    __tablename__ = "agents"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Basic agent information
    name = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique agent name/identifier",
    )
    display_name = Column(
        String(200), nullable=True, comment="Human-readable display name"
    )
    description = Column(
        Text,
        nullable=True,
        comment="Detailed description of the agent's purpose and capabilities",
    )

    # Agent configuration
    version = Column(
        String(50), nullable=True, default="1.0.0", comment="Agent version"
    )

    # Status and availability
    enabled = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether the agent is currently enabled",
    )

    # Capabilities and metadata
    capabilities = Column(
        JSON,
        nullable=True,
        comment="JSON object describing agent capabilities (streaming, notifications, etc.)",
    )
    agent_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata (author, tags, supported features, etc.)",
    )

    # Configuration
    config = Column(
        JSON, nullable=True, comment="Agent-specific configuration parameters"
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<Agent(id={self.id}, name='{self.name}', enabled={self.enabled})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "capabilities": self.capabilities,
            "agent_metadata": self.agent_metadata,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_config(cls, config_data: Dict[str, Any]) -> "Agent":
        """Create an Agent instance from configuration data."""
        return cls(
            name=config_data.get("name"),
            display_name=config_data.get("display_name"),
            description=config_data.get("description"),
            version=config_data.get("version", "1.0.0"),
            enabled=config_data.get("enabled", True),
            capabilities=config_data.get(
                "capabilities",
                {
                    "streaming": True,
                    "push_notifications": False,
                },
            ),
            agent_metadata=config_data.get("metadata"),
            config=config_data.get("config"),
        )
