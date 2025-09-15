import logging
from typing import Dict, List, Type

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Agent registry for managing decorated agents"""

    def __init__(self):
        """Initialize the registry."""
        self._agents: Dict[str, Type] = {}

    def register(self, agent_class: Type, agent_name: str) -> None:
        """Register an Agent class

        Args:
            agent_class: The decorated agent class
            agent_name: The agent name (from decorator parameter or class name)
        """
        self._agents[agent_name] = agent_class
        logger.info(f"Registered agent: '{agent_name}'")

    def get_agent_class_by_name(self, name: str) -> Type:
        """Get a registered Agent class by name"""
        return self._agents.get(name)

    def get_name_for_class(self, agent_class: Type) -> str:
        """Get the agent name for a given class"""
        return agent_class.__name__

    def list_agent_names(self) -> List[str]:
        """List all registered agent names (primary names only)"""
        # Get unique agent class names (avoid duplicate entries for same class)
        seen_classes = set()
        unique_names = []
        for _, agent_class in self._agents.items():
            class_id = id(agent_class)
            if class_id not in seen_classes:
                seen_classes.add(class_id)
                unique_names.append(self.get_name_for_class(agent_class))
        return unique_names

    def get_all_agents(self) -> Dict[str, Type]:
        """Get all registered Agents (includes both primary and secondary keys)"""
        return self._agents.copy()

    def get_registry_info(self) -> Dict[str, dict]:
        """Get detailed registry information for debugging"""
        info = {}
        processed_classes = set()

        for _, agent_class in self._agents.items():
            class_id = id(agent_class)
            if class_id in processed_classes:
                continue

            processed_classes.add(class_id)
            agent_name = self.get_name_for_class(agent_class)

            info[agent_name] = {
                "class_name": agent_class.__name__,
                "agent_name": agent_name,
                "registered_keys": [
                    k for k, v in self._agents.items() if v is agent_class
                ],
                "class_qualname": getattr(agent_class, "__qualname__", "N/A"),
            }

        return info

    def unregister_by_name(self, name: str) -> List[str]:
        """Unregister an agent by name (agent_name or class_name)

        Args:
            name: The agent name or class name to unregister

        Returns:
            bool: True if agent was found and unregistered, False otherwise
        """
        agent_class = self._agents.get(name)
        if not agent_class:
            return []

        # Find all keys that point to this agent class
        keys_to_remove = [k for k, v in self._agents.items() if v is agent_class]

        # Remove all keys for this agent
        for key in keys_to_remove:
            del self._agents[key]

        agent_name = self.get_name_for_class(agent_class)
        logger.info(
            f"Unregistered agent: '{agent_name}' (removed keys: {keys_to_remove})"
        )
        return keys_to_remove

    def unregister_by_class(self, agent_class: Type) -> List[str]:
        """Unregister an agent by class reference

        Args:
            agent_class: The agent class to unregister

        Returns:
            bool: True if agent was found and unregistered, False otherwise
        """
        # Find all keys that point to this agent class
        keys_to_remove = [k for k, v in self._agents.items() if v is agent_class]

        if not keys_to_remove:
            return []

        # Remove all keys for this agent
        for key in keys_to_remove:
            del self._agents[key]

        agent_name = self.get_name_for_class(agent_class)
        logger.info(
            f"Unregistered agent: '{agent_name}' (removed keys: {keys_to_remove})"
        )
        return keys_to_remove

    def is_registered(self, name: str) -> bool:
        """Check if an agent is registered by name

        Args:
            name: The agent name or class name to check

        Returns:
            bool: True if agent is registered, False otherwise
        """
        return name in self._agents

    def unregister_all(self, pattern: str = None) -> List[str]:
        """Unregister multiple agents, optionally by pattern

        Args:
            pattern: Optional string pattern to match agent names (substring match)
                    If None, unregisters all agents

        Returns:
            List[str]: List of unregistered agent names
        """
        if pattern is None:
            # Unregister all
            agent_names = self.list_agent_names()
            self.clear()
            logger.info(f"Unregistered all agents: {agent_names}")
            return agent_names

        # Find registration keys matching pattern
        matching_keys = []
        for key in self._agents:
            if pattern in key:
                matching_keys.append(key)

        # Unregister matching agents by key
        unregistered = []
        for key in matching_keys:
            if self.unregister_by_name(key):
                # Get the agent name for reporting
                unregistered.append(key)

        return unregistered

    def count(self) -> int:
        """Get the number of unique registered agents

        Returns:
            int: Number of unique agents (not counting duplicate keys)
        """
        return len(self.list_agent_names())

    def clear(self) -> None:
        """Clear all registered agents (useful for testing)"""
        self._agents.clear()


# Global instance for backward compatibility and ease of use
_default_registry = AgentRegistry()


# Convenience functions that delegate to the default instance
def register(agent_class: Type, agent_name: str) -> None:
    """Register an agent in the default registry"""
    _default_registry.register(agent_class, agent_name)


def get_agent_class_by_name(name: str) -> Type:
    """Get an agent from the default registry"""
    return _default_registry.get_agent_class_by_name(name)


def get_name_for_class(agent_class: Type) -> str:
    """Get agent name from the default registry"""
    return _default_registry.get_name_for_class(agent_class)


def list_agent_names() -> List[str]:
    """List agents from the default registry"""
    return _default_registry.list_agent_names()


def get_all_agents() -> Dict[str, Type]:
    """Get all agents from the default registry"""
    return _default_registry.get_all_agents()


def get_registry_info() -> Dict[str, dict]:
    """Get registry info from the default registry"""
    return _default_registry.get_registry_info()


def unregister_by_name(name: str) -> List[str]:
    """Unregister an agent from the default registry"""
    return _default_registry.unregister_by_name(name)


def unregister_by_class(agent_class: Type) -> List[str]:
    """Unregister an agent by class from the default registry"""
    return _default_registry.unregister_by_class(agent_class)


def is_registered(name: str) -> bool:
    """Check if an agent is registered in the default registry"""
    return _default_registry.is_registered(name)


def unregister_all(pattern: str = None) -> List[str]:
    """Unregister multiple agents from the default registry"""
    return _default_registry.unregister_all(pattern)


def count() -> int:
    """Count agents in the default registry"""
    return _default_registry.count()


def clear_registry() -> None:
    """Clear the default registry"""
    _default_registry.clear()


def get_default_registry() -> AgentRegistry:
    """Get the default registry instance"""
    return _default_registry
