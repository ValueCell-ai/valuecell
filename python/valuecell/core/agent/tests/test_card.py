"""
Unit tests for valuecell.core.agent.card module
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch


from valuecell.core.agent.card import (
    find_local_agent_card_by_agent_name,
    parse_local_agent_card_dict,
)


class TestParseLocalAgentCardDict:
    """Test parse_local_agent_card_dict function."""

    def test_parse_valid_card_dict(self):
        """Test parsing a valid agent card dictionary."""
        card_dict = {
            "name": "test_agent",
            "url": "http://localhost:8000",
            "description": "Test agent",
            "capabilities": {"streaming": True, "push_notifications": False},
            "default_input_modes": ["text"],
            "default_output_modes": ["text"],
            "version": "1.0.0",
            "skills": [
                {
                    "id": "test_skill",
                    "name": "Test Skill",
                    "description": "A test skill",
                    "tags": ["test"],
                }
            ],
        }

        result = parse_local_agent_card_dict(card_dict)

        assert result is not None
        assert result.name == "test_agent"
        assert result.url == "http://localhost:8000"
        assert result.description == "Test agent"
        assert result.capabilities.streaming is True
        assert result.capabilities.push_notifications is False

    def test_parse_minimal_card_dict(self):
        """Test parsing a minimal agent card dictionary with defaults."""
        card_dict = {
            "name": "minimal_agent",
            "url": "http://localhost:8001",
            "skills": [
                {
                    "id": "minimal_skill",
                    "name": "Minimal Skill",
                    "description": "A minimal skill",
                    "tags": ["minimal"],
                }
            ],
        }

        result = parse_local_agent_card_dict(card_dict)

        assert result is not None
        assert result.name == "minimal_agent"
        assert result.url == "http://localhost:8001"
        assert "No description available" in result.description
        assert result.capabilities.streaming is True
        assert result.capabilities.push_notifications is False
        assert result.default_input_modes == []
        assert result.default_output_modes == []
        assert result.version == ""

    def test_parse_invalid_input(self):
        """Test parsing invalid input types."""
        assert parse_local_agent_card_dict(None) is None
        assert parse_local_agent_card_dict("string") is None
        assert parse_local_agent_card_dict([]) is None

    def test_remove_undefined_fields(self):
        """Test that undefined fields are removed from the dict."""
        card_dict = {
            "name": "test_agent",
            "url": "http://localhost:8000",
            "enabled": True,  # Should be removed
            "metadata": {"key": "value"},  # Should be removed
            "display_name": "Display Name",  # Should be removed
            "capabilities": {"streaming": True, "push_notifications": False},
            "skills": [
                {
                    "id": "test_skill",
                    "name": "Test Skill",
                    "description": "A test skill",
                    "tags": ["test"],
                }
            ],
        }

        result = parse_local_agent_card_dict(card_dict)

        assert result is not None
        assert result.name == "test_agent"
        # Verify undefined fields were removed from original dict
        assert "enabled" not in card_dict
        assert "metadata" not in card_dict
        assert "display_name" not in card_dict


class TestFindLocalAgentCardByAgentName:
    """Test find_local_agent_card_by_agent_name function."""

    @patch("valuecell.core.agent.card.get_agent_card_path")
    def test_find_existing_agent_card(self, mock_get_path):
        """Test finding an existing agent card."""
        # Create a temporary directory with agent card files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_get_path.return_value = temp_path

            # Create a test agent card file
            card_data = {
                "name": "test_agent",
                "url": "http://localhost:8000",
                "description": "Test agent",
                "capabilities": {"streaming": True, "push_notifications": False},
                "default_input_modes": ["text"],
                "default_output_modes": ["text"],
                "version": "1.0.0",
                "skills": [
                    {
                        "id": "test_skill",
                        "name": "Test Skill",
                        "description": "A test skill",
                        "tags": ["test"],
                    }
                ],
            }

            card_file = temp_path / "test_agent.json"
            card_file.write_text(json.dumps(card_data))

            result = find_local_agent_card_by_agent_name("test_agent")

            assert result is not None
            assert result.name == "test_agent"
            assert result.url == "http://localhost:8000"

    @patch("valuecell.core.agent.card.get_agent_card_path")
    def test_find_nonexistent_agent_card(self, mock_get_path):
        """Test finding a non-existent agent card."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_get_path.return_value = temp_path

            result = find_local_agent_card_by_agent_name("nonexistent_agent")

            assert result is None

    @patch("valuecell.core.agent.card.get_agent_card_path")
    def test_custom_base_dir(self, mock_get_path):
        """Test using a custom base directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Don't mock get_agent_card_path since we're providing base_dir

            # Create a test agent card file in custom directory
            card_data = {
                "name": "custom_agent",
                "url": "http://localhost:8000",
                "capabilities": {"streaming": True, "push_notifications": False},
                "skills": [
                    {
                        "id": "custom_skill",
                        "name": "Custom Skill",
                        "description": "A custom skill",
                        "tags": ["custom"],
                    }
                ],
            }

            card_file = temp_path / "custom_agent.json"
            card_file.write_text(json.dumps(card_data))

            result = find_local_agent_card_by_agent_name(
                "custom_agent", base_dir=temp_path
            )

            assert result is not None
            assert result.name == "custom_agent"

    @patch("valuecell.core.agent.card.get_agent_card_path")
    def test_find_disabled_agent_card(self, mock_get_path):
        """Test that disabled agent cards are not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            mock_get_path.return_value = temp_path

            # Create a disabled agent card file
            card_data = {
                "name": "disabled_agent",
                "url": "http://localhost:8000",
                "description": "Disabled agent",
                "capabilities": {"streaming": True, "push_notifications": False},
                "enabled": False,
                "skills": [
                    {
                        "id": "disabled_skill",
                        "name": "Disabled Skill",
                        "description": "A disabled skill",
                        "tags": ["disabled"],
                    }
                ],
            }

            card_file = temp_path / "disabled_agent.json"
            card_file.write_text(json.dumps(card_data))

            result = find_local_agent_card_by_agent_name("disabled_agent")

            assert result is None
