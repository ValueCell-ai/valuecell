"""User profile utility functions for ValueCell application."""

import logging
from typing import Dict, List, Optional

from ..server.db.models.user_profile import ProfileCategory
from ..server.services.user_profile_service import get_user_profile_service

logger = logging.getLogger(__name__)


def get_user_profile_summary(user_id: str) -> Dict:
    """Get user profile summary grouped by category.

    Args:
        user_id: User ID

    Returns:
        Dictionary with user profiles grouped by category
    """
    service = get_user_profile_service()
    return service.get_profile_summary(user_id)


def get_user_product_behavior(user_id: str) -> List[str]:
    """Get user's product behavior profiles.

    Args:
        user_id: User ID

    Returns:
        List of product behavior profile contents
    """
    summary = get_user_profile_summary(user_id)
    return summary.get(ProfileCategory.PRODUCT_BEHAVIOR.value, [])


def get_user_risk_preference(user_id: str) -> List[str]:
    """Get user's risk preference profiles.

    Args:
        user_id: User ID

    Returns:
        List of risk preference profile contents
    """
    summary = get_user_profile_summary(user_id)
    return summary.get(ProfileCategory.RISK_PREFERENCE.value, [])


def get_user_reading_preference(user_id: str) -> List[str]:
    """Get user's reading preference profiles.

    Args:
        user_id: User ID

    Returns:
        List of reading preference profile contents
    """
    summary = get_user_profile_summary(user_id)
    return summary.get(ProfileCategory.READING_PREFERENCE.value, [])


def get_user_profiles(user_id: str, category: Optional[str] = None) -> List[Dict]:
    """Get user profiles, optionally filtered by category.

    Args:
        user_id: User ID
        category: Optional category filter (see ProfileCategory enum for valid values)

    Returns:
        List of profile dictionaries
    """
    service = get_user_profile_service()
    return service.get_user_profiles(user_id, category)


def create_user_profile(user_id: str, category: str, content: str) -> Optional[Dict]:
    """Create a new user profile.

    Args:
        user_id: User ID
        category: Profile category
        content: Profile content

    Returns:
        Created profile dictionary or None if creation failed
    """
    service = get_user_profile_service()
    return service.create_profile(user_id, category, content)


def update_user_profile(profile_id: int, user_id: str, content: str) -> Optional[Dict]:
    """Update a user profile.

    Args:
        profile_id: Profile ID
        user_id: User ID
        content: Updated content

    Returns:
        Updated profile dictionary or None if update failed
    """
    service = get_user_profile_service()
    return service.update_profile(profile_id, user_id, content)


def delete_user_profile(profile_id: int, user_id: str) -> bool:
    """Delete a user profile.

    Args:
        profile_id: Profile ID
        user_id: User ID

    Returns:
        True if deletion succeeded, False otherwise
    """
    service = get_user_profile_service()
    return service.delete_profile(profile_id, user_id)


def format_profile_for_agent(user_id: str) -> Dict[str, List[str]]:
    """Format user profiles for agent metadata.

    This function formats user profiles in a way that can be easily
    consumed by agents through the orchestrator metadata.

    Args:
        user_id: User ID

    Returns:
        Dictionary with formatted profile data for agent consumption
    """
    summary = get_user_profile_summary(user_id)

    return {
        ProfileCategory.PRODUCT_BEHAVIOR.value: summary.get(
            ProfileCategory.PRODUCT_BEHAVIOR.value, []
        ),
        ProfileCategory.RISK_PREFERENCE.value: summary.get(
            ProfileCategory.RISK_PREFERENCE.value, []
        ),
        ProfileCategory.READING_PREFERENCE.value: summary.get(
            ProfileCategory.READING_PREFERENCE.value, []
        ),
    }


def has_user_profiles(user_id: str) -> bool:
    """Check if user has any profiles.

    Args:
        user_id: User ID

    Returns:
        True if user has at least one profile, False otherwise
    """
    service = get_user_profile_service()
    return service.get_profile_count(user_id) > 0


def get_profile_categories() -> List[str]:
    """Get list of available profile categories.

    Returns:
        List of category values
    """
    return [category.value for category in ProfileCategory]


def validate_profile_category(category: str) -> bool:
    """Validate if category is valid.

    Args:
        category: Category string to validate

    Returns:
        True if category is valid, False otherwise
    """
    return category in get_profile_categories()


def merge_profile_contents(profiles: List[str], separator: str = "\n") -> str:
    """Merge multiple profile contents into a single string.

    Args:
        profiles: List of profile content strings
        separator: Separator to use between profiles

    Returns:
        Merged profile content string
    """
    return separator.join(profiles)


def get_formatted_user_context(user_id: str) -> str:
    """Get formatted user context string from all profiles.

    This creates a human-readable summary of all user profiles
    that can be included in agent prompts.

    Args:
        user_id: User ID

    Returns:
        Formatted user context string
    """
    summary = get_user_profile_summary(user_id)

    context_parts = []

    product_behavior_key = ProfileCategory.PRODUCT_BEHAVIOR.value
    if summary.get(product_behavior_key):
        context_parts.append("Product Behavior:")
        for behavior in summary[product_behavior_key]:
            context_parts.append(f"  - {behavior}")

    risk_preference_key = ProfileCategory.RISK_PREFERENCE.value
    if summary.get(risk_preference_key):
        context_parts.append("Risk Preference:")
        for preference in summary[risk_preference_key]:
            context_parts.append(f"  - {preference}")

    reading_preference_key = ProfileCategory.READING_PREFERENCE.value
    if summary.get(reading_preference_key):
        context_parts.append("Reading Preference:")
        for preference in summary[reading_preference_key]:
            context_parts.append(f"  - {preference}")

    if not context_parts:
        return ""

    return "\n".join(context_parts)


def get_user_profile_metadata(user_id: str) -> Dict:
    """Get user profile metadata for orchestrator.

    This function provides a structured metadata dictionary that can be
    used in the orchestrator's metadata dictionary.

    Args:
        user_id: User ID

    Returns:
        Dictionary with user profile metadata
    """
    try:
        summary = get_user_profile_summary(user_id)
        return {
            "user_id": user_id,
            "profiles": {
                ProfileCategory.PRODUCT_BEHAVIOR.value: summary.get(
                    ProfileCategory.PRODUCT_BEHAVIOR.value, []
                ),
                ProfileCategory.RISK_PREFERENCE.value: summary.get(
                    ProfileCategory.RISK_PREFERENCE.value, []
                ),
                ProfileCategory.READING_PREFERENCE.value: summary.get(
                    ProfileCategory.READING_PREFERENCE.value, []
                ),
            },
            "total_profiles": summary.get("total_count", 0),
            "has_profiles": summary.get("total_count", 0) > 0,
        }
    except Exception as e:
        logger.exception(f"Error getting user profile metadata for {user_id}: {e}")
        return {
            "user_id": user_id,
            "profiles": {
                ProfileCategory.PRODUCT_BEHAVIOR.value: [],
                ProfileCategory.RISK_PREFERENCE.value: [],
                ProfileCategory.READING_PREFERENCE.value: [],
            },
            "total_profiles": 0,
            "has_profiles": False,
        }
