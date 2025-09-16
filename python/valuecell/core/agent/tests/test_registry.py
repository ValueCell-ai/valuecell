"""
Pytest unit tests for the AgentRegistry system.
"""

from typing import AsyncIterator

import pytest
from valuecell.core.agent.registry import (
    AgentRegistry,
    clear_registry,
    count,
    get_agent_class_by_name,
    get_all_agents,
    get_default_registry,
    get_name_for_class,
    get_registry_info,
    is_registered,
    list_agent_names,
    register,
    unregister_all,
    unregister_by_class,
    unregister_by_name,
)
from valuecell.core.types import BaseAgent


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    async def stream(
        self, query: str, session_id: str, task_id: str
    ) -> AsyncIterator[dict]:
        """Mock stream method."""
        yield {"content": f"Mock response to: {query}", "is_task_complete": True}


class TestAgentRegistryInstance:
    """Test cases for AgentRegistry instance methods."""

    def setup_method(self):
        """Setup before each test method."""
        self._registry = AgentRegistry()

    def test_init(self):
        """Test registry initialization."""
        registry = AgentRegistry()
        assert isinstance(registry._agents, dict)
        assert len(registry._agents) == 0

    def test_register_and_get_agent(self):
        """Test basic registration and retrieval."""

        class TestAgent(MockAgent):
            pass

        # Test registration
        self._registry.register(TestAgent, "TestAgent")
        assert self._registry.is_registered("TestAgent")

        # Test retrieval
        retrieved = self._registry.get_agent_class_by_name("TestAgent")
        assert retrieved == TestAgent

    def test_get_agent_name_simplified(self):
        """Test that get_agent_name always returns class name."""

        class SimpleAgent(MockAgent):
            pass

        # Should always return class name
        assert self._registry.get_name_for_class(SimpleAgent) == "SimpleAgent"

        # Even if we manually add __agent_name__, it should be ignored
        SimpleAgent.__agent_name__ = "SomeOtherName"
        assert self._registry.get_name_for_class(SimpleAgent) == "SimpleAgent"

    def test_register_multiple_keys_same_class(self):
        """Test registering the same class with multiple keys."""

        class MultiKeyAgent(MockAgent):
            pass

        # Register with multiple keys
        self._registry.register(MultiKeyAgent, "MultiKeyAgent")
        self._registry.register(MultiKeyAgent, "Alias1")
        self._registry.register(MultiKeyAgent, "Alias2")

        # All keys should work
        assert self._registry.get_agent_class_by_name("MultiKeyAgent") == MultiKeyAgent
        assert self._registry.get_agent_class_by_name("Alias1") == MultiKeyAgent
        assert self._registry.get_agent_class_by_name("Alias2") == MultiKeyAgent

        # Should be counted as one unique agent
        assert self._registry.count() == 1
        assert len(self._registry.list_agent_names()) == 1
        assert "MultiKeyAgent" in self._registry.list_agent_names()

    def test_list_agents_unique(self):
        """Test that list_agents returns unique agent names."""

        class AgentA(MockAgent):
            pass

        class AgentB(MockAgent):
            pass

        # Register with multiple keys
        self._registry.register(AgentA, "AgentA")
        self._registry.register(AgentA, "AliasA")
        self._registry.register(AgentB, "AgentB")

        # Should only return unique class names
        agent_list = self._registry.list_agent_names()
        assert len(agent_list) == 2
        assert "AgentA" in agent_list
        assert "AgentB" in agent_list

    def test_get_all_agents(self):
        """Test get_all_agents returns all registration keys."""

        class TestAgent(MockAgent):
            pass

        self._registry.register(TestAgent, "TestAgent")
        self._registry.register(TestAgent, "Alias")

        all_agents = self._registry.get_all_agents()
        assert len(all_agents) == 2
        assert "TestAgent" in all_agents
        assert "Alias" in all_agents
        assert all_agents["TestAgent"] == TestAgent
        assert all_agents["Alias"] == TestAgent

    def test_count_unique_agents(self):
        """Test that count returns unique agent count."""

        class AgentA(MockAgent):
            pass

        class AgentB(MockAgent):
            pass

        # Register with multiple keys
        self._registry.register(AgentA, "AgentA")
        self._registry.register(AgentA, "AliasA")
        self._registry.register(AgentB, "AgentB")

        # Should count unique agents only
        assert self._registry.count() == 2

    def test_unregister_by_name(self):
        """Test unregistering by name removes all keys for that agent."""

        class TestAgent(MockAgent):
            pass

        # Register with multiple keys
        self._registry.register(TestAgent, "TestAgent")
        self._registry.register(TestAgent, "Alias")

        # Verify both keys exist
        assert self._registry.is_registered("TestAgent")
        assert self._registry.is_registered("Alias")

        # Unregister by one key (returns list of removed keys)
        result = self._registry.unregister_by_name("TestAgent")
        assert result == ["TestAgent", "Alias"]

        # Both keys should be removed
        assert not self._registry.is_registered("TestAgent")
        assert not self._registry.is_registered("Alias")

    def test_unregister_by_class(self):
        """Test unregistering by class reference."""

        class TestAgent(MockAgent):
            pass

        self._registry.register(TestAgent, "TestAgent")
        self._registry.register(TestAgent, "Alias")

        # Unregister by class (returns list of removed keys)
        result = self._registry.unregister_by_class(TestAgent)
        assert result == ["TestAgent", "Alias"]

        # Should be completely removed
        assert not self._registry.is_registered("TestAgent")
        assert not self._registry.is_registered("Alias")

    def test_unregister_nonexistent(self):
        """Test unregistering nonexistent agents returns False."""

        result = self._registry.unregister_by_name("NonExistent")
        assert result == []

        class UnregisteredAgent(MockAgent):
            pass

        result = self._registry.unregister_by_class(UnregisteredAgent)
        assert result == []

    def test_unregister_all_with_pattern(self):
        """Test pattern-based unregistration."""

        class TestAgent1(MockAgent):
            pass

        class TestAgent2(MockAgent):
            pass

        class OtherAgent(MockAgent):
            pass

        self._registry.register(TestAgent1, "TestPrefix_1")
        self._registry.register(TestAgent2, "TestPrefix_2")
        self._registry.register(OtherAgent, "Other")

        # Unregister by pattern
        unregistered = self._registry.unregister_all("TestPrefix")
        assert len(unregistered) == 2
        assert "TestPrefix_1" in unregistered
        assert "TestPrefix_2" in unregistered

        # Other agent should remain
        assert self._registry.is_registered("Other")
        assert not self._registry.is_registered("TestPrefix_1")
        assert not self._registry.is_registered("TestPrefix_2")

    def test_unregister_all_no_pattern(self):
        """Test unregistering all agents without pattern."""

        class Agent1(MockAgent):
            pass

        class Agent2(MockAgent):
            pass

        self._registry.register(Agent1, "Agent1")
        self._registry.register(Agent2, "Agent2")

        assert self._registry.count() == 2

        unregistered = self._registry.unregister_all()
        assert len(unregistered) == 2
        assert "Agent1" in unregistered
        assert "Agent2" in unregistered
        assert self._registry.count() == 0

    def test_is_registered(self):
        """Test registration check."""

        class TestAgent(MockAgent):
            pass

        assert not self._registry.is_registered("TestAgent")

        self._registry.register(TestAgent, "TestAgent")
        assert self._registry.is_registered("TestAgent")

        self._registry.register(TestAgent, "Alias")
        assert self._registry.is_registered("Alias")

    def test_get_registry_info(self):
        """Test registry info generation."""

        class TestAgent(MockAgent):
            pass

        self._registry.register(TestAgent, "TestAgent")
        self._registry.register(TestAgent, "Alias")

        info = self._registry.get_registry_info()

        # Should have one entry for the unique class
        assert len(info) == 1
        assert "TestAgent" in info

        agent_info = info["TestAgent"]
        assert agent_info["class_name"] == "TestAgent"
        assert agent_info["agent_name"] == "TestAgent"
        assert sorted(agent_info["registered_keys"]) == ["Alias", "TestAgent"]
        assert "class_qualname" in agent_info

    def test_clear(self):
        """Test clearing the registry."""

        class TestAgent(MockAgent):
            pass

        self._registry.register(TestAgent, "TestAgent")
        assert self._registry.count() == 1

        self._registry.clear()
        assert self._registry.count() == 0
        assert not self._registry.is_registered("TestAgent")

    def test_empty_registry_operations(self):
        """Test operations on empty registry."""

        assert self._registry.count() == 0
        assert self._registry.list_agent_names() == []
        assert self._registry.get_agent_class_by_name("NonExistent") is None
        assert not self._registry.is_registered("NonExistent")
        assert self._registry.get_all_agents() == {}
        assert self._registry.get_registry_info() == {}


class TestDefaultRegistry:
    """Test cases for default registry module functions."""

    def setup_method(self):
        """Setup before each test method."""
        clear_registry()

    def teardown_method(self):
        """Cleanup after each test method."""
        clear_registry()

    def test_get_default_registry(self):
        """Test getting the default registry instance."""
        registry = get_default_registry()
        assert isinstance(registry, AgentRegistry)

        # Should be the same instance across calls
        registry2 = get_default_registry()
        assert registry is registry2

    def test_register_agent_function(self):
        """Test the register_agent module function."""

        class TestAgent(MockAgent):
            pass

        register(TestAgent, "TestAgent")
        assert is_registered("TestAgent")

        retrieved = get_agent_class_by_name("TestAgent")
        assert retrieved == TestAgent

    def test_module_functions_delegation(self):
        """Test that module functions properly delegate to default registry."""

        class Agent1(MockAgent):
            pass

        class Agent2(MockAgent):
            pass

        # Test registration and basic functions
        register(Agent1, "Agent1")
        register(Agent2, "Agent2")
        register(Agent1, "Agent1Alias")  # Multiple keys

        # Test all module functions
        assert count() == 2
        agents = list_agent_names()
        assert len(agents) == 2
        assert "Agent1" in agents
        assert "Agent2" in agents

        assert get_agent_class_by_name("Agent1") == Agent1
        assert get_agent_class_by_name("Agent1Alias") == Agent1
        assert get_name_for_class(Agent1) == "Agent1"

        all_agents = get_all_agents()
        assert len(all_agents) == 3  # 3 keys total
        assert "Agent1" in all_agents
        assert "Agent2" in all_agents
        assert "Agent1Alias" in all_agents

        assert is_registered("Agent1")
        assert is_registered("Agent1Alias")
        assert not is_registered("NonExistent")

        # Test unregistration (module-level functions return list of removed keys)
        result = unregister_by_name("Agent1")
        assert result == ["Agent1", "Agent1Alias"]
        assert not is_registered("Agent1")
        assert not is_registered("Agent1Alias")  # Should remove all keys
        result = unregister_by_class(Agent2)
        assert result == ["Agent2"]
        assert not is_registered("Agent2")

        assert count() == 0

    def test_unregister_all_function(self):
        """Test the unregister_all module function."""

        class TestAgent1(MockAgent):
            pass

        class TestAgent2(MockAgent):
            pass

        register(TestAgent1, "Test_1")
        register(TestAgent2, "Test_2")
        register(TestAgent1, "Other")

        # Test pattern unregistration
        unregistered = unregister_all("Test")
        assert len(unregistered) == 2
        assert "Test_1" in unregistered
        assert "Test_2" in unregistered
        # Note: Since TestAgent1 was unregistered by "Test_1", "Other" is also removed
        assert not is_registered("Other")  # Changed expectation

        # Register again for next test
        register(TestAgent1, "Remaining")

        # Test unregister all without pattern
        unregistered = unregister_all()
        assert len(unregistered) == 1
        assert "TestAgent1" in unregistered
        assert count() == 0

    def test_get_registry_info_function(self):
        """Test the get_registry_info module function."""

        class InfoTestAgent(MockAgent):
            pass

        register(InfoTestAgent, "InfoTestAgent")
        register(InfoTestAgent, "InfoAlias")

        info = get_registry_info()
        assert len(info) == 1
        assert "InfoTestAgent" in info

        agent_info = info["InfoTestAgent"]
        assert agent_info["class_name"] == "InfoTestAgent"
        assert sorted(agent_info["registered_keys"]) == ["InfoAlias", "InfoTestAgent"]


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Setup before each test method."""
        self._registry = AgentRegistry()

    def test_duplicate_registration(self):
        """Test registering the same agent with the same key multiple times."""

        class DuplicateAgent(MockAgent):
            pass

        self._registry.register(DuplicateAgent, "DuplicateAgent")
        self._registry.register(DuplicateAgent, "DuplicateAgent")  # Same registration

        # Should only be counted once
        assert self._registry.count() == 1
        assert len(self._registry.list_agent_names()) == 1
        assert len(self._registry.get_all_agents()) == 1

    def test_none_values(self):
        """Test handling of None values."""

        # get_agent with None or empty string
        assert self._registry.get_agent_class_by_name(None) is None
        assert self._registry.get_agent_class_by_name("") is None

        # is_registered with None or empty string
        assert not self._registry.is_registered(None)
        assert not self._registry.is_registered("")

    def test_class_without_name(self):
        """Test handling classes with modified __name__ attribute."""

        class TestAgent(MockAgent):
            pass

        # Test normal behavior first
        assert self._registry.get_name_for_class(TestAgent) == "TestAgent"

        # We can't delete __name__ from a class, so let's test with None __name__
        # This is more of a theoretical edge case

        # Create a mock class-like object that doesn't have __name__
        class MockClassWithoutName:
            pass

        # Remove __name__ after creation (only works with certain objects)
        try:
            # This will likely fail, which is expected behavior
            result = self._registry.get_name_for_class(MockClassWithoutName)
            assert result == "MockClassWithoutName"
        except AttributeError:
            # This is the expected behavior for malformed classes
            pass

    def test_large_registry(self):
        """Test performance with a larger number of agents."""

        agents = []
        for i in range(100):
            # Create dynamic agent classes using type() - cleaner than exec
            def make_stream_method(agent_num):
                async def stream(self, query, session_id, task_id):
                    yield {
                        "content": f"Agent{agent_num} response to: {query}",
                        "is_task_complete": True,
                    }

                return stream

            agent_class = type(
                f"Agent{i}", (MockAgent,), {"stream": make_stream_method(i)}
            )

            agents.append(agent_class)

            self._registry.register(agent_class, f"Agent{i}")
            if i % 2 == 0:  # Register some with aliases
                self._registry.register(agent_class, f"Alias{i}")

        # Test operations on large registry
        assert self._registry.count() == 100
        assert len(self._registry.list_agent_names()) == 100
        assert len(self._registry.get_all_agents()) == 150  # 100 + 50 aliases

        # When unregistering by pattern "Alias", all agent classes with an alias matching the pattern are found,
        # and for each, all associated keys (including primary names and all aliases) are removed from the registry.
        unregistered = self._registry.unregister_all("Alias")
        assert len(unregistered) == 50  # 50 alias keys matched

        # After unregistering agents that had aliases, those agents are completely removed
        # So we should have 50 agents left (the odd-numbered ones that didn't have aliases)
        remaining_count = self._registry.count()
        assert remaining_count == 50  # Only the agents without aliases remain

        remaining_agents = self._registry.get_all_agents()
        assert len(remaining_agents) == 50  # Only the keys for agents without aliases


if __name__ == "__main__":
    pytest.main([__file__])
