"""Constitutional Hash: cdd01ef066bc6cf2
Notification service for policy updates via WebSocket and Kafka
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Set

try:
    from aiokafka import AIOKafkaProducer
except ImportError:
    AIOKafkaProducer = None

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for real-time notifications of policy changes"""

    def __init__(
        self, kafka_bootstrap_servers: str = "localhost:9092", kafka_topic: str = "policy-updates"
    ):
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.kafka_topic = kafka_topic
        self.kafka_producer = None
        self.websocket_connections: Set[asyncio.Queue] = set()
        self._running = False

    async def initialize(self):
        """Initialize notification services"""
        # Initialize Kafka producer
        if AIOKafkaProducer:
            try:
                self.kafka_producer = AIOKafkaProducer(
                    bootstrap_servers=self.kafka_bootstrap_servers
                )
                await self.kafka_producer.start()
                logger.info("Kafka producer initialized")
            except Exception as e:
                logger.warning(f"Kafka producer initialization failed: {e}")
                self.kafka_producer = None
        else:
            logger.warning("aiokafka not available, Kafka notifications disabled")

    async def shutdown(self):
        """Shutdown notification services"""
        self._running = False

        # Close Kafka producer
        if self.kafka_producer:
            await self.kafka_producer.stop()

        # Close WebSocket connections
        for queue in self.websocket_connections.copy():
            try:
                queue.put_nowait({"type": "shutdown"})
            except (asyncio.QueueFull, RuntimeError, AttributeError):
                # Queue full or connection already closed, skip
                pass
        self.websocket_connections.clear()

    async def notify_policy_update(
        self, policy_id: str, version: str, action: str, metadata: Dict[str, Any] = None
    ):
        """
        Notify subscribers of policy updates

        Args:
            policy_id: Policy identifier
            version: Policy version
            action: Update action (created, updated, activated, etc.)
            metadata: Additional metadata
        """
        notification = {
            "type": "policy_update",
            "policy_id": policy_id,
            "version": version,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

        # Send to Kafka
        await self._send_to_kafka(notification)

        # Send to WebSocket connections
        await self._send_to_websockets(notification)

    async def _send_to_kafka(self, notification: Dict[str, Any]):
        """Send notification to Kafka topic"""
        if not self.kafka_producer:
            return

        try:
            message = json.dumps(notification).encode("utf-8")
            await self.kafka_producer.send_and_wait(
                self.kafka_topic, message, key=notification["policy_id"].encode("utf-8")
            )

        except Exception as e:
            logger.error(f"Kafka send failed: {e}")

    async def _send_to_websockets(self, notification: Dict[str, Any]):
        """Send notification to WebSocket connections"""
        disconnected = set()

        for queue in self.websocket_connections:
            try:
                await queue.put(notification)
            except Exception as e:
                logger.warning(f"WebSocket send failed: {e}")
                disconnected.add(queue)

        # Remove disconnected clients
        self.websocket_connections -= disconnected

    def register_websocket_connection(self, queue: asyncio.Queue):
        """Register a WebSocket connection for notifications"""
        self.websocket_connections.add(queue)

    def unregister_websocket_connection(self, queue: asyncio.Queue):
        """Unregister a WebSocket connection"""
        self.websocket_connections.discard(queue)

    async def broadcast_health_status(self, status: Dict[str, Any]):
        """Broadcast health status to all connections"""
        notification = {
            "type": "health_status",
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await self._send_to_websockets(notification)

    async def get_connection_count(self) -> Dict[str, int]:
        """Get current connection counts"""
        return {
            "websocket_connections": len(self.websocket_connections),
            "kafka_available": self.kafka_producer is not None,
        }
