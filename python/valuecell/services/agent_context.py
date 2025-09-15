"""Agent context management for ValueCell application."""

from typing import Optional
from datetime import datetime
import threading
from contextlib import contextmanager

from ..api.schemas import AgentI18nContext


class AgentContextManager:
    """Manages context for agents to access user i18n settings."""

    def __init__(self):
        """Initialize agent context manager."""
        self._local = threading.local()

    def set_user_context(self, user_id: str, session_id: Optional[str] = None):
        """Set current user context for the agent."""
        # Store in thread local storage with default values
        self._local.user_id = user_id
        self._local.session_id = session_id
        self._local.language = "en-US"  # Default language
        self._local.timezone = "UTC"  # Default timezone

    def get_current_user_id(self) -> Optional[str]:
        """Get current user ID."""
        return getattr(self._local, "user_id", None)

    def get_current_session_id(self) -> Optional[str]:
        """Get current session ID."""
        return getattr(self._local, "session_id", None)

    def get_current_language(self) -> str:
        """Get current user's language."""
        return getattr(self._local, "language", "en-US")

    def get_current_timezone(self) -> str:
        """Get current user's timezone."""
        return getattr(self._local, "timezone", "UTC")

    def get_i18n_context(self) -> AgentI18nContext:
        """Get complete i18n context for agent."""
        return AgentI18nContext(
            language=self.get_current_language(),
            timezone=self.get_current_timezone(),
            currency_symbol="$",  # Default currency symbol
            date_format="YYYY-MM-DD",  # Default date format
            time_format="HH:mm:ss",  # Default time format
            number_format="en-US",  # Default number format
            user_id=self.get_current_user_id(),
            session_id=self.get_current_session_id(),
        )

    def translate(self, key: str, **variables) -> str:
        """Translate using current user's language."""
        # i18n service removed, return key as fallback
        return key

    def format_datetime(self, dt: datetime, format_type: str = "datetime") -> str:
        """Format datetime using current user's settings."""
        # i18n service removed, return basic format
        return dt.isoformat()

    def format_number(self, number: float, decimal_places: int = 2) -> str:
        """Format number using current user's settings."""
        # i18n service removed, return basic format
        return f"{number:.{decimal_places}f}"

    def format_currency(self, amount: float, decimal_places: int = 2) -> str:
        """Format currency using current user's settings."""
        # i18n service removed, return basic format
        return f"${amount:.{decimal_places}f}"

    @contextmanager
    def user_context(self, user_id: str, session_id: Optional[str] = None):
        """Context manager for temporary user context."""
        # Save current context
        old_user_id = getattr(self._local, "user_id", None)
        old_session_id = getattr(self._local, "session_id", None)
        old_language = getattr(self._local, "language", "en-US")
        old_timezone = getattr(self._local, "timezone", "UTC")

        try:
            # Set new context
            self.set_user_context(user_id, session_id)
            yield self
        finally:
            # Restore old context
            if old_user_id:
                self._local.user_id = old_user_id
                self._local.session_id = old_session_id
                self._local.language = old_language
                self._local.timezone = old_timezone
                self.i18n_service.set_language(old_language)
                self.i18n_service.set_timezone(old_timezone)
            else:
                # Clear context
                if hasattr(self._local, "user_id"):
                    delattr(self._local, "user_id")
                if hasattr(self._local, "session_id"):
                    delattr(self._local, "session_id")
                if hasattr(self._local, "language"):
                    delattr(self._local, "language")
                if hasattr(self._local, "timezone"):
                    delattr(self._local, "timezone")

    def clear_context(self):
        """Clear current user context."""
        if hasattr(self._local, "user_id"):
            delattr(self._local, "user_id")
        if hasattr(self._local, "session_id"):
            delattr(self._local, "session_id")
        if hasattr(self._local, "language"):
            delattr(self._local, "language")
        if hasattr(self._local, "timezone"):
            delattr(self._local, "timezone")


# Global agent context manager
_agent_context: Optional[AgentContextManager] = None


def get_agent_context() -> AgentContextManager:
    """Get global agent context manager."""
    global _agent_context
    if _agent_context is None:
        _agent_context = AgentContextManager()
    return _agent_context


def reset_agent_context():
    """Reset global agent context manager."""
    global _agent_context
    _agent_context = None


# Convenience functions for agents
def set_user_context(user_id: str, session_id: Optional[str] = None):
    """Set user context for current agent (convenience function)."""
    return get_agent_context().set_user_context(user_id, session_id)


def get_current_user_id() -> Optional[str]:
    """Get current user ID (convenience function)."""
    return get_agent_context().get_current_user_id()


def get_i18n_context() -> AgentI18nContext:
    """Get i18n context (convenience function)."""
    return get_agent_context().get_i18n_context()


def t(key: str, **variables) -> str:
    """Translate using current user context (convenience function)."""
    return get_agent_context().translate(key, **variables)


def user_context(user_id: str, session_id: Optional[str] = None):
    """Context manager for user context (convenience function)."""
    return get_agent_context().user_context(user_id, session_id)
