# C4 Code Level: Enhanced Agent Bus Core

## Overview

- **Name**: Enhanced Agent Bus Core
- **Description**: Core message bus implementation for ACGS-2 constitutional AI governance with agent registration, message routing, validation, and deliberation support
- **Location**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/`
- **Language**: Python 3.11+
- **Constitutional Hash**: `cdd01ef066bc6cf2`
- **Purpose**: Provides the foundational messaging infrastructure for multi-agent coordination with constitutional compliance, multi-tenant isolation, and comprehensive metrics instrumentation

## Code Elements

### Core Classes

#### EnhancedAgentBus
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/agent_bus.py:76-938`

Primary entry point for agent communication with constitutional governance.

**Key Methods**:

- `__init__(**kwargs)`
  - Initializes the Enhanced Agent Bus with configuration parameters.
  - Supports: `redis_url`, `enable_maci`, `maci_strict_mode`, `use_dynamic_policy`, `enable_metering`, `use_redis_registry`, `router`, `validator`, `processor`, `enable_adaptive_governance`.
  - Returns: None

- `from_config(config: Any) -> EnhancedAgentBus` (classmethod)
  - Factory method for creating bus from configuration object or dictionary.
  - Returns: Configured EnhancedAgentBus instance

- `async start() -> None`
  - Starts the agent bus and initializes all services.
  - Initializes metering manager, Kafka bus, Prometheus service info, circuit breakers, and adaptive governance.
  - Returns: None

- `async stop() -> None`
  - Gracefully stops the agent bus and cleans up resources.
  - Cancels Kafka consumer task, stops Kafka bus, metering manager, and adaptive governance.
  - Returns: None

- `async register_agent(agent_id, agent_type="worker", capabilities=None, tenant_id=None, maci_role=None, **kwargs) -> bool`
  - Registers an agent with multi-tenant isolation and optional MACI role enforcement.
  - Validates agent identity via `auth_token` in kwargs if provided.
  - Returns: True if registration successful, False otherwise

- `async unregister_agent(aid: str) -> bool`
  - Unregisters an agent from the bus.
  - Returns: True if agent found and removed

- `get_agent_info(aid: str) -> Optional[Dict[str, Any]]`
  - Retrieves information about a registered agent.
  - Returns: Agent info dict or None

- `async send_message(msg: AgentMessage) -> ValidationResult`
  - Sends a message through the bus with constitutional validation.
  - Enforces multi-tenant isolation, adaptive governance, and deliberation for high-impact messages.
  - Returns: ValidationResult with validation status and metadata

- `async receive_message(timeout: float = 1.0) -> Optional[AgentMessage]`
  - Receives a message from the bus with optional timeout.
  - Returns: AgentMessage or None on timeout

- `async broadcast_message(msg: AgentMessage) -> Dict[str, ValidationResult]`
  - Broadcasts a message to all agents in the same tenant.
  - Enforces strict multi-tenant isolation.
  - Returns: Dict mapping agent_id to ValidationResult

- `get_registered_agents() -> List[str]`
  - Returns list of registered agent IDs.

- `get_agents_by_type(atype: str) -> List[str]`
  - Returns list of agent IDs filtered by type.

- `get_agents_by_capability(cap: str) -> List[str]`
  - Returns list of agent IDs with specific capability.

- `get_metrics() -> Dict[str, Any]`
  - Returns bus metrics synchronously.
  - Returns: Dict with metrics

- `async get_metrics_async() -> Dict[str, Any]`
  - Returns comprehensive bus metrics asynchronously.
  - Returns: Dict with extended metrics

**Properties**:

- `processor: MessageProcessor` - Get the message processor
- `is_running: bool` - Check if the bus is running
- `registry: AgentRegistry` - Get the agent registry (DI component)
- `router: MessageRouter` - Get the message router (DI component)
- `validator: ValidationStrategy` - Get the validation strategy (DI component)
- `maci_enabled: bool` - Check if MACI role separation is enabled
- `maci_registry: Optional[MACIRoleRegistry]` - Get the MACI role registry
- `maci_enforcer: Optional[MACIEnforcer]` - Get the MACI enforcer

**Dependencies**: asyncio, logging, time, datetime, Optional, Dict, List, ValidationResult, AgentMessage, MessageType, MessageStatus, CircuitBreaker, PolicyClient, OPAClient, AuditClient, AgentRegistry, MessageRouter, ValidationStrategy, MessageProcessor, MACIEnforcement, MeteringManager

#### MessageProcessor
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/message_processor.py` (referenced in core.py)

Processes messages with validation and routing logic.

**Key Methods** (inferred from usage):
- `async process(message: AgentMessage) -> ValidationResult` - Processes a message through validation pipeline
- `get_metrics() -> Dict[str, Any]` - Returns processor metrics

**Dependencies**: Validation strategies, policy client, OPA client, audit client, metering hooks, MACI enforcement

---

### Data Models

#### AgentMessage
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py:117-209`

Agent message with constitutional compliance and multi-tenant support.

**Attributes**:
- `message_id: str` - Unique message identifier (default: UUID)
- `conversation_id: str` - Conversation identifier (default: UUID)
- `content: Dict[str, Any]` - Message content
- `payload: Dict[str, Any]` - Message payload
- `from_agent: str` - Sender agent ID
- `to_agent: str` - Recipient agent ID
- `sender_id: str` - Alternative sender identifier
- `message_type: MessageType` - Type of message
- `routing: Optional[RoutingContext]` - Routing context
- `headers: Dict[str, str]` - Message headers
- `tenant_id: str` - Multi-tenant isolation ID
- `security_context: Dict[str, Any]` - Security context data
- `priority: Priority` - Message priority level
- `status: MessageStatus` - Current message status
- `constitutional_hash: str` - Constitutional hash for validation
- `constitutional_validated: bool` - Whether message passed constitutional validation
- `created_at: datetime` - Message creation timestamp
- `updated_at: datetime` - Last update timestamp
- `expires_at: Optional[datetime]` - Message expiration time
- `impact_score: Optional[float]` - Impact score for deliberation
- `performance_metrics: Dict[str, Any]` - Performance tracking data

**Methods**:
- `to_dict() -> Dict[str, Any]` - Convert message to dictionary
- `to_dict_raw() -> Dict[str, Any]` - Convert to dictionary with all fields
- `from_dict(data: Dict[str, Any]) -> AgentMessage` (classmethod) - Create message from dictionary

#### MessageType (Enum)
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py:27-39`

Message type enumeration for routing and handling.

**Values**:
- COMMAND = "command"
- QUERY = "query"
- RESPONSE = "response"
- EVENT = "event"
- NOTIFICATION = "notification"
- HEARTBEAT = "heartbeat"
- GOVERNANCE_REQUEST = "governance_request"
- GOVERNANCE_RESPONSE = "governance_response"
- CONSTITUTIONAL_VALIDATION = "constitutional_validation"
- TASK_REQUEST = "task_request"
- TASK_RESPONSE = "task_response"

#### Priority (Enum)
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py:42-55`

Priority levels for message processing (ascending order).

**Values**:
- LOW = 0
- NORMAL = 1 (alias for MEDIUM for backward compatibility)
- MEDIUM = 1
- HIGH = 2
- CRITICAL = 3

#### MessageStatus (Enum)
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py:86-93`

Message processing status throughout lifecycle.

**Values**:
- PENDING = "pending"
- PROCESSING = "processing"
- DELIVERED = "delivered"
- FAILED = "failed"
- EXPIRED = "expired"
- PENDING_DELIBERATION = "pending_deliberation"

#### ValidationStatus (Enum)
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py:58-63`

Message validation status.

**Values**:
- PENDING = "pending"
- VALID = "valid"
- INVALID = "invalid"
- WARNING = "warning"

#### RoutingContext
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py:97-114`

Context for message routing in the agent bus.

**Attributes**:
- `source_agent_id: str` - Sending agent ID (required)
- `target_agent_id: str` - Receiving agent ID (required)
- `routing_key: str` - Routing key for advanced routing (default: "")
- `routing_tags: List[str]` - Tags for routing logic (default: [])
- `retry_count: int` - Current retry count (default: 0)
- `max_retries: int` - Maximum retries (default: 3)
- `timeout_ms: int` - Routing timeout in milliseconds (default: 5000)
- `constitutional_hash: str` - Constitutional hash

#### DecisionLog
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py:212-240`

Structured decision log for compliance and observability.

**Attributes**:
- `trace_id: str` - Distributed trace ID
- `span_id: str` - Distributed trace span ID
- `agent_id: str` - Agent that made the decision
- `tenant_id: str` - Tenant identifier
- `policy_version: str` - Policy version used
- `risk_score: float` - Risk assessment score
- `decision: str` - Decision made
- `constitutional_hash: str` - Constitutional hash
- `timestamp: datetime` - Decision timestamp
- `compliance_tags: List[str]` - Compliance tags
- `metadata: Dict[str, Any]` - Additional metadata

---

### Validation

#### ValidationResult
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/validators.py:22-69`

Result of a validation operation.

**Attributes**:
- `is_valid: bool` - Whether validation passed (default: True)
- `errors: List[str]` - Error messages
- `warnings: List[str]` - Warning messages
- `metadata: Dict[str, Any]` - Additional metadata
- `decision: str` - Validation decision (default: "ALLOW")
- `constitutional_hash: str` - Constitutional hash

**Methods**:
- `add_error(error: str) -> None` - Add error and mark as invalid
- `add_warning(warning: str) -> None` - Add warning message
- `merge(other: ValidationResult) -> None` - Merge another result
- `to_dict() -> Dict[str, Any]` - Convert to dictionary

#### Validation Functions
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/validators.py:72-108`

- `validate_constitutional_hash(hash_value: str) -> ValidationResult`
  - Validates constitutional hash using constant-time comparison to prevent timing attacks
  - Uses hmac.compare_digest for security

- `validate_message_content(content: Dict[str, Any]) -> ValidationResult`
  - Validates message content structure and required fields

---

### Exception Hierarchy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/exceptions.py`

33 typed exception classes for precise error handling (including base classes):

#### Base Exception
- `AgentBusError(message, details, constitutional_hash)` (19-46)
  - Base exception for all Enhanced Agent Bus errors
  - All exceptions inherit from this class
  - Methods: `to_dict() -> Dict[str, Any]`

#### Constitutional Validation Errors
- `ConstitutionalError` (53-56)
  - Base for constitutional compliance failures

- `ConstitutionalHashMismatchError(expected_hash, actual_hash, context)` (59-109)
  - Hash validation failures with sanitized error messages
  - Properties: `expected_hash`, `actual_hash` (internal use only)
  - Static method: `_sanitize_hash(hash_value, max_visible=8) -> str`

- `ConstitutionalValidationError(validation_errors, agent_id, action_type)` (111-131)
  - General constitutional validation failures

#### Message Processing Errors
- `MessageError` (139-142)
  - Base for message-related errors

- `MessageValidationError(message_id, errors, warnings)` (145-166)
  - Message validation failures

- `MessageDeliveryError(message_id, target_agent, reason)` (168-187)
  - Message delivery failures

- `MessageTimeoutError(message_id, timeout_ms, operation)` (190-212)
  - Message processing timeout

- `MessageRoutingError(message_id, source_agent, target_agent, reason)` (215-237)
  - Message routing failures

#### Agent Registration Errors
- `AgentError` (245-248)
  - Base for agent-related errors

- `AgentNotRegisteredError(agent_id, operation)` (251-266)
  - Agent not found for operation

- `AgentAlreadyRegisteredError(agent_id)` (269-277)
  - Agent already registered

- `AgentCapabilityError(agent_id, required_capabilities, available_capabilities)` (280-301)
  - Agent missing required capabilities

#### Policy and OPA Errors
- `PolicyError` (309-312)
  - Base for policy-related errors

- `PolicyEvaluationError(policy_path, reason, input_data)` (315-334)
  - Policy evaluation failures

- `PolicyNotFoundError(policy_path)` (337-345)
  - Required policy not found

- `OPAConnectionError(opa_url, reason)` (348-360)
  - OPA server connection failure

- `OPANotInitializedError(operation)` (363-371)
  - OPA client not initialized

#### Governance and Alignment Errors
- `GovernanceError(message, details)` (379-387)
  - Base for governance-related errors

- `ImpactAssessmentError(assessment_type, reason)` (389-397)
  - Impact assessment operation failures

- `AlignmentViolationError(reason, alignment_score, agent_id)` (679-701)
  - Constitutional alignment failures

#### Deliberation Layer Errors
- `DeliberationError` (405-408)
  - Base for deliberation layer errors

- `DeliberationTimeoutError(decision_id, timeout_seconds, pending_reviews, pending_signatures)` (411-433)
  - Deliberation process timeout

- `SignatureCollectionError(decision_id, required_signers, collected_signers, reason)` (436-460)
  - Signature collection failure

- `ReviewConsensusError(decision_id, approval_count, rejection_count, escalation_count)` (463-487)
  - Critic review consensus failure

#### Bus Operation Errors
- `BusOperationError` (495-498)
  - Base for bus operation errors

- `BusNotStartedError(operation)` (501-509)
  - Bus not started for operation

- `BusAlreadyStartedError()` (512-519)
  - Bus already running

- `HandlerExecutionError(handler_name, message_id, original_error)` (522-542)
  - Message handler execution failure

#### Configuration Errors
- `ConfigurationError(config_key, reason)` (550-562)
  - Invalid or missing configuration

#### MACI Role Separation Errors
- `MACIError` (570-573)
  - Base for MACI role separation errors

- `MACIRoleViolationError(agent_id, role, action, allowed_roles)` (576-601)
  - Agent attempts action outside role permissions

- `MACISelfValidationError(agent_id, action, output_id)` (604-627)
  - Gödel bypass prevention: self-validation attempt

- `MACICrossRoleValidationError(validator_agent, validator_role, target_agent, target_role, reason)` (630-656)
  - Cross-role validation constraint violation

- `MACIRoleNotAssignedError(agent_id, operation)` (659-671)
  - Agent has no MACI role assigned

---

### Policy and OPA Integration

#### OPAClient
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/opa_client.py:66-100`

Client for OPA (Open Policy Agent) policy evaluation.

**Initialization Parameters**:
- `opa_url: str = "http://localhost:8181"` - OPA server URL
- `mode: str = "http"` - Operation mode: "http", "embedded", or "fallback"
- `timeout: float = 5.0` - Request timeout
- `cache_ttl: int = 300` - Cache TTL in seconds
- `enable_cache: bool = True` - Enable caching
- `redis_url: Optional[str] = None` - Redis URL for distributed cache
- `fail_closed: bool = True` - Fail-closed on OPA errors

**Attributes**:
- `opa_url: str` - OPA server URL
- `mode: str` - Operation mode
- `timeout: float` - Request timeout
- `cache_ttl: int` - Cache TTL
- `enable_cache: bool` - Cache enabled flag
- `fail_closed: bool` - Fail-closed mode
- `_http_client: Optional[httpx.AsyncClient]` - Async HTTP client
- `_redis_client: Optional[Any]` - Redis client for distributed caching
- `_embedded_opa: Optional[Any]` - Embedded OPA instance
- `_memory_cache: Dict[str, Dict[str, Any]]` - In-memory cache
- `_lkg_bundle_path: Optional[str]` - Last Known Good bundle path

**Supports Multiple Modes**:
1. HTTP API mode - Connect to remote OPA server via REST
2. Embedded mode - Use OPA Python SDK if available
3. Fallback mode - Local validation when OPA unavailable

#### PolicyRegistryClient (PolicyClient)
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/policy_client.py:27-75`

Client for dynamic policy registry service.

**Initialization Parameters**:
- `registry_url: Optional[str] = None` - Policy registry URL (default: "http://localhost:8000")
- `api_key: Optional[str] = None` - API key for authentication
- `timeout: float = 5.0` - Request timeout
- `cache_ttl: int = 300` - Cache TTL in seconds
- `fail_closed: bool = True` - Fail-closed behavior for safety
- `max_cache_size: int = DEFAULT_MAX_CACHE_SIZE` - Maximum cache size (default: 1000)

**Attributes**:
- `registry_url: str` - Registry URL
- `api_key: Optional[str]` - API key
- `timeout: float` - Request timeout
- `cache_ttl: int` - Cache TTL
- `fail_closed: bool` - Fail-closed flag
- `max_cache_size: int` - Max cache size
- `_cache: OrderedDict[str, Dict[str, Any]]` - LRU-style cache
- `_http_client: Optional[httpx.AsyncClient]` - Async HTTP client

**Methods**:
- `async initialize() -> None` - Initialize HTTP client
- `async close() -> None` - Close HTTP client
- `async get_policy_content(policy_id, client_id) -> Optional[Dict[str, Any]]` - Get policy content

**Context Manager**:
- Supports async context manager protocol (`async with ... as:`)

---

### MACI Role Separation

#### MACIRole (Enum)
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/maci_enforcement.py:37-42`

MACI framework roles implementing separation of powers (Trias Politica).

**Values**:
- EXECUTIVE = "executive" - Proposes decisions
- LEGISLATIVE = "legislative" - Extracts and synthesizes rules
- JUDICIAL = "judicial" - Validates decisions from other roles

#### MACIAction (Enum)
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/maci_enforcement.py:67-76`

Actions that can be performed by MACI agents.

**Values**:
- PROPOSE = "propose" - Create decision/proposal
- VALIDATE = "validate" - Validate another agent's output
- EXTRACT_RULES = "extract_rules" - Extract rules from content
- SYNTHESIZE = "synthesize" - Synthesize policies
- AUDIT = "audit" - Audit trail operations
- QUERY = "query" - Read-only query (allowed for all)
- MANAGE_POLICY = "manage_policy" - Manage governance policies
- EMERGENCY_COOLDOWN = "emergency_cooldown" - Initiate emergency system cooldown

#### ROLE_PERMISSIONS (Dict)
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/maci_enforcement.py:78-87`

Role-to-action mapping.

**Structure**:
```
{
    EXECUTIVE: {PROPOSE, SYNTHESIZE, QUERY},
    LEGISLATIVE: {EXTRACT_RULES, SYNTHESIZE, QUERY},
    JUDICIAL: {VALIDATE, AUDIT, QUERY, EMERGENCY_COOLDOWN}
}
```

#### VALIDATION_CONSTRAINTS (Dict)
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/maci_enforcement.py:77-79`

Cross-role validation constraints.

**Structure**:
```
{
    JUDICIAL: {EXECUTIVE, LEGISLATIVE}  # Judicial can validate Executive and Legislative
}
```

#### MACIAgentRecord
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/maci_enforcement.py:82-111`

Record of an agent's MACI role and outputs.

**Attributes**:
- `agent_id: str` - Agent identifier
- `role: MACIRole` - Assigned MACI role
- `outputs: List[str]` - List of output IDs produced by this agent
- `registered_at: datetime` - Registration timestamp
- `metadata: Dict[str, Any]` - Additional metadata
- `constitutional_hash: str` - Constitutional hash

**Methods**:
- `add_output(output_id: str) -> None` - Record an output
- `owns_output(output_id: str) -> bool` - Check if agent produced output
- `can_perform(action: MACIAction) -> bool` - Check if role allows action
- `can_validate_role(target_role: MACIRole) -> bool` - Check if can validate target role

#### MACIValidationContext
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/maci_enforcement.py:113-123`

Context for MACI validation operations.

**Attributes**:
- `source_agent_id: str` - Agent performing the validation
- `action: MACIAction` - Action being performed
- `target_output_id: Optional[str]` - Output being validated
- `target_agent_id: Optional[str]` - Target agent
- `message_id: Optional[str]` - Related message ID
- `timestamp: datetime` - Operation timestamp
- `constitutional_hash: str` - Constitutional hash

#### MACIValidationResult
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/maci_enforcement.py:126-146`

Result of MACI role validation.

**Attributes**:
- `is_valid: bool` - Whether validation passed
- `context: MACIValidationContext` - Validation context
- `error_message: Optional[str]` - Error message if validation failed
- `violation_type: Optional[str]` - Type of violation if any
- `constitutional_hash: str` - Constitutional hash

**Methods**:
- `to_dict() -> Dict[str, Any]` - Convert to dictionary

#### MACIRoleRegistry
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/maci_enforcement.py:149-` (continues)

Registry for MACI agent roles and outputs (referenced but partially shown).

#### MACIEnforcer
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/maci_enforcement.py:` (referenced in agent_bus.py)

Enforcer for MACI role separation validation.

---

### Processing Strategies

#### HandlerExecutorMixin
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/processing_strategies.py:48-107`

Mixin providing common handler execution logic.

**Methods**:
- `async _execute_handlers(message: AgentMessage, handlers: Dict[Any, List[Callable]]) -> ValidationResult`
  - Executes registered handlers for the message
  - Updates message status through PROCESSING -> DELIVERED/FAILED lifecycle
  - Handles both sync and async handlers transparently
  - Returns: ValidationResult

#### PythonProcessingStrategy
**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/processing_strategies.py:110-150`

Python-based processing strategy with static hash validation.

**Initialization Parameters**:
- `validation_strategy: Optional[Any] = None` - Validation strategy (defaults to StaticHashValidationStrategy)
- `metrics_enabled: bool = False` - Whether to record Prometheus metrics

**Methods**:
- `async process(message: AgentMessage, handlers: Dict[Any, List[Callable]]) -> ValidationResult`
  - Processes message with validation and handlers
  - Returns: ValidationResult

---

## Dependencies

### Internal Dependencies

#### From enhanced_agent_bus package
- `models.py`: AgentMessage, MessageType, MessageStatus, Priority, ValidationStatus, RoutingContext, DecisionLog, CONSTITUTIONAL_HASH
- `validators.py`: ValidationResult, validate_constitutional_hash, validate_message_content
- `exceptions.py`: 22 typed exceptions including ConstitutionalHashMismatchError, MACIRoleViolationError, etc.
- `opa_client.py`: OPAClient for policy evaluation
- `policy_client.py`: PolicyRegistryClient for dynamic policy registry
- `maci_enforcement.py`: MACIRole, MACIAction, MACIRoleRegistry, MACIEnforcer, role/action validation
- `processing_strategies.py`: Processing strategy implementations
- `message_processor.py`: MessageProcessor for message processing
- `metering_manager.py`: MeteringManager for usage metering
- `metering_integration.py`: MeteringHooks for instrumentation
- `config.py`: BusConfiguration for configuration management
- `interfaces.py`: AgentRegistry, MessageRouter, ValidationStrategy, ProcessingStrategy (protocols)
- `registry.py`: InMemoryAgentRegistry, DirectMessageRouter, validation strategies

#### From shared package
- `shared.constants`: CONSTITUTIONAL_HASH, SECURITY_HEADERS
- `shared.metrics`: Prometheus metrics (MESSAGE_QUEUE_DEPTH, set_service_info)
- `shared.circuit_breaker`: Circuit breaker (get_circuit_breaker, initialize_core_circuit_breakers, CircuitBreakerConfig)
- `shared.config`: settings (configuration management)
- `shared.crypto`: CryptoService (JWT verification)
- `shared.audit`: AuditClient (audit trail logging)
- `shared.redis_config`: get_redis_url (Redis configuration)

#### From deliberation_layer package
- `deliberation_layer.interfaces`: VotingService
- `deliberation_layer.queue`: DeliberationQueue

### External Dependencies

#### Core Libraries
- `asyncio` - Async/await and concurrency primitives
- `logging` - Structured logging
- `time` - Performance measurement (perf_counter)
- `datetime` - Timestamp generation (now, timezone)
- `typing` - Type hints (Any, Dict, List, Optional, Callable, TYPE_CHECKING)
- `uuid` - Unique identifier generation
- `hmac` - Constant-time comparison for security
- `dataclasses` - Data class definitions (dataclass, field)
- `enum` - Enumeration types (Enum)
- `json` - JSON serialization
- `os` - Environment variable access
- `collections` - OrderedDict for LRU caching

#### Third-party Libraries
- `pydantic` - Data validation (referenced in imports)
- `httpx` - Async HTTP client for OPA and policy registry
- `redis.asyncio` - Redis client for distributed caching (optional)
- `opa` - OPA Python SDK for embedded mode (optional)

#### Optional/Feature-gated
- `enhanced_agent_bus_rust` - Rust acceleration backend (optional)
- OpenTelemetry tracing (conditional import)
- Kafka message bus (conditional import)

---

## Relationships

### Class Relationships and Dependencies

```mermaid
---
title: Enhanced Agent Bus Core - Class Diagram
---
classDiagram
    namespace Core {
        class EnhancedAgentBus {
            -_registry: AgentRegistry
            -_router: MessageRouter
            -_validator: ValidationStrategy
            -_processor: MessageProcessor
            -_policy_client: Optional[PolicyClient]
            -_opa_client: Optional[OPAClient]
            -_audit_client: Optional[AuditClient]
            -_metering_manager: MeteringManager
            -_maci_registry: Optional[MACIRoleRegistry]
            -_maci_enforcer: Optional[MACIEnforcer]
            -_agents: Dict[str, Dict]
            -_message_queue: asyncio.Queue
            +async start() void
            +async stop() void
            +async register_agent() bool
            +async send_message() ValidationResult
            +async receive_message() Optional[AgentMessage]
            +get_metrics() Dict
        }

        class MessageProcessor {
            -_validation_strategy: ValidationStrategy
            +async process() ValidationResult
            +get_metrics() Dict
        }
    }

    namespace Models {
        class AgentMessage {
            +message_id: str
            +conversation_id: str
            +from_agent: str
            +to_agent: str
            +message_type: MessageType
            +tenant_id: str
            +priority: Priority
            +status: MessageStatus
            +constitutional_hash: str
            +to_dict() Dict
            +from_dict() AgentMessage*
        }

        class RoutingContext {
            +source_agent_id: str
            +target_agent_id: str
            +routing_key: str
            +retry_count: int
            +max_retries: int
        }

        class DecisionLog {
            +trace_id: str
            +agent_id: str
            +decision: str
            +risk_score: float
            +to_dict() Dict
        }
    }

    namespace Validation {
        class ValidationResult {
            +is_valid: bool
            +errors: List[str]
            +warnings: List[str]
            +metadata: Dict
            +add_error() void
            +merge() void
            +to_dict() Dict
        }
    }

    namespace Interfaces {
        class AgentRegistry {
            <<interface>>
        }

        class MessageRouter {
            <<interface>>
        }

        class ValidationStrategy {
            <<interface>>
        }

        class ProcessingStrategy {
            <<interface>>
        }
    }

    namespace PolicyIntegration {
        class OPAClient {
            -opa_url: str
            -mode: str
            -_http_client: httpx.AsyncClient
            -_redis_client: Optional[aioredis.Redis]
            -_memory_cache: Dict
        }

        class PolicyRegistryClient {
            -registry_url: str
            -_cache: OrderedDict
            -_http_client: httpx.AsyncClient
            +async get_policy_content() Optional[Dict]
        }
    }

    namespace MACI {
        class MACIRoleRegistry {
            <<class>>
        }

        class MACIEnforcer {
            <<class>>
        }

        class MACIRole {
            <<enumeration>>
            EXECUTIVE
            LEGISLATIVE
            JUDICIAL
        }

        class MACIAction {
            <<enumeration>>
            PROPOSE
            VALIDATE
            EXTRACT_RULES
            SYNTHESIZE
            AUDIT
            QUERY
        }

        class MACIAgentRecord {
            +agent_id: str
            +role: MACIRole
            +outputs: List[str]
            +can_perform() bool
            +owns_output() bool
        }
    }

    namespace Metering {
        class MeteringManager {
            <<class>>
        }

        class MeteringHooks {
            <<interface>>
        }
    }

    namespace Exceptions {
        class AgentBusError {
            +message: str
            +details: Dict
            +to_dict() Dict
        }

        class ConstitutionalError {
            <<abstract>>
        }

        class MessageError {
            <<abstract>>
        }

        class MACIError {
            <<abstract>>
        }
    }

    %% Relationships
    EnhancedAgentBus --> AgentRegistry : uses
    EnhancedAgentBus --> MessageRouter : uses
    EnhancedAgentBus --> ValidationStrategy : uses
    EnhancedAgentBus --> MessageProcessor : contains
    EnhancedAgentBus --> PolicyRegistryClient : optional
    EnhancedAgentBus --> OPAClient : optional
    EnhancedAgentBus --> MeteringManager : contains
    EnhancedAgentBus --> MACIRoleRegistry : optional
    EnhancedAgentBus --> MACIEnforcer : optional

    MessageProcessor --> ValidationStrategy : uses
    MessageProcessor --> ProcessingStrategy : uses

    AgentMessage --> MessageType : uses
    AgentMessage --> Priority : uses
    AgentMessage --> MessageStatus : uses
    AgentMessage --> RoutingContext : optional

    ValidationResult --> AgentBusError : creates

    OPAClient --|> PolicyIntegration : validates
    PolicyRegistryClient --|> PolicyIntegration : provides

    MACIRoleRegistry --> MACIAgentRecord : manages
    MACIEnforcer --> MACIRoleRegistry : uses
    MACIEnforcer --> MACIError : throws

    AgentBusError <|-- ConstitutionalError
    AgentBusError <|-- MessageError
    AgentBusError <|-- MACIError
```

### Data Flow

**Message Processing Pipeline**:

```
Agent → EnhancedAgentBus.send_message()
    ↓
Multi-tenant validation (tenant_id consistency)
    ↓
ValidationStrategy.validate()
    ├─ StaticHashValidationStrategy (default)
    ├─ DynamicPolicyValidationStrategy
    └─ OPAValidationStrategy
    ↓
Impact Score Assessment → deliberation_layer.impact_scorer
    ↓
High-impact (≥0.8) → Deliberation Queue
Low-impact (<0.8) → Fast Lane
    ↓
MACI Role Validation (if enabled)
    ↓
MessageProcessor.process()
    ↓
Handler Execution
    ↓
Routing & Delivery
    ├─ Kafka Bus (if enabled)
    └─ Local Queue
    ↓
Audit Logging (async, fire-and-forget)
    ↓
Metering & Metrics (async, fire-and-forget)
    ↓
Return ValidationResult
```

### Security Boundaries

**Multi-tenant Isolation**:
- Messages with `tenant_id` only reach agents in the same tenant
- Messages without `tenant_id` only reach agents without `tenant_id`
- Cross-tenant broadcast is explicitly denied

**Constitutional Validation**:
- Every message passes constitutional hash validation
- Hash used: `cdd01ef066bc6cf2`
- Constant-time comparison prevents timing attacks

**MACI Role Separation**:
- Prevents Gödel bypass attacks through strict role enforcement
- Executive proposes, Legislative extracts rules, Judicial validates
- No agent can validate its own output

**Fail-Closed Behavior**:
- OPA/Policy evaluation failures reject requests by default
- Fallback to static validation on infrastructure failure

---

## Technology Stack

### Programming Language
- **Python 3.12+** (async-first)
- Type hints throughout for static analysis
- Dataclasses for data models
- Enums for type-safe enumeration

### Concurrency & Async
- **asyncio** - Event loop and async primitives
- **httpx** - Async HTTP client for remote services
- **redis.asyncio** - Async Redis client (optional)

### Data & Serialization
- **dataclasses** - Data model definitions
- **JSON** - Message serialization
- **uuid** - Unique identifier generation

### Security
- **hmac** - Constant-time comparison for hash validation
- **JWT tokens** - Agent identity verification
- **Constitutional hash** - Immutable governance enforcement

### Messaging & Events
- **asyncio.Queue** - Local message queue
- **Kafka** - Distributed message bus (optional)
- **Redis** - Cache and pub/sub (optional)

### Monitoring & Observability
- **Prometheus** - Metrics collection
- **OpenTelemetry** - Distributed tracing (optional)
- **Custom logging** - Structured logging throughout

### Policy & Governance
- **OPA** (Open Policy Agent) - Policy evaluation (HTTP or embedded)
- **Policy Registry** - Dynamic policy management
- **MACI Framework** - Role-based separation of powers

---

## Code Organization

### Module Structure

```
enhanced_agent_bus/
├── agent_bus.py                    # EnhancedAgentBus main class
├── core.py                         # Backward compatibility facade
├── models.py                       # Data models (AgentMessage, etc.)
├── validators.py                   # Validation functions & ValidationResult
├── exceptions.py                   # 22 typed exceptions
├── opa_client.py                   # OPA integration
├── policy_client.py                # Policy registry client
├── maci_enforcement.py             # MACI role separation
├── processing_strategies.py        # Processing strategy implementations
├── message_processor.py            # Message processing logic
├── metering_manager.py             # Usage metering
├── metering_integration.py         # Metering hooks & integration
├── config.py                       # BusConfiguration
├── interfaces.py                   # Protocol interfaces for DI
├── registry.py                     # Registry & router implementations
├── imports.py                      # Centralized optional imports
├── kafka_bus.py                    # Kafka event bus (optional)
└── tests/                          # 990+ test files
```

### Design Patterns

**Dependency Injection**:
- Registry, Router, Validator, and Processor are injected
- Allows testing with mock implementations
- Backward compatible with default implementations

**Strategy Pattern**:
- ValidationStrategy (static hash, dynamic policy, OPA)
- ProcessingStrategy (Python, Rust, composite)

**Mixin Pattern**:
- HandlerExecutorMixin for DRY handler execution

**Fire-and-Forget Pattern**:
- Async task creation for non-critical operations
- Maintains low latency while ensuring audit/metering

**Fail-Closed Pattern**:
- OPA evaluation failures reject by default
- Fallback to static validation on errors

---

## Performance Characteristics

### Latency Targets
- **P99 Latency**: 0.328ms per message (target: 0.278ms)
- **Constitutional Validation**: Sub-microsecond (constant-time comparison)
- **Message Routing**: Sub-millisecond
- **Metering Integration**: <5μs overhead (fire-and-forget)

### Throughput
- **Target**: >100 RPS
- **Achieved**: 2,605 RPS (target: 6,310 RPS)
- **Concurrent Agents**: Unlimited with async event loop

### Memory Efficiency
- **Queue**: asyncio.Queue (memory-efficient)
- **Policy Cache**: LRU with max_cache_size to prevent unbounded growth
- **Agent Registry**: In-memory by default, Redis-backed optional

### Scalability
- **Horizontal**: Kafka-based distributed message bus
- **Vertical**: Async I/O maximizes single-node throughput
- **Multi-tenant**: Strict isolation prevents cross-tenant resource sharing

---

## Configuration

### Environment Variables
- `REDIS_URL` - Redis connection (default: redis://localhost:6379)
- `OPA_URL` - OPA server endpoint (default: http://localhost:8181)
- `POLICY_REGISTRY_URL` - Policy registry endpoint (default: http://localhost:8000)
- `USE_RUST_BACKEND` - Enable Rust acceleration (default: false)
- `METRICS_ENABLED` - Prometheus metrics (default: true)
- `METERING_ENABLED` - Usage metering (default: true)

### Configuration Objects
- `BusConfiguration` - Complete bus configuration with builder pattern
- `BusConfiguration.for_testing()` - Optimized for testing
- `BusConfiguration.for_production()` - Enterprise settings

---

## Testing

### Test Coverage
- **990+ test files** across multiple test suites
- **Constitutional compliance testing** with @pytest.mark.constitutional
- **MACI role separation** - 108 dedicated test files
- **Integration testing** with @pytest.mark.integration
- **Performance testing** with @pytest.mark.slow
- **Chaos testing** for resilience validation

### Key Test Areas
- Agent registration and lifecycle
- Message validation and routing
- Multi-tenant isolation enforcement
- Constitutional hash validation
- MACI role separation (Gödel bypass prevention)
- Policy evaluation (OPA and registry)
- Error handling and exception hierarchy
- Concurrent message processing
- Metering and metrics collection

---

## Notes

### Constitutional Hash
- **Hash**: `cdd01ef066bc6cf2`
- **Usage**: Appears in every message, validation, and exception
- **Purpose**: Cryptographic proof of constitutional compliance
- **Validation**: Constant-time comparison to prevent timing attacks

### Backward Compatibility
- `core.py` provides facade for refactored code
- `MessagePriority` enum deprecated in favor of `Priority`
- All public APIs maintain backward compatibility

### Production Readiness
- **Tested**: 990+ test files ensure reliability
- **Monitored**: Comprehensive metrics and logging
- **Secure**: Multi-layered validation and MACI enforcement
- **Scalable**: Async-first design with optional Kafka distribution
- **Documented**: Extensive docstrings and type hints

### Known Limitations
- Default registry is in-memory (not distributed)
- Policy caching has maximum size to prevent unbounded growth
- Kafka bus requires separate Kafka cluster setup
- OPA embedded mode requires OPA Python SDK installation

---

## Related Documentation

- **Enhanced Agent Bus**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/`
- **Deliberation Layer**: Integration with impact scoring and HITL approval
- **MACI Framework**: Role-based separation for Gödel bypass prevention
- **Constitutional Framework**: Overall governance principles and hash validation
- **Shared Services**: Circuit breakers, metrics, audit, crypto services
- **Microservices**: Policy registry, audit service, constraint generation
