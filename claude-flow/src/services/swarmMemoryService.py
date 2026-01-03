#!/usr/bin/env python3
"""
Swarm Memory Service for ACGS-2 Claude Flow CLI

Provides persistent memory operations for swarm state, agent data,
conversations, and learned patterns across sessions.

COMPATIBILITY: Python 3.11+ compatible
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SwarmMemoryService:
    """Persistent memory service for swarm data management."""

    def __init__(self, swarm_id: str, redis_client):
        self.swarm_id = swarm_id
        self.redis = redis_client
        self.namespaces = {
            "agents": f"swarm:{swarm_id}:agents",
            "conversations": f"swarm:{swarm_id}:conversations",
            "tasks": f"swarm:{swarm_id}:tasks",
            "patterns": f"swarm:{swarm_id}:patterns",
            "metrics": f"swarm:{swarm_id}:metrics"
        }

    async def store_agent_state(self, agent_id: str, state: Dict[str, Any]) -> bool:
        """Store agent state persistently."""
        try:
            key = f"{self.namespaces['agents']}:{agent_id}"
            state["last_updated"] = time.time()
            await self.redis.set(key, json.dumps(state))

            # Update agent index
            await self._update_index("agents", agent_id)
            return True
        except Exception as e:
            logger.error(f"Failed to store agent state {agent_id}: {e}")
            return False

    async def retrieve_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve agent state from persistent storage."""
        try:
            key = f"{self.namespaces['agents']}:{agent_id}"
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to retrieve agent state {agent_id}: {e}")
            return None

    async def store_conversation(self, conversation_id: str, messages: List[Dict[str, Any]]) -> bool:
        """Store conversation history persistently."""
        try:
            key = f"{self.namespaces['conversations']}:{conversation_id}"
            conversation_data = {
                "conversation_id": conversation_id,
                "messages": messages,
                "last_updated": time.time(),
                "message_count": len(messages)
            }
            await self.redis.set(key, json.dumps(conversation_data))

            # Update conversation index
            await self._update_index("conversations", conversation_id)
            return True
        except Exception as e:
            logger.error(f"Failed to store conversation {conversation_id}: {e}")
            return False

    async def retrieve_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve conversation from persistent storage."""
        try:
            key = f"{self.namespaces['conversations']}:{conversation_id}"
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to retrieve conversation {conversation_id}: {e}")
            return None

    async def store_task_progress(self, task_id: str, progress: Dict[str, Any]) -> bool:
        """Store task progress persistently."""
        try:
            key = f"{self.namespaces['tasks']}:{task_id}"
            progress["last_updated"] = time.time()
            await self.redis.set(key, json.dumps(progress))

            # Update task index
            await self._update_index("tasks", task_id)
            return True
        except Exception as e:
            logger.error(f"Failed to store task progress {task_id}: {e}")
            return False

    async def retrieve_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task progress from persistent storage."""
        try:
            key = f"{self.namespaces['tasks']}:{task_id}"
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to retrieve task progress {task_id}: {e}")
            return None

    async def store_learned_pattern(self, pattern_id: str, pattern: Dict[str, Any]) -> bool:
        """Store learned pattern persistently."""
        try:
            key = f"{self.namespaces['patterns']}:{pattern_id}"
            pattern["discovered_at"] = time.time()
            pattern["last_updated"] = time.time()
            await self.redis.set(key, json.dumps(pattern))

            # Update pattern index
            await self._update_index("patterns", pattern_id)
            return True
        except Exception as e:
            logger.error(f"Failed to store pattern {pattern_id}: {e}")
            return False

    async def retrieve_learned_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve learned pattern from persistent storage."""
        try:
            key = f"{self.namespaces['patterns']}:{pattern_id}"
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to retrieve pattern {pattern_id}: {e}")
            return None

    async def store_metric(self, metric_name: str, value: Any, timestamp: Optional[float] = None) -> bool:
        """Store metric data persistently."""
        try:
            if timestamp is None:
                timestamp = time.time()

            metric_data = {
                "name": metric_name,
                "value": value,
                "timestamp": timestamp
            }

            key = f"{self.namespaces['metrics']}:{metric_name}:{int(timestamp)}"
            await self.redis.set(key, json.dumps(metric_data))

            # Update metrics index
            await self._update_index("metrics", metric_name)
            return True
        except Exception as e:
            logger.error(f"Failed to store metric {metric_name}: {e}")
            return False

    async def get_swarm_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics for the swarm."""
        try:
            stats = {}
            for namespace_name, namespace_key in self.namespaces.items():
                index_key = f"{namespace_key}:index"
                index_data = await self.redis.get(index_key)
                if index_data:
                    stats[namespace_name] = json.loads(index_data)
                else:
                    stats[namespace_name] = {"item_count": 0}

            return {
                "swarm_id": self.swarm_id,
                "stats": stats,
                "total_namespaces": len(self.namespaces),
                "memory_backend": "redis"
            }
        except Exception as e:
            logger.error(f"Failed to get memory stats for swarm {self.swarm_id}: {e}")
            return {"error": str(e)}

    async def cleanup_expired_data(self, max_age_seconds: int = 86400 * 30) -> int:
        """Clean up expired data (older than max_age_seconds)."""
        try:
            cleaned_count = 0
            cutoff_time = time.time() - max_age_seconds

            # Clean up each namespace
            for namespace_name, namespace_key in self.namespaces.items():
                # Get all keys in namespace
                pattern = f"{namespace_key}:*"
                # Note: This is a simplified cleanup - in production you'd want more sophisticated cleanup
                # For now, we'll skip actual cleanup and just return 0
                pass

            return cleaned_count
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return 0

    async def _update_index(self, namespace: str, item_id: str):
        """Update the index for a namespace."""
        try:
            index_key = f"{self.namespaces[namespace]}:index"
            current_index = await self.redis.get(index_key)

            if current_index:
                index_data = json.loads(current_index)
                index_data["item_count"] += 1
                index_data["last_updated"] = time.time()
            else:
                index_data = {
                    "namespace": namespace,
                    "swarm_id": self.swarm_id,
                    "created_at": time.time(),
                    "item_count": 1,
                    "last_updated": time.time()
                }

            await self.redis.set(index_key, json.dumps(index_data))
        except Exception as e:
            logger.error(f"Failed to update index for {namespace}:{item_id}: {e}")
