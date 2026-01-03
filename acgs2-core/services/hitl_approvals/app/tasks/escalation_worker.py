"""
Escalation Worker Task
Monitors Redis for approval timeouts and triggers auto-escalation.
"""

import asyncio
import logging

import redis.asyncio as redis

from ..config.settings import settings
from ..database import AsyncSessionLocal
from ..services.approval_chain_engine import ApprovalChainEngine

logger = logging.getLogger(__name__)


class EscalationWorker:
    """
    Background worker that handles time-based escalations using Redis keyspace notifications.
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._running = False

    async def start(self):
        """Start the escalation worker loop"""
        self._running = True

        try:
            # Connect to Redis
            self.redis_client = await redis.from_url(settings.redis_url, decode_responses=True)

            # Enable keyspace notifications for expired keys (Ex)
            # This requires Redis to be configured with 'notify-keyspace-events Ex'
            try:
                await self.redis_client.config_set("notify-keyspace-events", "Ex")
                logger.info("Enabled Redis keyspace notifications for expired keys")
            except Exception as e:
                logger.warning(
                    f"Could not enable keyspace notifications: {e}. Ensure Redis user has CONFIG permissions."
                )

            # Subscribe to expiration events
            pubsub = self.redis_client.pubsub()
            await pubsub.psubscribe("__keyevent@*__:expired")

            logger.info("Escalation worker started, monitoring expiration events")

            while self._running:
                try:
                    # Listen for messages with timeout
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message["type"] == "pmessage":
                        expired_key = message["data"]

                        # Pattern: hitl:escalation:pending:{request_id}
                        if expired_key.startswith("hitl:escalation:pending:"):
                            request_id = expired_key.split(":")[-1]
                            logger.info(f"Escalation timeout triggered for request {request_id}")

                            await self._process_escalation(request_id)

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error in escalation worker loop: {e}")
                    await asyncio.sleep(5)  # Backoff on error

        except Exception as e:
            logger.critical(f"Escalation worker failed to start: {e}")
            self._running = False

    async def stop(self):
        """Stop the escalation worker"""
        self._running = False
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Escalation worker stopped")

    async def _process_escalation(self, request_id: str):
        """Trigger the escalation logic for a request"""
        async with AsyncSessionLocal() as db:
            try:
                engine = ApprovalChainEngine(db)
                await engine.escalate_request(request_id)
                await db.commit()
                logger.info(f"Successfully processed escalation for request {request_id}")
            except Exception as e:
                logger.error(f"Failed to process escalation for request {request_id}: {e}")
                await db.rollback()


async def run_worker():
    """Entry point for the escalation worker process"""
    worker = EscalationWorker()

    # Handle signals for graceful shutdown
    asyncio.get_event_loop()

    try:
        await worker.start()
    except asyncio.CancelledError:
        await worker.stop()


if __name__ == "__main__":
    # Setup basic logging for standalone execution
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
