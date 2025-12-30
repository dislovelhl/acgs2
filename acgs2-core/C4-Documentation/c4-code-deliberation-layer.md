# C4 Code Level: Deliberation Layer

## Overview

- **Name**: ACGS-2 Deliberation Layer
- **Description**: AI-powered review system for high-impact decisions using DistilBERT-based impact scoring, multi-agent consensus, human-in-the-loop workflows, and OPA policy enforcement
- **Location**: `/home/dislove/document/acgs2/acgs2-core/enhanced_agent_bus/deliberation_layer/`
- **Language**: Python 3.11+ (async/await)
- **Purpose**: Implements VERIFY-BEFORE-ACT pattern with dual-path routing (fast lane for low-impact, deliberation path for high-impact decisions)
- **Constitutional Hash**: `cdd01ef066bc6cf2` (enforced at all boundaries)
- **Architecture Pattern**: Microservice component with dependency injection, message-driven async processing

## Code Elements

### Classes

#### `ImpactScorer` (impact_scorer.py)
- **Location**: `impact_scorer.py:83-499`
- **Description**: Multi-dimensional impact scoring using DistilBERT/ONNX embeddings, semantic analysis, permission assessment, volume tracking, behavioral drift detection, and priority/type factors
- **Key Methods**:
  - `__init__(model_name: str = 'distilbert-base-uncased', onnx_path: Optional[str] = None, config: Optional[ScoringConfig] = None) -> None` - Initialize with transformer model and configuration
  - `calculate_impact_score(message_content: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> float` - Calculate multi-dimensional impact score (0.0-1.0)
  - `_get_embeddings(text: str) -> np.ndarray` - Retrieve DistilBERT/ONNX embeddings with profiling
  - `_infer_onnx(text: str) -> np.ndarray` - ONNX Runtime inference path
  - `_infer_distilbert(text: str) -> np.ndarray` - PyTorch DistilBERT inference with GPU acceleration tracking
  - `_calculate_permission_score(message_content: Dict[str, Any]) -> float` - Score based on requested tool permissions (admin, delete, transfer, execute, blockchain, payment)
  - `_calculate_volume_score(agent_id: str) -> float` - Score based on request rate (threshold: 10=0.1, 50=0.4, 100=0.7, 100+=1.0)
  - `_calculate_context_score(message_content: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float` - Score based on time, transaction amounts, and anomalies
  - `_calculate_drift_score(agent_id: str, combined_baseline: float) -> float` - Detect behavioral drift from historical baseline (threshold: 0.3)
  - `_calculate_priority_factor(message_content: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> float` - Map Priority enum to factor (LOW=0.1, MEDIUM=0.3, HIGH=0.7, CRITICAL=1.0)
  - `_calculate_type_factor(message_content: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> float` - Score message type (GOVERNANCE_REQUEST, CONSTITUTIONAL_VALIDATION, TASK_REQUEST = 0.8, others = 0.2)
  - `validate_with_baseline(message_content: Dict[str, Any], baseline_scorer: 'ImpactScorer') -> bool` - Validate score consistency with baseline scorer
  - `_extract_text_content(message_content: Dict[str, Any]) -> str` - Recursively extract text from content, payload, description, etc.
  - `_get_keyword_embeddings() -> np.ndarray` - Get cached embeddings for high-impact keywords
- **Configuration Attributes**:
  - `semantic_weight: float = 0.30` - Weight for BERT semantic similarity
  - `permission_weight: float = 0.20` - Weight for tool permission risk
  - `volume_weight: float = 0.10` - Weight for request rate
  - `context_weight: float = 0.10` - Weight for historical context
  - `drift_weight: float = 0.15` - Weight for behavioral drift detection
  - `priority_weight: float = 0.10` - Weight for message priority
  - `type_weight: float = 0.05` - Weight for message type
  - `critical_priority_boost: float = 0.9` - Non-linear boost for critical priority
  - `high_semantic_boost: float = 0.8` - Non-linear boost for high semantic relevance
- **Dependencies**: transformers (AutoTokenizer, AutoModel), torch, scikit-learn (cosine_similarity), numpy, onnxruntime (optional), mlflow (optional), profiling module (optional)
- **GPU Acceleration**: Supports DistilBERT and ONNX inference profiling via optional ModelProfiler

#### `ScoringConfig` (impact_scorer.py)
- **Location**: `impact_scorer.py:67-81`
- **Description**: Dataclass for configurable impact scoring weights
- **Attributes**: All weights and boost thresholds (see above)

#### `AdaptiveRouter` (adaptive_router.py)
- **Location**: `adaptive_router.py:35-331`
- **Description**: Routes messages to fast lane or deliberation path based on impact score with adaptive threshold learning
- **Key Methods**:
  - `__init__(impact_threshold: float = 0.8, deliberation_timeout: int = 300, enable_learning: bool = True) -> None` - Initialize with routing threshold and learning capability
  - `async route_message(message: AgentMessage, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]` - Main routing decision (returns lane='fast' or 'deliberation')
  - `async _route_to_fast_lane(message: AgentMessage, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]` - Route to high-performance fast path
  - `async _route_to_deliberation(message: AgentMessage, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]` - Route to deliberation queue with OPA enforcement
  - `_record_routing_history(message: AgentMessage, routing_decision: Dict[str, Any]) -> None` - Record decision for learning
  - `async update_performance_feedback(message_id: str, actual_outcome: str, processing_time: float, feedback_score: Optional[float] = None) -> None` - Update router with performance data
  - `async _adjust_threshold() -> None` - Adaptively adjust impact threshold based on false positive/negative rates
  - `get_routing_stats() -> Dict[str, Any]` - Get routing performance metrics
  - `set_impact_threshold(threshold: float) -> None` - Manually set routing threshold
  - `async force_deliberation(message: AgentMessage, reason: str = "manual_override") -> Dict[str, Any]` - Override routing to force deliberation
- **Attributes**:
  - `impact_threshold: float = 0.8` - Score threshold for deliberation routing
  - `deliberation_timeout: int = 300` - Timeout for deliberation in seconds
  - `enable_learning: bool = True` - Enable adaptive threshold learning
  - `routing_history: list` - Recent routing decisions (max 1000 entries)
  - `performance_metrics: Dict` - Tracks fast_lane_count, deliberation_count, approval/rejection rates
- **Dependencies**: asyncio, models.AgentMessage, impact_scorer, deliberation_queue

#### `HITLManager` (hitl_manager.py)
- **Location**: `hitl_manager.py:81-172`
- **Description**: Manages human-in-the-loop approval workflows with Slack/Teams integration and audit ledger recording
- **Key Methods**:
  - `__init__(deliberation_queue: DeliberationQueue, audit_ledger: Optional[AuditLedger] = None) -> None` - Initialize with queue and audit ledger
  - `async request_approval(item_id: str, channel: str = "slack") -> None` - Send approval request to stakeholders via Slack/Teams
  - `async process_approval(item_id: str, reviewer_id: str, decision: str, reasoning: str) -> bool` - Process human decision and record to audit ledger
- **Attributes**:
  - `queue: DeliberationQueue` - Reference to deliberation queue
  - `audit_ledger: AuditLedger` - Blockchain-anchored audit trail
- **Returns**: Serialized approval payload with request metadata, impact score, action type, content preview
- **Dependencies**: deliberation_queue, validators.ValidationResult, audit_ledger, models.CONSTITUTIONAL_HASH

#### `OPAGuard` (opa_guard.py)
- **Location**: `opa_guard.py:68-746`
- **Description**: Policy-based verification engine implementing VERIFY-BEFORE-ACT pattern with multi-signature collection and critic agent reviews
- **Key Methods**:
  - `__init__(opa_client: Optional[OPAClient] = None, fail_closed: bool = True, enable_signatures: bool = True, enable_critic_review: bool = True, signature_timeout: int = 300, review_timeout: int = 300, high_risk_threshold: float = 0.8, critical_risk_threshold: float = 0.95) -> None` - Initialize OPA guard with policy evaluation and signatures
  - `async initialize() -> None` - Initialize async components (OPA client)
  - `async close() -> None` - Cleanup resources
  - `async verify_action(agent_id: str, action: Dict[str, Any], context: Dict[str, Any]) -> GuardResult` - Pre-action validation with constitutional compliance check, OPA policy evaluation, risk assessment, and signature/review requirements
  - `_calculate_risk_score(action: Dict[str, Any], context: Dict[str, Any], policy_result: Dict[str, Any]) -> float` - Calculate composite risk score (0.0-1.0) from action type, impact, scope, and policy result
  - `_determine_risk_level(risk_score: float) -> str` - Map risk score to level (critical/high/medium/low)
  - `_identify_risk_factors(action: Dict[str, Any], context: Dict[str, Any]) -> List[str]` - Identify specific risk factors (destructive actions, user data impact, irreversibility, scope, environment)
  - `async collect_signatures(decision_id: str, required_signers: List[str], threshold: float = 1.0, timeout: Optional[int] = None) -> SignatureResult` - Collect multi-signatures with timeout monitoring
  - `async submit_signature(decision_id: str, signer_id: str, reasoning: str = "", confidence: float = 1.0) -> bool` - Submit individual signature
  - `async reject_signature(decision_id: str, signer_id: str, reason: str = "") -> bool` - Reject signing a decision
  - `async submit_for_review(decision: Dict[str, Any], critic_agents: List[str], review_types: Optional[List[str]] = None, timeout: Optional[int] = None) -> ReviewResult` - Submit decision for critic agent review
  - `async submit_review(decision_id: str, critic_id: str, verdict: str, reasoning: str = "", concerns: Optional[List[str]] = None, recommendations: Optional[List[str]] = None, confidence: float = 1.0) -> bool` - Submit critic review
  - `register_critic_agent(critic_id: str, review_types: List[str], callback: Optional[Any] = None, metadata: Optional[Dict[str, Any]] = None) -> None` - Register critic agent for reviews
  - `unregister_critic_agent(critic_id: str) -> None` - Unregister critic agent
  - `async check_constitutional_compliance(action: Dict[str, Any]) -> bool` - Check constitutional hash compliance and evaluate constitutional policy
  - `async log_decision(decision: Dict[str, Any], result: Dict[str, Any]) -> None` - Log decision to audit log (max 10,000 recent entries)
  - `get_stats() -> Dict[str, Any]` - Get guard statistics (verifications, decisions, signatures, reviews)
  - `get_audit_log(limit: int = 100, offset: int = 0, agent_id: Optional[str] = None) -> List[Dict[str, Any]]` - Retrieve paginated audit log
- **Attributes**:
  - `opa_client: Optional[OPAClient]` - OPA policy evaluator
  - `fail_closed: bool = True` - Deny on evaluation error (security default)
  - `enable_signatures: bool = True` - Enable multi-signature collection
  - `enable_critic_review: bool = True` - Enable critic agent reviews
  - `signature_timeout: int = 300` - Signature collection timeout
  - `review_timeout: int = 300` - Critic review timeout
  - `high_risk_threshold: float = 0.8` - Require signatures if risk >= 0.8
  - `critical_risk_threshold: float = 0.95` - Require both signatures and reviews if risk >= 0.95
  - `_pending_signatures: Dict[str, SignatureResult]` - Active signature collections
  - `_pending_reviews: Dict[str, ReviewResult]` - Active reviews
  - `_audit_log: List[Dict[str, Any]]` - Immutable decision log
  - `_stats: Dict` - Counters for verifications, decisions, signatures, reviews
  - `_critic_agents: Dict[str, Dict[str, Any]]` - Registered critic agents with review types and callbacks
  - `_default_signers: Dict[str, List[str]]` - Default signers by risk level
- **Enums**: GuardDecision (ALLOW/REQUIRE_SIGNATURES/REQUIRE_REVIEW/DENY), SignatureStatus (PENDING/COMPLETE/REJECTED/EXPIRED), ReviewStatus (PENDING/COMPLETE/ESCALATED)
- **Dependencies**: asyncio, opa_client, validators.ValidationResult, models.CONSTITUTIONAL_HASH, opa_guard_models

#### `DeliberationQueue` (deliberation_queue.py)
- **Location**: `deliberation_queue.py:77-342`
- **Description**: Persistent queue for high-impact messages awaiting approval with task monitoring, consensus checking, and persistent storage
- **Key Methods**:
  - `__init__(persistence_path: Optional[str] = None, consensus_threshold: float = 0.66, default_timeout: int = 300) -> None` - Initialize queue with persistence and consensus settings
  - `async enqueue_for_deliberation(message: AgentMessage, requires_human_review: bool = False, requires_multi_agent_vote: bool = False, timeout_seconds: Optional[int] = None) -> str` - Enqueue message and return task_id
  - `async enqueue(...)` - Alias for enqueue_for_deliberation
  - `async _monitor_task(task_id: str) -> None` - Background task monitoring for timeout
  - `async stop() -> None` - Cancel all background monitoring tasks
  - `async update_status(task_id: str, status: Any) -> None` - Update deliberation task status
  - `get_pending_tasks() -> List[DeliberationItem]` - Get tasks awaiting deliberation
  - `get_task(task_id: str) -> Optional[DeliberationItem]` - Retrieve task by ID
  - `get_item_details(item_id: str) -> Optional[Dict[str, Any]]` - Get task details for testing
  - `get_queue_status() -> Dict[str, Any]` - Get overall queue status
  - `async submit_agent_vote(item_id: str, agent_id: str, vote: VoteType, reasoning: str, confidence: float = 1.0) -> bool` - Submit agent vote and check for consensus
  - `_check_consensus(task: DeliberationTask) -> bool` - Check if consensus threshold reached (vote count >= required_votes && approval_ratio >= consensus_threshold)
  - `async submit_human_decision(item_id: str, reviewer: str, decision: DeliberationStatus, reasoning: str) -> bool` - Submit human decision (only if UNDER_REVIEW)
  - `_save_tasks() -> None` - Persist tasks to JSON file
  - `_load_tasks() -> None` - Load tasks from JSON file on initialization
  - `async resolve_task(task_id: str, approved: bool) -> None` - Finalize task and set message status
- **Attributes**:
  - `queue: Dict[str, DeliberationTask]` - Task storage (alias: tasks)
  - `processing_tasks: List[asyncio.Task]` - Background monitoring tasks
  - `persistence_path: Optional[str]` - JSON persistence file path
  - `consensus_threshold: float = 0.66` - Consensus approval ratio
  - `default_timeout: int = 300` - Default task timeout
  - `stats: Dict` - Tracks total_queued, approved, rejected, timed_out, consensus_reached
  - `_lock: asyncio.Lock()` - Async lock for queue operations
- **Enums**: DeliberationStatus (PENDING/UNDER_REVIEW/APPROVED/REJECTED/TIMED_OUT/CONSENSUS_REACHED), VoteType (APPROVE/REJECT/ABSTAIN)
- **Data Classes**: DeliberationTask, AgentVote, DeliberationItem (alias)
- **Dependencies**: asyncio, models.AgentMessage, uuid, json, datetime

#### `VotingService` (voting_service.py)
- **Location**: `voting_service.py:45-149`
- **Description**: Multi-agent consensus voting system with strategy-based resolution
- **Key Methods**:
  - `__init__(default_strategy: VotingStrategy = VotingStrategy.QUORUM) -> None` - Initialize with voting strategy
  - `async create_election(message: AgentMessage, participants: List[str], timeout: int = 30) -> str` - Create voting election and return election_id
  - `async cast_vote(election_id: str, vote: Vote) -> bool` - Cast vote and check for early resolution
  - `async _check_resolution(election: Election) -> None` - Check if election meets resolution criteria for strategy
  - `async get_result(election_id: str) -> Optional[str]` - Get election result (APPROVE/DENY/None), handle timeout expiry
- **Attributes**:
  - `default_strategy: VotingStrategy = QUORUM` - Default voting strategy
  - `elections: Dict[str, Election]` - Active elections
  - `_lock: asyncio.Lock()` - Async lock for vote operations
- **Enums**: VotingStrategy (QUORUM=50%+1, UNANIMOUS=100%, SUPER_MAJORITY=2/3)
- **Data Classes**: Vote (agent_id, decision, reason, timestamp), Election (election_id, message_id, strategy, participants, votes dict, status, expires_at)
- **Resolution Logic**:
  - QUORUM: Approvals > 50% → APPROVE; Denials >= 50% → DENY
  - UNANIMOUS: All approve → APPROVE; Any deny → DENY
  - SUPER_MAJORITY: Approvals >= 2/3 → APPROVE; Denials > 1/3 → DENY
- **Dependencies**: asyncio, uuid, datetime, models.AgentMessage

#### `MultiApproverWorkflowEngine` (multi_approver.py)
- **Location**: `multi_approver.py:488-884`
- **Description**: Enterprise-grade multi-approver workflow with role-based policies, escalation, and notification channels
- **Key Methods**:
  - `__init__(notification_channels: Optional[List[NotificationChannel]] = None, audit_callback: Optional[Callable[[ApprovalRequest, ApprovalDecision], None]] = None) -> None` - Initialize with notification and audit support
  - `async start() -> None` - Start escalation background task
  - `async stop() -> None` - Stop background tasks
  - `register_approver(approver: Approver) -> None` - Register an approver
  - `register_policy(policy_id: str, policy: ApprovalPolicy) -> None` - Register approval policy
  - `async create_request(request_type: str, requester_id: str, requester_name: str, tenant_id: str, title: str, description: str, risk_score: float, payload: Dict[str, Any], policy_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> ApprovalRequest` - Create approval request with auto-approval for low-risk items
  - `async submit_decision(request_id: str, approver_id: str, decision: ApprovalStatus, reasoning: str, metadata: Optional[Dict[str, Any]] = None) -> tuple[bool, str]` - Submit approver decision and check if requirements met
  - `async cancel_request(request_id: str, reason: str) -> bool` - Cancel pending request
  - `get_request(request_id: str) -> Optional[ApprovalRequest]` - Retrieve request by ID
  - `get_pending_requests(tenant_id: Optional[str] = None, approver_id: Optional[str] = None) -> List[ApprovalRequest]` - Get filtered pending requests
  - `get_stats() -> Dict[str, Any]` - Get workflow statistics
  - `_select_policy_for_risk(risk_score: float) -> str` - Select policy based on risk (0.9+=critical, 0.7+=high, 0.5+=policy_change, else=standard)
  - `_get_eligible_approvers(policy: ApprovalPolicy, tenant_id: str) -> List[Approver]` - Get approvers eligible for policy
  - `async _escalation_loop() -> None` - Background task for timeout and escalation monitoring
- **Attributes**:
  - `notification_channels: List[NotificationChannel]` - Slack, Teams, Email handlers
  - `audit_callback: Optional[Callable]` - Audit logging callback
  - `_requests: Dict[str, ApprovalRequest]` - Active requests
  - `_approvers: Dict[str, Approver]` - Registered approvers
  - `_policies: Dict[str, ApprovalPolicy]` - Approval policies
  - `_escalation_task: Optional[asyncio.Task]` - Background escalation monitor
  - `_running: bool` - Engine running state
- **Enums**: ApprovalStatus (PENDING/APPROVED/REJECTED/ESCALATED/TIMEOUT/CANCELLED), ApproverRole (SECURITY_TEAM/COMPLIANCE_TEAM/PLATFORM_ADMIN/TENANT_ADMIN/POLICY_OWNER/ENGINEERING_LEAD/ON_CALL), EscalationLevel (LEVEL_1/LEVEL_2/LEVEL_3/EXECUTIVE)
- **Data Classes**: Approver, ApprovalDecision, ApprovalPolicy, ApprovalRequest
- **Default Policies**:
  - high_risk_action: min_approvers=2, roles=[SECURITY, COMPLIANCE], require_all_roles=true, timeout=24h
  - policy_change: min_approvers=2, roles=[POLICY_OWNER, PLATFORM_ADMIN], timeout=48h
  - critical_deployment: min_approvers=3, roles=[ENGINEERING_LEAD, SECURITY, ON_CALL], timeout=4h
  - standard_request: min_approvers=1, role=[TENANT_ADMIN], timeout=72h
- **Dependencies**: asyncio, uuid, hashlib, json, datetime, dataclasses, enum, logging

#### `SlackNotificationChannel` (multi_approver.py)
- **Location**: `multi_approver.py:258-402`
- **Description**: Slack notification implementation with interactive approval buttons
- **Key Methods**:
  - `async send_approval_request(request: ApprovalRequest, approvers: List[Approver]) -> bool` - Send Slack blocks with request details and approve/reject buttons
  - `async send_decision_notification(request: ApprovalRequest, decision: ApprovalDecision) -> bool` - Notify channel of decision
  - `async send_escalation_notification(request: ApprovalRequest, escalation_level: EscalationLevel) -> bool` - Send escalation alert
  - `_get_risk_emoji(score: float) -> str` - Map risk score to emoji (0.9+=red, 0.7+=orange, 0.5+=yellow, else=green)

#### `TeamsNotificationChannel` (multi_approver.py)
- **Location**: `multi_approver.py:404-486`
- **Description**: Microsoft Teams notification with adaptive cards and response forms

#### `DeliberationLayer` (integration.py)
- **Location**: `integration.py:97-982`
- **Description**: Main integration class combining all deliberation components with dependency injection support
- **Key Methods**:
  - `__init__(impact_threshold: float = 0.8, deliberation_timeout: int = 300, enable_redis: bool = False, enable_learning: bool = True, enable_llm: bool = True, enable_opa_guard: bool = True, high_risk_threshold: float = 0.8, critical_risk_threshold: float = 0.95, impact_scorer: Optional = None, adaptive_router: Optional = None, deliberation_queue: Optional = None, llm_assistant: Optional = None, opa_guard: Optional = None, redis_queue: Optional = None, redis_voting: Optional = None) -> None` - Initialize with full dependency injection support
  - `async initialize() -> None` - Initialize async components (Redis, OPA Guard)
  - `async process_message(message: AgentMessage) -> Dict[str, Any]` - Main message processing (VERIFY-BEFORE-ACT pattern)
    1. Prepare processing context
    2. Calculate impact score
    3. OPA Guard pre-action verification
    4. Execute routing (fast lane or deliberation)
    5. Finalize and record metrics
  - `_prepare_processing_context(message: AgentMessage) -> Dict[str, Any]` - Extract agent_id, tenant_id, priority, message_type, constitutional_hash
  - `_ensure_impact_score(message: AgentMessage, context: Dict[str, Any]) -> None` - Calculate impact score if missing
  - `async _evaluate_opa_guard(message: AgentMessage, start_time: datetime) -> Optional[Dict[str, Any]]` - Verify with OPA and handle early returns (denial, signature requirement, review requirement)
  - `async _execute_routing(message: AgentMessage, context: Dict[str, Any]) -> Dict[str, Any]` - Route based on impact score
  - `async _finalize_processing(message: AgentMessage, result: Dict[str, Any], start_time: datetime) -> Dict[str, Any]` - Record performance feedback and return result
  - `async _verify_with_opa_guard(message: AgentMessage) -> Optional[GuardResult]` - Perform OPA verification with fail-closed error handling
  - `async _handle_guard_denial(message: AgentMessage, guard_result: GuardResult, start_time: datetime) -> Dict[str, Any]` - Return rejection result
  - `async _handle_signature_requirement(...) -> Dict[str, Any]` - Collect signatures and proceed if valid
  - `async _handle_review_requirement(...) -> Dict[str, Any]` - Collect critic reviews and proceed if consensus reached
  - `async _process_fast_lane(message: AgentMessage, routing_decision: Dict[str, Any]) -> Dict[str, Any]` - Mark delivered and execute callback
  - `async _process_deliberation(message: AgentMessage, routing_decision: Dict[str, Any]) -> Dict[str, Any]` - Enqueue for deliberation and Redis persistence
  - `async submit_human_decision(item_id: str, reviewer: str, decision: str, reasoning: str) -> bool` - Submit human decision with learning update
  - `async submit_agent_vote(item_id: str, agent_id: str, vote: str, reasoning: str, confidence: float = 1.0) -> bool` - Submit agent vote with Redis synchronization
  - `async _update_deliberation_outcome(item_id: str, decision: str, reasoning: str) -> None` - Update learning model
  - `get_layer_stats() -> Dict[str, Any]` - Get comprehensive deliberation layer statistics
  - `set_fast_lane_callback(callback: Callable) -> None` - Set fast lane processing callback
  - `set_deliberation_callback(callback: Callable) -> None` - Set deliberation processing callback
  - `set_guard_callback(callback: Callable) -> None` - Set OPA guard verification callback
  - `async close() -> None` - Cleanup resources
  - `async analyze_trends() -> Dict[str, Any]` - Analyze deliberation trends using LLM assistant
  - `async force_deliberation(message: AgentMessage, reason: str = "manual_override") -> Dict[str, Any]` - Force message into deliberation
  - `async resolve_deliberation_item(item_id: str, approved: bool, feedback_score: Optional[float] = None) -> Dict[str, Any]` - Finalize deliberation item and update learning
- **Attributes**:
  - `impact_threshold: float = 0.8` - Routing threshold
  - `deliberation_timeout: int = 300` - Deliberation timeout
  - `enable_redis: bool` - Redis persistence enabled
  - `enable_learning: bool` - Adaptive learning enabled
  - `enable_llm: bool` - LLM assistant enabled
  - `enable_opa_guard: bool` - OPA Guard enabled
  - `high_risk_threshold: float = 0.8` - Risk threshold for signatures
  - `critical_risk_threshold: float = 0.95` - Risk threshold for full review
  - `impact_scorer: ImpactScorerProtocol` - Injected or default impact scorer
  - `adaptive_router: AdaptiveRouterProtocol` - Injected or default router
  - `deliberation_queue: DeliberationQueueProtocol` - Injected or default queue
  - `llm_assistant: Optional[LLMAssistantProtocol]` - Optional LLM assistant
  - `opa_guard: Optional[OPAGuard]` - Optional OPA Guard
  - `redis_queue: Optional[RedisQueueProtocol]` - Optional Redis queue
  - `redis_voting: Optional[RedisVotingProtocol]` - Optional Redis voting
  - `fast_lane_callback: Optional[Callable]` - Fast lane processing hook
  - `deliberation_callback: Optional[Callable]` - Deliberation processing hook
  - `guard_callback: Optional[Callable]` - OPA Guard verification hook
- **Error Handling**: Fail-closed error handling for security-critical operations (VULN-002, VULN-003)
- **Dependencies**: All deliberation layer components, models, validators

### Data Classes

#### `ScoringConfig` (impact_scorer.py)
- **Location**: `impact_scorer.py:67-81`
- **Attributes**: Scoring weights and boost thresholds

#### `DeliberationTask` (deliberation_queue.py)
- **Location**: `deliberation_queue.py:44-73`
- **Attributes**: task_id, message, status, required_votes, consensus_threshold, timeout_seconds, current_votes, metadata, created_at, updated_at, human_reviewer, human_decision, human_reasoning
- **Properties**: voting_deadline, item_id, is_complete

#### `AgentVote` (deliberation_queue.py)
- **Location**: `deliberation_queue.py:35-42`
- **Attributes**: agent_id, vote (VoteType), reasoning, confidence_score, timestamp

#### `Approver` (multi_approver.py)
- **Location**: `multi_approver.py:68-81`
- **Attributes**: id, name, email, roles (List[ApproverRole]), slack_id, teams_id, timezone, is_active
- **Methods**: has_role(role: ApproverRole) -> bool

#### `ApprovalDecision` (multi_approver.py)
- **Location**: `multi_approver.py:84-101`
- **Attributes**: approver_id, approver_name, decision (ApprovalStatus), reasoning, timestamp, metadata
- **Methods**: to_dict() -> Dict[str, Any]

#### `ApprovalPolicy` (multi_approver.py)
- **Location**: `multi_approver.py:104-165`
- **Attributes**: name, required_roles, min_approvers, require_all_roles, timeout_hours, escalation_hours, allow_self_approval, require_reasoning, auto_approve_low_risk, risk_threshold
- **Methods**: validate_approvers(decisions, approvers, requester_id) -> tuple[bool, str]

#### `ApprovalRequest` (multi_approver.py)
- **Location**: `multi_approver.py:169-227`
- **Attributes**: id, request_type, requester_id, requester_name, tenant_id, title, description, risk_score, policy, payload, status, decisions, escalation_level, created_at, updated_at, deadline, constitutional_hash, metadata
- **Methods**:
  - compute_hash() -> str (SHA256 for audit)
  - to_dict() -> Dict[str, Any]

#### `Vote` (voting_service.py)
- **Location**: `voting_service.py:27-32`
- **Attributes**: agent_id, decision ('APPROVE'/'DENY'/'ABSTAIN'), reason, timestamp

#### `Election` (voting_service.py)
- **Location**: `voting_service.py:34-43`
- **Attributes**: election_id, message_id, strategy (VotingStrategy), participants (Set[str]), votes (Dict[str, Vote]), status ('OPEN'/'CLOSED'/'EXPIRED'), created_at, expires_at

#### `GuardResult` (opa_guard.py)
- **Location**: `opa_guard.py` (imported from opa_guard_models)
- **Attributes**: agent_id, action_type, constitutional_valid, decision (GuardDecision), is_allowed, requires_signatures, requires_review, required_signers, required_reviewers, risk_score, risk_level, risk_factors, policy_path, policy_result, validation_errors, validation_warnings
- **Methods**: to_dict() -> Dict[str, Any]

#### `SignatureResult` (opa_guard.py)
- **Location**: `opa_guard.py` (imported from opa_guard_models)
- **Attributes**: decision_id, required_signers, required_count, signatures (List[Signature]), threshold, status (SignatureStatus), created_at, expires_at
- **Methods**: add_signature(sig: Signature) -> bool, reject(signer_id, reason) -> bool, is_complete -> bool, is_valid -> bool, to_dict() -> Dict[str, Any]

#### `ReviewResult` (opa_guard.py)
- **Location**: `opa_guard.py` (imported from opa_guard_models)
- **Attributes**: decision_id, required_critics, reviews (List[CriticReview]), review_types, status (ReviewStatus), consensus_verdict, created_at, timeout_seconds
- **Methods**: add_review(review: CriticReview) -> bool, consensus_reached -> bool, to_dict() -> Dict[str, Any]

### Functions

#### Module-Level Functions (impact_scorer.py)

```python
def cosine_similarity_fallback(a, b) -> float
```
- **Location**: `impact_scorer.py:56-64`
- **Description**: Fallback cosine similarity using numpy (when scikit-learn unavailable)

```python
def get_impact_scorer(model_name: str = 'distilbert-base-uncased', onnx_path: Optional[str] = None, config: Optional[ScoringConfig] = None) -> ImpactScorer
```
- **Location**: `impact_scorer.py:519-530`
- **Description**: Get or create global impact scorer singleton

```python
def calculate_message_impact(message_content: Dict[str, Any]) -> float
```
- **Location**: `impact_scorer.py:532-543`
- **Description**: Convenience function to calculate impact score

```python
def get_profiling_report() -> str
```
- **Location**: `impact_scorer.py:550-569`
- **Description**: Get GPU acceleration profiling report (requires profiling module)

```python
def get_gpu_decision_matrix() -> Dict[str, Any]
```
- **Location**: `impact_scorer.py:572-588`
- **Description**: Get structured GPU decision data for programmatic use

```python
def reset_profiling() -> None
```
- **Location**: `impact_scorer.py:591-595`
- **Description**: Reset all profiling data

#### Module-Level Functions (adaptive_router.py)

```python
def get_adaptive_router() -> AdaptiveRouter
```
- **Location**: `adaptive_router.py:326-331`
- **Description**: Get or create global adaptive router singleton

#### Module-Level Functions (deliberation_queue.py)

```python
def get_deliberation_queue(persistence_path: Optional[str] = None) -> DeliberationQueue
```
- **Location**: `deliberation_queue.py:337-342`
- **Description**: Get or create global deliberation queue singleton

#### Module-Level Functions (voting_service.py)

None defined (class-based approach)

#### Module-Level Functions (multi_approver.py)

```python
async def initialize_workflow_engine(notification_channels: Optional[List[NotificationChannel]] = None, audit_callback: Optional[Callable[[ApprovalRequest, ApprovalDecision], None]] = None) -> MultiApproverWorkflowEngine
```
- **Location**: `multi_approver.py:895-906`
- **Description**: Initialize global workflow engine singleton with start() called

```python
async def shutdown_workflow_engine() -> None
```
- **Location**: `multi_approver.py:909-914`
- **Description**: Shutdown global workflow engine

```python
def get_workflow_engine() -> Optional[MultiApproverWorkflowEngine]
```
- **Location**: `multi_approver.py:890-892`
- **Description**: Get global workflow engine instance

#### Module-Level Functions (opa_guard.py)

```python
def get_opa_guard() -> OPAGuard
```
- **Location**: `opa_guard.py:753-758`
- **Description**: Get or create global OPA guard singleton

```python
async def initialize_opa_guard(**kwargs) -> OPAGuard
```
- **Location**: `opa_guard.py:761-774`
- **Description**: Initialize global OPA guard with async setup

```python
async def close_opa_guard() -> None
```
- **Location**: `opa_guard.py:777-782`
- **Description**: Close global OPA guard

#### Module-Level Functions (integration.py)

```python
def get_deliberation_layer() -> DeliberationLayer
```
- **Location**: `integration.py:987-992`
- **Description**: Get or create global deliberation layer singleton

#### Module-Level Functions (hitl_manager.py)

None (class-based approach with explicit instantiation)

### Enumerations

#### Priority (models.py, imported)
- Values: LOW, MEDIUM, HIGH, CRITICAL

#### MessageType (models.py, imported)
- Values: COMMAND, QUERY, GOVERNANCE_REQUEST, CONSTITUTIONAL_VALIDATION, TASK_REQUEST, etc.

#### MessageStatus (models.py, imported)
- Values: PENDING, DELIVERED, FAILED, PROCESSING, etc.

#### DeliberationStatus (deliberation_queue.py)
- **Location**: `deliberation_queue.py:22-28`
- **Values**: PENDING, UNDER_REVIEW, APPROVED, REJECTED, TIMED_OUT, CONSENSUS_REACHED

#### VoteType (deliberation_queue.py)
- **Location**: `deliberation_queue.py:30-33`
- **Values**: APPROVE, REJECT, ABSTAIN

#### ApprovalStatus (multi_approver.py)
- **Location**: `multi_approver.py:38-45`
- **Values**: PENDING, APPROVED, REJECTED, ESCALATED, TIMEOUT, CANCELLED

#### ApproverRole (multi_approver.py)
- **Location**: `multi_approver.py:48-56`
- **Values**: SECURITY_TEAM, COMPLIANCE_TEAM, PLATFORM_ADMIN, TENANT_ADMIN, POLICY_OWNER, ENGINEERING_LEAD, ON_CALL

#### EscalationLevel (multi_approver.py)
- **Location**: `multi_approver.py:59-64`
- **Values**: LEVEL_1 (1), LEVEL_2 (2), LEVEL_3 (3), EXECUTIVE (4)

#### VotingStrategy (voting_service.py)
- **Location**: `voting_service.py:22-25`
- **Values**: QUORUM (50%+1), UNANIMOUS (100%), SUPER_MAJORITY (2/3)

#### GuardDecision (opa_guard_models.py)
- **Values**: ALLOW, REQUIRE_SIGNATURES, REQUIRE_REVIEW, DENY

#### SignatureStatus (opa_guard_models.py)
- **Values**: PENDING, COMPLETE, REJECTED, EXPIRED

#### ReviewStatus (opa_guard_models.py)
- **Values**: PENDING, COMPLETE, ESCALATED

## Dependencies

### Internal Dependencies

**Within Deliberation Layer:**
- `impact_scorer.py` → imports ScoringConfig, defines get_impact_scorer(), calculate_message_impact()
- `adaptive_router.py` → imports from impact_scorer, deliberation_queue
- `deliberation_queue.py` → no internal deliberation layer imports (standalone)
- `voting_service.py` → no internal deliberation layer imports (standalone)
- `multi_approver.py` → no internal deliberation layer imports (standalone)
- `opa_guard.py` → imports opa_guard_models, deliberation_queue, adaptive_router
- `hitl_manager.py` → imports deliberation_queue, validators.ValidationResult, audit_ledger
- `integration.py` → imports all deliberation layer components with fallback chain
- `interfaces.py` → Protocol definitions only, no implementation imports
- `opa_guard_models.py` → Data class and enum definitions

**From Enhanced Agent Bus:**
- `models.AgentMessage`, `MessageStatus`, `Priority`, `MessageType`, `CONSTITUTIONAL_HASH`
- `validators.ValidationResult`
- `opa_client.OPAClient`, `get_opa_client()`

**From Shared Services:**
- `shared.constants.CONSTITUTIONAL_HASH` (with fallback to literal string)
- Optional: `audit_service.core.audit_ledger.AuditLedger`

### External Dependencies

**Core ML/AI:**
- `transformers`: AutoTokenizer, AutoModel for DistilBERT embeddings
- `torch`: PyTorch tensor operations and inference
- `sklearn.metrics.pairwise`: cosine_similarity
- `numpy`: Array operations, linear algebra
- `onnxruntime`: ONNX model inference (optional)

**Monitoring/Observability:**
- `mlflow`: Model versioning and tracking (optional)
- Custom profiling module: GPU acceleration tracking (optional)

**Async/Concurrency:**
- `asyncio`: Core async orchestration
- Standard library: logging, json, uuid, datetime, enum, abc, dataclasses, hashlib, os

**Communication (Multi-Approver):**
- `requests` or `aiohttp`: Slack/Teams webhook (simulated, not explicitly imported)

## Relationships & Data Flows

### Message Processing Flow (DeliberationLayer.process_message)

```
AgentMessage
    ↓
_prepare_processing_context() → Extract context (agent_id, tenant_id, priority, type, hash)
    ↓
_ensure_impact_score() → ImpactScorer.calculate_impact_score()
    ↓ Multi-dimensional scoring (semantic, permission, volume, context, drift, priority, type)
    ↓
_evaluate_opa_guard() → OPAGuard.verify_action()
    ↓ Check constitutional hash, evaluate OPA policies, assess risk, determine requirements
    ├─ Decision == DENY → _handle_guard_denial() → Return {success: false, ...}
    ├─ Decision == REQUIRE_SIGNATURES → _handle_signature_requirement() → collect_signatures()
    ├─ Decision == REQUIRE_REVIEW → _handle_review_requirement() → submit_for_review()
    └─ Decision == ALLOW → Continue
    ↓
_execute_routing() → AdaptiveRouter.route_message()
    ├─ impact_score >= impact_threshold (0.8) → _process_deliberation()
    │   ├─ DeliberationQueue.enqueue_for_deliberation()
    │   ├─ RedisQueue.enqueue_deliberation_item() (if enabled)
    │   └─ deliberation_callback() (if set)
    └─ impact_score < impact_threshold → _process_fast_lane()
        ├─ Set message.status = DELIVERED
        └─ fast_lane_callback() (if set)
    ↓
_finalize_processing() → Record feedback, calculate latency
    ↓
AdaptiveRouter.update_performance_feedback() (if learning enabled)
    ↓
Return {success: true, lane: 'fast'|'deliberation', ...}
```

### Impact Scoring Multi-Dimensional Analysis

```
ImpactScorer.calculate_impact_score(message_content, context)
├─ Semantic Score (30% weight)
│  ├─ _get_embeddings() → DistilBERT or ONNX inference
│  └─ cosine_similarity(message_embedding, keyword_embedding)
│     Keywords: "critical", "emergency", "security", "breach", "violation", etc.
├─ Permission Score (20% weight)
│  └─ _calculate_permission_score() → High-risk tools (admin, delete, transfer, execute, blockchain, payment)
├─ Volume Score (10% weight)
│  └─ _calculate_volume_score(agent_id) → Request rate thresholds (<10/min=0.1, 100+/min=1.0)
├─ Context/History Score (10% weight)
│  └─ _calculate_context_score() → Night time anomalies, large transaction amounts
├─ Behavioral Drift Score (15% weight)
│  └─ _calculate_drift_score(agent_id) → Deviation from historical baseline (threshold: 0.3)
├─ Priority Factor (10% weight)
│  └─ _calculate_priority_factor() → LOW=0.1, MEDIUM=0.3, HIGH=0.7, CRITICAL=1.0
└─ Type Factor (5% weight)
   └─ _calculate_type_factor() → GOVERNANCE_REQUEST/CONSTITUTIONAL_VALIDATION/TASK_REQUEST=0.8, else=0.2

Weighted Combination (normalized by total weight)
Non-linear Boosts:
├─ Critical priority → min(combined_score, 0.9)
└─ High semantic (>0.8) → min(combined_score, 0.8)

Final: Clamp to [0.0, 1.0]
```

### OPA Guard Verification (VERIFY-BEFORE-ACT)

```
OPAGuard.verify_action(agent_id, action, context)
├─ check_constitutional_compliance(action)
│  ├─ Verify constitutional_hash matches GUARD_CONSTITUTIONAL_HASH
│  └─ Evaluate policy: data.acgs.constitutional.validate
├─ evaluate_policy(input, policy_path)
│  └─ OPA client evaluation with fail_closed=true error handling
├─ _calculate_risk_score(action, context, policy_result)
│  ├─ Base risk from action type (delete/modify/execute/deploy/shutdown = +0.3)
│  ├─ Impact score contribution (* 0.4)
│  ├─ Scope contribution (global/system/all = +0.2, org/tenant = +0.1)
│  └─ Policy risk contribution (* 0.1)
├─ _determine_risk_level(risk_score)
│  └─ critical (≥0.9) / high (≥0.7) / medium (≥0.4) / low
├─ Decision Routing
│  ├─ risk_score ≥ critical_risk_threshold (0.95) → REQUIRE_REVIEW (both signatures and reviews)
│  ├─ risk_score ≥ high_risk_threshold (0.8) → REQUIRE_SIGNATURES
│  ├─ policy_result.allowed == false → DENY
│  └─ else → ALLOW
└─ Return GuardResult with decision, risk metrics, requirements
```

### Multi-Signature Collection

```
OPAGuard.collect_signatures(decision_id, required_signers, threshold=1.0, timeout=300)
├─ Create SignatureResult with required_signers and expiry
├─ Store in _pending_signatures[decision_id]
└─ Wait loop (check every second)
   ├─ Check timeout → Mark EXPIRED
   ├─ Check completeness (threshold met) → Mark COMPLETE
   ├─ Check rejection → Mark REJECTED
   └─ On timeout/completion/rejection → Return SignatureResult

submit_signature(decision_id, signer_id, reasoning, confidence)
├─ Retrieve pending signature request
└─ Add Signature(signer_id, reasoning, confidence) if not already signed
```

### Critic Agent Review Process

```
OPAGuard.submit_for_review(decision, critic_agents, review_types, timeout)
├─ Create ReviewResult with required_critics and review_types
├─ Store in _pending_reviews[decision_id]
├─ Notify registered critic agents via callbacks
└─ Wait loop
   ├─ Check timeout → Mark ESCALATED (consensus not reached)
   ├─ Check consensus_reached → Mark COMPLETE
   └─ Return ReviewResult with consensus_verdict

submit_review(decision_id, critic_id, verdict, reasoning, concerns, recommendations, confidence)
├─ Retrieve pending review
├─ Add CriticReview(critic_id, verdict, reasoning, concerns, recommendations, confidence)
└─ Check if consensus reached:
   └─ consensus_verdict determined when enough reviewers vote
```

### Deliberation Queue & Voting

```
DeliberationQueue.enqueue_for_deliberation(message, requires_human_review, requires_multi_agent_vote, timeout)
├─ Create DeliberationTask(task_id, message, status=PENDING)
├─ Store in self.tasks[task_id]
├─ Start background _monitor_task(task_id) → Marks TIMED_OUT on timeout
└─ Return task_id for tracking

submit_agent_vote(item_id, agent_id, vote, reasoning, confidence)
├─ Add AgentVote(agent_id, vote, reasoning, confidence) to task.current_votes
├─ Check if consensus reached:
│  └─ _check_consensus(task) → votes count >= required_votes && approval_ratio >= consensus_threshold
└─ If consensus → Update status to APPROVED

submit_human_decision(item_id, reviewer, decision, reasoning)
├─ Only if task.status == UNDER_REVIEW
├─ Update task.status to decision (APPROVED/REJECTED)
├─ Update stats
└─ Persist to storage

VotingService.create_election(message, participants, timeout)
├─ Create Election(election_id, message_id, strategy, participants)
└─ Return election_id

VotingService.cast_vote(election_id, vote)
├─ Validate vote participant in election.participants
├─ Add vote to election.votes[vote.agent_id]
├─ _check_resolution(election) → Check if resolution criteria met based on strategy
│  ├─ QUORUM: approvals > 50% → APPROVE
│  ├─ UNANIMOUS: any deny → DENY, all approve → APPROVE
│  └─ SUPER_MAJORITY: approvals >= 2/3 → APPROVE
└─ If resolved → Set election.status = CLOSED
```

### Multi-Approver Workflow

```
MultiApproverWorkflowEngine.create_request(...)
├─ Select policy based on risk_score if not specified
├─ Check auto-approval (if policy.auto_approve_low_risk && risk < policy.risk_threshold)
│  └─ Create with status=APPROVED (skip deliberation)
├─ Create ApprovalRequest with status=PENDING
├─ Get eligible_approvers(policy, tenant_id)
└─ Notify approvers via notification_channels (Slack/Teams)

submit_decision(request_id, approver_id, decision, reasoning)
├─ Validate approver not already decided
├─ Create ApprovalDecision(approver_id, decision, reasoning)
├─ If decision == REJECTED → Set request.status = REJECTED (fail fast)
├─ Else → Check if requirements met via policy.validate_approvers(...)
│  ├─ Check min_approvers count
│  ├─ Check self-approval if !allow_self_approval
│  └─ Check required_roles if require_all_roles
└─ If requirements met → Set request.status = APPROVED

_escalation_loop() (background task)
├─ Every 60 seconds:
│  ├─ Check timeout → request.status = TIMEOUT
│  ├─ Check escalation levels based on elapsed time
│  │  ├─ hours >= escalation_hours * 3 → EXECUTIVE
│  │  ├─ hours >= escalation_hours * 2 → LEVEL_3
│  │  └─ hours >= escalation_hours → LEVEL_2
│  └─ Send escalation notifications via channels
```

### Adaptive Router Learning

```
AdaptiveRouter.route_message(message) [Per message]
├─ Calculate impact_score if missing
├─ If score >= impact_threshold → route to deliberation
├─ Else → route to fast lane
└─ Record in routing_history[{message_id, impact_score, lane, timestamp, ...}]

update_performance_feedback(message_id, actual_outcome, processing_time, feedback_score)
├─ Find routing_entry in history
├─ Update entry with actual_outcome, processing_time, feedback_score
├─ Update performance counters
└─ Call _adjust_threshold() if learning enabled

_adjust_threshold() [Periodic, min 50 messages]
├─ Analyze recent 100 routing decisions
├─ Calculate false positive rate (deliberation items with good feedback)
├─ Calculate false negative rate (fast lane failures)
├─ Adjust threshold:
│  ├─ fp_rate > 0.3 → threshold += 0.05 (raise threshold, fewer deliberations)
│  └─ fn_rate > 0.1 → threshold -= 0.05 (lower threshold, more deliberations)
└─ Log adjustment with rates
```

## Relationships Diagram

```mermaid
---
title: Deliberation Layer Code Architecture
---
classDiagram
    namespace Input {
        class AgentMessage {
            +message_id: str
            +from_agent: str
            +to_agent: str
            +content: Dict
            +priority: Priority
            +message_type: MessageType
            +impact_score: float
            +status: MessageStatus
            +constitutional_hash: str
        }
    }

    namespace ImpactScoring {
        class ImpactScorer {
            -model_name: str
            -tokenizer: AutoTokenizer
            -model: AutoModel
            -session: ort.InferenceSession
            -_bert_enabled: bool
            -_onnx_enabled: bool
            -config: ScoringConfig
            -high_impact_keywords: List~str~
            -_agent_request_rates: Dict
            -_agent_impact_history: Dict
            +__init__(model_name, onnx_path, config)
            +calculate_impact_score(content, context) float
            #_get_embeddings(text) ndarray
            #_infer_onnx(text) ndarray
            #_infer_distilbert(text) ndarray
            #_calculate_permission_score(content) float
            #_calculate_volume_score(agent_id) float
            #_calculate_context_score(content, context) float
            #_calculate_drift_score(agent_id, baseline) float
            #_calculate_priority_factor(content, context) float
            #_calculate_type_factor(content, context) float
        }

        class ScoringConfig {
            +semantic_weight: float
            +permission_weight: float
            +volume_weight: float
            +context_weight: float
            +drift_weight: float
            +priority_weight: float
            +type_weight: float
            +critical_priority_boost: float
            +high_semantic_boost: float
        }
    }

    namespace Routing {
        class AdaptiveRouter {
            -impact_threshold: float
            -deliberation_timeout: int
            -enable_learning: bool
            -routing_history: List
            -performance_metrics: Dict
            -deliberation_queue: DeliberationQueue
            +__init__(impact_threshold, timeout, enable_learning)
            +route_message(message, context) Dict
            -_route_to_fast_lane(message, context) Dict
            -_route_to_deliberation(message, context) Dict
            -_record_routing_history(message, decision)
            +update_performance_feedback(msg_id, outcome, time, score)
            -_adjust_threshold()
            +get_routing_stats() Dict
            +set_impact_threshold(threshold)
            +force_deliberation(message, reason) Dict
        }
    }

    namespace PolicyGuard {
        class OPAGuard {
            -opa_client: OPAClient
            -fail_closed: bool
            -enable_signatures: bool
            -enable_critic_review: bool
            -signature_timeout: int
            -review_timeout: int
            -high_risk_threshold: float
            -critical_risk_threshold: float
            -_pending_signatures: Dict
            -_pending_reviews: Dict
            -_audit_log: List
            -_stats: Dict
            -_critic_agents: Dict
            +__init__(opa_client, fail_closed, signatures, reviews, thresholds)
            +verify_action(agent_id, action, context) GuardResult
            #_calculate_risk_score(action, context, policy) float
            #_determine_risk_level(score) str
            #_identify_risk_factors(action, context) List
            +collect_signatures(id, signers, threshold, timeout) SignatureResult
            +submit_signature(id, signer, reasoning, confidence) bool
            +reject_signature(id, signer, reason) bool
            +submit_for_review(decision, critics, types, timeout) ReviewResult
            +submit_review(id, critic, verdict, reasoning, concerns, recs, confidence) bool
            +register_critic_agent(id, types, callback, metadata)
            +check_constitutional_compliance(action) bool
            +log_decision(decision, result)
            +get_stats() Dict
            +get_audit_log(limit, offset, agent_id) List
        }

        class GuardResult {
            +agent_id: str
            +action_type: str
            +constitutional_valid: bool
            +decision: GuardDecision
            +is_allowed: bool
            +requires_signatures: bool
            +requires_review: bool
            +required_signers: List
            +required_reviewers: List
            +risk_score: float
            +risk_level: str
            +risk_factors: List
            +validation_errors: List
            +validation_warnings: List
        }

        class GuardDecision {
            <<enumeration>>
            ALLOW
            REQUIRE_SIGNATURES
            REQUIRE_REVIEW
            DENY
        }
    }

    namespace DeliberationQueue {
        class DeliberationQueue {
            -queue: Dict~str, DeliberationTask~
            -processing_tasks: List~asyncio.Task~
            -persistence_path: Optional
            -consensus_threshold: float
            -default_timeout: int
            -stats: Dict
            -_lock: asyncio.Lock
            +enqueue_for_deliberation(msg, human, vote, timeout) str
            -_monitor_task(task_id)
            +update_status(task_id, status)
            +get_pending_tasks() List~DeliberationItem~
            +get_task(task_id) Optional~DeliberationItem~
            +get_item_details(item_id) Optional~Dict~
            +get_queue_status() Dict
            +submit_agent_vote(id, agent, vote, reasoning, conf) bool
            -_check_consensus(task) bool
            +submit_human_decision(id, reviewer, decision, reasoning) bool
            -_save_tasks()
            -_load_tasks()
            +resolve_task(task_id, approved)
        }

        class DeliberationTask {
            +task_id: str
            +message: AgentMessage
            +status: DeliberationStatus
            +required_votes: int
            +consensus_threshold: float
            +timeout_seconds: int
            +current_votes: List~AgentVote~
            +metadata: Dict
            +created_at: datetime
            +updated_at: datetime
            +human_reviewer: Optional~str~
            +human_decision: Optional~DeliberationStatus~
        }

        class AgentVote {
            +agent_id: str
            +vote: VoteType
            +reasoning: str
            +confidence_score: float
            +timestamp: datetime
        }

        class DeliberationStatus {
            <<enumeration>>
            PENDING
            UNDER_REVIEW
            APPROVED
            REJECTED
            TIMED_OUT
            CONSENSUS_REACHED
        }

        class VoteType {
            <<enumeration>>
            APPROVE
            REJECT
            ABSTAIN
        }
    }

    namespace Voting {
        class VotingService {
            -default_strategy: VotingStrategy
            -elections: Dict~str, Election~
            -_lock: asyncio.Lock
            +create_election(message, participants, timeout) str
            +cast_vote(election_id, vote) bool
            -_check_resolution(election)
            +get_result(election_id) Optional~str~
        }

        class Election {
            +election_id: str
            +message_id: str
            +strategy: VotingStrategy
            +participants: Set~str~
            +votes: Dict~str, Vote~
            +status: str
            +created_at: datetime
            +expires_at: datetime
        }

        class Vote {
            +agent_id: str
            +decision: str
            +reason: Optional~str~
            +timestamp: datetime
        }

        class VotingStrategy {
            <<enumeration>>
            QUORUM
            UNANIMOUS
            SUPER_MAJORITY
        }
    }

    namespace ApprovalWorkflow {
        class MultiApproverWorkflowEngine {
            -notification_channels: List~NotificationChannel~
            -audit_callback: Optional~Callable~
            -_requests: Dict~str, ApprovalRequest~
            -_approvers: Dict~str, Approver~
            -_policies: Dict~str, ApprovalPolicy~
            -_escalation_task: Optional~asyncio.Task~
            -_running: bool
            +start() async
            +stop() async
            +register_approver(approver)
            +register_policy(policy_id, policy)
            +create_request(...) ApprovalRequest async
            +submit_decision(req_id, approver_id, decision, reasoning) async
            +cancel_request(req_id, reason) async
            +get_request(req_id) Optional
            +get_pending_requests(tenant_id, approver_id) List
            +get_stats() Dict
            -_select_policy_for_risk(score) str
            -_get_eligible_approvers(policy, tenant_id) List
            -_escalation_loop() async
        }

        class ApprovalRequest {
            +id: str
            +request_type: str
            +requester_id: str
            +requester_name: str
            +tenant_id: str
            +title: str
            +description: str
            +risk_score: float
            +policy: ApprovalPolicy
            +payload: Dict
            +status: ApprovalStatus
            +decisions: List~ApprovalDecision~
            +escalation_level: EscalationLevel
            +created_at: datetime
            +updated_at: datetime
            +deadline: Optional~datetime~
            +constitutional_hash: str
        }

        class ApprovalPolicy {
            +name: str
            +required_roles: List~ApproverRole~
            +min_approvers: int
            +require_all_roles: bool
            +timeout_hours: float
            +escalation_hours: float
            +allow_self_approval: bool
            +require_reasoning: bool
            +auto_approve_low_risk: bool
            +risk_threshold: float
            +validate_approvers(decisions, approvers, requester_id) tuple
        }

        class Approver {
            +id: str
            +name: str
            +email: str
            +roles: List~ApproverRole~
            +slack_id: Optional~str~
            +teams_id: Optional~str~
            +timezone: str
            +is_active: bool
            +has_role(role) bool
        }

        class ApprovalDecision {
            +approver_id: str
            +approver_name: str
            +decision: ApprovalStatus
            +reasoning: str
            +timestamp: datetime
            +metadata: Dict
            +to_dict() Dict
        }
    }

    namespace HITL {
        class HITLManager {
            -queue: DeliberationQueue
            -audit_ledger: AuditLedger
            +request_approval(item_id, channel) async
            +process_approval(item_id, reviewer_id, decision, reasoning) async
        }
    }

    namespace Integration {
        class DeliberationLayer {
            -impact_threshold: float
            -deliberation_timeout: int
            -enable_redis: bool
            -enable_learning: bool
            -enable_llm: bool
            -enable_opa_guard: bool
            -high_risk_threshold: float
            -critical_risk_threshold: float
            -impact_scorer: ImpactScorerProtocol
            -adaptive_router: AdaptiveRouterProtocol
            -deliberation_queue: DeliberationQueueProtocol
            -llm_assistant: Optional
            -opa_guard: Optional~OPAGuard~
            -redis_queue: Optional
            -redis_voting: Optional
            -fast_lane_callback: Optional~Callable~
            -deliberation_callback: Optional~Callable~
            -guard_callback: Optional~Callable~
            +__init__(...)
            +initialize() async
            +process_message(message) async Dict
            -_prepare_processing_context(msg) Dict
            -_ensure_impact_score(msg, context)
            -_evaluate_opa_guard(msg, start) async
            -_execute_routing(msg, context) async Dict
            -_finalize_processing(msg, result, start) async Dict
            -_verify_with_opa_guard(msg) async
            -_handle_guard_denial(msg, result, start) async Dict
            -_handle_signature_requirement(msg, result, start) async Dict
            -_handle_review_requirement(msg, result, start) async Dict
            -_process_fast_lane(msg, routing) async Dict
            -_process_deliberation(msg, routing) async Dict
            +submit_human_decision(id, reviewer, decision, reasoning) async bool
            +submit_agent_vote(id, agent, vote, reasoning, conf) async bool
            +get_layer_stats() Dict
            +set_fast_lane_callback(callback)
            +set_deliberation_callback(callback)
            +set_guard_callback(callback)
            +close() async
            +analyze_trends() async Dict
            +force_deliberation(msg, reason) async Dict
            +resolve_deliberation_item(id, approved, score) async Dict
        }
    }

    %% Relationships
    AgentMessage --> ImpactScorer : scores
    ImpactScorer --> ScoringConfig : configured by
    AdaptiveRouter --> ImpactScorer : uses
    AdaptiveRouter --> DeliberationQueue : routes to
    OPAGuard --> GuardResult : returns
    OPAGuard --> GuardDecision : uses
    DeliberationQueue --> DeliberationTask : manages
    DeliberationTask --> AgentVote : contains
    DeliberationTask --> DeliberationStatus : has
    VotingService --> Election : manages
    Election --> VoteType : uses
    MultiApproverWorkflowEngine --> ApprovalRequest : manages
    MultiApproverWorkflowEngine --> ApprovalPolicy : uses
    MultiApproverWorkflowEngine --> Approver : coordinates
    ApprovalRequest --> ApprovalPolicy : follows
    ApprovalRequest --> ApprovalDecision : contains
    HITLManager --> DeliberationQueue : reads from
    DeliberationLayer --> ImpactScorer : uses
    DeliberationLayer --> AdaptiveRouter : uses
    DeliberationLayer --> DeliberationQueue : uses
    DeliberationLayer --> OPAGuard : uses (conditional)
    DeliberationLayer --> VotingService : uses
    DeliberationLayer --> MultiApproverWorkflowEngine : uses (optional)
```

## Notes

- **Constitutional Hash Enforcement**: All classes validate `constitutional_hash == "cdd01ef066bc6cf2"` at critical boundaries (ApprovalRequest.__post_init__, OPAGuard.verify_action, etc.)
- **Fail-Closed Security**: OPA Guard and integration layer implement fail-closed error handling - security violations default to denial
- **Async/Await Throughout**: All I/O operations are async (OPA calls, Redis, database, message queues)
- **Dependency Injection**: DeliberationLayer supports full DI for all components, enabling comprehensive testing without external services
- **GPU Acceleration Profiling**: ImpactScorer tracks DistilBERT and ONNX inference for GPU recommendation (requires optional profiling module)
- **Persistent Storage**: DeliberationQueue supports JSON file persistence; production deployments would use Redis or database
- **Multi-Channel Notifications**: MultiApproverWorkflowEngine supports Slack and Teams; extensible via NotificationChannel protocol
- **Learning & Adaptation**: AdaptiveRouter automatically adjusts impact_threshold based on false positive/negative rates to optimize routing decisions
- **Role-Based Access Control**: MultiApproverWorkflowEngine enforces approval policies with role requirements and self-approval prevention
- **Escalation Automation**: Background tasks monitor timeout and trigger automatic escalation via notification channels
- **Audit Trails**: OPAGuard maintains immutable audit log (max 10K entries); integrated with blockchain via HITLManager.audit_ledger
- **Risk-Based Routing**: OPA Guard decision routing based on risk assessment (low=allow, medium=signatures, high=signatures+reviews, critical=deny)
- **Consensus Mechanisms**: DeliberationQueue supports both agent voting (consensus threshold) and human HITL decisions with different status transitions
- **Performance Metrics**: All components track performance statistics accessible via get_stats() methods for monitoring and alerting
