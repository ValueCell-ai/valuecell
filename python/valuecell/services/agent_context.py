"""Agent context management for ValueCell application."""

from typing import Optional
from datetime import datetime
import threading
from contextlib import contextmanager

from ..api.i18n_api import get_i18n_api
from ..services.i18n_service import get_i18n_service
from ..api.schemas import AgentI18nContext


class AgentContextManager:
    """Manages context for agents to access user i18n settings."""

    def __init__(self):
        """Initialize agent context manager."""
        self.i18n_api = get_i18n_api()
        self.i18n_service = get_i18n_service()
        self._local = threading.local()

    def set_user_context(self, user_id: str, session_id: Optional[str] = None):
        """Set current user context for the agent."""
        user_context = self.i18n_api.get_user_context(user_id)

        # Store in thread local storage
        self._local.user_id = user_id
        self._local.session_id = session_id
        self._local.language = user_context.get("language", "en-US")
        self._local.timezone = user_context.get("timezone", "UTC")

        # Update i18n service
        self.i18n_service.set_language(self._local.language)
        self.i18n_service.set_timezone(self._local.timezone)

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
            currency_symbol=self.i18n_service._i18n_config.get_currency_symbol(),
            date_format=self.i18n_service._i18n_config.get_date_format(),
            time_format=self.i18n_service._i18n_config.get_time_format(),
            number_format=self.i18n_service._i18n_config.get_number_format(),
            user_id=self.get_current_user_id(),
            session_id=self.get_current_session_id(),
        )

    def translate(self, key: str, **variables) -> str:
        """Translate using current user's language."""
        return self.i18n_service.translate(
            key, self.get_current_language(), **variables
        )

    def format_datetime(self, dt: datetime, format_type: str = "datetime") -> str:
        """Format datetime using current user's settings."""
        return self.i18n_service.format_datetime(dt, format_type)

    def format_number(self, number: float, decimal_places: int = 2) -> str:
        """Format number using current user's settings."""
        return self.i18n_service.format_number(number, decimal_places)

    def format_currency(self, amount: float, decimal_places: int = 2) -> str:
        """Format currency using current user's settings."""
        return self.i18n_service.format_currency(amount, decimal_places)

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
