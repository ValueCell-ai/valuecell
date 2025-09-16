"""
Auto-import all agents to ensure they are registered with the AgentRegistry.
This module dynamically discovers and imports all agent classes.
"""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import List

from valuecell.core.types import BaseAgent


def _discover_and_import_agents() -> List[str]:
    """
    Dynamically discover and import all agent modules in this package.

    Returns:
        List of agent class names that were imported
    """
    imported_agents = []
    current_package = __name__
    current_path = Path(__file__).parent

    # Iterate through all Python files in the current directory
    for _, module_name, _ in pkgutil.iter_modules([str(current_path)]):
        if module_name.startswith("_"):
            # Skip private modules
            continue

        try:
            # Import the module
            module = importlib.import_module(f"{current_package}.{module_name}")

            # Find all classes in the module that inherit from BaseAgent
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    obj.__module__ == module.__name__
                    and issubclass(obj, BaseAgent)
                    and obj != BaseAgent
                ):
                    imported_agents.append(name)
                    # Make the class available at package level
                    globals()[name] = obj

        except Exception as e:
            # Log import errors but continue with other modules
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to import module {module_name}: {e}")

    return imported_agents


# Auto-import all agents
_imported_agent_names = _discover_and_import_agents()

# Export all discovered agents for convenient access
__all__ = _imported_agent_names
