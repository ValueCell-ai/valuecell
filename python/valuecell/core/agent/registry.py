from typing import Dict, Type, List
import logging

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Simple Agent registry for managing decorated agents"""

    _agents: Dict[str, Type] = {}

    @classmethod
    def register(cls, agent_class: Type, agent_name: str) -> None:
        """Register an Agent class

        Args:
            agent_class: The decorated agent class
            agent_name: The agent name (from decorator parameter or class name)
        """
        class_name = agent_class.__name__

        # Primary registration: use agent_name (this is what users will lookup)
        cls._agents[agent_name] = agent_class

        # Secondary registration: use class_name if different from agent_name
        # This helps with debugging and class-based lookups
        if class_name != agent_name:
            cls._agents[class_name] = agent_class
            logger.info(f"Registered agent: '{agent_name}' (class: {class_name})")
        else:
            logger.info(f"Registered agent: '{agent_name}'")

    @classmethod
    def get_agent(cls, name: str) -> Type:
        """Get a registered Agent class by name"""
        return cls._agents.get(name)

    @classmethod
    def get_agent_name(cls, agent_class: Type) -> str:
        """Get the agent name for a given class"""
        if hasattr(agent_class, "__agent_name__"):
            return agent_class.__agent_name__
        return agent_class.__name__

    @classmethod
    def list_agents(cls) -> List[str]:
        """List all registered agent names (primary names only)"""
        # Filter out duplicates by checking if the agent_name matches the stored __agent_name__
        unique_names = []
        for name, agent_class in cls._agents.items():
            if (
                hasattr(agent_class, "__agent_name__")
                and agent_class.__agent_name__ == name
            ):
                unique_names.append(name)
            elif (
                not hasattr(agent_class, "__agent_name__")
                and agent_class.__name__ == name
            ):
                unique_names.append(name)
        return unique_names

    @classmethod
    def get_all_agents(cls) -> Dict[str, Type]:
        """Get all registered Agents (includes both primary and secondary keys)"""
        return cls._agents.copy()

    @classmethod
    def get_registry_info(cls) -> Dict[str, dict]:
        """Get detailed registry information for debugging"""
        info = {}
        processed_classes = set()

        for _, agent_class in cls._agents.items():
            class_id = id(agent_class)
            if class_id in processed_classes:
                continue

            processed_classes.add(class_id)
            agent_name = cls.get_agent_name(agent_class)

            info[agent_name] = {
                "class_name": agent_class.__name__,
                "agent_name": agent_name,
                "registered_keys": [
                    k for k, v in cls._agents.items() if v is agent_class
                ],
                "class_qualname": getattr(agent_class, "__qualname__", "N/A"),
            }

        return info

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Unregister an agent by name (agent_name or class_name)

        Args:
            name: The agent name or class name to unregister

        Returns:
            bool: True if agent was found and unregistered, False otherwise
        """
        agent_class = cls._agents.get(name)
        if not agent_class:
            return False

        # Find all keys that point to this agent class
        keys_to_remove = [k for k, v in cls._agents.items() if v is agent_class]

        # Remove all keys for this agent
        for key in keys_to_remove:
            del cls._agents[key]

        agent_name = cls.get_agent_name(agent_class)
        logger.info(
            f"Unregistered agent: '{agent_name}' (removed keys: {keys_to_remove})"
        )
        return True

    @classmethod
    def unregister_by_class(cls, agent_class: Type) -> bool:
        """Unregister an agent by class reference

        Args:
            agent_class: The agent class to unregister

        Returns:
            bool: True if agent was found and unregistered, False otherwise
        """
        # Find all keys that point to this agent class
        keys_to_remove = [k for k, v in cls._agents.items() if v is agent_class]

        if not keys_to_remove:
            return False

        # Remove all keys for this agent
        for key in keys_to_remove:
            del cls._agents[key]

        agent_name = cls.get_agent_name(agent_class)
        logger.info(
            f"Unregistered agent: '{agent_name}' (removed keys: {keys_to_remove})"
        )
        return True

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if an agent is registered by name

        Args:
            name: The agent name or class name to check

        Returns:
            bool: True if agent is registered, False otherwise
        """
        return name in cls._agents

    @classmethod
    def unregister_all(cls, pattern: str = None) -> List[str]:
        """Unregister multiple agents, optionally by pattern

        Args:
            pattern: Optional string pattern to match agent names (substring match)
                    If None, unregisters all agents

        Returns:
            List[str]: List of unregistered agent names
        """
        if pattern is None:
            # Unregister all
            agent_names = cls.list_agents()
            cls.clear()
            logger.info(f"Unregistered all agents: {agent_names}")
            return agent_names

        # Find agents matching pattern
        matching_agents = []
        for name in cls.list_agents():
            if pattern in name:
                matching_agents.append(name)

        # Unregister matching agents
        unregistered = []
        for name in matching_agents:
            if cls.unregister(name):
                unregistered.append(name)

        return unregistered

    @classmethod
    def count(cls) -> int:
        """Get the number of unique registered agents

        Returns:
            int: Number of unique agents (not counting duplicate keys)
        """
        return len(cls.list_agents())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered agents (useful for testing)"""
        cls._agents.clear()
