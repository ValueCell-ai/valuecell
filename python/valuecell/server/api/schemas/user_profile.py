"""API schemas for user profile operations."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from ...db.models.user_profile import ProfileCategory


class UserProfileData(BaseModel):
    """User profile data schema."""

    id: int = Field(..., description="Profile ID")
    user_id: str = Field(..., description="User ID")
    category: str = Field(..., description="Profile category")
    content: str = Field(..., description="Profile content")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class CreateUserProfileRequest(BaseModel):
    """Request schema for creating a user profile."""

    category: str = Field(
        ...,
        description=f"Profile category: {', '.join([e.value for e in ProfileCategory])}",
    )
    content: str = Field(
        ..., description="Profile content", min_length=1, max_length=10000
    )


class UpdateUserProfileRequest(BaseModel):
    """Request schema for updating a user profile."""

    content: str = Field(
        ..., description="Updated profile content", min_length=1, max_length=10000
    )


class UserProfileListData(BaseModel):
    """User profile list data schema."""

    profiles: List[UserProfileData] = Field(..., description="List of user profiles")
    count: int = Field(..., description="Total number of profiles")


class UserProfileSummaryData(BaseModel):
    """User profile summary data schema."""

    user_id: str = Field(..., description="User ID")
    product_behavior: List[str] = Field(
        default_factory=list, description="Product behavior profiles"
    )
    risk_preference: List[str] = Field(
        default_factory=list, description="Risk preference profiles"
    )
    reading_preference: List[str] = Field(
        default_factory=list, description="Reading preference profiles"
    )
    total_count: int = Field(..., description="Total number of profiles")
