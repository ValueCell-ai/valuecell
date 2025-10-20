"""
ValueCell Server - User Profile Repository

This module provides database operations for user profile management.
"""

from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..connection import get_database_manager
from ..models.user_profile import ProfileCategory, UserProfile


class UserProfileRepository:
    """Repository class for user profile database operations."""

    def __init__(self, db_session: Optional[Session] = None):
        """Initialize repository with optional database session."""
        self.db_session = db_session

    def _get_session(self) -> Session:
        """Get database session."""
        if self.db_session:
            return self.db_session
        return get_database_manager().get_session()

    def create_profile(
        self,
        user_id: str,
        category: ProfileCategory,
        content: str,
    ) -> Optional[UserProfile]:
        """Create a new user profile."""
        session = self._get_session()

        try:
            profile = UserProfile(
                user_id=user_id,
                category=category,
                content=content,
            )

            session.add(profile)
            session.commit()
            session.refresh(profile)

            # Expunge to avoid session issues
            session.expunge(profile)

            return profile

        except IntegrityError:
            session.rollback()
            return None
        except Exception:
            session.rollback()
            return None
        finally:
            if not self.db_session:
                session.close()

    def get_profile(self, profile_id: int, user_id: str) -> Optional[UserProfile]:
        """Get a specific profile by ID and user ID."""
        session = self._get_session()

        try:
            profile = (
                session.query(UserProfile)
                .filter(UserProfile.id == profile_id, UserProfile.user_id == user_id)
                .first()
            )

            if profile:
                session.expunge(profile)

            return profile

        finally:
            if not self.db_session:
                session.close()

    def get_profiles_by_user(
        self,
        user_id: str,
        category: Optional[ProfileCategory] = None,
    ) -> List[UserProfile]:
        """Get all profiles for a user, optionally filtered by category."""
        session = self._get_session()

        try:
            query = session.query(UserProfile).filter(UserProfile.user_id == user_id)

            if category:
                query = query.filter(UserProfile.category == category)

            profiles = query.order_by(desc(UserProfile.created_at)).all()

            # Expunge all profiles
            for profile in profiles:
                session.expunge(profile)

            return profiles

        finally:
            if not self.db_session:
                session.close()

    def update_profile(
        self,
        profile_id: int,
        user_id: str,
        content: str,
    ) -> Optional[UserProfile]:
        """Update a profile's content."""
        session = self._get_session()

        try:
            profile = (
                session.query(UserProfile)
                .filter(UserProfile.id == profile_id, UserProfile.user_id == user_id)
                .first()
            )

            if not profile:
                return None

            profile.content = content
            session.commit()
            session.refresh(profile)
            session.expunge(profile)

            return profile

        except Exception:
            session.rollback()
            return None
        finally:
            if not self.db_session:
                session.close()

    def delete_profile(self, profile_id: int, user_id: str) -> bool:
        """Delete a profile."""
        session = self._get_session()

        try:
            profile = (
                session.query(UserProfile)
                .filter(UserProfile.id == profile_id, UserProfile.user_id == user_id)
                .first()
            )

            if not profile:
                return False

            session.delete(profile)
            session.commit()
            return True

        except Exception:
            session.rollback()
            return False
        finally:
            if not self.db_session:
                session.close()

    def get_profile_count(
        self,
        user_id: str,
        category: Optional[ProfileCategory] = None,
    ) -> int:
        """Get count of profiles for a user, optionally filtered by category."""
        session = self._get_session()

        try:
            query = session.query(UserProfile).filter(UserProfile.user_id == user_id)

            if category:
                query = query.filter(UserProfile.category == category)

            return query.count()

        finally:
            if not self.db_session:
                session.close()

    def get_profiles_by_category(
        self, user_id: str
    ) -> dict[ProfileCategory, List[UserProfile]]:
        """Get all profiles for a user grouped by category."""
        session = self._get_session()

        try:
            profiles = (
                session.query(UserProfile)
                .filter(UserProfile.user_id == user_id)
                .order_by(desc(UserProfile.created_at))
                .all()
            )

            # Group profiles by category
            grouped: dict[ProfileCategory, List[UserProfile]] = {
                ProfileCategory.PRODUCT_BEHAVIOR: [],
                ProfileCategory.RISK_PREFERENCE: [],
                ProfileCategory.READING_PREFERENCE: [],
            }

            for profile in profiles:
                session.expunge(profile)
                if profile.category in grouped:
                    grouped[profile.category].append(profile)

            return grouped

        finally:
            if not self.db_session:
                session.close()
