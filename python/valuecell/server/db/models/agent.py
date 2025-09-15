"""Agent model for ValueCell Server."""

from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from .base import Base


class Agent(Base):
    """Agent model for storing agent configurations and metadata."""
    
    __tablename__ = "agents"
    
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    agent_type = Column(String(100), nullable=False, index=True)
    config = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Metadata
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    
    # Performance tracking
    execution_count = Column(Integer, default=0, nullable=False)
    last_executed_at = Column(DateTime(timezone=True), nullable=True)
    average_execution_time = Column(Float, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Agent(id='{self.id}', name='{self.name}', type='{self.agent_type}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "config": self.config,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "execution_count": self.execution_count,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "average_execution_time": self.average_execution_time,
        }
    
    def update_execution_stats(self, execution_time: float) -> None:
        """Update execution statistics."""
        self.execution_count += 1
        self.last_executed_at = datetime.utcnow()
        
        if self.average_execution_time is None:
            self.average_execution_time = execution_time
        else:
            # Calculate running average
            total_time = self.average_execution_time * (self.execution_count - 1)
            self.average_execution_time = (total_time + execution_time) / self.execution_count