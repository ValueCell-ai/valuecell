"""User profile related API routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query

from ...db.models.user_profile import ProfileCategory
from ...services.user_profile_service import get_user_profile_service
from ..schemas import SuccessResponse
from ..schemas.user_profile import (
    CreateUserProfileRequest,
    UpdateUserProfileRequest,
    UserProfileData,
    UserProfileListData,
    UserProfileSummaryData,
)

# Global default user ID for open source API
DEFAULT_USER_ID = "default_user"


def create_user_profile_router() -> APIRouter:
    """Create user profile related routes."""
    router = APIRouter(prefix="/user/profile", tags=["User Profile"])

    # Get service dependency
    profile_service = get_user_profile_service()

    @router.post(
        "",
        response_model=SuccessResponse[UserProfileData],
        summary="Create user profile",
        description="Create a new user profile with specified category and content",
    )
    async def create_profile(request: CreateUserProfileRequest):
        """Create a new user profile."""
        try:
            # Use default user ID for now
            user_id = DEFAULT_USER_ID

            # Validate category
            valid_categories = [e.value for e in ProfileCategory]
            if request.category not in valid_categories:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}",
                )

            # Create profile
            profile = profile_service.create_profile(
                user_id=user_id,
                category=request.category,
                content=request.content,
            )

            if not profile:
                raise HTTPException(status_code=500, detail="Failed to create profile")

            return SuccessResponse.create(
                data=UserProfileData(**profile),
                msg="Profile created successfully",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error creating profile: {str(e)}"
            )

    @router.get(
        "",
        response_model=SuccessResponse[UserProfileListData],
        summary="Get user profiles",
        description="Get all user profiles, optionally filtered by category",
    )
    async def get_profiles(
        category: Optional[str] = Query(
            None,
            description=f"Filter by category ({', '.join([e.value for e in ProfileCategory])})",
        ),
    ):
        """Get all user profiles."""
        try:
            # Use default user ID for now
            user_id = DEFAULT_USER_ID

            # Validate category if provided
            if category:
                valid_categories = [e.value for e in ProfileCategory]
                if category not in valid_categories:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}",
                    )

            # Get profiles
            profiles = profile_service.get_user_profiles(user_id, category)

            return SuccessResponse.create(
                data=UserProfileListData(
                    profiles=[UserProfileData(**p) for p in profiles],
                    count=len(profiles),
                ),
                msg="Profiles retrieved successfully",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error retrieving profiles: {str(e)}"
            )

    @router.get(
        "/summary",
        response_model=SuccessResponse[UserProfileSummaryData],
        summary="Get user profile summary",
        description="Get summary of all user profiles grouped by category",
    )
    async def get_profile_summary():
        """Get user profile summary."""
        try:
            # Use default user ID for now
            user_id = DEFAULT_USER_ID

            # Get summary
            summary = profile_service.get_profile_summary(user_id)

            return SuccessResponse.create(
                data=UserProfileSummaryData(**summary),
                msg="Profile summary retrieved successfully",
            )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error retrieving profile summary: {str(e)}"
            )

    @router.get(
        "/{profile_id}",
        response_model=SuccessResponse[UserProfileData],
        summary="Get specific profile",
        description="Get a specific user profile by ID",
    )
    async def get_profile(
        profile_id: int = Path(..., description="Profile ID", ge=1),
    ):
        """Get a specific user profile."""
        try:
            # Use default user ID for now
            user_id = DEFAULT_USER_ID

            # Get profile
            profile = profile_service.get_profile(profile_id, user_id)

            if not profile:
                raise HTTPException(status_code=404, detail="Profile not found")

            return SuccessResponse.create(
                data=UserProfileData(**profile),
                msg="Profile retrieved successfully",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error retrieving profile: {str(e)}"
            )

    @router.put(
        "/{profile_id}",
        response_model=SuccessResponse[UserProfileData],
        summary="Update user profile",
        description="Update content of a specific user profile",
    )
    async def update_profile(
        profile_id: int = Path(..., description="Profile ID", ge=1),
        request: UpdateUserProfileRequest = ...,
    ):
        """Update a user profile."""
        try:
            # Use default user ID for now
            user_id = DEFAULT_USER_ID

            # Update profile
            profile = profile_service.update_profile(
                profile_id=profile_id,
                user_id=user_id,
                content=request.content,
            )

            if not profile:
                raise HTTPException(
                    status_code=404, detail="Profile not found or update failed"
                )

            return SuccessResponse.create(
                data=UserProfileData(**profile),
                msg="Profile updated successfully",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error updating profile: {str(e)}"
            )

    @router.delete(
        "/{profile_id}",
        response_model=SuccessResponse[dict],
        summary="Delete user profile",
        description="Delete a specific user profile",
    )
    async def delete_profile(
        profile_id: int = Path(..., description="Profile ID", ge=1),
    ):
        """Delete a user profile."""
        try:
            # Use default user ID for now
            user_id = DEFAULT_USER_ID

            # Delete profile
            success = profile_service.delete_profile(profile_id, user_id)

            if not success:
                raise HTTPException(
                    status_code=404, detail="Profile not found or deletion failed"
                )

            return SuccessResponse.create(
                data={"profile_id": profile_id, "deleted": True},
                msg="Profile deleted successfully",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error deleting profile: {str(e)}"
            )

    return router
