"""User profile service for ValueCell application."""

import logging
from typing import Dict, List, Optional

from ..db.models.user_profile import ProfileCategory
from ..db.repositories.user_profile_repository import UserProfileRepository

logger = logging.getLogger(__name__)


class UserProfileService:
    """Service class for user profile management."""

    def __init__(self, repository: Optional[UserProfileRepository] = None):
        """Initialize user profile service.

        Args:
            repository: Optional repository instance for dependency injection
        """
        self.repository = repository or UserProfileRepository()

    def create_profile(
        self,
        user_id: str,
        category: str,
        content: str,
    ) -> Optional[Dict]:
        """Create a new user profile.

        Args:
            user_id: User ID
            category: Profile category (see ProfileCategory enum for valid values)
            content: Profile content

        Returns:
            Profile data dictionary or None if creation failed
        """
        try:
            # Validate and convert category
            profile_category = self._validate_category(category)
            if not profile_category:
                logger.error(f"Invalid category: {category}")
                return None

            profile = self.repository.create_profile(
                user_id=user_id,
                category=profile_category,
                content=content,
            )

            if profile:
                logger.info(
                    f"Created profile {profile.id} for user {user_id} with category {category}"
                )
                return profile.to_dict()

            return None

        except Exception as e:
            logger.exception(f"Error creating profile: {e}")
            return None

    def get_profile(self, profile_id: int, user_id: str) -> Optional[Dict]:
        """Get a specific profile.

        Args:
            profile_id: Profile ID
            user_id: User ID

        Returns:
            Profile data dictionary or None if not found
        """
        try:
            profile = self.repository.get_profile(profile_id, user_id)
            if profile:
                return profile.to_dict()
            return None

        except Exception as e:
            logger.exception(f"Error getting profile {profile_id}: {e}")
            return None

    def get_user_profiles(
        self,
        user_id: str,
        category: Optional[str] = None,
    ) -> List[Dict]:
        """Get all profiles for a user.

        Args:
            user_id: User ID
            category: Optional category filter

        Returns:
            List of profile data dictionaries
        """
        try:
            profile_category = None
            if category:
                profile_category = self._validate_category(category)
                if not profile_category:
                    logger.error(f"Invalid category: {category}")
                    return []

            profiles = self.repository.get_profiles_by_user(user_id, profile_category)
            return [profile.to_dict() for profile in profiles]

        except Exception as e:
            logger.exception(f"Error getting profiles for user {user_id}: {e}")
            return []

    def update_profile(
        self,
        profile_id: int,
        user_id: str,
        content: str,
    ) -> Optional[Dict]:
        """Update a profile's content.

        Args:
            profile_id: Profile ID
            user_id: User ID
            content: Updated content

        Returns:
            Updated profile data dictionary or None if update failed
        """
        try:
            profile = self.repository.update_profile(profile_id, user_id, content)
            if profile:
                logger.info(f"Updated profile {profile_id} for user {user_id}")
                return profile.to_dict()
            return None

        except Exception as e:
            logger.exception(f"Error updating profile {profile_id}: {e}")
            return None

    def delete_profile(self, profile_id: int, user_id: str) -> bool:
        """Delete a profile.

        Args:
            profile_id: Profile ID
            user_id: User ID

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            success = self.repository.delete_profile(profile_id, user_id)
            if success:
                logger.info(f"Deleted profile {profile_id} for user {user_id}")
            return success

        except Exception as e:
            logger.exception(f"Error deleting profile {profile_id}: {e}")
            return False

    def get_profile_summary(self, user_id: str) -> Dict:
        """Get a summary of all profiles for a user grouped by category.

        Args:
            user_id: User ID

        Returns:
            Dictionary with profiles grouped by category
        """
        try:
            grouped_profiles = self.repository.get_profiles_by_category(user_id)

            summary = {
                "user_id": user_id,
                ProfileCategory.PRODUCT_BEHAVIOR.value: [
                    p.content
                    for p in grouped_profiles[ProfileCategory.PRODUCT_BEHAVIOR]
                ],
                ProfileCategory.RISK_PREFERENCE.value: [
                    p.content for p in grouped_profiles[ProfileCategory.RISK_PREFERENCE]
                ],
                ProfileCategory.READING_PREFERENCE.value: [
                    p.content
                    for p in grouped_profiles[ProfileCategory.READING_PREFERENCE]
                ],
                "total_count": sum(
                    len(profiles) for profiles in grouped_profiles.values()
                ),
            }

            return summary

        except Exception as e:
            logger.exception(f"Error getting profile summary for user {user_id}: {e}")
            return {
                "user_id": user_id,
                ProfileCategory.PRODUCT_BEHAVIOR.value: [],
                ProfileCategory.RISK_PREFERENCE.value: [],
                ProfileCategory.READING_PREFERENCE.value: [],
                "total_count": 0,
            }

    def get_profile_count(self, user_id: str, category: Optional[str] = None) -> int:
        """Get count of profiles for a user.

        Args:
            user_id: User ID
            category: Optional category filter

        Returns:
            Number of profiles
        """
        try:
            profile_category = None
            if category:
                profile_category = self._validate_category(category)
                if not profile_category:
                    return 0

            return self.repository.get_profile_count(user_id, profile_category)

        except Exception as e:
            logger.exception(f"Error getting profile count for user {user_id}: {e}")
            return 0

    def _validate_category(self, category: str) -> Optional[ProfileCategory]:
        """Validate and convert category string to ProfileCategory enum.

        Args:
            category: Category string

        Returns:
            ProfileCategory enum or None if invalid
        """
        try:
            return ProfileCategory(category)
        except ValueError:
            return None


# Global service instance
_user_profile_service: Optional[UserProfileService] = None


def get_user_profile_service() -> UserProfileService:
    """Get global user profile service instance."""
    global _user_profile_service
    if _user_profile_service is None:
        _user_profile_service = UserProfileService()
    return _user_profile_service


def reset_user_profile_service() -> None:
    """Reset global user profile service instance."""
    global _user_profile_service
    _user_profile_service = None
