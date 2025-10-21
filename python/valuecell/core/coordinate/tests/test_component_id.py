"""Tests for component_id override functionality."""

from valuecell.core.agent.responses import streaming, notification
from valuecell.core.coordinate.response import ResponseFactory
from valuecell.core.types import CommonResponseEvent


class TestComponentIdInStreamingResponse:
    """Test component_id in streaming.component_generator()"""

    def test_component_generator_without_component_id(self):
        """Test that component_generator works without component_id (backward compatible)"""
        response = streaming.component_generator(
            content='{"data": "test"}',
            component_type="test_component",
        )

        assert response.event == CommonResponseEvent.COMPONENT_GENERATOR
        assert response.content == '{"data": "test"}'
        assert response.metadata["component_type"] == "test_component"
        assert "component_id" not in response.metadata

    def test_component_generator_with_component_id(self):
        """Test that component_id is included in metadata when provided"""
        response = streaming.component_generator(
            content='{"data": "test"}',
            component_type="test_component",
            component_id="my_custom_id",
        )

        assert response.event == CommonResponseEvent.COMPONENT_GENERATOR
        assert response.content == '{"data": "test"}'
        assert response.metadata["component_type"] == "test_component"
        assert response.metadata["component_id"] == "my_custom_id"

    def test_component_generator_with_none_component_id(self):
        """Test that explicitly passing None for component_id doesn't include it"""
        response = streaming.component_generator(
            content='{"data": "test"}',
            component_type="test_component",
            component_id=None,
        )

        assert "component_id" not in response.metadata


class TestComponentIdInNotificationResponse:
    """Test component_id in notification.component_generator()"""

    def test_notification_component_generator_without_component_id(self):
        """Test that notification component_generator works without component_id"""
        response = notification.component_generator(
            content='{"data": "test"}',
            component_type="test_component",
        )

        assert response.event == CommonResponseEvent.COMPONENT_GENERATOR
        assert response.content == '{"data": "test"}'
        assert response.metadata["component_type"] == "test_component"
        assert "component_id" not in response.metadata

    def test_notification_component_generator_with_component_id(self):
        """Test that component_id is included in metadata for notifications"""
        response = notification.component_generator(
            content='{"data": "test"}',
            component_type="test_component",
            component_id="notification_id",
        )

        assert response.event == CommonResponseEvent.COMPONENT_GENERATOR
        assert response.content == '{"data": "test"}'
        assert response.metadata["component_type"] == "test_component"
        assert response.metadata["component_id"] == "notification_id"


class TestComponentIdInResponseFactory:
    """Test component_id in ResponseFactory.component_generator()"""

    def test_response_factory_without_component_id(self):
        """Test ResponseFactory generates item_id when no component_id provided"""
        factory = ResponseFactory()

        response = factory.component_generator(
            conversation_id="conv_123",
            thread_id="thread_456",
            task_id="task_789",
            content='{"data": "test"}',
            component_type="test_component",
        )

        assert response.data.conversation_id == "conv_123"
        assert response.data.thread_id == "thread_456"
        assert response.data.task_id == "task_789"
        assert response.data.payload.content == '{"data": "test"}'
        assert response.data.payload.component_type == "test_component"
        # Should have auto-generated item_id
        assert response.data.item_id is not None
        assert response.data.item_id.startswith("item-")

    def test_response_factory_with_component_id(self):
        """Test ResponseFactory uses component_id to override item_id"""
        factory = ResponseFactory()

        response = factory.component_generator(
            conversation_id="conv_123",
            thread_id="thread_456",
            task_id="task_789",
            content='{"data": "test"}',
            component_type="test_component",
            component_id="my_stable_id",
        )

        # component_id should override item_id
        assert response.data.item_id == "my_stable_id"

    def test_response_factory_with_both_item_id_and_component_id(self):
        """Test that component_id takes precedence over item_id"""
        factory = ResponseFactory()

        response = factory.component_generator(
            conversation_id="conv_123",
            thread_id="thread_456",
            task_id="task_789",
            content='{"data": "test"}',
            component_type="test_component",
            item_id="item_abc",
            component_id="component_xyz",
        )

        # component_id should take precedence
        assert response.data.item_id == "component_xyz"

    def test_response_factory_with_only_item_id(self):
        """Test that item_id is used when component_id is not provided"""
        factory = ResponseFactory()

        response = factory.component_generator(
            conversation_id="conv_123",
            thread_id="thread_456",
            task_id="task_789",
            content='{"data": "test"}',
            component_type="test_component",
            item_id="item_custom",
        )

        # item_id should be used
        assert response.data.item_id == "item_custom"

    def test_response_factory_priority_order(self):
        """Test the priority order: component_id > item_id > auto-generated"""
        factory = ResponseFactory()

        # Priority 1: component_id (highest)
        r1 = factory.component_generator(
            conversation_id="conv",
            thread_id="thread",
            task_id="task",
            content="test",
            component_type="type",
            item_id="item_id",
            component_id="component_id",
        )
        assert r1.data.item_id == "component_id"

        # Priority 2: item_id
        r2 = factory.component_generator(
            conversation_id="conv",
            thread_id="thread",
            task_id="task",
            content="test",
            component_type="type",
            item_id="item_id",
            component_id=None,
        )
        assert r2.data.item_id == "item_id"

        # Priority 3: auto-generated (lowest)
        r3 = factory.component_generator(
            conversation_id="conv",
            thread_id="thread",
            task_id="task",
            content="test",
            component_type="type",
            item_id=None,
            component_id=None,
        )
        assert r3.data.item_id.startswith("item-")


class TestComponentIdReplaceScenario:
    """Integration test simulating real-world replace scenario"""

    def test_simulated_replace_scenario(self):
        """Simulate an agent sending updates with the same component_id"""
        factory = ResponseFactory()
        CHART_ID = "portfolio_chart_live"

        # First update
        update1 = factory.component_generator(
            conversation_id="conv_1",
            thread_id="thread_1",
            task_id="task_1",
            content='{"value": 100}',
            component_type="chart",
            component_id=CHART_ID,
        )

        # Second update (same component_id)
        update2 = factory.component_generator(
            conversation_id="conv_1",
            thread_id="thread_1",
            task_id="task_1",
            content='{"value": 150}',
            component_type="chart",
            component_id=CHART_ID,
        )

        # Third update (same component_id)
        update3 = factory.component_generator(
            conversation_id="conv_1",
            thread_id="thread_1",
            task_id="task_1",
            content='{"value": 200}',
            component_type="chart",
            component_id=CHART_ID,
        )

        # All should have the same item_id (for frontend to replace)
        assert update1.data.item_id == CHART_ID
        assert update2.data.item_id == CHART_ID
        assert update3.data.item_id == CHART_ID

        # But different content
        assert update1.data.payload.content == '{"value": 100}'
        assert update2.data.payload.content == '{"value": 150}'
        assert update3.data.payload.content == '{"value": 200}'

    def test_simulated_append_scenario(self):
        """Simulate an agent sending news items that should append"""
        factory = ResponseFactory()

        # Create multiple news items without component_id
        news_items = []
        for i in range(3):
            item = factory.component_generator(
                conversation_id="conv_1",
                thread_id="thread_1",
                task_id="task_1",
                content=f'{{"title": "News {i}"}}',
                component_type="news",
                # No component_id = append behavior
            )
            news_items.append(item)

        # Each should have a different auto-generated item_id
        item_ids = [item.data.item_id for item in news_items]
        assert len(item_ids) == len(set(item_ids))  # All unique
        assert all(item_id.startswith("item-") for item_id in item_ids)
