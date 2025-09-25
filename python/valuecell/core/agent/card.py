import json
from pathlib import Path
from typing import Optional

from a2a.types import AgentCapabilities, AgentCard
from valuecell.utils import get_agent_card_path

FIELDS_UNDEFINED_IN_AGENT_CARD_MODEL = {"enabled", "metadata", "display_name"}


def parse_local_agent_card_dict(agent_card_dict: dict) -> Optional[AgentCard]:
    """Parse a dictionary into an AgentCard, filling in missing required fields.

    Args:
        agent_card_dict: Dictionary containing agent card data

    Returns:
        AgentCard instance if parsing succeeds, None if input is not a dict
    """
    if not isinstance(agent_card_dict, dict):
        return None
    # Defined by us, remove fields that are not part of AgentCard
    for field in FIELDS_UNDEFINED_IN_AGENT_CARD_MODEL:
        if field in agent_card_dict:
            del agent_card_dict[field]

    # Requested fields as per AgentCard model
    if "description" not in agent_card_dict:
        agent_card_dict["description"] = (
            f"No description available for {agent_card_dict.get('name', 'unknown')} agent."
        )
    if "capabilities" not in agent_card_dict:
        agent_card_dict["capabilities"] = AgentCapabilities(
            streaming=True, push_notifications=False
        ).model_dump()
    if "default_input_modes" not in agent_card_dict:
        agent_card_dict["default_input_modes"] = []
    if "default_output_modes" not in agent_card_dict:
        agent_card_dict["default_output_modes"] = []
    if "version" not in agent_card_dict:
        agent_card_dict["version"] = ""

    # Parse into AgentCard model
    agent_card = AgentCard.model_validate(agent_card_dict)
    return agent_card


def find_local_agent_card_by_agent_name(
    agent_name: str, base_dir: Optional[str | Path] = None
) -> Optional[AgentCard]:
    """Find an agent card by name from local JSON configuration files.

    Searches through JSON files in the agent_cards directory and returns the first
    matching agent card where the name field matches the provided agent_name.

    Args:
        agent_name: The name of the agent to search for
        base_dir: Optional base directory to search in. If None, uses default path

    Returns:
        AgentCard instance if found and enabled, None otherwise
    """
    agent_cards_path = Path(base_dir) if base_dir else Path(get_agent_card_path())

    # Check if the agent_cards directory exists
    if not agent_cards_path.exists():
        return None

    # Iterate through all JSON files in the agent_cards directory
    for json_file in agent_cards_path.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                agent_card_dict = json.load(f)

            # Check if this agent config has the matching name
            if not isinstance(agent_card_dict, dict):
                continue
            if agent_card_dict.get("name") != agent_name:
                continue
            if agent_card_dict.get("enabled", True) is False:
                continue
            return parse_local_agent_card_dict(agent_card_dict)

        except (json.JSONDecodeError, IOError):
            # Skip files that can't be read or parsed
            continue

    # Return None if no matching agent is found
    return None
