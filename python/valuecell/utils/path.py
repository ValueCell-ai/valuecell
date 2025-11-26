"""Utilities for resolving Python package and repository root paths.

Note: Database default location logic moved to `valuecell.utils.db.resolve_db_path`,
which defaults to storing `valuecell.db` in the system application directory
(same path as `.env`).
"""

import os
import shutil
from pathlib import Path

from .env import get_system_env_dir


def get_python_root_path() -> str:
    """
    Returns the root directory of the current Python project (where pyproject.toml is located)

    Returns:
        str: Absolute path of the project root directory

    Raises:
        FileNotFoundError: If pyproject.toml file cannot be found
    """
    # Start searching from the current file's directory upwards
    current_path = Path(__file__).resolve()

    # Traverse upwards through parent directories to find pyproject.toml
    for parent in current_path.parents:
        pyproject_path = parent / "pyproject.toml"
        if pyproject_path.exists():
            return str(parent)

    # If not found, raise an exception
    raise FileNotFoundError(
        "pyproject.toml file not found, unable to determine project root directory"
    )


def get_repo_root_path() -> str:
    """
    Resolve repository root directory path.

    Assumes this file is at `repo_root/python/valuecell/utils/path.py`.
    Walk up three levels to reach `repo_root`.
    """
    here = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    return repo_root


def get_agent_card_path() -> str:
    """
    Returns the path to the agent card JSON file located in the configs/agent_cards directory.

    Returns:
        str: Absolute path of the agent card JSON file
    """
    root_path = get_python_root_path()
    agent_card_path = Path(root_path) / "configs" / "agent_cards"
    return str(agent_card_path)


def get_knowledge_path() -> str:
    """
    Resolve the Knowledge directory path under the system application directory.

    Behavior:
    - Default location: `<system_env_dir>/.knowledge` (same base dir as `.env`)
    - One-time migration: if old repo-root `.knowledge` exists and the system dir
      is empty, copy the contents for continuity.
    """
    new_path = Path(get_system_env_dir()) / ".knowledge"
    new_path.mkdir(parents=True, exist_ok=True)

    old_path = Path(get_repo_root_path()) / ".knowledge"
    try:
        if old_path.exists() and not any(new_path.iterdir()):
            for item in old_path.iterdir():
                src = item
                dst = new_path / item.name
                if item.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
    except Exception:
        # Non-fatal: proceed with new_path even if migration fails
        pass

    return str(new_path)
