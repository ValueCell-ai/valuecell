from pathlib import Path


def get_root_path() -> str:
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


def get_agent_card_path() -> str:
    """
    Returns the path to the agent card JSON file located in the configs/agent_cards directory.

    Returns:
        str: Absolute path of the agent card JSON file
    """
    root_path = get_root_path()
    agent_card_path = Path(root_path) / "configs" / "agent_cards"
    return str(agent_card_path)
