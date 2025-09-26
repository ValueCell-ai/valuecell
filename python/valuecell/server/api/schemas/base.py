"""Base API schemas for ValueCell application."""

from datetime import datetime
from enum import IntEnum
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class StatusCode(IntEnum):
    """Unified API status code enumeration."""

    # Success status codes
    SUCCESS = 0

    # Client error status codes
    BAD_REQUEST = 400  # Bad request parameters
    UNAUTHORIZED = 401  # Unauthorized access
    FORBIDDEN = 403  # Forbidden access
    NOT_FOUND = 404  # Resource not found

    # Server error status codes
    INTERNAL_ERROR = 500  # Internal server error


class BaseResponse(BaseModel, Generic[T]):
    """Unified API response base model."""

    code: int = Field(..., description="Status code")
    msg: str = Field(..., description="Response message")
    data: Optional[T] = Field(None, description="Response data")


class SuccessResponse(BaseResponse[T]):
    """Success response model."""

    code: int = Field(default=StatusCode.SUCCESS, description="Success status code")
    msg: str = Field(default="success", description="Success message")

    @classmethod
    def create(cls, data: T = None, msg: str = "success") -> "SuccessResponse[T]":
        """Create success response."""
        return cls(code=StatusCode.SUCCESS, msg=msg, data=data)


class ErrorResponse(BaseResponse[None]):
    """Error response model."""

    code: int = Field(..., description="Error status code")
    msg: str = Field(..., description="Error message")
    data: None = Field(default=None, description="Data is null for errors")

    @classmethod
    def create(cls, code: StatusCode, msg: str) -> "ErrorResponse":
        """Create error response."""
        return cls(code=code, msg=msg, data=None)


# Common data response models
class AppInfoData(BaseModel):
    """Application information data."""

    name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Runtime environment")


class HealthCheckData(BaseModel):
    """Health check data."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: Optional[datetime] = Field(None, description="Check timestamp")
