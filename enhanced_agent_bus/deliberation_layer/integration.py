"""
ACGS-2 Deliberation Layer - Integration
Main integration point for the deliberation layer components.
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone

try:
    from ..models import AgentMessage, MessageStatus, CONSTITUTIONAL_HASH
except ImportError:
    # Fallback for direct execution or testing
    from models import AgentMessage, MessageStatus, CONSTITUTIONAL_HASH  # type: ignore

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
    from .opa_guard import (
        OPAGuard, get_opa_guard, GuardResult, GuardDecision,
        SignatureResult, ReviewResult
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
    from opa_guard import (  # type: ignore
        OPAGuard, get_opa_guard, GuardResult, GuardDecision,
        SignatureResult, ReviewResult
    )


logger = logging.getLogger(__name__)


class DeliberationLayer:
    """
    Main integration class for the deliberation layer.

    Integrates OPA policy guard for VERIFY-BEFORE-ACT pattern,
    multi-signature collection, and critic agent reviews.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(
        self,
        impact_threshold: float = 0.8,
        deliberation_timeout: int = 300,
        enable_redis: bool = False,
        enable_learning: bool = True,
        enable_llm: bool = True,
        enable_opa_guard: bool = True,
        high_risk_threshold: float = 0.8,
        critical_risk_threshold: float = 0.95,
    ):
        """
        Initialize the deliberation layer.

        Args:
            impact_threshold: Threshold for routing to deliberation
            deliberation_timeout: Timeout for deliberation in seconds
            enable_redis: Whether to use Redis for persistence
            enable_learning: Whether to enable adaptive learning
            enable_llm: Whether to enable LLM assistance
            enable_opa_guard: Whether to enable OPA policy guard
            high_risk_threshold: Threshold for requiring signatures
            critical_risk_threshold: Threshold for requiring full review
        """
        self.impact_threshold = impact_threshold
        self.deliberation_timeout = deliberation_timeout
        self.enable_redis = enable_redis
        self.enable_learning = enable_learning
        self.enable_llm = enable_llm
        self.enable_opa_guard = enable_opa_guard
        self.high_risk_threshold = high_risk_threshold
        self.critical_risk_threshold = critical_risk_threshold

        # Initialize components
        self.impact_scorer = get_impact_scorer()
        self.adaptive_router = get_adaptive_router()
        self.deliberation_queue = get_deliberation_queue()
        self.llm_assistant = get_llm_assistant() if enable_llm else None

        # OPA Guard for policy-based verification
        self.opa_guard: Optional[OPAGuard] = None
        if enable_opa_guard:
            self.opa_guard = OPAGuard(
                enable_signatures=True,
                enable_critic_review=True,
                signature_timeout=deliberation_timeout,
                review_timeout=deliberation_timeout,
                high_risk_threshold=high_risk_threshold,
                critical_risk_threshold=critical_risk_threshold,
            )

        # Redis components (if enabled)
        self.redis_queue = (
            get_redis_deliberation_queue() if enable_redis else None
        )
        self.redis_voting = (
            get_redis_voting_system() if enable_redis else None
        )

        # Processing callbacks
        self.fast_lane_callback: Optional[Callable] = None
        self.deliberation_callback: Optional[Callable] = None
        self.guard_callback: Optional[Callable] = None

        logger.info(
            "Initialized ACGS-2 Deliberation Layer with OPA Guard: "
            f"{enable_opa_guard}"
        )

    async def initialize(self):
        """Initialize async components."""
        if self.enable_redis:
            if self.redis_queue:
                await self.redis_queue.connect()
            if self.redis_voting:
                await self.redis_voting.connect()

        # Initialize OPA Guard
        if self.opa_guard:
            await self.opa_guard.initialize()
            logger.info("OPA Guard initialized")

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Process a message through the deliberation layer.

        Implements VERIFY-BEFORE-ACT pattern with OPA guard integration.

        Returns:
            Processing result with routing decision and guard result
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Step 1: Calculate impact score if not present
            if message.impact_score is None:
                message.impact_score = calculate_message_impact(message.content)
                logger.debug(
                    f"Calculated impact score {message.impact_score:.3f} "
                    f"for message {message.message_id}"
                )

            # Step 2: OPA Guard pre-action verification (VERIFY-BEFORE-ACT)
            guard_result = None
            if self.opa_guard:
                guard_result = await self._verify_with_opa_guard(message)

                # If guard denies, return immediately
                if guard_result and not guard_result.is_allowed:
                    if guard_result.decision == GuardDecision.DENY:
                        return await self._handle_guard_denial(
                            message, guard_result, start_time
                        )
                    elif guard_result.decision == GuardDecision.REQUIRE_SIGNATURES:
                        return await self._handle_signature_requirement(
                            message, guard_result, start_time
                        )
                    elif guard_result.decision == GuardDecision.REQUIRE_REVIEW:
                        return await self._handle_review_requirement(
                            message, guard_result, start_time
                        )

            # Step 3: Route the message
            routing_decision = await self.adaptive_router.route_message(message)

            # Step 4: Execute routing
            if routing_decision.get('lane') == 'fast':
                result = await self._process_fast_lane(
                    message, routing_decision
                )
            else:
                result = await self._process_deliberation(
                    message, routing_decision
                )

            # Step 5: Record performance feedback
            elapsed = datetime.now(timezone.utc) - start_time
            processing_time = elapsed.total_seconds()
            await self._record_performance_feedback(
                message, result, processing_time
            )

            result['processing_time'] = processing_time
            result['success'] = True

            # Include guard result if available
            if guard_result:
                result['guard_result'] = guard_result.to_dict()

            logger.info(
                f"Processed message {message.message_id} in "
                f"{processing_time:.2f}s: {result.get('lane')}"
            )

            return result

        except asyncio.CancelledError:
            logger.info(
                f"Message processing cancelled for {message.message_id}"
            )
            raise
        except asyncio.TimeoutError as e:
            logger.error(
                f"Timeout processing message {message.message_id}: {e}"
            )
            elapsed = datetime.now(timezone.utc) - start_time
            return {
                'success': False,
                'error': f'Timeout: {e}',
                'processing_time': elapsed.total_seconds()
            }
        except (ValueError, KeyError, TypeError) as e:
            logger.error(
                f"Data error processing message {message.message_id}: "
                f"{type(e).__name__}: {e}"
            )
            elapsed = datetime.now(timezone.utc) - start_time
            return {
                'success': False,
                'error': f'{type(e).__name__}: {e}',
                'processing_time': elapsed.total_seconds()
            }
        except (AttributeError, RuntimeError) as e:
            logger.error(
                f"Runtime error processing message {message.message_id}: "
                f"{type(e).__name__}: {e}"
            )
            elapsed = datetime.now(timezone.utc) - start_time
            return {
                'success': False,
                'error': f'{type(e).__name__}: {e}',
                'processing_time': elapsed.total_seconds()
            }

    async def _verify_with_opa_guard(
        self,
        message: AgentMessage
    ) -> Optional[GuardResult]:
        """
        Verify message with OPA Guard before processing.

        Args:
            message: Message to verify

        Returns:
            GuardResult with verification outcome
        """
        if not self.opa_guard:
            return None

        try:
            action = {
                "type": message.message_type.value,
                "content": message.content,
                "impact_score": message.impact_score,
                "constitutional_hash": message.constitutional_hash,
            }

            context = {
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
                "tenant_id": message.tenant_id,
                "priority": (
                    message.priority.value
                    if hasattr(message.priority, 'value')
                    else str(message.priority)
                ),
            }

            guard_result = await self.opa_guard.verify_action(
                agent_id=message.from_agent or message.sender_id,
                action=action,
                context=context,
            )

            # Execute guard callback if provided
            if self.guard_callback:
                await self.guard_callback(message, guard_result)

            return guard_result

        except Exception as e:
            logger.error(f"OPA Guard verification error: {e}")
            # Return permissive result on error to avoid blocking
            return GuardResult(
                decision=GuardDecision.ALLOW,
                is_allowed=True,
                validation_warnings=[f"Guard error: {str(e)}"],
            )

    async def _handle_guard_denial(
        self,
        message: AgentMessage,
        guard_result: GuardResult,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Handle guard denial of action."""
        message.status = MessageStatus.FAILED

        elapsed = datetime.now(timezone.utc) - start_time
        processing_time = elapsed.total_seconds()

        logger.warning(
            f"Message {message.message_id} denied by OPA Guard: "
            f"{guard_result.validation_errors}"
        )

        return {
            'success': False,
            'lane': 'denied',
            'status': 'denied_by_guard',
            'guard_result': guard_result.to_dict(),
            'errors': guard_result.validation_errors,
            'processing_time': processing_time,
        }

    async def _handle_signature_requirement(
        self,
        message: AgentMessage,
        guard_result: GuardResult,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Handle requirement for multi-signature collection."""
        # Create signature request
        decision_id = f"sig_{message.message_id}"

        signature_result = await self.opa_guard.collect_signatures(
            decision_id=decision_id,
            required_signers=guard_result.required_signers,
            threshold=1.0,
            timeout=self.deliberation_timeout,
        )

        elapsed = datetime.now(timezone.utc) - start_time
        processing_time = elapsed.total_seconds()

        if signature_result.is_valid:
            # Signatures collected, proceed with processing
            logger.info(
                f"Signatures collected for message {message.message_id}"
            )
            # Re-process without guard (already verified)
            routing = await self.adaptive_router.route_message(message)
            if routing.get('lane') == 'fast':
                result = await self._process_fast_lane(message, routing)
            else:
                result = await self._process_deliberation(message, routing)
            result['signature_result'] = signature_result.to_dict()
            result['processing_time'] = processing_time
            return result
        else:
            message.status = MessageStatus.FAILED
            logger.warning(
                f"Signature collection failed for message "
                f"{message.message_id}: {signature_result.status.value}"
            )
            return {
                'success': False,
                'lane': 'signature_required',
                'status': 'signature_collection_failed',
                'guard_result': guard_result.to_dict(),
                'signature_result': signature_result.to_dict(),
                'processing_time': processing_time,
            }

    async def _handle_review_requirement(
        self,
        message: AgentMessage,
        guard_result: GuardResult,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Handle requirement for critic agent review."""
        decision = {
            "id": f"review_{message.message_id}",
            "message": message.to_dict(),
            "guard_result": guard_result.to_dict(),
        }

        review_result = await self.opa_guard.submit_for_review(
            decision=decision,
            critic_agents=guard_result.required_reviewers,
            review_types=["safety", "ethics", "compliance"],
            timeout=self.deliberation_timeout,
        )

        elapsed = datetime.now(timezone.utc) - start_time
        processing_time = elapsed.total_seconds()

        if review_result.consensus_verdict == "approve":
            # Review approved, proceed with processing
            logger.info(
                f"Review approved for message {message.message_id}"
            )
            routing = await self.adaptive_router.route_message(message)
            if routing.get('lane') == 'fast':
                result = await self._process_fast_lane(message, routing)
            else:
                result = await self._process_deliberation(message, routing)
            result['review_result'] = review_result.to_dict()
            result['processing_time'] = processing_time
            return result
        else:
            message.status = MessageStatus.FAILED
            logger.warning(
                f"Review rejected for message {message.message_id}: "
                f"{review_result.consensus_verdict}"
            )
            return {
                'success': False,
                'lane': 'review_required',
                'status': f'review_{review_result.consensus_verdict}',
                'guard_result': guard_result.to_dict(),
                'review_result': review_result.to_dict(),
                'processing_time': processing_time,
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
                    'llm_enabled': self.enable_llm,
                    'opa_guard_enabled': self.enable_opa_guard,
                },
                'router_stats': router_stats,
                'queue_stats': queue_stats['stats'],
                'queue_size': queue_stats['queue_size'],
                'processing_count': queue_stats['processing_count']
            }

            # Include OPA Guard stats if enabled
            if self.opa_guard:
                stats['opa_guard_stats'] = self.opa_guard.get_stats()

            if self.redis_queue:
                try:
                    stats['redis_info'] = asyncio.run(
                        self.redis_queue.get_stream_info()
                    )
                except RuntimeError:
                    # Already in async context
                    stats['redis_info'] = None

            return stats

        except (ValueError, KeyError, AttributeError) as e:
            logger.error(
                f"Failed to get layer stats: {type(e).__name__}: {e}"
            )
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

    def set_guard_callback(self, callback: Callable):
        """Set callback for OPA guard verification events."""
        self.guard_callback = callback

    # OPA Guard integration methods

    async def verify_action(
        self,
        agent_id: str,
        action: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[GuardResult]:
        """
        Verify an action using OPA Guard (VERIFY-BEFORE-ACT pattern).

        Args:
            agent_id: ID of the agent performing the action
            action: Action details
            context: Additional context

        Returns:
            GuardResult with verification outcome, or None if guard disabled
        """
        if not self.opa_guard:
            return None

        return await self.opa_guard.verify_action(
            agent_id=agent_id,
            action=action,
            context=context or {},
        )

    async def collect_signatures(
        self,
        decision_id: str,
        required_signers: List[str],
        threshold: float = 1.0,
        timeout: Optional[int] = None
    ) -> Optional[SignatureResult]:
        """
        Collect multi-signatures for a decision.

        Args:
            decision_id: Unique ID for the decision
            required_signers: List of required signer IDs
            threshold: Percentage of signatures required
            timeout: Timeout in seconds

        Returns:
            SignatureResult, or None if guard disabled
        """
        if not self.opa_guard:
            return None

        return await self.opa_guard.collect_signatures(
            decision_id=decision_id,
            required_signers=required_signers,
            threshold=threshold,
            timeout=timeout or self.deliberation_timeout,
        )

    async def submit_signature(
        self,
        decision_id: str,
        signer_id: str,
        reasoning: str = "",
        confidence: float = 1.0
    ) -> bool:
        """
        Submit a signature for a pending decision.

        Args:
            decision_id: Decision ID to sign
            signer_id: ID of the signer
            reasoning: Reason for signing
            confidence: Confidence level

        Returns:
            True if signature was accepted
        """
        if not self.opa_guard:
            return False

        return await self.opa_guard.submit_signature(
            decision_id=decision_id,
            signer_id=signer_id,
            reasoning=reasoning,
            confidence=confidence,
        )

    async def submit_for_review(
        self,
        decision: Dict[str, Any],
        critic_agents: List[str],
        review_types: Optional[List[str]] = None,
        timeout: Optional[int] = None
    ) -> Optional[ReviewResult]:
        """
        Submit a decision for critic agent review.

        Args:
            decision: Decision details to review
            critic_agents: List of critic agent IDs
            review_types: Types of review to request
            timeout: Timeout in seconds

        Returns:
            ReviewResult, or None if guard disabled
        """
        if not self.opa_guard:
            return None

        return await self.opa_guard.submit_for_review(
            decision=decision,
            critic_agents=critic_agents,
            review_types=review_types,
            timeout=timeout or self.deliberation_timeout,
        )

    async def submit_critic_review(
        self,
        decision_id: str,
        critic_id: str,
        verdict: str,
        reasoning: str = "",
        concerns: Optional[List[str]] = None,
        recommendations: Optional[List[str]] = None,
        confidence: float = 1.0
    ) -> bool:
        """
        Submit a critic review for a pending decision.

        Args:
            decision_id: Decision ID being reviewed
            critic_id: ID of the critic agent
            verdict: Review verdict (approve/reject/escalate)
            reasoning: Reason for verdict
            concerns: List of concerns raised
            recommendations: List of recommendations
            confidence: Confidence level

        Returns:
            True if review was accepted
        """
        if not self.opa_guard:
            return False

        return await self.opa_guard.submit_review(
            decision_id=decision_id,
            critic_id=critic_id,
            verdict=verdict,
            reasoning=reasoning,
            concerns=concerns,
            recommendations=recommendations,
            confidence=confidence,
        )

    def register_critic_agent(
        self,
        critic_id: str,
        review_types: List[str],
        callback: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Register a critic agent for reviews.

        Args:
            critic_id: Unique ID for the critic agent
            review_types: Types of reviews this critic can perform
            callback: Async callback function for review requests
            metadata: Additional metadata about the critic
        """
        if self.opa_guard:
            self.opa_guard.register_critic_agent(
                critic_id=critic_id,
                review_types=review_types,
                callback=callback,
                metadata=metadata,
            )

    def unregister_critic_agent(self, critic_id: str):
        """Unregister a critic agent."""
        if self.opa_guard:
            self.opa_guard.unregister_critic_agent(critic_id)

    def get_guard_audit_log(
        self,
        limit: int = 100,
        offset: int = 0,
        agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get OPA guard audit log entries.

        Args:
            limit: Maximum entries to return
            offset: Offset for pagination
            agent_id: Filter by agent ID

        Returns:
            List of audit log entries
        """
        if not self.opa_guard:
            return []

        return self.opa_guard.get_audit_log(
            limit=limit,
            offset=offset,
            agent_id=agent_id,
        )

    async def close(self):
        """Close the deliberation layer and cleanup resources."""
        if self.opa_guard:
            await self.opa_guard.close()

        if self.redis_queue:
            await self.redis_queue.close()

        if self.redis_voting:
            await self.redis_voting.close()

        logger.info("Deliberation layer closed")

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