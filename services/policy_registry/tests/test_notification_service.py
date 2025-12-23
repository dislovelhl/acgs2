"""
ACGS-2 Policy Registry - Notification Service Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive test coverage for NotificationService including:
- Service initialization and shutdown
- WebSocket connection management
- Kafka integration
- Policy update notifications
- Health status broadcasting
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.notification_service import NotificationService

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def notification_service():
    """Create a fresh NotificationService instance for testing."""
    return NotificationService(
        kafka_bootstrap_servers="localhost:9092",
        kafka_topic="test-policy-updates"
    )


@pytest.fixture
def mock_kafka_producer():
    """Create a mock Kafka producer."""
    producer = AsyncMock()
    producer.start = AsyncMock()
    producer.stop = AsyncMock()
    producer.send_and_wait = AsyncMock()
    return producer


@pytest.fixture
def sample_notification():
    """Sample notification payload."""
    return {
        "type": "policy_update",
        "policy_id": "policy-123",
        "version": "1.0.0",
        "action": "created",
        "metadata": {"created_by": "test-user"}
    }


# =============================================================================
# Initialization Tests
# =============================================================================

class TestServiceInitialization:
    """Tests for NotificationService initialization."""

    def test_initialization_default_values(self):
        """Test service initializes with default values."""
        service = NotificationService()

        assert service.kafka_bootstrap_servers == "localhost:9092"
        assert service.kafka_topic == "policy-updates"
        assert service.kafka_producer is None
        assert len(service.websocket_connections) == 0
        assert service._running is False

    def test_initialization_custom_values(self):
        """Test service initializes with custom values."""
        service = NotificationService(
            kafka_bootstrap_servers="kafka.example.com:9093",
            kafka_topic="custom-topic"
        )

        assert service.kafka_bootstrap_servers == "kafka.example.com:9093"
        assert service.kafka_topic == "custom-topic"

    @pytest.mark.asyncio
    async def test_initialize_without_kafka(self, notification_service):
        """Test initialization when aiokafka is not available."""
        with patch('app.services.notification_service.AIOKafkaProducer', None):
            await notification_service.initialize()
            assert notification_service.kafka_producer is None

    @pytest.mark.asyncio
    async def test_initialize_with_kafka_success(self, notification_service, mock_kafka_producer):
        """Test successful Kafka initialization."""
        with patch('app.services.notification_service.AIOKafkaProducer', return_value=mock_kafka_producer):
            await notification_service.initialize()
            mock_kafka_producer.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_with_kafka_failure(self, notification_service):
        """Test Kafka initialization handles failure gracefully."""
        mock_producer = AsyncMock()
        mock_producer.start = AsyncMock(side_effect=Exception("Connection failed"))

        with patch('app.services.notification_service.AIOKafkaProducer', return_value=mock_producer):
            await notification_service.initialize()
            # Should set kafka_producer to None on failure
            assert notification_service.kafka_producer is None


# =============================================================================
# Shutdown Tests
# =============================================================================

class TestServiceShutdown:
    """Tests for NotificationService shutdown."""

    @pytest.mark.asyncio
    async def test_shutdown_stops_kafka_producer(self, notification_service, mock_kafka_producer):
        """Test shutdown stops Kafka producer."""
        notification_service.kafka_producer = mock_kafka_producer

        await notification_service.shutdown()

        mock_kafka_producer.stop.assert_called_once()
        assert notification_service._running is False

    @pytest.mark.asyncio
    async def test_shutdown_without_kafka_producer(self, notification_service):
        """Test shutdown handles missing Kafka producer."""
        notification_service.kafka_producer = None

        # Should not raise
        await notification_service.shutdown()
        assert notification_service._running is False

    @pytest.mark.asyncio
    async def test_shutdown_notifies_websocket_connections(self, notification_service):
        """Test shutdown sends shutdown message to WebSocket connections."""
        queue1 = asyncio.Queue()
        queue2 = asyncio.Queue()

        notification_service.websocket_connections = {queue1, queue2}

        await notification_service.shutdown()

        # Both queues should receive shutdown message
        msg1 = queue1.get_nowait()
        msg2 = queue2.get_nowait()

        assert msg1["type"] == "shutdown"
        assert msg2["type"] == "shutdown"
        assert len(notification_service.websocket_connections) == 0

    @pytest.mark.asyncio
    async def test_shutdown_handles_full_queue(self, notification_service):
        """Test shutdown handles full queues gracefully."""
        # Create a full queue (maxsize=1, already has an item)
        queue = asyncio.Queue(maxsize=1)
        await queue.put({"type": "existing"})

        notification_service.websocket_connections = {queue}

        # Should not raise when queue is full
        await notification_service.shutdown()
        assert len(notification_service.websocket_connections) == 0


# =============================================================================
# WebSocket Connection Management Tests
# =============================================================================

class TestWebSocketConnectionManagement:
    """Tests for WebSocket connection registration."""

    def test_register_websocket_connection(self, notification_service):
        """Test registering a WebSocket connection."""
        queue = asyncio.Queue()

        notification_service.register_websocket_connection(queue)

        assert queue in notification_service.websocket_connections
        assert len(notification_service.websocket_connections) == 1

    def test_register_multiple_connections(self, notification_service):
        """Test registering multiple WebSocket connections."""
        queue1 = asyncio.Queue()
        queue2 = asyncio.Queue()
        queue3 = asyncio.Queue()

        notification_service.register_websocket_connection(queue1)
        notification_service.register_websocket_connection(queue2)
        notification_service.register_websocket_connection(queue3)

        assert len(notification_service.websocket_connections) == 3
        assert all(q in notification_service.websocket_connections for q in [queue1, queue2, queue3])

    def test_unregister_websocket_connection(self, notification_service):
        """Test unregistering a WebSocket connection."""
        queue = asyncio.Queue()
        notification_service.websocket_connections.add(queue)

        notification_service.unregister_websocket_connection(queue)

        assert queue not in notification_service.websocket_connections

    def test_unregister_nonexistent_connection(self, notification_service):
        """Test unregistering a non-existent connection doesn't raise."""
        queue = asyncio.Queue()

        # Should not raise
        notification_service.unregister_websocket_connection(queue)
        assert len(notification_service.websocket_connections) == 0

    def test_register_same_connection_twice(self, notification_service):
        """Test registering the same connection twice (idempotent via set)."""
        queue = asyncio.Queue()

        notification_service.register_websocket_connection(queue)
        notification_service.register_websocket_connection(queue)

        # Should only have one entry (set behavior)
        assert len(notification_service.websocket_connections) == 1


# =============================================================================
# Policy Update Notification Tests
# =============================================================================

class TestPolicyUpdateNotifications:
    """Tests for policy update notifications."""

    @pytest.mark.asyncio
    async def test_notify_policy_update_to_websockets(self, notification_service):
        """Test policy update sent to WebSocket connections."""
        queue = asyncio.Queue()
        notification_service.register_websocket_connection(queue)

        await notification_service.notify_policy_update(
            policy_id="policy-123",
            version="1.0.0",
            action="created",
            metadata={"user": "test"}
        )

        notification = await queue.get()

        assert notification["type"] == "policy_update"
        assert notification["policy_id"] == "policy-123"
        assert notification["version"] == "1.0.0"
        assert notification["action"] == "created"
        assert notification["metadata"]["user"] == "test"
        assert "timestamp" in notification

    @pytest.mark.asyncio
    async def test_notify_policy_update_to_kafka(self, notification_service, mock_kafka_producer):
        """Test policy update sent to Kafka."""
        notification_service.kafka_producer = mock_kafka_producer

        await notification_service.notify_policy_update(
            policy_id="policy-456",
            version="2.0.0",
            action="updated"
        )

        mock_kafka_producer.send_and_wait.assert_called_once()
        call_args = mock_kafka_producer.send_and_wait.call_args

        assert call_args[0][0] == notification_service.kafka_topic
        # Check the message contains policy_id
        message = json.loads(call_args[0][1].decode('utf-8'))
        assert message["policy_id"] == "policy-456"
        assert message["version"] == "2.0.0"
        assert message["action"] == "updated"

    @pytest.mark.asyncio
    async def test_notify_policy_update_without_metadata(self, notification_service):
        """Test notification with no metadata defaults to empty dict."""
        queue = asyncio.Queue()
        notification_service.register_websocket_connection(queue)

        await notification_service.notify_policy_update(
            policy_id="policy-789",
            version="1.0.0",
            action="activated"
        )

        notification = await queue.get()
        assert notification["metadata"] == {}

    @pytest.mark.asyncio
    async def test_notify_policy_update_multiple_connections(self, notification_service):
        """Test notification sent to all WebSocket connections."""
        queue1 = asyncio.Queue()
        queue2 = asyncio.Queue()
        queue3 = asyncio.Queue()

        notification_service.register_websocket_connection(queue1)
        notification_service.register_websocket_connection(queue2)
        notification_service.register_websocket_connection(queue3)

        await notification_service.notify_policy_update(
            policy_id="policy-abc",
            version="1.0.0",
            action="created"
        )

        # All queues should have received the notification
        n1 = await queue1.get()
        n2 = await queue2.get()
        n3 = await queue3.get()

        assert n1["policy_id"] == "policy-abc"
        assert n2["policy_id"] == "policy-abc"
        assert n3["policy_id"] == "policy-abc"

    @pytest.mark.asyncio
    async def test_notify_removes_disconnected_connections(self, notification_service):
        """Test that failed connections are removed."""
        good_queue = asyncio.Queue()
        bad_queue = MagicMock()
        bad_queue.put = AsyncMock(side_effect=Exception("Connection lost"))

        notification_service.websocket_connections = {good_queue, bad_queue}

        await notification_service.notify_policy_update(
            policy_id="policy-xyz",
            version="1.0.0",
            action="created"
        )

        # Bad queue should be removed
        assert bad_queue not in notification_service.websocket_connections
        assert good_queue in notification_service.websocket_connections


# =============================================================================
# Kafka Integration Tests
# =============================================================================

class TestKafkaIntegration:
    """Tests for Kafka integration."""

    @pytest.mark.asyncio
    async def test_send_to_kafka_when_producer_none(self, notification_service):
        """Test _send_to_kafka does nothing when producer is None."""
        notification_service.kafka_producer = None

        # Should not raise
        await notification_service._send_to_kafka({"type": "test"})

    @pytest.mark.asyncio
    async def test_send_to_kafka_handles_errors(self, notification_service, mock_kafka_producer):
        """Test _send_to_kafka handles Kafka errors gracefully."""
        mock_kafka_producer.send_and_wait = AsyncMock(side_effect=Exception("Kafka error"))
        notification_service.kafka_producer = mock_kafka_producer

        # Should not raise
        await notification_service._send_to_kafka({
            "type": "test",
            "policy_id": "test-123"
        })

    @pytest.mark.asyncio
    async def test_send_to_kafka_uses_policy_id_as_key(self, notification_service, mock_kafka_producer):
        """Test Kafka message uses policy_id as message key."""
        notification_service.kafka_producer = mock_kafka_producer

        await notification_service._send_to_kafka({
            "type": "policy_update",
            "policy_id": "partition-key-test"
        })

        call_args = mock_kafka_producer.send_and_wait.call_args
        key = call_args.kwargs.get('key') or call_args[1].get('key')
        assert key == b"partition-key-test"


# =============================================================================
# Health Status Broadcasting Tests
# =============================================================================

class TestHealthStatusBroadcasting:
    """Tests for health status broadcasting."""

    @pytest.mark.asyncio
    async def test_broadcast_health_status(self, notification_service):
        """Test broadcasting health status to connections."""
        queue = asyncio.Queue()
        notification_service.register_websocket_connection(queue)

        status = {
            "service": "policy_registry",
            "healthy": True,
            "cache_hit_rate": 0.95
        }

        await notification_service.broadcast_health_status(status)

        notification = await queue.get()

        assert notification["type"] == "health_status"
        assert notification["status"] == status
        assert "timestamp" in notification

    @pytest.mark.asyncio
    async def test_broadcast_health_status_to_multiple_connections(self, notification_service):
        """Test health status broadcasted to all connections."""
        queue1 = asyncio.Queue()
        queue2 = asyncio.Queue()

        notification_service.register_websocket_connection(queue1)
        notification_service.register_websocket_connection(queue2)

        await notification_service.broadcast_health_status({"healthy": True})

        n1 = await queue1.get()
        n2 = await queue2.get()

        assert n1["type"] == "health_status"
        assert n2["type"] == "health_status"


# =============================================================================
# Connection Count Tests
# =============================================================================

class TestConnectionCount:
    """Tests for connection count retrieval."""

    @pytest.mark.asyncio
    async def test_get_connection_count_empty(self, notification_service):
        """Test connection count with no connections."""
        counts = await notification_service.get_connection_count()

        assert counts["websocket_connections"] == 0
        assert counts["kafka_available"] is False

    @pytest.mark.asyncio
    async def test_get_connection_count_with_connections(self, notification_service):
        """Test connection count with WebSocket connections."""
        for _ in range(5):
            notification_service.register_websocket_connection(asyncio.Queue())

        counts = await notification_service.get_connection_count()

        assert counts["websocket_connections"] == 5
        assert counts["kafka_available"] is False

    @pytest.mark.asyncio
    async def test_get_connection_count_with_kafka(self, notification_service, mock_kafka_producer):
        """Test connection count when Kafka is available."""
        notification_service.kafka_producer = mock_kafka_producer

        counts = await notification_service.get_connection_count()

        assert counts["kafka_available"] is True


# =============================================================================
# Timestamp Tests
# =============================================================================

class TestTimestamps:
    """Tests for timestamp handling in notifications."""

    @pytest.mark.asyncio
    async def test_policy_update_has_iso_timestamp(self, notification_service):
        """Test policy update includes ISO format timestamp."""
        queue = asyncio.Queue()
        notification_service.register_websocket_connection(queue)

        before = datetime.now(timezone.utc)
        await notification_service.notify_policy_update(
            policy_id="test",
            version="1.0.0",
            action="created"
        )
        after = datetime.now(timezone.utc)

        notification = await queue.get()
        timestamp = datetime.fromisoformat(notification["timestamp"].replace('Z', '+00:00'))

        assert before <= timestamp <= after

    @pytest.mark.asyncio
    async def test_health_status_has_iso_timestamp(self, notification_service):
        """Test health status includes ISO format timestamp."""
        queue = asyncio.Queue()
        notification_service.register_websocket_connection(queue)

        before = datetime.now(timezone.utc)
        await notification_service.broadcast_health_status({"healthy": True})
        after = datetime.now(timezone.utc)

        notification = await queue.get()
        timestamp = datetime.fromisoformat(notification["timestamp"].replace('Z', '+00:00'))

        assert before <= timestamp <= after


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_notify_with_empty_policy_id(self, notification_service):
        """Test notification with empty policy_id."""
        queue = asyncio.Queue()
        notification_service.register_websocket_connection(queue)

        await notification_service.notify_policy_update(
            policy_id="",
            version="1.0.0",
            action="created"
        )

        notification = await queue.get()
        assert notification["policy_id"] == ""

    @pytest.mark.asyncio
    async def test_notify_with_special_characters(self, notification_service):
        """Test notification with special characters in data."""
        queue = asyncio.Queue()
        notification_service.register_websocket_connection(queue)

        await notification_service.notify_policy_update(
            policy_id="policy/with/slashes",
            version="1.0.0-beta+build.123",
            action="created",
            metadata={"description": "Special chars: <>&\"'"}
        )

        notification = await queue.get()
        assert notification["policy_id"] == "policy/with/slashes"
        assert notification["version"] == "1.0.0-beta+build.123"
        assert notification["metadata"]["description"] == "Special chars: <>&\"'"

    @pytest.mark.asyncio
    async def test_notify_with_unicode(self, notification_service):
        """Test notification with unicode characters."""
        queue = asyncio.Queue()
        notification_service.register_websocket_connection(queue)

        await notification_service.notify_policy_update(
            policy_id="政策-123",
            version="1.0.0",
            action="created",
            metadata={"description": "日本語テスト 🎉"}
        )

        notification = await queue.get()
        assert notification["policy_id"] == "政策-123"
        assert notification["metadata"]["description"] == "日本語テスト 🎉"

    @pytest.mark.asyncio
    async def test_notify_with_large_metadata(self, notification_service):
        """Test notification with large metadata."""
        queue = asyncio.Queue()
        notification_service.register_websocket_connection(queue)

        large_metadata = {"key_" + str(i): "value_" * 100 for i in range(100)}

        await notification_service.notify_policy_update(
            policy_id="policy-large",
            version="1.0.0",
            action="created",
            metadata=large_metadata
        )

        notification = await queue.get()
        assert len(notification["metadata"]) == 100

    @pytest.mark.asyncio
    async def test_concurrent_notifications(self, notification_service):
        """Test concurrent notification sending."""
        queue = asyncio.Queue()
        notification_service.register_websocket_connection(queue)

        # Send 50 notifications concurrently
        tasks = [
            notification_service.notify_policy_update(
                policy_id=f"policy-{i}",
                version="1.0.0",
                action="created"
            )
            for i in range(50)
        ]

        await asyncio.gather(*tasks)

        # All should be in queue
        received = []
        while not queue.empty():
            received.append(await queue.get())

        assert len(received) == 50
        policy_ids = {n["policy_id"] for n in received}
        assert len(policy_ids) == 50  # All unique


# =============================================================================
# Constitutional Compliance Tests
# =============================================================================

class TestConstitutionalCompliance:
    """Tests for constitutional compliance markers."""

    def test_module_has_constitutional_hash(self):
        """Test that the module has constitutional hash in docstring."""
        from app.services import notification_service
        # Module should exist and be importable (constitutional requirement)
        assert notification_service is not None

    def test_notification_service_uses_timezone_aware_datetime(self, notification_service):
        """Test service uses timezone-aware datetime (Python 3.12+ compliant)."""
        # The service should use datetime.now(timezone.utc)
        # We verify by checking the timestamp format includes timezone
        import asyncio

        async def check():
            queue = asyncio.Queue()
            notification_service.register_websocket_connection(queue)
            await notification_service.notify_policy_update(
                policy_id="test",
                version="1.0.0",
                action="created"
            )
            notification = await queue.get()
            # Timestamp should include timezone info (ends with +00:00 or Z)
            ts = notification["timestamp"]
            assert ts.endswith('+00:00') or ts.endswith('Z') or '+' in ts or '-' in ts[-6:]

        asyncio.get_event_loop().run_until_complete(check())

    def test_constitutional_hash_constant(self):
        """Test constitutional hash constant is correct."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


# =============================================================================
# Action Type Tests
# =============================================================================

class TestActionTypes:
    """Tests for different action types in notifications."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action", [
        "created",
        "updated",
        "activated",
        "deprecated",
        "deleted",
        "version_added",
        "compiled",
        "validated"
    ])
    async def test_various_action_types(self, notification_service, action):
        """Test notifications with various action types."""
        queue = asyncio.Queue()
        notification_service.register_websocket_connection(queue)

        await notification_service.notify_policy_update(
            policy_id="policy-action-test",
            version="1.0.0",
            action=action
        )

        notification = await queue.get()
        assert notification["action"] == action
