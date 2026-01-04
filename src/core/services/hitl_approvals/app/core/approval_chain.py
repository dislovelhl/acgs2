"""Constitutional Hash: cdd01ef066bc6cf2
Approval Chain Engine

Manages configurable approval workflows with role-based routing and escalation policies.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import redis.asyncio as redis
from kafka import KafkaProducer

from ..config.settings import settings

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval request status"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class ApprovalPriority(Enum):
    """Approval request priority levels"""

    LOW = "low"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ApprovalStep:
    """Single step in an approval chain"""

    step_id: str
    role: str
    description: str
    timeout_minutes: int
    required_approvals: int = 1
    can_escalate: bool = True
    escalation_role: Optional[str] = None


@dataclass
class ApprovalChain:
    """Complete approval chain definition"""

    chain_id: str
    name: str
    description: str
    priority: ApprovalPriority
    steps: List[ApprovalStep]
    max_escalation_level: int = 3
    emergency_override_role: Optional[str] = None


@dataclass
class ApprovalRequest:
    """Approval request instance"""

    request_id: str
    chain_id: str
    decision_id: str  # Reference to the original AI decision
    tenant_id: str
    requested_by: str
    title: str
    description: str
    priority: ApprovalPriority
    context: Dict[str, Any]  # AI decision context
    status: ApprovalStatus
    current_step_index: int
    approvals: List[Dict[str, Any]]  # Approval history
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    escalation_history: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.escalation_history is None:
            self.escalation_history = []


class ApprovalChainEngine:
    """
    Core engine for managing approval chains and workflows.
    """

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.kafka_producer: Optional[KafkaProducer] = None
        self.chains: Dict[str, ApprovalChain] = {}
        self.active_requests: Dict[str, ApprovalRequest] = {}

    async def initialize(self):
        """Initialize the approval chain engine"""
        try:
            # Initialize Redis connection
            self.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)

            # Initialize Kafka producer
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=3,
            )

            # Load approval chains
            await self._load_approval_chains()

            logger.info("Approval Chain Engine initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Approval Chain Engine: {e}")
            raise

    async def shutdown(self):
        """Shutdown the approval chain engine"""
        if self.kafka_producer:
            self.kafka_producer.close()
        if self.redis:
            await self.redis.close()

    async def _load_approval_chains(self):
        """Load approval chain definitions"""
        # Default approval chains - in production, these would be loaded from config
        self.chains = {
            "standard": ApprovalChain(
                chain_id="standard",
                name="Standard Approval Chain",
                description="Three-level approval for standard AI decisions",
                priority=ApprovalPriority.STANDARD,
                steps=[
                    ApprovalStep(
                        step_id="l1_engineer",
                        role="ai_engineer",
                        description="Initial review by AI Engineer",
                        timeout_minutes=30,
                        escalation_role="ai_engineer_lead",
                    ),
                    ApprovalStep(
                        step_id="l2_manager",
                        role="ai_manager",
                        description="Manager approval for business impact",
                        timeout_minutes=60,
                        escalation_role="ai_director",
                    ),
                    ApprovalStep(
                        step_id="l3_director",
                        role="ai_director",
                        description="Final director approval",
                        timeout_minutes=120,
                        can_escalate=False,  # Final level
                    ),
                ],
                emergency_override_role="ciso",
            ),
            "critical": ApprovalChain(
                chain_id="critical",
                name="Critical Approval Chain",
                description="Accelerated approval for critical AI decisions",
                priority=ApprovalPriority.CRITICAL,
                steps=[
                    ApprovalStep(
                        step_id="security_review",
                        role="security_engineer",
                        description="Immediate security review",
                        timeout_minutes=15,
                        escalation_role="ciso",
                    ),
                    ApprovalStep(
                        step_id="executive_approval",
                        role="ciso",
                        description="Executive security approval",
                        timeout_minutes=30,
                        can_escalate=False,
                    ),
                ],
                emergency_override_role="ceo",
            ),
        }

        logger.info(f"Loaded {len(self.chains)} approval chains")

    async def create_approval_request(
        self,
        decision_id: str,
        tenant_id: str,
        requested_by: str,
        title: str,
        description: str,
        priority: ApprovalPriority,
        context: Dict[str, Any],
        chain_id: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Create a new approval request and start the approval chain.
        """
        # Determine which chain to use
        if not chain_id:
            chain_id = self._determine_chain(priority, context)

        if chain_id not in self.chains:
            raise ValueError(f"Unknown approval chain: {chain_id}")

        self.chains[chain_id]

        # Create approval request
        request = ApprovalRequest(
            request_id=str(uuid4()),
            chain_id=chain_id,
            decision_id=decision_id,
            tenant_id=tenant_id,
            requested_by=requested_by,
            title=title,
            description=description,
            priority=priority,
            context=context,
            status=ApprovalStatus.PENDING,
            current_step_index=0,
            approvals=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Store in Redis
        await self._store_request(request)

        # Start the approval chain
        await self._start_approval_chain(request)

        # Emit event
        await self._emit_event(
            "hitl.approvals.pending",
            {
                "request_id": request.request_id,
                "chain_id": chain_id,
                "priority": priority.value,
                "tenant_id": tenant_id,
            },
        )

        logger.info(f"Created approval request {request.request_id} for chain {chain_id}")
        return request

    def _determine_chain(self, priority: ApprovalPriority, context: Dict[str, Any]) -> str:
        """Determine which approval chain to use based on priority and context"""
        if priority == ApprovalPriority.CRITICAL:
            return "critical"
        elif priority == ApprovalPriority.HIGH:
            # Check if it involves sensitive data or high business impact
            if (
                context.get("data_sensitivity") == "high"
                or context.get("business_impact") == "high"
            ):
                return "critical"
            else:
                return "standard"
        else:
            return settings.approval_chains.default_chain

    async def _store_request(self, request: ApprovalRequest):
        """Store approval request in Redis"""
        key = f"approval:{request.request_id}"
        data = asdict(request)
        # Convert datetime objects to ISO strings
        data["created_at"] = request.created_at.isoformat()
        data["updated_at"] = request.updated_at.isoformat()
        if request.expires_at:
            data["expires_at"] = request.expires_at.isoformat()

        await self.redis.set(key, json.dumps(data))
        await self.redis.expire(key, 30 * 24 * 60 * 60)  # 30 days TTL

    async def _load_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Load approval request from Redis"""
        key = f"approval:{request_id}"
        data = await self.redis.get(key)
        if not data:
            return None

        parsed = json.loads(data)
        # Convert ISO strings back to datetime
        parsed["created_at"] = datetime.fromisoformat(parsed["created_at"])
        parsed["updated_at"] = datetime.fromisoformat(parsed["updated_at"])
        if parsed.get("expires_at"):
            parsed["expires_at"] = datetime.fromisoformat(parsed["expires_at"])

        return ApprovalRequest(**parsed)

    async def _start_approval_chain(self, request: ApprovalRequest):
        """Start the approval chain for a request"""
        chain = self.chains[request.chain_id]
        current_step = chain.steps[request.current_step_index]

        # Set expiration time for current step
        expires_at = datetime.utcnow() + timedelta(minutes=current_step.timeout_minutes)
        request.expires_at = expires_at

        # Store updated request
        await self._store_request(request)

        # Schedule escalation check
        await self._schedule_escalation_check(request.request_id, current_step.timeout_minutes)

        logger.info(
            f"Started approval chain for request {request.request_id}, step {current_step.step_id}"
        )

    async def _schedule_escalation_check(self, request_id: str, timeout_minutes: int):
        """Schedule escalation check using Redis TTL"""
        key = f"escalation:{request_id}"
        await self.redis.setex(key, timeout_minutes * 60, "pending")

        # In a real implementation, you'd have a separate worker process
        # monitoring Redis TTL expirations. For this demo, we'll simulate it.
        asyncio.create_task(self._monitor_escalation(request_id, timeout_minutes))

    async def _monitor_escalation(self, request_id: str, timeout_minutes: int):
        """Monitor for escalation timeout"""
        await asyncio.sleep(timeout_minutes * 60)

        # Check if request still exists and needs escalation
        request = await self._load_request(request_id)
        if request and request.status == ApprovalStatus.PENDING:
            await self._escalate_request(request)

    async def _escalate_request(self, request: ApprovalRequest):
        """Escalate an approval request to the next level"""
        chain = self.chains[request.chain_id]

        # Record escalation in history
        escalation_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "from_step": request.current_step_index,
            "reason": "timeout",
            "escalation_level": len(request.escalation_history) + 1,
        }
        request.escalation_history.append(escalation_record)

        # Move to next step or mark as timed out
        if request.current_step_index < len(chain.steps) - 1:
            request.current_step_index += 1
            request.status = ApprovalStatus.ESCALATED
            request.updated_at = datetime.utcnow()

            await self._store_request(request)
            await self._start_approval_chain(request)

            # Emit escalation event
            await self._emit_event(
                "hitl.approvals.escalated",
                {
                    "request_id": request.request_id,
                    "escalation_level": escalation_record["escalation_level"],
                    "next_step": request.current_step_index,
                },
            )

            logger.info(
                f"Escalated request {request.request_id} to step {request.current_step_index}"
            )
        else:
            # Max escalation level reached
            request.status = ApprovalStatus.TIMED_OUT
            request.updated_at = datetime.utcnow()
            await self._store_request(request)

            logger.warning(f"Request {request.request_id} timed out after max escalation")

    async def approve_request(
        self, request_id: str, approved_by: str, decision: str, rationale: Optional[str] = None
    ) -> bool:
        """
        Approve or reject an approval request.
        Returns True if the request is fully resolved.
        """
        request = await self._load_request(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False

        chain = self.chains[request.chain_id]
        current_step = chain.steps[request.current_step_index]

        # Record the approval/rejection
        approval_record = {
            "step_id": current_step.step_id,
            "approved_by": approved_by,
            "decision": decision,
            "rationale": rationale,
            "timestamp": datetime.utcnow().isoformat(),
        }
        request.approvals.append(approval_record)

        if decision == "approved":
            # Check if we need more approvals for this step
            step_approvals = [
                a
                for a in request.approvals
                if a["step_id"] == current_step.step_id and a["decision"] == "approved"
            ]

            if len(step_approvals) >= current_step.required_approvals:
                # Step complete, move to next step or complete
                if request.current_step_index < len(chain.steps) - 1:
                    request.current_step_index += 1
                    request.updated_at = datetime.utcnow()
                    await self._store_request(request)
                    await self._start_approval_chain(request)
                    return False  # Not fully resolved yet
                else:
                    # All steps complete
                    request.status = ApprovalStatus.APPROVED
                    request.updated_at = datetime.utcnow()
                    await self._store_request(request)

                    # Emit completion event
                    await self._emit_event(
                        "hitl.approvals.completed",
                        {
                            "request_id": request.request_id,
                            "status": "approved",
                            "total_approvals": len(request.approvals),
                        },
                    )

                    logger.info(f"Request {request.request_id} fully approved")
                    return True
            else:
                # Still need more approvals for this step
                request.updated_at = datetime.utcnow()
                await self._store_request(request)
                return False
        else:
            # Request rejected
            request.status = ApprovalStatus.REJECTED
            request.updated_at = datetime.utcnow()
            await self._store_request(request)

            # Emit rejection event
            await self._emit_event(
                "hitl.approvals.completed",
                {
                    "request_id": request.request_id,
                    "status": "rejected",
                    "rejected_by": approved_by,
                    "rationale": rationale,
                },
            )

            logger.info(f"Request {request.request_id} rejected by {approved_by}")
            return True

    async def _emit_event(self, topic: str, message: Dict[str, Any]):
        """Emit event to Kafka"""
        if self.kafka_producer:
            try:
                self.kafka_producer.send(topic, value=message)
                self.kafka_producer.flush()
            except Exception as e:
                logger.error(f"Failed to emit event to {topic}: {e}")

    async def get_request_status(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get the current status of an approval request"""
        return await self._load_request(request_id)

    async def list_pending_requests(self, tenant_id: Optional[str] = None) -> List[ApprovalRequest]:
        """List all pending approval requests"""
        # In a real implementation, you'd scan Redis for pending requests
        # For this demo, we'll return a simplified response
        return []

    async def cancel_request(self, request_id: str, cancelled_by: str) -> bool:
        """Cancel an approval request"""
        request = await self._load_request(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False

        request.status = ApprovalStatus.CANCELLED
        request.updated_at = datetime.utcnow()
        await self._store_request(request)

        logger.info(f"Request {request.request_id} cancelled by {cancelled_by}")
        return True


# Global instance
approval_engine = ApprovalChainEngine()
