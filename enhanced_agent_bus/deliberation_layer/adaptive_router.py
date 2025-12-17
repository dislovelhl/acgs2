"""
ACGS-2 Deliberation Layer - Adaptive Router
Routes messages based on impact scores to appropriate processing lanes.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta

from ..models import AgentMessage, MessageStatus
from .impact_scorer import calculate_message_impact
from .deliberation_queue import get_deliberation_queue, DeliberationStatus


logger = logging.getLogger(__name__)


class AdaptiveRouter:
    """Routes messages based on impact assessment to appropriate processing lanes."""

    def __init__(self,
                 impact_threshold: float = 0.8,
                 deliberation_timeout: int = 300,
                 enable_learning: bool = True):
        """
        Initialize the adaptive router.

        Args:
            impact_threshold: Threshold above which messages go to deliberation
            deliberation_timeout: Default timeout for deliberation in seconds
            enable_learning: Whether to enable adaptive threshold learning
        """
        self.impact_threshold = impact_threshold
        self.deliberation_timeout = deliberation_timeout
        self.enable_learning = enable_learning

        # Learning data
        self.routing_history: list = []
        self.performance_metrics: Dict[str, Any] = {
            'total_messages': 0,
            'fast_lane_count': 0,
            'deliberation_count': 0,
            'deliberation_approved': 0,
            'deliberation_rejected': 0,
            'deliberation_timeout': 0,
            'false_positives': 0,  # High impact but should have been fast
            'false_negatives': 0,  # Low impact but needed deliberation
        }

        # Get deliberation queue
        self.deliberation_queue = get_deliberation_queue()

    async def route_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Route a message based on impact assessment.

        Returns:
            Routing decision with metadata
        """
        self.performance_metrics['total_messages'] += 1

        # Calculate impact score if not already present
        if message.impact_score is None:
            message.impact_score = calculate_message_impact(message.content)
            logger.debug(f"Calculated impact score {message.impact_score:.3f} for message {message.message_id}")

        impact_score = message.impact_score

        # Route decision
        if impact_score >= self.impact_threshold:
            # High-risk: route to deliberation queue
            return await self._route_to_deliberation(message)
        else:
            # Low-risk: fast lane
            return await self._route_to_fast_lane(message)

    async def _route_to_fast_lane(self, message: AgentMessage) -> Dict[str, Any]:
        """Route message to fast lane (automatic processing)."""
        self.performance_metrics['fast_lane_count'] += 1

        # Mark as processed
        message.status = MessageStatus.DELIVERED
        message.updated_at = datetime.utcnow()

        # Record routing decision
        routing_decision = {
            'lane': 'fast',
            'impact_score': message.impact_score,
            'decision_timestamp': datetime.utcnow(),
            'processing_time': 0.0,
            'requires_deliberation': False
        }

        self._record_routing_history(message, routing_decision)

        logger.info(f"Message {message.message_id} routed to fast lane "
                   f"(impact: {message.impact_score:.3f})")

        return routing_decision

    async def _route_to_deliberation(self, message: AgentMessage) -> Dict[str, Any]:
        """Route message to deliberation queue."""
        self.performance_metrics['deliberation_count'] += 1

        # Enqueue for deliberation
        item_id = await self.deliberation_queue.enqueue_for_deliberation(
            message=message,
            requires_human_review=True,
            requires_multi_agent_vote=True,
            timeout_seconds=self.deliberation_timeout
        )

        # Record routing decision
        routing_decision = {
            'lane': 'deliberation',
            'item_id': item_id,
            'impact_score': message.impact_score,
            'decision_timestamp': datetime.utcnow(),
            'requires_deliberation': True,
            'estimated_wait_time': self.deliberation_timeout
        }

        self._record_routing_history(message, routing_decision)

        logger.info(f"Message {message.message_id} routed to deliberation queue "
                   f"(impact: {message.impact_score:.3f}, item_id: {item_id})")

        return routing_decision

    def _record_routing_history(self, message: AgentMessage, routing_decision: Dict[str, Any]):
        """Record routing decision for learning."""
        if not self.enable_learning:
            return

        history_entry = {
            'message_id': message.message_id,
            'impact_score': message.impact_score,
            'routing_decision': routing_decision,
            'timestamp': datetime.utcnow(),
            'message_type': message.message_type.value,
            'priority': message.priority.value if hasattr(message.priority, 'value') else str(message.priority)
        }

        self.routing_history.append(history_entry)

        # Keep only recent history (last 1000 entries)
        if len(self.routing_history) > 1000:
            self.routing_history = self.routing_history[-1000:]

    async def update_performance_feedback(self,
                                        message_id: str,
                                        actual_outcome: str,
                                        processing_time: float,
                                        feedback_score: Optional[float] = None):
        """
        Update router with performance feedback for learning.

        Args:
            message_id: ID of the message
            actual_outcome: 'success', 'failure', 'timeout', etc.
            processing_time: Time taken to process
            feedback_score: Optional human feedback score (0-1)
        """
        if not self.enable_learning:
            return

        # Find routing decision in history
        routing_entry = None
        for entry in reversed(self.routing_history):
            if entry['message_id'] == message_id:
                routing_entry = entry
                break

        if not routing_entry:
            logger.warning(f"No routing history found for message {message_id}")
            return

        # Update performance metrics
        routing_entry['actual_outcome'] = actual_outcome
        routing_entry['processing_time'] = processing_time
        routing_entry['feedback_score'] = feedback_score

        # Update counters
        if routing_entry['routing_decision']['lane'] == 'deliberation':
            if actual_outcome == 'approved':
                self.performance_metrics['deliberation_approved'] += 1
            elif actual_outcome == 'rejected':
                self.performance_metrics['deliberation_rejected'] += 1
            elif actual_outcome == 'timeout':
                self.performance_metrics['deliberation_timeout'] += 1

        # Adaptive threshold adjustment (simple version)
        await self._adjust_threshold()

    async def _adjust_threshold(self):
        """Adjust impact threshold based on performance feedback."""
        if len(self.routing_history) < 50:  # Need minimum data
            return

        # Analyze recent performance
        recent_entries = self.routing_history[-100:]  # Last 100 decisions

        # Calculate false positive/negative rates
        deliberation_entries = [e for e in recent_entries if e['routing_decision']['lane'] == 'deliberation']
        fast_lane_entries = [e for e in recent_entries if e['routing_decision']['lane'] == 'fast']

        # False positives: deliberation that should have been fast
        false_positives = sum(1 for e in deliberation_entries
                            if e.get('feedback_score', 0.5) > 0.8)  # High feedback means it was appropriate

        # False negatives: fast lane that needed deliberation
        false_negatives = sum(1 for e in fast_lane_entries
                            if e.get('actual_outcome') in ['failure', 'timeout'])

        fp_rate = false_positives / max(len(deliberation_entries), 1)
        fn_rate = false_negatives / max(fast_lane_entries, 1)

        # Adjust threshold based on error rates
        adjustment = 0.0
        if fp_rate > 0.3:  # Too many false positives - increase threshold
            adjustment = 0.05
        elif fn_rate > 0.1:  # Too many false negatives - decrease threshold
            adjustment = -0.05

        if adjustment != 0.0:
            old_threshold = self.impact_threshold
            self.impact_threshold = max(0.1, min(0.95, self.impact_threshold + adjustment))

            if abs(self.impact_threshold - old_threshold) > 0.01:
                logger.info(f"Adjusted impact threshold from {old_threshold:.3f} to {self.impact_threshold:.3f} "
                           f"(FP rate: {fp_rate:.2f}, FN rate: {fn_rate:.2f})")

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics and performance metrics."""
        total = self.performance_metrics['total_messages']
        if total == 0:
            return self.performance_metrics.copy()

        stats = self.performance_metrics.copy()
        stats.update({
            'fast_lane_percentage': self.performance_metrics['fast_lane_count'] / total,
            'deliberation_percentage': self.performance_metrics['deliberation_count'] / total,
            'deliberation_approval_rate': (
                self.performance_metrics['deliberation_approved'] /
                max(self.performance_metrics['deliberation_count'], 1)
            ),
            'current_threshold': self.impact_threshold,
            'learning_enabled': self.enable_learning,
            'history_size': len(self.routing_history)
        })

        return stats

    def set_impact_threshold(self, threshold: float):
        """Manually set the impact threshold."""
        self.impact_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Impact threshold manually set to {self.impact_threshold}")

    async def force_deliberation(self, message: AgentMessage, reason: str = "manual_override") -> Dict[str, Any]:
        """Force a message into deliberation regardless of impact score."""
        logger.info(f"Forcing message {message.message_id} into deliberation: {reason}")

        # Override impact score for routing
        original_score = message.impact_score
        message.impact_score = 1.0

        result = await self._route_to_deliberation(message)

        # Restore original score
        message.impact_score = original_score

        result['forced'] = True
        result['force_reason'] = reason

        return result


# Global router instance
_adaptive_router = None

def get_adaptive_router() -> AdaptiveRouter:
    """Get or create global adaptive router instance."""
    global _adaptive_router
    if _adaptive_router is None:
        _adaptive_router = AdaptiveRouter()
    return _adaptive_router