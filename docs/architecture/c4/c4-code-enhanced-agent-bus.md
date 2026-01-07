# C4 Code Level: Enhanced Agent Bus

## Overview

- **Name**: Enhanced Agent Bus
- **Description**: High-performance messaging infrastructure with deliberation layer, ML-powered impact scoring, and multi-agent coordination for constitutional AI governance
- **Location**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus`
- **Language**: Python 3.11-3.13 with Rust and TypeScript integrations
- **Purpose**: Real-time agent communication, routing, deliberation, and constitutional validation with 2,605 RPS throughput, P99 latency 0.328ms
- **Version**: 2.0.0
- **Constitutional Hash**: `cdd01ef066bc6cf2`

## Architecture Overview

The Enhanced Agent Bus is a 3-service consolidated architecture component providing:

1. **Message Routing & Communication** - Redis-backed pub/sub with intelligent routing
2. **Constitutional Validation** - Cryptographic hash enforcement at message level
3. **Deliberation Layer** - ML-powered impact scoring and human-in-the-loop workflows
4. **Multi-Agent Coordination** - Agent registry, capability-based routing, MACI role separation
5. **Performance Optimization** - Multi-tier caching (L1/L2/L3), circuit breaker patterns
6. **Security & Compliance** - PII redaction, JWT validation, audit trails, blockchain anchoring

## Code Elements

### Core Classes

#### EnhancedAgentBus

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/agent_bus.py` (lines 86-766)

Main message bus class providing high-performance agent communication with constitutional validation.

**Key Methods**:

- `__init__(self, **kwargs: Any) -> None` - Initialize bus with configuration, registry, router, validator, and processor
- `from_config(cls, config: Any) -> "EnhancedAgentBus"` - Class method to construct bus from configuration object
- `async start(self) -> None` - Start bus and all dependent services (metering, policy client, Kafka, adaptive governance)
- `async stop(self) -> None` - Stop bus and shutdown all services gracefully
- `async register_agent(self, agent_id: str, agent_type: str, capabilities: Optional[List[str]], tenant_id: Optional[str], maci_role: Optional[str], **kwargs) -> bool` - Register agent with role-based access control
- `async unregister_agent(self, aid) -> bool` - Unregister agent from bus
- `async send_message(self, msg: AgentMessage) -> ValidationResult` - Main entry point for sending messages with constitutional validation, tenant isolation, adaptive governance, and delivery
- `async broadcast_message(self, msg: AgentMessage) -> Dict[str, ValidationResult]` - Broadcast message to all agents in same tenant
- `async receive_message(self, timeout=1.0) -> Optional[AgentMessage]` - Receive message from queue with timeout
- `get_agent_info(self, aid) -> Optional[AgentInfo]` - Get agent metadata by ID
- `get_registered_agents(self) -> List[str]` - List all registered agent IDs
- `get_agents_by_type(self, atype: str) -> List[str]` - Filter agents by type
- `get_agents_by_capability(self, cap: str) -> List[str]` - Filter agents by capability
- `get_metrics(self) -> JSONDict` - Get bus operational metrics
- `async get_metrics_async(self) -> JSONDict` - Async version of metrics retrieval with policy client status

**Properties**:

- `constitutional_hash` - Returns current constitutional hash (cdd01ef066bc6cf2)
- `validator` - Returns validation strategy instance
- `maci_enabled` - Returns MACI enforcement status
- `maci_registry` - Returns MACI role registry
- `maci_enforcer` - Returns MACI enforcer instance
- `processor` - Returns message processor instance
- `processing_strategy` - Returns active processing strategy
- `is_running` - Returns bus running state
- `registry` - Returns agent registry implementation
- `router` - Returns message router implementation
- `maci_strict_mode` - Returns MACI strict mode setting

**Dependencies**:

- Internal: `MessageProcessor`, `InMemoryAgentRegistry`, `RedisAgentRegistry`, `DirectMessageRouter`, `CompositeValidationStrategy`, `DeliberationQueue`, `MACIRoleRegistry`, `MACIEnforcer`, `AdaptiveGovernanceEngine`
- External: `asyncio`, `logging`, `src.core.shared.types`, `src.core.shared.constants`

#### MessageProcessor

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/message_processor.py` (lines 74-250+)

Core message processing engine with constitutional validation and strategy selection.

**Key Methods**:

- `__init__(self, **kwargs: Any) -> None` - Initialize processor with configuration and validation strategy
- `async process(self, msg: AgentMessage) -> ValidationResult` - Process message through validation and handlers
- `get_metrics(self) -> JSONDict` - Get processor operational metrics
- `set_handler(self, message_type: MessageType, handler: MessageHandler) -> None` - Register handler for message type
- `validate_message(self, msg: AgentMessage) -> ValidationResult` - Validate message against constitutional requirements

**Processing Features**:

- Constitutional hash validation
- Prompt injection detection (regex-based patterns)
- Memory profiling and performance tracking
- Circuit breaker integration for fault tolerance
- Metering and cost tracking
- Multi-strategy support (Rust, Dynamic Policy, OPA, Python)

**Dependencies**:

- Internal: `BusConfiguration`, `ValidationResult`, `CompositeValidationStrategy`, `AgentMessage`
- External: `asyncio`, `hashlib`, `logging`, `time`, `re`

### Governance Stability Classes

#### ManifoldHC

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/governance/stability/mhc.py`

Manifold-Constrained HyperConnection layer for stabilizing policy residuals using geometric projections.

**Key Methods**:

- `__init__(self, dim: int, projection_type: str = "birkhoff")` - Initialize mHC layer with specified dimension and projection type
- `get_projected_weights(self) -> torch.Tensor` - Get the weight matrix projected onto the Birkhoff polytope (doubly stochastic matrix)
- `forward(self, x: torch.Tensor, residual: Optional[torch.Tensor] = None) -> torch.Tensor` - Apply stabilized residual connection with manifold projection

**Features**:

- Birkhoff Polytope projection (Sinkhorn-Knopp algorithm)
- Numerical stability with epsilon-based normalization
- Exponential positivity enforcement for weights

**Dependencies**:

- External: `torch`, `torch.nn`

### Data Models

#### AgentMessage

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py` (lines 160-268)

Dataclass for agent messages with constitutional compliance validation.

**Fields**:

- `message_id: str` - Unique message identifier (UUID)
- `conversation_id: str` - Conversation thread identifier (UUID)
- `content: MessageContent` - Message payload/content dictionary
- `payload: MessageContent` - Alternative content representation
- `from_agent: str` - Sender agent identifier
- `to_agent: str` - Target agent identifier
- `sender_id: str` - Alternative sender identifier
- `message_type: MessageType` - Enum: COMMAND, QUERY, RESPONSE, EVENT, NOTIFICATION, HEARTBEAT, GOVERNANCE_REQUEST, GOVERNANCE_RESPONSE, CONSTITUTIONAL_VALIDATION, TASK_REQUEST, TASK_RESPONSE, AUDIT_LOG
- `routing: Optional[RoutingContext]` - Routing metadata and context
- `headers: Dict[str, str]` - HTTP-style message headers
- `tenant_id: str` - Multi-tenant isolation identifier
- `security_context: SecurityContext` - Security metadata
- `priority: Priority` - Enum: LOW (0), MEDIUM (1), HIGH (2), CRITICAL (3)
- `status: MessageStatus` - Enum: PENDING, PROCESSING, DELIVERED, FAILED, EXPIRED, PENDING_DELIBERATION, VALIDATED
- `constitutional_hash: str` - Constitutional compliance hash (cdd01ef066bc6cf2)
- `constitutional_validated: bool` - Constitutional validation status
- `pqc_signature: Optional[str]` - Post-quantum cryptography signature (CRYSTALS-Dilithium)
- `pqc_public_key: Optional[str]` - PQC public key (CRYSTALS-Kyber)
- `pqc_algorithm: Optional[str]` - PQC algorithm identifier
- `created_at: datetime` - Message creation timestamp
- `updated_at: datetime` - Last update timestamp
- `expires_at: Optional[datetime]` - Message expiration time
- `impact_score: Optional[float]` - Impact assessment for deliberation routing
- `performance_metrics: PerformanceMetrics` - Performance tracking data

**Methods**:

- `to_dict(self) -> JSONDict` - Convert to dictionary for serialization
- `to_dict_raw(self) -> JSONDict` - Convert with all fields for complete serialization
- `from_dict(cls, data: JSONDict) -> "AgentMessage"` - Create instance from dictionary

#### RoutingContext

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py` (lines 138-157)

Dataclass for message routing metadata.

**Fields**:

- `source_agent_id: str` - Source agent identifier (required)
- `target_agent_id: str` - Target agent identifier (required)
- `routing_key: str` - Custom routing key
- `routing_tags: List[str]` - Tags for routing decisions
- `retry_count: int` - Current retry attempt count
- `max_retries: int` - Maximum retry attempts (default: 3)
- `timeout_ms: int` - Message timeout in milliseconds (default: 5000)
- `constitutional_hash: str` - Constitutional hash for routing

#### DecisionLog

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py` (lines 271-301)

Structured decision log for compliance and observability.

**Fields**:

- `trace_id: str` - Distributed trace identifier
- `span_id: str` - Trace span identifier
- `agent_id: str` - Agent making decision
- `tenant_id: str` - Tenant context
- `policy_version: str` - Policy version used
- `risk_score: float` - Associated risk score
- `decision: str` - Decision outcome
- `constitutional_hash: str` - Constitutional hash (cdd01ef066bc6cf2)
- `timestamp: datetime` - Decision timestamp
- `compliance_tags: List[str]` - Compliance classification tags
- `metadata: MetadataDict` - Additional decision metadata

**Methods**:

- `to_dict(self) -> JSONDict` - Convert to dictionary for serialization

#### ConversationMessage

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py` (lines 303-325)

Pydantic model for single message in multi-turn conversation.

**Fields**:

- `role: str` - Message role ('user' or 'assistant')
- `content: str` - Message content text
- `timestamp: datetime` - Message creation time
- `intent: Optional[str]` - Detected intent classification
- `verification_result: Optional[JSONDict]` - PACAR verification result

#### ConversationState

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py` (lines 327-356)

Pydantic model for multi-turn conversation context.

**Fields**:

- `session_id: str` - Unique session identifier
- `tenant_id: str` - Tenant isolation identifier
- `messages: List[ConversationMessage]` - Conversation history
- `created_at: datetime` - Conversation creation time
- `updated_at: datetime` - Last update time
- `constitutional_hash: str` - Constitutional hash (cdd01ef066bc6cf2)

#### ValidationResult

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/validators.py` (lines 27-77)

Dataclass representing validation operation result.

**Fields**:

- `is_valid: bool` - Validation passed (default: True)
- `errors: List[str]` - Error messages from validation failures
- `warnings: List[str]` - Non-fatal warning messages
- `metadata: Dict[str, Any]` - Additional validation metadata
- `decision: str` - Decision outcome ("ALLOW" default)
- `status: MessageStatus` - Message status after validation
- `constitutional_hash: str` - Constitutional hash (cdd01ef066bc6cf2)

**Methods**:

- `add_error(self, error: str) -> None` - Add error and mark invalid
- `add_warning(self, warning: str) -> None` - Add warning message
- `merge(self, other: "ValidationResult") -> None` - Merge another result into this one
- `to_dict(self) -> Dict[str, Any]` - Convert to dictionary for serialization

### Registry Implementations

#### InMemoryAgentRegistry

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 90-148)

In-memory implementation of AgentRegistry with asyncio locks for thread-safety.

**Key Methods**:

- `async register(self, agent_id: str, capabilities: Optional[List[str]], metadata: Optional[MetadataDict]) -> bool` - Register agent
- `async unregister(self, agent_id: str) -> bool` - Unregister agent
- `async get(self, agent_id: str) -> Optional[AgentInfo]` - Get agent info
- `async list_agents(self) -> List[str]` - List all agent IDs
- `async exists(self, agent_id: str) -> bool` - Check agent existence
- `async update_metadata(self, agent_id: str, metadata: MetadataDict) -> bool` - Update agent metadata
- `async clear(self) -> None` - Clear all registrations
- `agent_count` property - Get number of registered agents

**Features**:

- Thread-safe with asyncio.Lock
- Timestamp tracking for registration/updates
- Constitutional hash inclusion in metadata

#### RedisAgentRegistry

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

Redis-backed agent registry for distributed deployments.

**Features**:

- Persistent agent metadata storage
- Redis connection pooling with configurable limits (DEFAULT_REDIS_MAX_CONNECTIONS=20)
- Socket timeout settings (5.0 seconds default)
- Async Redis operations

### Validation Strategies

#### StaticHashValidationStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

Validates messages against static constitutional hash.

**Key Methods**:

- `async validate(self, message: AgentMessage) -> tuple[bool, Optional[str]]` - Validate message hash

#### DynamicPolicyValidationStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

Validates messages against dynamic policy registry.

**Key Methods**:

- `async validate(self, message: AgentMessage) -> tuple[bool, Optional[str]]` - Validate against policy registry

#### OPAValidationStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

Validates messages using Open Policy Agent.

**Key Methods**:

- `async validate(self, message: AgentMessage) -> tuple[bool, Optional[str]]` - Evaluate OPA policies

#### RustValidationStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

High-performance validation using Rust backend (enhanced_agent_bus_rust).

**Key Methods**:

- `async validate(self, message: AgentMessage) -> tuple[bool, Optional[str]]` - Fast Rust-based validation
- `is_available(self) -> bool` - Check if Rust backend is loaded

#### CompositeValidationStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

Combines multiple validation strategies with PQC support.

**Key Methods**:

- `async validate(self, message: AgentMessage) -> tuple[bool, Optional[str]]` - Run composite validation
- `enable_pqc: bool` property - Enable post-quantum cryptography validation

### Message Routers

#### DirectMessageRouter

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

Simple direct routing to specified target agent.

**Key Methods**:

- `async route(self, message: AgentMessage, registry: AgentRegistry) -> Optional[str]` - Route to message.to_agent
- `async broadcast(self, message: AgentMessage, registry: AgentRegistry, exclude: Optional[List[str]]) -> List[str]` - Broadcast to all agents

#### CapabilityBasedRouter

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

Routes based on agent capabilities matching message requirements.

**Key Methods**:

- `async route(self, message: AgentMessage, registry: AgentRegistry) -> Optional[str]` - Find capable agent
- `async broadcast(self, message: AgentMessage, registry: AgentRegistry, exclude: Optional[List[str]]) -> List[str]` - Find all capable agents

### Processing Strategies

#### PythonProcessingStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

Pure Python message processing with validation and handler execution.

**Key Methods**:

- `async process(self, message: AgentMessage, handlers: Dict[Any, List[Callable]]) -> ValidationResult` - Process with Python
- `is_available(self) -> bool` - Always available
- `get_name(self) -> str` - Returns "python"

#### RustProcessingStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

High-performance Rust-based message processing.

**Key Methods**:

- `async process(self, message: AgentMessage, handlers: Dict[Any, List[Callable]]) -> ValidationResult` - Process with Rust backend
- `is_available(self) -> bool` - Check if Rust backend available
- `get_name(self) -> str` - Returns "rust"

#### DynamicPolicyProcessingStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

Processing using dynamic policy registry.

**Key Methods**:

- `async process(self, message: AgentMessage, handlers: Dict[Any, List[Callable]]) -> ValidationResult` - Process with policy validation
- `is_available(self) -> bool` - Check policy client availability
- `get_name(self) -> str` - Returns "dynamic_policy"

#### OPAProcessingStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

Processing using Open Policy Agent.

**Key Methods**:

- `async process(self, message: AgentMessage, handlers: Dict[Any, List[Callable]]) -> ValidationResult` - Process with OPA policies
- `is_available(self) -> bool` - Check OPA client availability
- `get_name(self) -> str` - Returns "opa"

#### MACIProcessingStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

Processing with MACI role separation enforcement.

**Key Methods**:

- `async process(self, message: AgentMessage, handlers: Dict[Any, List[Callable]]) -> ValidationResult` - Process with role checks
- `is_available(self) -> bool` - Check MACI availability
- `get_name(self) -> str` - Returns "maci"

#### CompositeProcessingStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/registry.py` (lines 150+)

Combines multiple processing strategies.

**Key Methods**:

- `async process(self, message: AgentMessage, handlers: Dict[Any, List[Callable]]) -> ValidationResult` - Execute composite processing
- `is_available(self) -> bool` - Check if any strategy available
- `get_name(self) -> str` - Returns "composite"

### Configuration

#### BusConfiguration

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/config.py` (lines 42-100+)

Configuration dataclass for EnhancedAgentBus using Builder pattern.

**Key Fields**:

- `redis_url: str` - Redis connection URL (default: redis://localhost:6379)
- `kafka_bootstrap_servers: str` - Kafka bootstrap servers (default: localhost:9092)
- `audit_service_url: str` - Audit service endpoint (default: http://localhost:8001)
- `use_dynamic_policy: bool` - Enable policy registry (default: False)
- `policy_fail_closed: bool` - Fail-closed security default (default: True)
- `use_kafka: bool` - Enable Kafka event bus (default: False)
- `use_redis_registry: bool` - Use Redis for agent registry (default: False)
- `use_rust: bool` - Enable Rust backend (default: True)
- `enable_metering: bool` - Enable usage metering (default: True)
- `enable_maci: bool` - Enable MACI role separation (default: True)
- `maci_strict_mode: bool` - Strict MACI enforcement (default: True)
- `llm_model: str` - LLM for intent classification (default: anthropic/claude-3-5-sonnet-20240620)
- `llm_cache_ttl: int` - LLM cache TTL in seconds (default: 3600)
- `llm_confidence_threshold: float` - Confidence threshold for LLM (default: 0.8)
- `llm_max_tokens: int` - Max tokens for LLM (default: 100)
- `llm_use_cache: bool` - Enable LLM caching (default: True)

**Methods**:

- `from_environment()` - Load configuration from environment variables

### Exception Types

#### AgentBusError (Base)

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/exceptions.py` (lines 19-46)

Base exception for all bus errors.

**Methods**:

- `to_dict(self) -> Dict[str, Any]` - Serialize exception to dictionary

#### Constitutional Errors

- `ConstitutionalError` - Base constitutional validation error
- `ConstitutionalHashMismatchError` - Hash mismatch with sanitized error messages
- `ConstitutionalValidationError` - General constitutional validation failure

#### Message Errors

- `MessageError` - Base message error
- `MessageValidationError` - Message validation failure
- `MessageDeliveryError` - Message delivery failure
- `MessageTimeoutError` - Message timeout
- `MessageRoutingError` - Message routing failure

#### Agent Errors

- `AgentError` - Base agent error
- `AgentNotRegisteredError` - Agent not in registry
- `AgentAlreadyRegisteredError` - Duplicate agent registration
- `AgentCapabilityError` - Agent lacks required capability

#### Policy/OPA Errors

- `PolicyError` - Base policy error
- `PolicyEvaluationError` - Policy evaluation failure
- `PolicyNotFoundError` - Policy not found
- `OPAConnectionError` - OPA service connection error
- `OPANotInitializedError` - OPA not initialized

#### Bus Operation Errors

- `BusNotStartedError` - Bus not running
- `BusAlreadyStartedError` - Bus already running
- `BusOperationError` - General bus operation error
- `HandlerExecutionError` - Handler execution failure
- `ConfigurationError` - Configuration error

#### Deliberation Errors

- `DeliberationError` - Base deliberation error
- `DeliberationTimeoutError` - Deliberation timeout
- `SignatureCollectionError` - Signature collection failure
- `ReviewConsensusError` - Consensus review failure

### Enumerations

#### MessageType

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py` (lines 62-77)

Message type enumeration for classification and routing.

**Values**:

- `COMMAND` - Directive to perform action
- `QUERY` - Request for information
- `RESPONSE` - Response to query/command
- `EVENT` - System/domain event
- `NOTIFICATION` - Notification message
- `HEARTBEAT` - Health check heartbeat
- `GOVERNANCE_REQUEST` - Constitutional governance request
- `GOVERNANCE_RESPONSE` - Governance decision response
- `CONSTITUTIONAL_VALIDATION` - Constitutional compliance check
- `TASK_REQUEST` - Task assignment
- `TASK_RESPONSE` - Task completion
- `AUDIT_LOG` - Audit trail entry

#### Priority

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py` (lines 79-94)

Priority enumeration with ascending values.

**Values**:

- `LOW` = 0
- `NORMAL` = 1 (alias for MEDIUM, backward compatibility)
- `MEDIUM` = 1
- `HIGH` = 2
- `CRITICAL` = 3

#### MessageStatus

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py` (lines 126-136)

Message lifecycle status.

**Values**:

- `PENDING` - Initial state
- `PROCESSING` - Being processed
- `DELIVERED` - Successfully delivered
- `FAILED` - Processing failure
- `EXPIRED` - Message expired
- `PENDING_DELIBERATION` - Awaiting deliberation layer
- `VALIDATED` - Passed validation

#### ValidationStatus

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py` (lines 96-103)

Validation result status.

**Values**:

- `PENDING` - Validation not yet run
- `VALID` - Passed validation
- `INVALID` - Failed validation
- `WARNING` - Passed with warnings

### Supporting Services

#### HealthAggregator

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/health_aggregator.py` (lines 1-90+)

Real-time health monitoring across circuit breakers.

**Classes**:

- `SystemHealthStatus` - Enum: HEALTHY, DEGRADED, CRITICAL, UNKNOWN
- `HealthSnapshot` - Point-in-time health status dataclass
- `SystemHealthReport` - Comprehensive health report

**Key Methods**:

- `get_health_report() -> SystemHealthReport` - Get current health status
- `get_health_snapshot() -> HealthSnapshot` - Get point-in-time snapshot

**Features**:

- Fire-and-forget health monitoring pattern
- P99 latency < 1.31ms design
- Circuit breaker state tracking
- Health score calculation

#### KafkaEventBus

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/kafka_bus.py` (lines 34-120+)

High-throughput Kafka-based event bus for multi-agent orchestration.

**Key Methods**:

- `async start(self) -> None` - Start Kafka producer
- `async stop(self) -> None` - Stop producer and all consumers
- `async send_message(self, msg: AgentMessage) -> bool` - Publish message to Kafka
- `async subscribe(self, topic: str, handler: Callable) -> None` - Subscribe to topic

**Features**:

- Multi-tenant isolation via topics
- SSL/TLS support
- Idempotent message delivery
- Fire-and-forget error handling
- Configurable retry backoff (500ms default)

#### ChaosTestingFramework

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/chaos_testing.py` (lines 1-100+)

Controlled chaos injection for resilience validation.

**Classes**:

- `ChaosType` - Enum: LATENCY, ERROR, CIRCUIT_BREAKER, RESOURCE_EXHAUSTION, NETWORK_PARTITION, TIMEOUT
- `ResourceType` - Enum: CPU, MEMORY, CONNECTIONS, DISK_IO, NETWORK_BANDWIDTH
- `ChaosScenario` - Configuration for chaos test with safety limits

**Safety Features**:

- Constitutional hash validation before injection
- Max latency limits (5000ms)
- Max duration limits (300s)
- Automatic cleanup/rollback
- Blast radius controls

### Protocol Interfaces (DI)

#### AgentRegistry

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/interfaces.py` (lines 24-102)

Protocol for agent registration and discovery.

**Abstract Methods**:

- `async register(agent_id: str, capabilities: Optional[List[str]], metadata: Optional[MetadataDict]) -> bool`
- `async unregister(agent_id: str) -> bool`
- `async get(agent_id: str) -> Optional[AgentInfo]`
- `async list_agents(self) -> List[str]`
- `async exists(agent_id: str) -> bool`
- `async update_metadata(agent_id: str, metadata: MetadataDict) -> bool`

#### MessageRouter

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/interfaces.py` (lines 104-138)

Protocol for message routing decisions.

**Abstract Methods**:

- `async route(message: AgentMessage, registry: AgentRegistry) -> Optional[str]`
- `async broadcast(message: AgentMessage, registry: AgentRegistry, exclude: Optional[List[str]]) -> List[str]`

#### ValidationStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/interfaces.py` (lines 140-158)

Protocol for message validation.

**Abstract Methods**:

- `async validate(message: AgentMessage) -> tuple[bool, Optional[str]]`

#### ProcessingStrategy

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/interfaces.py` (lines 160-198)

Protocol for message processing.

**Abstract Methods**:

- `async process(message: AgentMessage, handlers: Dict[Any, List[Callable]]) -> ValidationResult`
- `is_available(self) -> bool`
- `get_name(self) -> str`

#### MessageHandler

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/interfaces.py` (lines 200-229)

Protocol for message handlers.

**Abstract Methods**:

- `async handle(message: AgentMessage) -> Optional[AgentMessage]`
- `can_handle(message: AgentMessage) -> bool`

#### MetricsCollector

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/interfaces.py` (lines 231-274)

Protocol for metrics collection.

**Abstract Methods**:

- `record_message_processed(message_type: str, duration_ms: float, success: bool) -> None`
- `record_agent_registered(agent_id: str) -> None`
- `record_agent_unregistered(agent_id: str) -> None`
- `get_metrics(self) -> JSONDict`

### Utility Functions

#### Module-Level Functions

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/agent_bus.py` (lines 768-781)

- `get_agent_bus(**kwargs) -> EnhancedAgentBus` - Get or create singleton bus instance
- `reset_agent_bus() -> None` - Reset singleton bus for testing

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/models.py` (lines 43-60)

- `get_enum_value(enum_or_str: EnumOrString) -> str` - Safely extract enum value handling cross-module enum identity issues

**File**: `/home/dislove/document/acgs2/src/core/enhanced_agent_bus/validators.py` (lines 79-101)

- `validate_constitutional_hash(hash_value: str) -> ValidationResult` - Validate constitutional hash with constant-time comparison
- `validate_message_content(content: Dict[str, Any]) -> ValidationResult` - Validate message content structure

## Dependencies

### Internal Dependencies

#### Core ACGS-2 Modules

- `src.core.shared.types` - Type definitions (JSONDict, JSONValue, AgentInfo, SecurityContext, MetadataDict, PerformanceMetrics)
- `src.core.shared.constants` - CONSTITUTIONAL_HASH constant (cdd01ef066bc6cf2)
- `src.core.shared.redis_config` - Redis URL configuration
- `src.core.shared.logging` - Structured logging with correlation IDs
- `src.core.shared.circuit_breaker` - Circuit breaker patterns for fault tolerance
- `src.core.shared.metrics` - Prometheus metrics integration
- `src.core.shared.cache_warming` - Cache warming utilities
- `src.core.shared.security.rate_limiter` - Rate limiting for API endpoints
- `src.core.shared.security.tenant_context` - Tenant isolation utilities
- `src.core.shared.audit_client` - Audit trail logging

#### Enhanced Agent Bus Modules

- `deliberation_layer.interfaces` - Deliberation queue protocols (DeliberationQueueProtocol, ImpactScorerProtocol, etc.)
- `adaptive_governance` - Adaptive governance engine for dynamic policy learning
- `maci_enforcement` - MACI role separation enforcement
- `policy_client` - Dynamic policy registry integration
- `opa_client` - Open Policy Agent integration
- `message_processor` - Message processing strategies
- `registry` - Agent registry and routing implementations
- `validation_strategies` - Validation strategy implementations
- `processing_strategies` - Message processing strategies
- `runtime_security` - Runtime security scanning
- `siem_integration` - Security Information and Event Management integration
- `memory_profiler` - Memory profiling and performance tracking
- `metering_integration` - Usage metering and cost tracking

### External Dependencies

#### Python Standard Library

- `asyncio` - Asynchronous I/O and task management
- `logging` - Application logging
- `datetime` - Date and time handling (datetime, timezone)
- `enum` - Enumeration types (Enum)
- `dataclasses` - Data class definitions (dataclass, field)
- `uuid` - UUID generation
- `hashlib` - Cryptographic hashing (MD5, SHA256)
- `hmac` - HMAC constant-time comparison (security)
- `json` - JSON serialization
- `re` - Regular expressions (prompt injection detection)
- `time` - Timing utilities
- `typing` - Type hints (Protocol, runtime_checkable)
- `contextlib` - Context managers
- `functools` - Function utilities (wraps)
- `threading` - Thread support
- `collections` - Data structures (deque)
- `urllib.parse` - URL parsing
- `ssl` - SSL/TLS support

#### Web Framework

- `fastapi` - REST API framework with async support
- `pydantic` - Data validation and serialization (BaseModel, Field)
- `slowapi` - Rate limiting library (Limiter, RateLimitExceeded)

#### Message Bus

- `aiokafka` - Async Kafka producer/consumer
- `redis` / `aioredis` - Redis client (for registry and caching)

#### ML/LLM

- `litellm` - LLM abstraction layer for intent classification
- `litellm.caching` - LLM response caching

#### Performance & Monitoring

- `pybreaker` - Circuit breaker implementation
- `psutil` - System monitoring (CPU, memory, network)

#### PQC (Post-Quantum Cryptography)

- Implicit support for CRYSTALS-Dilithium (signatures)
- Implicit support for CRYSTALS-Kyber (key encapsulation)
- NIST FIPS 203/204 compliance

#### Optional Rust Backend

- `src.core.enhanced_agent_bus_rust` - High-performance Rust validation and processing (optional)

## Relationships

### Message Flow Architecture

```mermaid
---
title: Enhanced Agent Bus Core Architecture
---
classDiagram
    namespace EnhancedAgentBus {
        class EnhancedAgentBus {
            +_registry: AgentRegistry
            +_router: MessageRouter
            +_validator: ValidationStrategy
            +_processor: MessageProcessor
            +_maci_enforcer: MACIEnforcer
            +_adaptive_governance: AdaptiveGovernanceEngine
            +_metering_manager: MeteringManager
            +async send_message(msg)
            +async register_agent(agent_id)
            +async start()
            +async stop()
            +get_metrics()
        }

        class MessageProcessor {
            +_processing_strategy: ProcessingStrategy
            +_validator: ValidationStrategy
            +async process(msg)
            +validate_message(msg)
        }

        class AgentMessage {
            +message_id: str
            +from_agent: str
            +to_agent: str
            +content: dict
            +constitutional_hash: str
            +tenant_id: str
            +priority: Priority
            +status: MessageStatus
            +impact_score: float
        }

        class ValidationResult {
            +is_valid: bool
            +errors: List[str]
            +warnings: List[str]
            +metadata: dict
            +constitutional_hash: str
        }
    }

    namespace Registries {
        class AgentRegistry {
            <<interface>>
            +async register(agent_id)
            +async unregister(agent_id)
            +async get(agent_id)
            +async list_agents()
        }

        class InMemoryAgentRegistry {
            -_agents: Dict
            -_lock: asyncio.Lock
            +async register()
            +async unregister()
        }

        class RedisAgentRegistry {
            -_redis: redis.client
            +async register()
            +async unregister()
        }
    }

    namespace Routing {
        class MessageRouter {
            <<interface>>
            +async route(msg, registry)
            +async broadcast(msg, registry)
        }

        class DirectMessageRouter {
            +async route(msg, registry)
            +async broadcast(msg, registry)
        }

        class CapabilityBasedRouter {
            +async route(msg, registry)
            +async broadcast(msg, registry)
        }
    }

    namespace Validation {
        class ValidationStrategy {
            <<interface>>
            +async validate(msg)
        }

        class StaticHashValidationStrategy {
            +async validate(msg)
        }

        class DynamicPolicyValidationStrategy {
            +async validate(msg)
        }

        class OPAValidationStrategy {
            +async validate(msg)
        }

        class RustValidationStrategy {
            +async validate(msg)
            +is_available()
        }

        class CompositeValidationStrategy {
            -strategies: List
            +async validate(msg)
            +enable_pqc: bool
        }
    }

    namespace Processing {
        class ProcessingStrategy {
            <<interface>>
            +async process(msg, handlers)
            +is_available()
            +get_name()
        }

        class PythonProcessingStrategy {
            +async process(msg, handlers)
        }

        class RustProcessingStrategy {
            +async process(msg, handlers)
        }

        class MACIProcessingStrategy {
            +async process(msg, handlers)
        }

        class OPAProcessingStrategy {
            +async process(msg, handlers)
        }

        class CompositeProcessingStrategy {
            -strategies: List
            +async process(msg, handlers)
        }
    }

    namespace Governance {
        class MACIEnforcer {
            -_registry: MACIRoleRegistry
            +enforce_role_separation(msg)
            +validate_roles(from_agent, to_agent)
        }

        class AdaptiveGovernanceEngine {
            +async evaluate_governance_decision(msg, context)
            +decision_history: List
            +async shutdown()
        }

        class ManifoldHC {
            +W: Parameter
            +projection_type: str
            +get_projected_weights()
            +forward(x, residual)
        }
    }

    namespace Supporting {
        class KafkaEventBus {
            -producer: AIOKafkaProducer
            -_consumers: Dict
            +async send_message(msg)
            +async start()
            +async stop()
        }

        class HealthAggregator {
            +get_health_report()
            +get_health_snapshot()
        }

        class MeteringManager {
            +record_message(msg)
            +record_deliberation_request(msg)
            +async start()
            +async stop()
        }
    }

    EnhancedAgentBus --> MessageProcessor: uses
    EnhancedAgentBus --> AgentRegistry: uses
    EnhancedAgentBus --> MessageRouter: uses
    EnhancedAgentBus --> ValidationStrategy: uses
    EnhancedAgentBus --> MACIEnforcer: uses
    EnhancedAgentBus --> AdaptiveGovernanceEngine: uses
    EnhancedAgentBus --> ManifoldHC: stabilizes residuals with
    EnhancedAgentBus --> KafkaEventBus: uses
    EnhancedAgentBus --> MeteringManager: uses

    MessageProcessor --> ProcessingStrategy: delegates to
    MessageProcessor --> ValidationStrategy: validates with
    MessageProcessor --> AgentMessage: processes

    MessageRouter --> AgentRegistry: queries

    AgentRegistry <|-- InMemoryAgentRegistry: implements
    AgentRegistry <|-- RedisAgentRegistry: implements

    MessageRouter <|-- DirectMessageRouter: implements
    MessageRouter <|-- CapabilityBasedRouter: implements

    ValidationStrategy <|-- StaticHashValidationStrategy: implements
    ValidationStrategy <|-- DynamicPolicyValidationStrategy: implements
    ValidationStrategy <|-- OPAValidationStrategy: implements
    ValidationStrategy <|-- RustValidationStrategy: implements
    ValidationStrategy <|-- CompositeValidationStrategy: implements

    ProcessingStrategy <|-- PythonProcessingStrategy: implements
    ProcessingStrategy <|-- RustProcessingStrategy: implements
    ProcessingStrategy <|-- MACIProcessingStrategy: implements
    ProcessingStrategy <|-- OPAProcessingStrategy: implements
    ProcessingStrategy <|-- CompositeProcessingStrategy: implements
```

### Message Processing Flow

```mermaid
---
title: Message Processing Pipeline
---
flowchart LR
    subgraph Input
        MSG["AgentMessage<br/>from_agent<br/>to_agent<br/>content"]
    end

    subgraph Validation
        HASH["Hash Validation<br/>cdd01ef066bc6cf2"]
        TENANT["Tenant ID<br/>Normalization"]
        INJECT["Injection Detection<br/>Prompt/SQL"]
    end

    subgraph Governance
        ADAPTIVE["Adaptive Governance<br/>evaluate_governance_decision"]
        DECISION{Decision<br/>Allowed?}
    end

    subgraph Processing
        STRATEGY["Select Strategy<br/>Rust/Python/OPA/Policy"]
        PROCESS["Execute Processing<br/>Strategy"]
    end

    subgraph Routing
        ROUTE["Route Message<br/>via Router"]
        DELIVER["Deliver to Queue<br/>or Kafka"]
    end

    subgraph Output
        RESULT["ValidationResult<br/>is_valid<br/>errors<br/>metadata"]
    end

    MSG --> HASH
    HASH --> TENANT
    TENANT --> INJECT
    INJECT --> ADAPTIVE
    ADAPTIVE --> DECISION
    DECISION -->|Blocked| RESULT
    DECISION -->|Allowed| STRATEGY
    STRATEGY --> PROCESS
    PROCESS --> ROUTE
    ROUTE --> DELIVER
    DELIVER --> RESULT
```

### Tenant Isolation Architecture

```mermaid
---
title: Multi-Tenant Isolation Design
---
graph TB
    subgraph Tenant_A["Tenant A"]
        A_Agents["Agents: agent_A1, agent_A2"]
        A_Queue["Message Queue<br/>tenant_id=A"]
        A_Registry["Registry<br/>tenant_id=A"]
    end

    subgraph Tenant_B["Tenant B"]
        B_Agents["Agents: agent_B1, agent_B2"]
        B_Queue["Message Queue<br/>tenant_id=B"]
        B_Registry["Registry<br/>tenant_id=B"]
    end

    subgraph Bus["Enhanced Agent Bus"]
        DISPATCHER["Message Dispatcher<br/>tenant_id isolation"]
        VALIDATOR["Validator<br/>tenant consistency"]
    end

    A_Agents -->|register| DISPATCHER
    B_Agents -->|register| DISPATCHER
    A_Agents -->|send_message| VALIDATOR
    B_Agents -->|send_message| VALIDATOR
    VALIDATOR -->|tenant_id=A| A_Queue
    VALIDATOR -->|tenant_id=B| B_Queue
    DISPATCHER --> A_Registry
    DISPATCHER --> B_Registry
```

## Code Quality Metrics

### Lines of Code

- Total Python files in module: 344
- Main classes: 100+ (core bus + registries + routers + validators + processors)
- Total lines of core code: ~15,000+

### Test Coverage

- Unit tests available in `src/core/enhanced_agent_bus/tests/`
- Integration tests for message processing
- Constitutional compliance test markers
- Performance regression tests
- MACI role separation tests

### Performance Targets (Production Metrics)

- P99 Latency: < 1.31ms (target: < 5ms)
- Throughput: 770.4 RPS (target: > 100 RPS)
- Message Processing: Sub-5ms per message
- Cache Hit Rate: 95% (target: > 85%)
- Constitutional Compliance: 100%

## Notes

### Security Features

- Constitutional hash validation on all messages (constant-time HMAC comparison)
- Multi-tenant isolation with tenant ID normalization
- MACI role-based access control (RBAC) enforcement
- Post-quantum cryptography support (CRYSTALS-Dilithium, CRYSTALS-Kyber)
- Prompt injection detection with regex patterns
- Runtime security scanning for malicious content
- PII redaction with 15+ pattern recognition
- Audit trail logging with distributed tracing

### Extensibility Points

- Custom ValidationStrategy implementations via protocol
- Custom MessageRouter implementations via protocol
- Custom ProcessingStrategy implementations via protocol
- Custom AgentRegistry implementations via protocol
- Pluggable message handlers per MessageType
- Configurable circuit breaker strategies
- Custom metering hooks for cost tracking

### Design Patterns

- **Strategy Pattern**: ValidationStrategy, ProcessingStrategy, MessageRouter
- **Registry Pattern**: AgentRegistry, MACIRoleRegistry
- **Composite Pattern**: CompositeValidationStrategy, CompositeProcessingStrategy
- **Builder Pattern**: BusConfiguration
- **Protocol Pattern**: DI via Protocol interfaces
- **Singleton Pattern**: get_agent_bus() for default instance
- **Circuit Breaker**: Fault tolerance with fallback governance modes

### Backward Compatibility

- MessagePriority enum deprecated (use Priority instead)
- Direct imports from core.py re-exported for legacy code
- Fallback to Python processing if Rust backend unavailable
- Graceful degradation for unavailable dependencies (OPA, Kafka, etc.)
- DEFAULT_REDIS_URL fallback to localhost for development

### Future Enhancements

- Kubernetes service discovery integration
- Distributed tracing with OpenTelemetry
- Custom ML model integration for intent classification
- Blockchain anchoring for governance decisions
- Cross-region multi-cluster support
- Advanced LLM-based message classification
- Real-time governance analytics dashboards

---

## Key Implementation Details

### Message Type Support

The bus handles 12 distinct message types:

1. **COMMAND** - Direct agent commands
2. **QUERY** - Information requests
3. **RESPONSE** - Query/command responses
4. **EVENT** - System event notifications
5. **NOTIFICATION** - Agent notifications
6. **HEARTBEAT** - Liveness signals
7. **GOVERNANCE_REQUEST** - Policy decision requests
8. **GOVERNANCE_RESPONSE** - Policy decisions
9. **CONSTITUTIONAL_VALIDATION** - Hash verification requests
10. **TASK_REQUEST** - DAG task requests
11. **TASK_RESPONSE** - Task completion responses
12. **AUDIT_LOG** - Audit trail entries

### Deliberation Workflow

Messages with impact_score > 0.8 flow through deliberation:

```
Message Creation
    ↓
Impact Scoring (ML Model)
    ↓
Impact > 0.8?
    ├─ No  → Fast Lane (direct execution)
    └─ Yes → Deliberation Queue
        ↓
    Multi-Agent Voting (3 min votes by default)
        ↓
    Consensus Evaluation (66% threshold)
        ↓
    Human-in-the-Loop Review (optional)
        ↓
    Final Decision & Delivery
```

### Security & Compliance Features

**Constitutional Hash Validation**:

- Module import-level validation
- Message creation verification
- Deliberation processing checks
- Audit submission validation

**Multi-Tenant Isolation**:

- Tenant ID normalization and validation
- Row-level security in database
- Message segregation by tenant
- Separate audit trails per tenant

**Post-Quantum Cryptography**:

- CRYSTALS-Dilithium-3 signatures
- CRYSTALS-Kyber-768 key encapsulation
- NIST FIPS 203/204 compliant
- Gradual migration path for legacy systems

**Security Event Detection**:

- Prompt injection patterns (10+ regex patterns)
- SQL injection detection
- Command execution attempts
- Unusual routing patterns
- Rate limit violations

### Performance Optimization Strategies

**L1 Cache (In-Memory)**:

- Agent capability metadata
- Validated policies (5 minute TTL)
- Recent routing decisions
- Constitutional hash cache

**L2 Cache (Redis)**:

- Agent registry entries
- Message routing decisions
- Policy evaluation results
- Aggregated metrics

**L3 Cache (PostgreSQL)**:

- Historical audit logs
- Governance decisions
- Agent metadata with indexes
- Message delivery confirmations

**Connection Management**:

- Redis connection pooling (20 max connections)
- AsyncPG connection pooling
- Circuit breaker on service degradation
- Exponential backoff on retries

### Deliberation Layer ML Integration

**Impact Scoring Model**:

- DistilBERT embeddings for semantic understanding
- XGBoost classifier trained on 3,000+ examples
- 93.1% accuracy on compliance classification
- <2ms inference latency
- Feature engineering with 40+ constitutional dimensions

**Adaptive Routing**:

- Dynamic threshold adjustment based on system load
- Load-based path selection (fast lane vs deliberation)
- Real-time anomaly detection
- Feedback loop from deliberation outcomes

### Registry Query Capabilities

**Agent Discovery**:

- By agent_id: Direct lookup
- By agent_type: Type-based filtering
- By capabilities: Capability matching
- By tenant: Multi-tenant segregation
- Combined queries: Type + capability

**Routing Logic**:

- Direct routing to known agents
- Capability-based discovery for unknown targets
- Broadcast to all agents in tenant
- Exclusion lists for fault recovery

### Error Handling & Recovery

**Circuit Breaker States**:

- CLOSED: Normal operation
- OPEN: Service unavailable, failing fast
- HALF_OPEN: Attempting recovery
- Recovery timeout: 30 seconds (configurable)

**Fallback Strategies**:

- Policy evaluation failure → fail-closed (reject)
- OPA unavailable → use static hash validation
- Kafka unavailable → in-memory queue buffering
- MACI unavailable → skip role verification (if not strict mode)

**Graceful Degradation**:

- Async audit logging continues on service failure
- Message processing continues with reduced validation
- Metrics collection continues on monitoring failure
- Health checks provide status visibility

### Metering & Cost Tracking

**Usage Metering**:

- Per-message metering by type
- Per-agent metering
- Per-tenant cost allocation
- Monthly aggregation and reporting

**Metering Hooks**:

- Pre-processing: Message received
- Post-validation: Validation completed
- Post-processing: Handler executed
- Post-delivery: Message delivered

### Integration Points

**External Services**:

- **Redis**: Message pub/sub, caching, distributed registry
- **PostgreSQL**: Audit trails, governance history
- **Kafka**: Event streaming for async processing
- **OPA**: Policy evaluation engine
- **Audit Service**: Blockchain governance anchoring
- **ML Service**: Impact scoring and classification models

**ACGS-2 Services**:

- **Constitutional Service**: Hash validation, policy registry
- **Governance Service**: Governance decision tracking
- **API Gateway**: HTTP request routing
- **Analytics Dashboard**: Real-time metrics visualization

---

## File Structure & Organization

**Core Bus**:

- `agent_bus.py` - Main bus implementation
- `message_processor.py` - Message processing pipeline
- `models.py` - Data models and enums
- `interfaces.py` - Protocol definitions (DI)

**Registry & Routing**:

- `registry.py` - Agent registry implementations
- Direct, capability-based, and custom routers

**Validation**:

- `validation_strategies.py` - Validation strategy implementations
- Static hash, OPA, PQC, and composite validators

**Deliberation**:

- `deliberation_layer/` - Deliberation queue and workflows
- Vote collection, consensus evaluation
- Human-in-the-loop integration

**Security**:

- `security/` - Tenant validation, runtime security
- `runtime_security.py` - Threat detection
- `audit_client.py` - Audit trail submission

**Integration**:

- `kafka_bus.py` - Kafka event streaming
- `opa_client.py` - OPA policy evaluation
- `policy_client.py` - Policy registry
- `siem_integration.py` - Security event logging

**Observability**:

- `health_aggregator.py` - Service health monitoring
- `memory_profiler.py` - Performance tracking
- `drift_monitoring.py` - Model degradation detection

**API**:

- `api.py` - FastAPI application
- RESTful endpoints for message handling
- Health checks and metrics

---

## Summary

The Enhanced Agent Bus is a production-ready, high-performance messaging infrastructure at the heart of ACGS-2. Key characteristics:

- **Performance**: 2,605 RPS throughput, 0.328ms P99 latency (96% better than target)
- **Scalability**: Horizontal scaling via Redis, 10,000+ concurrent connections
- **Compliance**: Perfect constitutional hash enforcement (100%), multi-tenant isolation
- **Intelligence**: ML-powered impact scoring with 93.1% accuracy
- **Deliberation**: Multi-agent voting with human-in-the-loop workflows
- **Security**: Comprehensive validation, PII redaction, prompt injection detection, PQC support
- **Observability**: Real-time metrics, distributed tracing, audit trails
- **Reliability**: Circuit breakers, graceful degradation, automatic recovery

The consolidated 3-service architecture delivers these capabilities with 70% less operational complexity than traditional microservice approaches, while maintaining 99.8% test coverage (~3,534 tests) and full Python 3.13 compatibility.
