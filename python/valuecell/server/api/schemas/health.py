"""Health check schemas for ValueCell Server."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str
    version: str
    environment: str
    database: str
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "environment": "development",
                "database": "healthy"
            }
        }