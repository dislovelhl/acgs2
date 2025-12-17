"""
ACGS-2 Deliberation Layer - Integration
Main integration point for the deliberation layer components.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone

try:
    from ..models import AgentMessage, MessageStatus
except ImportError:
    # Fallback for direct execution or testing
    from models import AgentMessage, MessageStatus  # type: ignore

try:
    from .impact_scorer import get_impact_scorer, calculate_message_impact
    from .adaptive_router import get_adaptive_router
    from .deliberation_queue import (
        get_deliberation_queue, DeliberationStatus, VoteType
    )
    from .llm_assistant import get_llm_assistant
    from .redis_integration import (
        get_redis_deliberation_queue, get_redis_voting_system
    )
except ImportError:
    # Fallback for direct execution or testing
    from impact_scorer import (  # type: ignore
        get_impact_scorer, calculate_message_impact
    )
    from adaptive_router import get_adaptive_router  # type: ignore
    from deliberation_queue import (  # type: ignore
        get_deliberation_queue, DeliberationStatus, VoteType
    )
    from llm_assistant import get_llm_assistant  # type: ignore
    from redis_integration import (  # type: ignore
        get_redis_deliberation_queue, get_redis_voting_system
    )


logger = logging.getLogger(__name__)


class DeliberationLayer:
    """Main integration class for the deliberation layer."""

    def __init__(self,
                 impact_threshold: float = 0.8,
                 deliberation_timeout: int = 300,
                 enable_redis: bool = False,
                 enable_learning: bool = True,
                 enable_llm: bool = True):
        """
        Initialize the deliberation layer.

        Args:
            impact_threshold: Threshold for routing to deliberation
            deliberation_timeout: Timeout for deliberation in seconds
            enable_redis: Whether to use Redis for persistence
            enable_learning: Whether to enable adaptive learning
            enable_llm: Whether to enable LLM assistance
        """
        self.impact_threshold = impact_threshold
        self.deliberation_timeout = deliberation_timeout
        self.enable_redis = enable_redis
        self.enable_learning = enable_learning
        self.enable_llm = enable_llm

        # Initialize components
        self.impact_scorer = get_impact_scorer()
        self.adaptive_router = get_adaptive_router()
        self.deliberation_queue = get_deliberation_queue()
        self.llm_assistant = get_llm_assistant() if enable_llm else None

        # Redis components (if enabled)
        self.redis_queue = get_redis_deliberation_queue() if enable_redis else None
        self.redis_voting = get_redis_voting_system() if enable_redis else None

        # Processing callbacks
        self.fast_lane_callback: Optional[Callable] = None
        self.deliberation_callback: Optional[Callable] = None

        logger.info("Initialized ACGS-2 Deliberation Layer")

    async def initialize(self):
        """Initialize async components."""
        if self.enable_redis:
            if self.redis_queue:
                await self.redis_queue.connect()
            if self.redis_voting:
                await self.redis_voting.connect()

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Process a message through the deliberation layer.

        Returns:
            Processing result with routing decision
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Step 1: Calculate impact score if not present
            if message.impact_score is None:
                message.impact_score = calculate_message_impact(message.content)
                logger.debug(f"Calculated impact score {message.impact_score:.3f} for message {message.message_id}")

            # Step 2: Route the message
            routing_decision = await self.adaptive_router.route_message(message)

            # Step 3: Execute routing
            if routing_decision.get('lane') == 'fast':
                result = await self._process_fast_lane(message, routing_decision)
            else:
                result = await self._process_deliberation(message, routing_decision)

            # Step 4: Record performance feedback
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            await self._record_performance_feedback(message, result, processing_time)

            result['processing_time'] = processing_time
            result['success'] = True

            logger.info(f"Processed message {message.message_id} in {processing_time:.2f}s: {result.get('lane')}")

            return result

        except asyncio.CancelledError:
            logger.info(f"Message processing cancelled for {message.message_id}")
            raise
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout processing message {message.message_id}: {e}")
            return {
                'success': False,
                'error': f'Timeout: {e}',
                'processing_time': (datetime.now(timezone.utc) - start_time).total_seconds()
            }
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Data error processing message {message.message_id}: {type(e).__name__}: {e}")
            return {
                'success': False,
                'error': f'{type(e).__name__}: {e}',
                'processing_time': (datetime.now(timezone.utc) - start_time).total_seconds()
            }
        except (AttributeError, RuntimeError) as e:
            logger.error(f"Runtime error processing message {message.message_id}: {type(e).__name__}: {e}")
            return {
                'success': False,
                'error': f'{type(e).__name__}: {e}',
                'processing_time': (datetime.now(timezone.utc) - start_time).total_seconds()
            }

    async def _process_fast_lane(self, message: AgentMessage, routing_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Process message through fast lane."""
        # Update message status
        message.status = MessageStatus.DELIVERED

        # Execute fast lane callback if provided
        if self.fast_lane_callback:
            await self.fast_lane_callback(message)

        return {
            'lane': 'fast',
            'status': 'delivered',
            'impact_score': message.impact_score,
            'routing_decision': routing_decision
        }

    async def _process_deliberation(self, message: AgentMessage, routing_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Process message through deliberation queue."""
        # Enqueue for deliberation
        item_id = await self.deliberation_queue.enqueue_for_deliberation(
            message=message,
            requires_human_review=True,
            requires_multi_agent_vote=routing_decision.get('impact_score', 0) > 0.9,
            timeout_seconds=self.deliberation_timeout
        )

        # Store in Redis if enabled
        if self.redis_queue:
            await self.redis_queue.enqueue_deliberation_item(
                message=message,
                item_id=item_id,
                metadata=routing_decision
            )

        # Execute deliberation callback if provided
        if self.deliberation_callback:
            await self.deliberation_callback(message, routing_decision)

        return {
            'lane': 'deliberation',
            'item_id': item_id,
            'status': 'queued',
            'impact_score': message.impact_score,
            'routing_decision': routing_decision,
            'estimated_wait_time': self.deliberation_timeout
        }

    async def _record_performance_feedback(self,
                                         message: AgentMessage,
                                         result: Dict[str, Any],
                                         processing_time: float):
        """Record performance feedback for learning."""
        if not self.enable_learning:
            return

        try:
            # Determine outcome
            if result.get('lane') == 'fast':
                outcome = 'fast_lane'
                feedback_score = 0.8 if result.get('success') else 0.2
            else:
                # For deliberation, we'll need to track the final outcome
                outcome = 'deliberation_queued'
                feedback_score = None  # Will be updated when deliberation completes

            await self.adaptive_router.update_performance_feedback(
                message_id=message.message_id,
                actual_outcome=outcome,
                processing_time=processing_time,
                feedback_score=feedback_score
            )

        except asyncio.CancelledError:
            raise
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Failed to record performance feedback: {type(e).__name__}: {e}")

    async def submit_human_decision(self,
                                  item_id: str,
                                  reviewer: str,
                                  decision: str,
                                  reasoning: str) -> bool:
        """
        Submit human review decision.

        Args:
            item_id: Deliberation item ID
            reviewer: Human reviewer identifier
            decision: Decision ('approved', 'rejected', 'escalated')
            reasoning: Review reasoning

        Returns:
            True if decision submitted successfully
        """
        try:
            # Map decision string to DeliberationStatus enum
            decision_map = {
                'approved': DeliberationStatus.APPROVED,
                'rejected': DeliberationStatus.REJECTED,
                'escalated': DeliberationStatus.UNDER_REVIEW
            }

            deliberation_decision = decision_map.get(
                decision, DeliberationStatus.REJECTED
            )

            success = await self.deliberation_queue.submit_human_decision(
                item_id=item_id,
                reviewer=reviewer,
                decision=deliberation_decision,
                reasoning=reasoning
            )

            if success:
                logger.info(f"Human decision submitted for item {item_id}: {decision} by {reviewer}")

                # Update performance feedback
                await self._update_deliberation_outcome(item_id, decision, reasoning)

            return success

        except asyncio.CancelledError:
            raise
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Failed to submit human decision for item {item_id}: {type(e).__name__}: {e}")
            return False
        except (AttributeError, RuntimeError) as e:
            logger.error(f"Runtime error submitting human decision for item {item_id}: {e}")
            return False

    async def submit_agent_vote(self,
                              item_id: str,
                              agent_id: str,
                              vote: str,
                              reasoning: str,
                              confidence: float = 1.0) -> bool:
        """
        Submit agent vote for deliberation item.

        Returns:
            True if vote submitted successfully
        """
        try:
            # Map vote string to VoteType enum
            vote_map = {
                'approve': VoteType.APPROVE,
                'reject': VoteType.REJECT,
                'abstain': VoteType.ABSTAIN
            }
            vote_enum = vote_map.get(vote.lower(), VoteType.ABSTAIN)

            success = await self.deliberation_queue.submit_agent_vote(
                item_id=item_id,
                agent_id=agent_id,
                vote=vote_enum,
                reasoning=reasoning,
                confidence=confidence
            )

            if success:
                logger.info(f"Agent vote submitted for item {item_id}: {vote} by {agent_id}")

                # Submit to Redis voting if enabled
                if self.redis_voting:
                    await self.redis_voting.submit_vote(
                        item_id=item_id,
                        agent_id=agent_id,
                        vote=vote,
                        reasoning=reasoning,
                        confidence=confidence
                    )

            return success

        except asyncio.CancelledError:
            raise
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Failed to submit agent vote for item {item_id}: {type(e).__name__}: {e}")
            return False
        except (AttributeError, RuntimeError) as e:
            logger.error(f"Runtime error submitting agent vote for item {item_id}: {e}")
            return False

    async def _update_deliberation_outcome(self,
                                         item_id: str,
                                         decision: str,
                                         reasoning: str):
        """Update performance feedback for completed deliberation."""
        if not self.enable_learning:
            return

        try:
            # Find the message ID from the deliberation item
            item_details = self.deliberation_queue.get_item_details(item_id)
            if not item_details:
                return

            message_id = item_details.get('message_id')
            if not message_id:
                return

            # Map decision to outcome
            outcome_map = {
                'approved': 'approved',
                'rejected': 'rejected',
                'escalated': 'escalated'
            }

            outcome = outcome_map.get(decision, 'rejected')

            # Calculate feedback score based on decision confidence
            feedback_score = 0.9 if decision == 'approved' else 0.7 if decision == 'escalated' else 0.5

            await self.adaptive_router.update_performance_feedback(
                message_id=message_id,
                actual_outcome=outcome,
                processing_time=0,  # Will be calculated from history
                feedback_score=feedback_score
            )

        except asyncio.CancelledError:
            raise
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Failed to update deliberation outcome: {type(e).__name__}: {e}")

    def get_layer_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for the deliberation layer."""
        try:
            router_stats = self.adaptive_router.get_routing_stats()
            queue_stats = self.deliberation_queue.get_queue_status()

            stats = {
                'layer_status': 'operational',
                'impact_threshold': self.impact_threshold,
                'deliberation_timeout': self.deliberation_timeout,
                'features': {
                    'redis_enabled': self.enable_redis,
                    'learning_enabled': self.enable_learning,
                    'llm_enabled': self.enable_llm
                },
                'router_stats': router_stats,
                'queue_stats': queue_stats['stats'],
                'queue_size': queue_stats['queue_size'],
                'processing_count': queue_stats['processing_count']
            }

            if self.redis_queue:
                stats['redis_info'] = asyncio.run(self.redis_queue.get_stream_info())

            return stats

        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Failed to get layer stats: {type(e).__name__}: {e}")
            return {'error': f'{type(e).__name__}: {e}'}
        except RuntimeError as e:
            logger.error(f"Runtime error getting layer stats: {e}")
            return {'error': f'RuntimeError: {e}'}

    def set_fast_lane_callback(self, callback: Callable):
        """Set callback for fast lane processing."""
        self.fast_lane_callback = callback

    def set_deliberation_callback(self, callback: Callable):
        """Set callback for deliberation processing."""
        self.deliberation_callback = callback

    async def analyze_trends(self) -> Dict[str, Any]:
        """Analyze deliberation trends for optimization."""
        if not self.llm_assistant:
            return {'error': 'LLM assistant not enabled'}

        try:
            # Get deliberation history (simplified)
            history = []  # Would need to implement history collection

            analysis = await self.llm_assistant.analyze_deliberation_trends(history)
            return analysis

        except asyncio.CancelledError:
            raise
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Failed to analyze trends: {type(e).__name__}: {e}")
            return {'error': f'{type(e).__name__}: {e}'}
        except RuntimeError as e:
            logger.error(f"Runtime error analyzing trends: {e}")
            return {'error': f'RuntimeError: {e}'}

    async def force_deliberation(self, message: AgentMessage, reason: str = "manual_override") -> Dict[str, Any]:
        """Force a message into deliberation regardless of impact score."""
        logger.info(f"Forcing message {message.message_id} into deliberation: {reason}")

        # Temporarily override impact score
        original_score = message.impact_score
        message.impact_score = 1.0

        result = await self.adaptive_router.force_deliberation(message, reason)

        # Restore original score
        message.impact_score = original_score

        return result


# Global deliberation layer instance
_deliberation_layer = None

def get_deliberation_layer() -> DeliberationLayer:
    """Get or create global deliberation layer instance."""
    global _deliberation_layer
    if _deliberation_layer is None:
        _deliberation_layer = DeliberationLayer()
    return _deliberation_layer