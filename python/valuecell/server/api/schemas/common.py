"""Common schemas for ValueCell Server."""

from typing import Dict, Any, Optional
from pydantic import BaseModel


class BaseResponse(BaseModel):
    """Base response schema."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ErrorResponse(BaseResponse):
    """Error response schema."""

    success: bool = False
    error: str
    data: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseResponse):
    """Success response schema."""

    success: bool = True
    data: Dict[str, Any]