"""
ValueCell Server - Watchlist Repository

This module provides database operations for watchlist management.
"""

from typing import List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..connection import get_database_manager
from ..models.asset import Asset
from ..models.watchlist import Watchlist, WatchlistItem


class WatchlistRepository:
    """Repository class for watchlist database operations."""

    def __init__(self, db_session: Optional[Session] = None):
        """Initialize repository with optional database session."""
        self.db_session = db_session

    def _get_session(self) -> Session:
        """Get database session."""
        if self.db_session:
            return self.db_session
        return get_database_manager().get_session()

    def create_watchlist(
        self,
        user_id: str,
        name: str,
        description: str = "",
        is_default: bool = False,
        is_public: bool = False,
    ) -> Optional[Watchlist]:
        """Create a new watchlist for a user."""
        session = self._get_session()

        try:
            # If this is set as default, unset other default watchlists for this user
            if is_default:
                session.query(Watchlist).filter(
                    Watchlist.user_id == user_id, Watchlist.is_default
                ).update({"is_default": False})

            watchlist = Watchlist(
                user_id=user_id,
                name=name,
                description=description,
                is_default=is_default,
                is_public=is_public,
            )

            session.add(watchlist)
            session.commit()
            session.refresh(watchlist)

            # Expunge to avoid session issues
            session.expunge(watchlist)

            return watchlist

        except IntegrityError:
            session.rollback()
            return None
        except Exception:
            session.rollback()
            return None
        finally:
            if not self.db_session:
                session.close()

    def get_watchlist(self, user_id: str, watchlist_name: str) -> Optional[Watchlist]:
        """Get a specific watchlist by user ID and name."""
        session = self._get_session()

        try:
            watchlist = (
                session.query(Watchlist)
                .filter(Watchlist.user_id == user_id, Watchlist.name == watchlist_name)
                .first()
            )

            if watchlist:
                # Eagerly load items to avoid lazy loading issues
                _ = len(watchlist.items)  # This triggers the lazy load
                for item in watchlist.items:
                    # Access all needed properties while session is active
                    _ = (
                        item.ticker,
                        item.notes,
                        item.order_index,
                        item.added_at,
                        item.updated_at,
                    )

            return watchlist

        finally:
            if not self.db_session:
                session.close()

    def get_watchlist_by_id(self, watchlist_id: int) -> Optional[Watchlist]:
        """Get a watchlist by ID."""
        session = self._get_session()

        try:
            watchlist = (
                session.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
            )

            if watchlist:
                # Eagerly load items to avoid lazy loading issues
                _ = len(watchlist.items)  # This triggers the lazy load
                for item in watchlist.items:
                    # Access all needed properties while session is active
                    _ = (
                        item.ticker,
                        item.notes,
                        item.order_index,
                        item.added_at,
                        item.updated_at,
                    )

            return watchlist

        finally:
            if not self.db_session:
                session.close()

    def get_default_watchlist(self, user_id: str) -> Optional[Watchlist]:
        """Get user's default watchlist."""
        session = self._get_session()

        try:
            watchlist = (
                session.query(Watchlist)
                .filter(Watchlist.user_id == user_id, Watchlist.is_default)
                .first()
            )

            if watchlist:
                # Eagerly load items to avoid lazy loading issues
                _ = len(watchlist.items)  # This triggers the lazy load
                for item in watchlist.items:
                    # Access all needed properties while session is active
                    _ = (
                        item.ticker,
                        item.notes,
                        item.order_index,
                        item.added_at,
                        item.updated_at,
                    )

            return watchlist

        finally:
            if not self.db_session:
                session.close()

    def get_user_watchlists(self, user_id: str) -> List[Watchlist]:
        """Get all watchlists for a user."""
        session = self._get_session()

        try:
            watchlists = (
                session.query(Watchlist)
                .filter(Watchlist.user_id == user_id)
                .order_by(desc(Watchlist.is_default), asc(Watchlist.name))
                .all()
            )

            # Eagerly load items for all watchlists to avoid lazy loading issues
            for watchlist in watchlists:
                # Force loading of items while session is still active
                _ = len(watchlist.items)  # This triggers the lazy load
                for item in watchlist.items:
                    # Access all needed properties while session is active
                    _ = (
                        item.ticker,
                        item.notes,
                        item.order_index,
                        item.added_at,
                        item.updated_at,
                    )

            return watchlists

        finally:
            if not self.db_session:
                session.close()

    def delete_watchlist(self, user_id: str, watchlist_name: str) -> bool:
        """Delete a watchlist."""
        session = self._get_session()

        try:
            watchlist = (
                session.query(Watchlist)
                .filter(Watchlist.user_id == user_id, Watchlist.name == watchlist_name)
                .first()
            )

            if not watchlist:
                return False

            session.delete(watchlist)
            session.commit()

            return True

        except Exception:
            session.rollback()
            return False
        finally:
            if not self.db_session:
                session.close()

    def add_asset_to_watchlist(
        self,
        user_id: str,
        ticker: str,
        watchlist_name: Optional[str] = None,
        display_name: Optional[str] = None,
        notes: str = "",
        order_index: Optional[int] = None,
    ) -> bool:
        """Add a asset to a watchlist."""
        session = self._get_session()

        try:
            # Get watchlist within the same session to avoid detached objects
            if watchlist_name:
                watchlist = (
                    session.query(Watchlist)
                    .filter(
                        Watchlist.user_id == user_id, Watchlist.name == watchlist_name
                    )
                    .first()
                )
            else:
                watchlist = (
                    session.query(Watchlist)
                    .filter(Watchlist.user_id == user_id, Watchlist.is_default)
                    .first()
                )

                if not watchlist:
                    # Create default watchlist if it doesn't exist
                    watchlist = Watchlist(
                        user_id=user_id,
                        name="My Watchlist",
                        description="Default watchlist",
                        is_default=True,
                    )
                    session.add(watchlist)
                    session.flush()  # Get the ID without committing

            if not watchlist:
                return False

            # If display_name is not provided, try to get it from assets table
            if not display_name:
                asset = session.query(Asset).filter(Asset.symbol == ticker).first()
                if asset and asset.name:
                    display_name = asset.name

            # Set order_index if not provided
            if order_index is None:
                max_order = (
                    session.query(WatchlistItem)
                    .filter(WatchlistItem.watchlist_id == watchlist.id)
                    .count()
                )
                order_index = max_order

            # Create watchlist item
            item = WatchlistItem(
                watchlist_id=watchlist.id,
                ticker=ticker,
                display_name=display_name,
                notes=notes,
                order_index=order_index,
            )

            session.add(item)
            session.commit()

            return True

        except IntegrityError:
            session.rollback()
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            if not self.db_session:
                session.close()

    def remove_asset_from_watchlist(
        self, user_id: str, ticker: str, watchlist_name: Optional[str] = None
    ) -> bool:
        """Remove a asset from a watchlist."""
        session = self._get_session()

        try:
            # Get watchlist within the same session
            if watchlist_name:
                watchlist = (
                    session.query(Watchlist)
                    .filter(
                        Watchlist.user_id == user_id, Watchlist.name == watchlist_name
                    )
                    .first()
                )
            else:
                watchlist = (
                    session.query(Watchlist)
                    .filter(Watchlist.user_id == user_id, Watchlist.is_default)
                    .first()
                )

            if not watchlist:
                return False

            # Find and delete the item
            item = (
                session.query(WatchlistItem)
                .filter(
                    WatchlistItem.watchlist_id == watchlist.id,
                    WatchlistItem.ticker == ticker,
                )
                .first()
            )

            if not item:
                return False

            session.delete(item)
            session.commit()

            return True

        except Exception:
            session.rollback()
            return False
        finally:
            if not self.db_session:
                session.close()

    def get_watchlist_assets(
        self, user_id: str, watchlist_name: Optional[str] = None
    ) -> List[WatchlistItem]:
        """Get all assets in a watchlist."""
        session = self._get_session()

        try:
            # Get watchlist within the same session
            if watchlist_name:
                watchlist = (
                    session.query(Watchlist)
                    .filter(
                        Watchlist.user_id == user_id, Watchlist.name == watchlist_name
                    )
                    .first()
                )
            else:
                watchlist = (
                    session.query(Watchlist)
                    .filter(Watchlist.user_id == user_id, Watchlist.is_default)
                    .first()
                )

            if not watchlist:
                return []

            items = (
                session.query(WatchlistItem)
                .filter(WatchlistItem.watchlist_id == watchlist.id)
                .order_by(asc(WatchlistItem.order_index))
                .all()
            )

            # Expunge items to avoid session issues
            for item in items:
                session.expunge(item)

            return items

        finally:
            if not self.db_session:
                session.close()

    def is_asset_in_watchlist(
        self, user_id: str, ticker: str, watchlist_name: Optional[str] = None
    ) -> bool:
        """Check if a asset is in a watchlist."""
        session = self._get_session()

        try:
            # Get watchlist
            if watchlist_name:
                watchlist = self.get_watchlist(user_id, watchlist_name)
            else:
                watchlist = self.get_default_watchlist(user_id)

            if not watchlist:
                return False

            item = (
                session.query(WatchlistItem)
                .filter(
                    WatchlistItem.watchlist_id == watchlist.id,
                    WatchlistItem.ticker == ticker,
                )
                .first()
            )

            return item is not None

        finally:
            if not self.db_session:
                session.close()

    def update_asset_notes(
        self,
        user_id: str,
        ticker: str,
        notes: str,
        watchlist_name: Optional[str] = None,
    ) -> bool:
        """Update notes for a asset in a watchlist."""
        session = self._get_session()

        try:
            # Get watchlist within the same session
            if watchlist_name:
                watchlist = (
                    session.query(Watchlist)
                    .filter(
                        Watchlist.user_id == user_id, Watchlist.name == watchlist_name
                    )
                    .first()
                )
            else:
                watchlist = (
                    session.query(Watchlist)
                    .filter(Watchlist.user_id == user_id, Watchlist.is_default)
                    .first()
                )

            if not watchlist:
                return False

            # Update the item
            item = (
                session.query(WatchlistItem)
                .filter(
                    WatchlistItem.watchlist_id == watchlist.id,
                    WatchlistItem.ticker == ticker,
                )
                .first()
            )

            if not item:
                return False

            item.notes = notes
            session.commit()

            return True

        except Exception:
            session.rollback()
            return False
        finally:
            if not self.db_session:
                session.close()


# Global repository instance
_watchlist_repository: Optional[WatchlistRepository] = None


def get_watchlist_repository() -> WatchlistRepository:
    """Get global watchlist repository instance."""
    global _watchlist_repository
    if _watchlist_repository is None:
        _watchlist_repository = WatchlistRepository()
    return _watchlist_repository


def reset_watchlist_repository() -> None:
    """Reset global watchlist repository instance (mainly for testing)."""
    global _watchlist_repository
    _watchlist_repository = None
