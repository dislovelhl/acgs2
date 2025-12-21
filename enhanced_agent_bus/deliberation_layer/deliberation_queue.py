"""
ACGS-2 Deliberation Layer - Deliberation Queue
Constitutional Hash: cdd01ef066bc6cf2
Persistent queue for high-impact messages awaiting approval.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import json
import uuid

from ..models import AgentMessage, MessageStatus

logger = logging.getLogger(__name__)

@dataclass
class DeliberationTask:
    task_id: str
    message: AgentMessage
    status: str = "PENDING" # PENDING, IN_PROGRESS, APPROVED, REJECTED
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class DeliberationQueue:
    """
    Queue for managing messages that require human-in-the-loop or 
    multi-agent deliberation.
    """
    def __init__(self, persistence_path: Optional[str] = None):
        self.tasks: Dict[str, DeliberationTask] = {}
        self.persistence_path = persistence_path or "deliberation_tasks.json"
        self._lock = asyncio.Lock()
        self._load_tasks()

    def _load_tasks(self):
        """Load tasks from persistent storage."""
        try:
            with open(self.persistence_path, 'r') as f:
                data = json.load(f)
                for tid, tdata in data.items():
                    # Simplified reconstruction
                    msg = AgentMessage.from_dict(tdata['message'])
                    task = DeliberationTask(
                        task_id=tid,
                        message=msg,
                        status=tdata['status'],
                        metadata=tdata.get('metadata', {}),
                        created_at=datetime.fromisoformat(tdata['created_at'])
                    )
                    self.tasks[tid] = task
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    async def enqueue(self, message: AgentMessage, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a message to the deliberation queue."""
        async with self._lock:
            task_id = str(uuid.uuid4())
            task = DeliberationTask(
                task_id=task_id,
                message=message,
                metadata=metadata or {}
            )
            self.tasks[task_id] = task
            self._save_tasks()
            logger.info(f"Message {message.message_id} enqueued for deliberation (Task {task_id})")
            return task_id

    async def update_status(self, task_id: str, status: str):
        """Update the status of a deliberation task."""
        async with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].status = status
                self._save_tasks()
                logger.debug(f"Task {task_id} status updated to {status}")

    def get_pending_tasks(self) -> List[DeliberationTask]:
        """Get all tasks awaiting deliberation."""
        return [t for t in self.tasks.values() if t.status == "PENDING"]

    def _save_tasks(self):
        """Save current tasks to persistent storage."""
        try:
            # Note: In production we'd use a real database
            storage = {
                tid: {
                    "message": t.message.to_dict_raw(),
                    "status": t.status,
                    "metadata": t.metadata,
                    "created_at": t.created_at.isoformat()
                } for tid, t in self.tasks.items()
            }
            with open(self.persistence_path, 'w') as f:
                json.dump(storage, f)
        except Exception as e:
            logger.error(f"Failed to persist deliberation tasks: {e}")

    async def resolve_task(self, task_id: str, approved: bool):
        """Resolve a task and return approval status."""
        status = "APPROVED" if approved else "REJECTED"
        await self.update_status(task_id, status)
        
        task = self.tasks.get(task_id)
        if not task:
            return
            
        if approved:
            task.message.status = MessageStatus.PENDING # Ready for re-delivery
        else:
            task.message.status = MessageStatus.FAILED