"""
HITL Approvals Core Module

This module contains the core approval chain engine with routing logic,
status management, integration with notification providers, OPA policy evaluation,
Redis-backed escalation timer system, SLA tracking, and Kafka event streaming.
"""

from app.core.approval_engine import (
    ApprovalEngine,
    ApprovalEngineError,
    ApprovalNotFoundError,
    ApprovalStateError,
    ChainNotFoundError,
)
from app.core.escalation import (
    EscalationCallback,
    EscalationEngine,
    EscalationPolicyManager,
    EscalationReason,
    EscalationTimer,
    EscalationTimerError,
    EscalationTimerManager,
    RedisConnectionError,
    SLABreach,
    SLAConfig,
    SLAMetrics,
    SLAStatus,
    TimerNotFoundError,
    close_escalation_manager,
    get_escalation_engine,
    get_escalation_manager,
    get_policy_manager,
    initialize_escalation_manager,
    reset_escalation_engine,
    reset_escalation_manager,
    reset_policy_manager,
)
from app.core.kafka_client import (
    HITLEvent,
    HITLEventType,
    HITLKafkaClient,
    HITLTopic,
    KafkaClientError,
    KafkaConnectionError,
    KafkaNotAvailableError,
    KafkaPublishError,
    close_kafka_client,
    get_kafka_client,
    initialize_kafka_client,
    reset_kafka_client,
)
from app.core.opa_client import (
    OPAClient,
    OPAClientError,
    OPAConnectionError,
    OPANotInitializedError,
    PolicyEvaluationError,
    close_opa_client,
    get_opa_client,
    initialize_opa_client,
    reset_opa_client,
)

__all__ = [
    # Approval Engine
    "ApprovalEngine",
    "ApprovalEngineError",
    "ApprovalNotFoundError",
    "ApprovalStateError",
    "ChainNotFoundError",
    # Escalation Exceptions
    "EscalationTimerError",
    "RedisConnectionError",
    "TimerNotFoundError",
    # Escalation Enums
    "EscalationReason",
    "SLAStatus",
    # SLA Data Classes
    "SLAConfig",
    "SLAMetrics",
    "SLABreach",
    # Escalation Timer
    "EscalationTimer",
    "EscalationCallback",
    "EscalationTimerManager",
    "get_escalation_manager",
    "initialize_escalation_manager",
    "close_escalation_manager",
    "reset_escalation_manager",
    # Escalation Policy Manager
    "EscalationPolicyManager",
    "get_policy_manager",
    "reset_policy_manager",
    # Escalation Engine with SLA Tracking
    "EscalationEngine",
    "get_escalation_engine",
    "reset_escalation_engine",
    # OPA Client
    "OPAClient",
    "OPAClientError",
    "OPAConnectionError",
    "OPANotInitializedError",
    "PolicyEvaluationError",
    "get_opa_client",
    "initialize_opa_client",
    "close_opa_client",
    "reset_opa_client",
    # Kafka Client
    "HITLEvent",
    "HITLEventType",
    "HITLKafkaClient",
    "HITLTopic",
    "KafkaClientError",
    "KafkaConnectionError",
    "KafkaNotAvailableError",
    "KafkaPublishError",
    "get_kafka_client",
    "initialize_kafka_client",
    "close_kafka_client",
    "reset_kafka_client",
]
