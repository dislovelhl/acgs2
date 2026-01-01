"""
ACGS-2 Deliberation Layer - Integration
Main integration point for the deliberation layer components.
Constitutional Hash: cdd01ef066bc6cf2

Supports dependency injection for all major components:
- ImpactScorer: Impact score calculation
- AdaptiveRouter: Message routing decisions
- DeliberationQueue: Deliberation processing
- LLMAssistant: AI-powered analysis
- OPAGuard: Policy-based verification
- Redis components: Persistent storage
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

try:
    from ..models import CONSTITUTIONAL_HASH
except (ImportError, ValueError):
    try:
        from enhanced_agent_bus.models import CONSTITUTIONAL_HASH
    except ImportError:
        try:
            from models import CONSTITUTIONAL_HASH
        except ImportError:
            CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

try:
    from ..models import AgentMessage, MessageStatus
except ImportError:
    # Fallback for direct execution or testing
    from models import AgentMessage, MessageStatus  # type: ignore

# Import deliberation layer components with fallback chain
_USING_MOCKS = False

try:
    from .adaptive_router import get_adaptive_router
    from .deliberation_queue import DeliberationStatus, VoteType, get_deliberation_queue
    from .impact_scorer import get_impact_scorer
    from .interfaces import (
        AdaptiveRouterProtocol,
        DeliberationQueueProtocol,
        ImpactScorerProtocol,
        LLMAssistantProtocol,
        OPAGuardProtocol,
        RedisQueueProtocol,
        RedisVotingProtocol,
    )
    from .llm_assistant import get_llm_assistant
    from .opa_guard import GuardDecision, GuardResult, OPAGuard
    from .redis_integration import get_redis_deliberation_queue, get_redis_voting_system
except (ImportError, ValueError):
    try:
        from adaptive_router import get_adaptive_router  # type: ignore
        from deliberation_queue import (  # type: ignore
            DeliberationStatus,
            VoteType,
            get_deliberation_queue,
        )
        from impact_scorer import get_impact_scorer  # type: ignore
        from llm_assistant import get_llm_assistant  # type: ignore
        from opa_guard import GuardDecision, GuardResult, OPAGuard  # type: ignore
        from redis_integration import (  # type: ignore
            get_redis_deliberation_queue,
            get_redis_voting_system,
        )

        from interfaces import (  # type: ignore
            AdaptiveRouterProtocol,
            DeliberationQueueProtocol,
            ImpactScorerProtocol,
            LLMAssistantProtocol,
            OPAGuardProtocol,
            RedisQueueProtocol,
            RedisVotingProtocol,
        )
    except (ImportError, ValueError):
        import os
        import sys

        d = os.path.dirname(os.path.abspath(__file__))
        if d not in sys.path:
            sys.path.append(d)
        from adaptive_router import get_adaptive_router  # type: ignore
        from deliberation_queue import (  # type: ignore
            DeliberationStatus,
            VoteType,
            get_deliberation_queue,
        )
        from impact_scorer import get_impact_scorer  # type: ignore
        from llm_assistant import get_llm_assistant  # type: ignore
        from opa_guard import GuardDecision, GuardResult, OPAGuard  # type: ignore
        from redis_integration import (  # type: ignore
            get_redis_deliberation_queue,
            get_redis_voting_system,
        )

        from interfaces import (  # type: ignore
            AdaptiveRouterProtocol,
            DeliberationQueueProtocol,
            ImpactScorerProtocol,
            LLMAssistantProtocol,
            OPAGuardProtocol,
            RedisQueueProtocol,
            RedisVotingProtocol,
        )
except (ImportError, ValueError):  # noqa: B025 - intentional fallback import pattern
    try:
        # Try absolute imports (direct execution context)
        # Use deliberation_layer prefix for interfaces to avoid conflict with
        # top-level enhanced_agent_bus.interfaces module
        from deliberation_layer.adaptive_router import get_adaptive_router  # type: ignore
        from deliberation_layer.deliberation_queue import (  # type: ignore
            DeliberationStatus,
            VoteType,
            get_deliberation_queue,
        )
        from deliberation_layer.impact_scorer import get_impact_scorer  # type: ignore
        from deliberation_layer.interfaces import (  # type: ignore
            AdaptiveRouterProtocol,
            DeliberationQueueProtocol,
            ImpactScorerProtocol,
            LLMAssistantProtocol,
            OPAGuardProtocol,
            RedisQueueProtocol,
            RedisVotingProtocol,
        )
        from deliberation_layer.llm_assistant import get_llm_assistant  # type: ignore
        from deliberation_layer.opa_guard import (  # type: ignore
            GuardDecision,
            GuardResult,
            OPAGuard,
        )
        from deliberation_layer.redis_integration import (  # type: ignore
            get_redis_deliberation_queue,
            get_redis_voting_system,
        )
    except ImportError as e:
        # FAIL-CLOSED: Critical security dependencies are missing.
        # System MUST NOT proceed in an insecure mocked state (VULN-003).
        logging.getLogger(__name__).critical(
            f"Critical Deliberation Layer dependencies missing: {e}"
        )
        raise RuntimeError(
            "CRITICAL SECURITY FAILURE: Deliberation Layer dependencies are missing. "
            "System is configured to fail-closed to prevent insecure operation "
            "with mock components."
        ) from e


logger = logging.getLogger(__name__)

# Import mixin for OPA Guard methods
try:
    from .opa_guard_mixin import OPAGuardMixin
except ImportError:
    try:
        from opa_guard_mixin import OPAGuardMixin  # type: ignore
    except ImportError:
        # Define empty mixin if import fails
        class OPAGuardMixin:  # type: ignore
            """Fallback empty mixin when opa_guard_mixin unavailable."""

            pass


class DeliberationLayer(OPAGuardMixin):
    """
    Main integration class for the deliberation layer.

    Integrates OPA policy guard for VERIFY-BEFORE-ACT pattern,
    multi-signature collection, and critic agent reviews.
    Constitutional Hash: cdd01ef066bc6cf2

    Supports dependency injection for testing and customization.
    All major components can be injected via constructor parameters.

    OPA Guard methods are provided by OPAGuardMixin.
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
        # Dependency injection parameters
        impact_scorer: Optional["ImpactScorerProtocol"] = None,
        adaptive_router: Optional["AdaptiveRouterProtocol"] = None,
        deliberation_queue: Optional["DeliberationQueueProtocol"] = None,
        llm_assistant: Optional["LLMAssistantProtocol"] = None,
        opa_guard: Optional["OPAGuardProtocol"] = None,
        redis_queue: Optional["RedisQueueProtocol"] = None,
        redis_voting: Optional["RedisVotingProtocol"] = None,
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
            impact_scorer: Optional injected impact scorer
            adaptive_router: Optional injected adaptive router
            deliberation_queue: Optional injected deliberation queue
            llm_assistant: Optional injected LLM assistant
            opa_guard: Optional injected OPA guard
            redis_queue: Optional injected Redis queue
            redis_voting: Optional injected Redis voting system
        """
        self.impact_threshold = impact_threshold
        self.deliberation_timeout = deliberation_timeout
        self.enable_redis = enable_redis
        self.enable_learning = enable_learning
        self.enable_llm = enable_llm
        self.enable_opa_guard = enable_opa_guard
        self.high_risk_threshold = high_risk_threshold
        self.critical_risk_threshold = critical_risk_threshold

        # Dependency injection with defaults for backward compatibility
        # If dependencies are not provided, use default implementations
        self.impact_scorer = impact_scorer or get_impact_scorer()
        self.adaptive_router = adaptive_router or get_adaptive_router()
        # Sync threshold
        if hasattr(self.adaptive_router, "set_impact_threshold"):
            self.adaptive_router.set_impact_threshold(self.impact_threshold)
        self.deliberation_queue = deliberation_queue or get_deliberation_queue()

        # LLM assistant (only if enabled and not injected)
        if llm_assistant is not None:
            self.llm_assistant = llm_assistant
        elif enable_llm:
            self.llm_assistant = get_llm_assistant()
        else:
            self.llm_assistant = None

        # OPA Guard for policy-based verification
        # Use injected instance or create default
        if opa_guard is not None:
            self.opa_guard: Optional[OPAGuard] = opa_guard
        elif enable_opa_guard:
            self.opa_guard = OPAGuard(
                enable_signatures=True,
                enable_critic_review=True,
                signature_timeout=deliberation_timeout,
                review_timeout=deliberation_timeout,
                high_risk_threshold=high_risk_threshold,
                critical_risk_threshold=critical_risk_threshold,
            )
        else:
            self.opa_guard = None

        # Redis components (use injected or create if enabled)
        if redis_queue is not None:
            self.redis_queue = redis_queue
        elif enable_redis:
            self.redis_queue = get_redis_deliberation_queue()
        else:
            self.redis_queue = None

        if redis_voting is not None:
            self.redis_voting = redis_voting
        elif enable_redis:
            self.redis_voting = get_redis_voting_system()
        else:
            self.redis_voting = None

        # Processing callbacks
        self.fast_lane_callback: Optional[Callable] = None
        self.deliberation_callback: Optional[Callable] = None
        self.guard_callback: Optional[Callable] = None

        logger.info(
            "Initialized ACGS-2 Deliberation Layer with OPA Guard: "
            f"{enable_opa_guard}, DI: impact_scorer={impact_scorer is not None}, "
            f"router={adaptive_router is not None}, queue={deliberation_queue is not None}"
        )

    # Property accessors for injected dependencies
    @property
    def injected_impact_scorer(self) -> Optional["ImpactScorerProtocol"]:
        """Get the impact scorer (injected or default)."""
        return self.impact_scorer

    @property
    def injected_router(self) -> Optional["AdaptiveRouterProtocol"]:
        """Get the adaptive router (injected or default)."""
        return self.adaptive_router

    @property
    def injected_queue(self) -> Optional["DeliberationQueueProtocol"]:
        """Get the deliberation queue (injected or default)."""
        return self.deliberation_queue

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
            # 1. Prepare context for multi-dimensional analysis
            context = self._prepare_processing_context(message)

            # 2. Ensure impact score is calculated
            self._ensure_impact_score(message, context)

            # 3. OPA Guard pre-action verification (VERIFY-BEFORE-ACT)
            guard_result = await self._evaluate_opa_guard(message, start_time)
            if guard_result and "success" in guard_result and not guard_result["success"]:
                return guard_result

            # 4. Route and execute (Dual-path Routing)
            result = await self._execute_routing(message, context)

            # 5. Finalize and record metrics
            return await self._finalize_processing(message, result, start_time)

        except asyncio.CancelledError:
            logger.info(f"Message processing cancelled for {message.message_id}")
            raise
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout processing message {message.message_id}: {e}")
            elapsed = datetime.now(timezone.utc) - start_time
            return {
                "success": False,
                "error": f"Timeout: {e}",
                "processing_time": elapsed.total_seconds(),
            }
        except (ValueError, KeyError, TypeError) as e:
            logger.error(
                f"Data error processing message {message.message_id}: " f"{type(e).__name__}: {e}"
            )
            elapsed = datetime.now(timezone.utc) - start_time
            return {
                "success": False,
                "error": f"{type(e).__name__}: {e}",
                "processing_time": elapsed.total_seconds(),
            }
        except (AttributeError, RuntimeError) as e:
            logger.error(
                f"Runtime error processing message {message.message_id}: "
                f"{type(e).__name__}: {e}"
            )
            elapsed = datetime.now(timezone.utc) - start_time
            return {
                "success": False,
                "error": f"{type(e).__name__}: {e}",
                "processing_time": elapsed.total_seconds(),
            }

    def _prepare_processing_context(self, message: AgentMessage) -> Dict[str, Any]:
        """Prepare context for multi-dimensional analysis."""
        return {
            "agent_id": message.from_agent or message.sender_id,
            "tenant_id": message.tenant_id,
            "priority": message.priority,
            "message_type": message.message_type,
            "constitutional_hash": message.constitutional_hash,
        }

    def _ensure_impact_score(self, message: AgentMessage, context: Dict[str, Any]):
        """Ensure impact score is calculated if not present."""
        if message.impact_score is None:
            message.impact_score = self.impact_scorer.calculate_impact_score(
                message.content, context
            )
            logger.debug(
                f"Calculated impact score {message.impact_score:.3f} "
                f"for message {message.message_id}"
            )

    async def _evaluate_opa_guard(
        self, message: AgentMessage, start_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """Evaluate message with OPA Guard and handle early returns."""
        if not self.opa_guard:
            return None

        guard_result = await self._verify_with_opa_guard(message)

        # If guard denies, return immediate rejection dictionary
        if guard_result and not guard_result.is_allowed:
            if guard_result.decision == GuardDecision.DENY:
                return await self._handle_guard_denial(message, guard_result, start_time)
            elif guard_result.decision == GuardDecision.REQUIRE_SIGNATURES:
                return await self._handle_signature_requirement(message, guard_result, start_time)
            elif guard_result.decision == GuardDecision.REQUIRE_REVIEW:
                return await self._handle_review_requirement(message, guard_result, start_time)

        return {"guard_result": guard_result}

    async def _execute_routing(
        self, message: AgentMessage, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine route and execute lane-specific processing."""
        routing_decision = await self.adaptive_router.route_message(message, context)

        if routing_decision.get("lane") == "fast":
            return await self._process_fast_lane(message, routing_decision)
        else:
            return await self._process_deliberation(message, routing_decision)

    async def _finalize_processing(
        self, message: AgentMessage, result: Dict[str, Any], start_time: datetime
    ) -> Dict[str, Any]:
        """Finalize processing, record metrics and return result."""
        elapsed = datetime.now(timezone.utc) - start_time
        processing_time = elapsed.total_seconds()

        await self._record_performance_feedback(message, result, processing_time)

        result["processing_time"] = processing_time
        result["success"] = True

        # Include guard result if available in result or message
        if "guard_result" not in result and hasattr(message, "_guard_result"):
            result["guard_result"] = message._guard_result

        logger.info(
            f"Processed message {message.message_id} in "
            f"{processing_time:.2f}s: {result.get('lane')}"
        )

        return result

    async def _verify_with_opa_guard(self, message: AgentMessage) -> Optional[GuardResult]:
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
                    if hasattr(message.priority, "value")
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
            # FAIL-CLOSED: Deny on error for security-critical operations (VULN-002)
            return GuardResult(
                decision=GuardDecision.DENY,
                is_allowed=False,
                validation_errors=[f"Guard verification failed: {str(e)}"],
                validation_warnings=[],
            )

    async def _handle_guard_denial(
        self, message: AgentMessage, guard_result: GuardResult, start_time: datetime
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
            "success": False,
            "lane": "denied",
            "status": "denied_by_guard",
            "guard_result": guard_result.to_dict(),
            "errors": guard_result.validation_errors,
            "processing_time": processing_time,
        }

    async def _handle_signature_requirement(
        self, message: AgentMessage, guard_result: GuardResult, start_time: datetime
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
            logger.info(f"Signatures collected for message {message.message_id}")
            # Re-process without guard (already verified)
            routing = await self.adaptive_router.route_message(message)
            if routing.get("lane") == "fast":
                result = await self._process_fast_lane(message, routing)
            else:
                result = await self._process_deliberation(message, routing)
            result["signature_result"] = signature_result.to_dict()
            result["processing_time"] = processing_time
            return result
        else:
            message.status = MessageStatus.FAILED
            logger.warning(
                f"Signature collection failed for message "
                f"{message.message_id}: {signature_result.status.value}"
            )
            return {
                "success": False,
                "lane": "signature_required",
                "status": "signature_collection_failed",
                "guard_result": guard_result.to_dict(),
                "signature_result": signature_result.to_dict(),
                "processing_time": processing_time,
            }

    async def _handle_review_requirement(
        self, message: AgentMessage, guard_result: GuardResult, start_time: datetime
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
            logger.info(f"Review approved for message {message.message_id}")
            routing = await self.adaptive_router.route_message(message)
            if routing.get("lane") == "fast":
                result = await self._process_fast_lane(message, routing)
            else:
                result = await self._process_deliberation(message, routing)
            result["review_result"] = review_result.to_dict()
            result["processing_time"] = processing_time
            return result
        else:
            message.status = MessageStatus.FAILED
            logger.warning(
                f"Review rejected for message {message.message_id}: "
                f"{review_result.consensus_verdict}"
            )
            return {
                "success": False,
                "lane": "review_required",
                "status": f"review_{review_result.consensus_verdict}",
                "guard_result": guard_result.to_dict(),
                "review_result": review_result.to_dict(),
                "processing_time": processing_time,
            }

    async def _process_fast_lane(
        self, message: AgentMessage, routing_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process message through fast lane."""
        # Update message status
        message.status = MessageStatus.DELIVERED

        # Execute fast lane callback if provided
        if self.fast_lane_callback:
            await self.fast_lane_callback(message)

        return {
            "lane": "fast",
            "status": "delivered",
            "impact_score": message.impact_score,
            "routing_decision": routing_decision,
        }

    async def _process_deliberation(
        self, message: AgentMessage, routing_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process message through deliberation queue."""
        # Enqueue for deliberation
        item_id = await self.deliberation_queue.enqueue_for_deliberation(
            message=message,
            requires_human_review=True,
            requires_multi_agent_vote=routing_decision.get("impact_score", 0) > 0.9,
            timeout_seconds=self.deliberation_timeout,
        )

        # Store in Redis if enabled
        if self.redis_queue:
            await self.redis_queue.enqueue_deliberation_item(
                message=message, item_id=item_id, metadata=routing_decision
            )

        # Execute deliberation callback if provided
        if self.deliberation_callback:
            await self.deliberation_callback(message, routing_decision)

        return {
            "lane": "deliberation",
            "item_id": item_id,
            "status": "queued",
            "impact_score": message.impact_score,
            "routing_decision": routing_decision,
            "estimated_wait_time": self.deliberation_timeout,
        }

    async def _record_performance_feedback(
        self, message: AgentMessage, result: Dict[str, Any], processing_time: float
    ):
        """Record performance feedback for learning."""
        if not self.enable_learning:
            return

        try:
            # Determine outcome
            if result.get("lane") == "fast":
                outcome = "fast_lane"
                feedback_score = 0.8 if result.get("success") else 0.2
            else:
                # For deliberation, we'll need to track the final outcome
                outcome = "deliberation_queued"
                feedback_score = None  # Will be updated when deliberation completes

            await self.adaptive_router.update_performance_feedback(
                message_id=message.message_id,
                actual_outcome=outcome,
                processing_time=processing_time,
                feedback_score=feedback_score,
            )

        except asyncio.CancelledError:
            raise
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Failed to record performance feedback: {type(e).__name__}: {e}")

    async def submit_human_decision(
        self, item_id: str, reviewer: str, decision: str, reasoning: str
    ) -> bool:
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
            # Handle enum objects by extracting value (avoids cross-module enum identity issues)
            if hasattr(decision, "value"):
                decision_str = decision.value
            else:
                decision_str = str(decision).lower()

            decision_map = {
                "approved": DeliberationStatus.APPROVED,
                "rejected": DeliberationStatus.REJECTED,
                "escalated": DeliberationStatus.UNDER_REVIEW,
                "under_review": DeliberationStatus.UNDER_REVIEW,
            }
            deliberation_decision = decision_map.get(decision_str, DeliberationStatus.REJECTED)

            success = await self.deliberation_queue.submit_human_decision(
                item_id=item_id,
                reviewer=reviewer,
                decision=deliberation_decision,
                reasoning=reasoning,
            )

            if success:
                logger.info(
                    f"Human decision submitted for item {item_id}: {decision} by {reviewer}"
                )

                # Update performance feedback
                await self._update_deliberation_outcome(item_id, decision, reasoning)

            return success

        except asyncio.CancelledError:
            raise
        except (ValueError, KeyError, TypeError) as e:
            logger.error(
                f"Failed to submit human decision for item {item_id}: {type(e).__name__}: {e}"
            )
            return False
        except (AttributeError, RuntimeError) as e:
            logger.error(f"Runtime error submitting human decision for item {item_id}: {e}")
            return False

    async def submit_agent_vote(
        self, item_id: str, agent_id: str, vote: str, reasoning: str, confidence: float = 1.0
    ) -> bool:
        """
        Submit agent vote for deliberation item.

        Returns:
            True if vote submitted successfully
        """
        try:
            # Map vote string to VoteType enum
            vote_map = {
                "approve": VoteType.APPROVE,
                "reject": VoteType.REJECT,
                "abstain": VoteType.ABSTAIN,
            }
            vote_enum = vote_map.get(vote.lower(), VoteType.ABSTAIN)

            success = await self.deliberation_queue.submit_agent_vote(
                item_id=item_id,
                agent_id=agent_id,
                vote=vote_enum,
                reasoning=reasoning,
                confidence=confidence,
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
                        confidence=confidence,
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

    async def _update_deliberation_outcome(self, item_id: str, decision: str, reasoning: str):
        """Update performance feedback for completed deliberation."""
        if not self.enable_learning:
            return

        try:
            # Find the message ID from the deliberation item
            item_details = self.deliberation_queue.get_item_details(item_id)
            if not item_details:
                return

            message_id = item_details.get("message_id")
            if not message_id:
                return

            # Map decision to outcome
            outcome_map = {"approved": "approved", "rejected": "rejected", "escalated": "escalated"}

            outcome = outcome_map.get(decision, "rejected")

            # Calculate feedback score based on decision confidence
            feedback_score = (
                0.9 if decision == "approved" else 0.7 if decision == "escalated" else 0.5
            )

            await self.adaptive_router.update_performance_feedback(
                message_id=message_id,
                actual_outcome=outcome,
                processing_time=0,  # Will be calculated from history
                feedback_score=feedback_score,
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
                "layer_status": "operational",
                "impact_threshold": self.impact_threshold,
                "deliberation_timeout": self.deliberation_timeout,
                "features": {
                    "redis_enabled": self.enable_redis,
                    "learning_enabled": self.enable_learning,
                    "llm_enabled": self.enable_llm,
                    "opa_guard_enabled": self.enable_opa_guard,
                },
                "router_stats": router_stats,
                "queue_stats": queue_stats["stats"],
                "queue_size": queue_stats["queue_size"],
                "processing_count": queue_stats["processing_count"],
            }

            # Include OPA Guard stats if enabled
            if self.opa_guard:
                stats["opa_guard_stats"] = self.opa_guard.get_stats()

            if self.redis_queue:
                try:
                    stats["redis_info"] = asyncio.run(self.redis_queue.get_stream_info())
                except RuntimeError:
                    # Already in async context
                    stats["redis_info"] = None

            return stats

        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Failed to get layer stats: {type(e).__name__}: {e}")
            return {"error": f"{type(e).__name__}: {e}"}
        except RuntimeError as e:
            logger.error(f"Runtime error getting layer stats: {e}")
            return {"error": f"RuntimeError: {e}"}

    def set_fast_lane_callback(self, callback: Callable):
        """Set callback for fast lane processing."""
        self.fast_lane_callback = callback

    def set_deliberation_callback(self, callback: Callable):
        """Set callback for deliberation processing."""
        self.deliberation_callback = callback

    def set_guard_callback(self, callback: Callable):
        """Set callback for OPA guard verification events."""
        self.guard_callback = callback

    # OPA Guard methods are provided by OPAGuardMixin:
    # - verify_action(), collect_signatures(), submit_signature()
    # - submit_for_review(), submit_critic_review()
    # - register_critic_agent(), unregister_critic_agent()
    # - get_guard_audit_log()

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
            return {"error": "LLM assistant not enabled"}

        try:
            # Get deliberation history (simplified)
            history = []  # Would need to implement history collection

            analysis = await self.llm_assistant.analyze_deliberation_trends(history)
            return analysis

        except asyncio.CancelledError:
            raise
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Failed to analyze trends: {type(e).__name__}: {e}")
            return {"error": f"{type(e).__name__}: {e}"}
        except RuntimeError as e:
            logger.error(f"Runtime error analyzing trends: {e}")
            return {"error": f"RuntimeError: {e}"}

    async def force_deliberation(
        self, message: AgentMessage, reason: str = "manual_override"
    ) -> Dict[str, Any]:
        """Force a message into deliberation regardless of impact score."""
        logger.info(f"Forcing message {message.message_id} into deliberation: {reason}")

        # Temporarily override impact score
        original_score = message.impact_score
        message.impact_score = 1.0

        result = await self.adaptive_router.force_deliberation(message, reason)

        # Restore original score
        message.impact_score = original_score

        return result

    async def resolve_deliberation_item(
        self, item_id: str, approved: bool, feedback_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Resolve a pending deliberation item and update learning model.

        Args:
            item_id: ID of the deliberation item/task
            approved: Whether the action was approved
            feedback_score: Optional feedback score (0.0-1.0)

        Returns:
            Resolution result
        """
        if not self.deliberation_queue:
            return {"status": "error", "message": "No deliberation queue configured"}

        # 1. Resolve in queue
        await self.deliberation_queue.resolve_task(item_id, approved)

        # 2. Get task details for feedback
        # Note: DeliberationQueue.get_task must be available
        if hasattr(self.deliberation_queue, "get_task"):
            task = self.deliberation_queue.get_task(item_id)
        else:
            task = None

        if not task:
            logger.warning(f"Resolved task {item_id} not found for feedback provided")
            return {"status": "resolved_no_feedback"}

        # 3. Calculate processing time
        now = datetime.now(timezone.utc)
        processing_time = (now - task.created_at).total_seconds()

        # 4. Update adaptive router
        if self.adaptive_router:
            actual_outcome = "approved" if approved else "rejected"
            await self.adaptive_router.update_performance_feedback(
                message_id=task.message.message_id,
                actual_outcome=actual_outcome,
                processing_time=processing_time,
                feedback_score=feedback_score,
            )

        return {
            "status": "resolved",
            "outcome": "approved" if approved else "rejected",
            "processing_time": processing_time,
        }


# Global deliberation layer instance
_deliberation_layer = None


def get_deliberation_layer() -> DeliberationLayer:
    """Get or create global deliberation layer instance."""
    global _deliberation_layer
    if _deliberation_layer is None:
        _deliberation_layer = DeliberationLayer()
    return _deliberation_layer


def reset_deliberation_layer() -> None:
    """Reset the global deliberation layer instance.

    Used primarily for test isolation to prevent state leakage between tests.
    Constitutional Hash: cdd01ef066bc6cf2
    """
    global _deliberation_layer
    _deliberation_layer = None


DeliberationEngine = DeliberationLayer
