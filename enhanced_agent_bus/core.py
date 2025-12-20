"""
ACGS-2 Enhanced Agent Bus - Unified Core Implementation
Constitutional Hash: cdd01ef066bc6cf2

High-performance agent communication with constitutional compliance.
Supports both Rust backend and dynamic policy registry.
Instrumented with Prometheus metrics for observability.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

# Import Prometheus metrics with fallback
try:
    from shared.metrics import (
        MESSAGE_PROCESSING_DURATION,
        MESSAGES_TOTAL,
        MESSAGE_QUEUE_DEPTH,
        CONSTITUTIONAL_VALIDATIONS_TOTAL,
        CONSTITUTIONAL_VIOLATIONS_TOTAL,
        CONSTITUTIONAL_VALIDATION_DURATION,
        set_service_info,
    )
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False

# Import OpenTelemetry with fallback
try:
    from opentelemetry import trace, metrics
    from opentelemetry.trace import Status, StatusCode
    OTEL_ENABLED = True
    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)
    
    # Define OTel metrics
    DECISION_COUNTER = meter.create_counter(
        "acgs2.decisions.total",
        description="Total number of agent decisions",
        unit="1"
    )
except ImportError:
    OTEL_ENABLED = False
    tracer = None
    meter = None

# Import circuit breaker with fallback
try:
    from shared.circuit_breaker import (
        get_circuit_breaker,
        with_circuit_breaker,
        circuit_breaker_health_check,
        initialize_core_circuit_breakers,
        CircuitBreakerConfig,
    )
    CIRCUIT_BREAKER_ENABLED = True
except ImportError:
    CIRCUIT_BREAKER_ENABLED = False

try:
    from .models import (
        AgentMessage,
        MessageType,
        MessagePriority,
        MessageStatus,
        CONSTITUTIONAL_HASH,
        DecisionLog,
    )
    from .validators import ValidationResult
    from .exceptions import (
        AgentNotRegisteredError,
        AgentAlreadyRegisteredError,
        BusNotStartedError,
        ConstitutionalHashMismatchError,
        MessageDeliveryError,
    )
    from .interfaces import AgentRegistry, MessageRouter, ValidationStrategy, ProcessingStrategy
    from .registry import (
        InMemoryAgentRegistry,
        DirectMessageRouter,
        ConstitutionalValidationStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
        DynamicPolicyProcessingStrategy,
    )
except ImportError:
    # Fallback for direct execution or testing
    from models import (  # type: ignore
        AgentMessage,
        MessageType,
        MessagePriority,
        MessageStatus,
        CONSTITUTIONAL_HASH,
        DecisionLog,
    )
    from validators import ValidationResult  # type: ignore
    from exceptions import (  # type: ignore
        AgentNotRegisteredError,
        AgentAlreadyRegisteredError,
        BusNotStartedError,
        ConstitutionalHashMismatchError,
        MessageDeliveryError,
    )
    from interfaces import AgentRegistry, MessageRouter, ValidationStrategy, ProcessingStrategy  # type: ignore
    from registry import (  # type: ignore
        InMemoryAgentRegistry,
        DirectMessageRouter,
        ConstitutionalValidationStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
        DynamicPolicyProcessingStrategy,
    )

# Import centralized Redis config with fallback
try:
    from shared.redis_config import get_redis_url
    DEFAULT_REDIS_URL = get_redis_url()
except ImportError:
    DEFAULT_REDIS_URL = "redis://localhost:6379"

# Import policy client for dynamic validation (optional)
try:
    from .policy_client import get_policy_client, PolicyClient
    POLICY_CLIENT_AVAILABLE = True
except ImportError:
    POLICY_CLIENT_AVAILABLE = False
    PolicyClient = None  # type: ignore

    def get_policy_client():
        return None

logger = logging.getLogger(__name__)

# Import Rust implementation for high-performance processing
try:
    import enhanced_agent_bus as rust_bus
    USE_RUST = True
    logger.info("Rust implementation loaded successfully")
except ImportError:
    USE_RUST = False
    rust_bus = None
    logger.info("Rust implementation not available, using Python implementation")


class MessageProcessor:
    """Processes messages with constitutional validation.

    This class handles the validation and processing of agent messages, supporting
    multiple execution modes including a high-performance Rust backend, dynamic
    policy validation via a policy registry, and a standard Python fallback with
    static hash validation.

    Supports dependency injection of processing strategies for testability and
    customization. If no strategy is provided, auto-selects based on configuration.

    Attributes:
        constitutional_hash (str): The expected constitutional hash for validation.
        processed_count (int): Total number of successfully processed messages.
        failed_count (int): Total number of failed processing attempts.
    """

    def __init__(
        self,
        use_dynamic_policy: bool = False,
        # Dependency injection parameter
        processing_strategy: Optional["ProcessingStrategy"] = None,
    ):
        """Initializes the message processor.

        Args:
            use_dynamic_policy (bool): If True, use dynamic policy registry for validation
                instead of static constitutional hash. Defaults to False.
            processing_strategy (Optional[ProcessingStrategy]): Optional custom processing
                strategy. If not provided, auto-selects based on configuration.
        """
        self._use_dynamic_policy = use_dynamic_policy and POLICY_CLIENT_AVAILABLE
        self._handlers: Dict[MessageType, List[Callable]] = {}
        self._processed_count = 0
        self._failed_count = 0

        # Initialize Rust processor if available (for backward compatibility)
        if USE_RUST and rust_bus is not None:
            try:
                self._rust_processor = rust_bus.MessageProcessor()
                logger.debug("Rust MessageProcessor initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Rust processor: {e}")
                self._rust_processor = None
        else:
            self._rust_processor = None

        # Initialize policy client if using dynamic validation (for backward compatibility)
        if self._use_dynamic_policy:
            self._policy_client = get_policy_client()
        else:
            self._policy_client = None

        self.constitutional_hash = CONSTITUTIONAL_HASH

        # Dependency injection: use provided strategy or auto-select
        if processing_strategy is not None:
            self._processing_strategy = processing_strategy
        else:
            self._processing_strategy = self._auto_select_strategy()

    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Register a message handler for a specific message type."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)
        logger.debug(f"Handler registered for message type: {message_type}")

    def unregister_handler(self, message_type: MessageType, handler: Callable) -> bool:
        """Unregister a message handler. Returns True if handler was found and removed."""
        if message_type in self._handlers and handler in self._handlers[message_type]:
            self._handlers[message_type].remove(handler)
            return True
        return False

    def _auto_select_strategy(self) -> "ProcessingStrategy":
        """Auto-select the appropriate processing strategy based on configuration.

        Selection order:
        1. Rust strategy if Rust backend is available and not using dynamic policy
        2. Dynamic policy strategy if using dynamic policy and policy client available
        3. Python strategy as default fallback

        Returns:
            ProcessingStrategy: The selected strategy instance
        """
        # Try Rust strategy first (highest performance)
        if self._rust_processor is not None and not self._use_dynamic_policy:
            # Pass Rust components to avoid circular import in strategy
            rust_strategy = RustProcessingStrategy(
                rust_processor=self._rust_processor,
                rust_bus=rust_bus
            )
            if rust_strategy.is_available():
                logger.debug("Auto-selected Rust processing strategy")
                return rust_strategy

        # Try dynamic policy strategy
        if self._use_dynamic_policy and self._policy_client is not None:
            policy_strategy = DynamicPolicyProcessingStrategy(self._policy_client)
            if policy_strategy.is_available():
                logger.debug("Auto-selected dynamic policy processing strategy")
                return policy_strategy

        # Default to Python strategy
        logger.debug("Auto-selected Python processing strategy")
        return PythonProcessingStrategy(metrics_enabled=METRICS_ENABLED)

    async def process(self, message: AgentMessage) -> ValidationResult:
        """
        Process a message through validation and registered handlers.

        Processing flow:
        1. Validate constitutional compliance (static hash or dynamic policy)
        2. Execute registered handlers for the message type
        3. Update message status and metrics
        """
        if OTEL_ENABLED and tracer:
            with tracer.start_as_current_span("process_message") as span:
                span.set_attribute("agent.id", message.from_agent)
                span.set_attribute("tenant.id", message.tenant_id)
                span.set_attribute("message.type", message.message_type.value)
                span.set_attribute("constitutional.hash", message.constitutional_hash)

                result = await self._do_process(message)

                span.set_attribute("decision.valid", result.is_valid)
                if not result.is_valid:
                    span.set_status(Status(StatusCode.ERROR, ", ".join(result.errors)))
                
                # Record decision metric
                DECISION_COUNTER.add(1, {
                    "tenant_id": message.tenant_id,
                    "decision": "ALLOW" if result.is_valid else "DENY",
                    "message_type": message.message_type.value
                })

                # Create structured decision log
                self._log_decision(message, result, span)
                
                return result
        else:
            return await self._do_process(message)

    async def _do_process(self, message: AgentMessage) -> ValidationResult:
        """Internal processing logic using strategy pattern.

        Delegates to the configured processing strategy for validation and
        handler execution. Updates processed/failed counts based on result.
        """
        result = await self._processing_strategy.process(message, self._handlers)

        # Update counts based on result
        if result.is_valid:
            self._processed_count += 1
        else:
            self._failed_count += 1

        return result

    def _log_decision(self, message: AgentMessage, result: ValidationResult, span: Any) -> None:
        """Log structured decision for compliance."""
        span_context = span.get_span_context()
        trace_id = format(span_context.trace_id, '032x') if span_context else "unknown"
        span_id = format(span_context.span_id, '016x') if span_context else "unknown"

        decision_log = DecisionLog(
            trace_id=trace_id,
            span_id=span_id,
            agent_id=message.from_agent,
            tenant_id=message.tenant_id,
            policy_version=message.security_context.get("policy_version", "v1.0.0"),
            risk_score=message.impact_score or 0.0,
            decision="ALLOW" if result.is_valid else "DENY",
            compliance_tags=self._get_compliance_tags(message, result)
        )
        
        # In a real implementation, this would go to an OTel Logger or a specialized audit service
        logger.info(f"DECISION_LOG: {json.dumps(decision_log.to_dict())}")

    def _get_compliance_tags(self, message: AgentMessage, result: ValidationResult) -> List[str]:
        """Map decision to compliance tags (EU AI Act, NIST RMF)."""
        tags = []
        if message.impact_score and message.impact_score >= 0.8:
            tags.append("eu-ai-act-high-risk")
            tags.append("nist-rmf-high-impact")
        
        if not result.is_valid:
            tags.append("constitutional-violation")
        
        return tags

    async def _process_rust(self, message: AgentMessage) -> ValidationResult:
        """Process using Rust backend for maximum performance."""
        try:
            # Convert Python message to Rust format
            rust_message = self._convert_to_rust_message(message)

            # Process with Rust
            rust_result = await asyncio.to_thread(
                self._rust_processor.process, rust_message
            )

            # Convert result back to Python
            result = self._convert_from_rust_result(rust_result)

            if result.is_valid:
                # Run Python handlers (Rust doesn't support Python callbacks)
                await self._run_handlers(message)
                message.status = MessageStatus.DELIVERED
                self._processed_count += 1
            else:
                message.status = MessageStatus.FAILED
                self._failed_count += 1

            return result

        except Exception as e:
            logger.error(f"Rust processing failed, falling back to Python: {e}")
            return await self._process_python(message)

    async def _process_with_policy(self, message: AgentMessage) -> ValidationResult:
        """Process with dynamic policy registry validation."""
        try:
            # Dynamic constitutional validation
            validation_result = await self._policy_client.validate_message_signature(message)

            if not validation_result.is_valid:
                message.status = MessageStatus.FAILED
                self._failed_count += 1
                return validation_result

            # Continue with handler execution
            return await self._execute_handlers(message)

        except Exception as e:
            logger.error(f"Policy validation failed: {e}")
            message.status = MessageStatus.FAILED
            self._failed_count += 1
            return ValidationResult(
                is_valid=False,
                errors=[f"Policy validation error: {e}"],
            )

    async def _process_python(self, message: AgentMessage) -> ValidationResult:
        """Standard Python implementation with static hash validation."""
        validation_start = time.perf_counter()

        # Validate constitutional hash
        if message.constitutional_hash != CONSTITUTIONAL_HASH:
            message.status = MessageStatus.FAILED
            self._failed_count += 1

            # Record metrics
            if METRICS_ENABLED:
                validation_duration = time.perf_counter() - validation_start
                CONSTITUTIONAL_VALIDATION_DURATION.labels(
                    service='enhanced_agent_bus'
                ).observe(validation_duration)
                CONSTITUTIONAL_VALIDATIONS_TOTAL.labels(
                    service='enhanced_agent_bus', result='failure'
                ).inc()
                CONSTITUTIONAL_VIOLATIONS_TOTAL.labels(
                    service='enhanced_agent_bus', violation_type='hash_mismatch'
                ).inc()

            return ValidationResult(
                is_valid=False,
                errors=["Constitutional hash mismatch"],
            )

        # Record successful validation
        if METRICS_ENABLED:
            validation_duration = time.perf_counter() - validation_start
            CONSTITUTIONAL_VALIDATION_DURATION.labels(
                service='enhanced_agent_bus'
            ).observe(validation_duration)
            CONSTITUTIONAL_VALIDATIONS_TOTAL.labels(
                service='enhanced_agent_bus', result='success'
            ).inc()

        return await self._execute_handlers(message)

    async def _execute_handlers(self, message: AgentMessage) -> ValidationResult:
        """Execute registered handlers for the message."""
        message.status = MessageStatus.PROCESSING
        message.updated_at = datetime.now(timezone.utc)
        processing_start = time.perf_counter()

        # Get message type and priority for metrics
        msg_type = (
            message.message_type.value
            if hasattr(message.message_type, 'value')
            else str(message.message_type)
        )
        priority = (
            message.priority.value
            if hasattr(message.priority, 'value')
            else str(message.priority)
        )

        try:
            await self._run_handlers(message)

            message.status = MessageStatus.DELIVERED
            message.updated_at = datetime.now(timezone.utc)
            self._processed_count += 1

            # Record success metrics
            if METRICS_ENABLED:
                processing_duration = time.perf_counter() - processing_start
                MESSAGE_PROCESSING_DURATION.labels(
                    message_type=msg_type, priority=priority
                ).observe(processing_duration)
                MESSAGES_TOTAL.labels(
                    message_type=msg_type, priority=priority, status='success'
                ).inc()

            return ValidationResult(is_valid=True)

        except asyncio.CancelledError:
            # Re-raise cancellation - must not be suppressed
            raise
        except (TypeError, ValueError, AttributeError) as e:
            message.status = MessageStatus.FAILED
            self._failed_count += 1
            logger.error(f"Handler error: {type(e).__name__}: {e}")

            # Record error metrics
            if METRICS_ENABLED:
                processing_duration = time.perf_counter() - processing_start
                MESSAGE_PROCESSING_DURATION.labels(
                    message_type=msg_type, priority=priority
                ).observe(processing_duration)
                MESSAGES_TOTAL.labels(
                    message_type=msg_type, priority=priority, status='error'
                ).inc()

            return ValidationResult(
                is_valid=False,
                errors=[f"Handler error: {type(e).__name__}: {e}"],
            )
        except RuntimeError as e:
            message.status = MessageStatus.FAILED
            self._failed_count += 1
            logger.error(f"Runtime error in handler: {e}")

            # Record error metrics
            if METRICS_ENABLED:
                processing_duration = time.perf_counter() - processing_start
                MESSAGE_PROCESSING_DURATION.labels(
                    message_type=msg_type, priority=priority
                ).observe(processing_duration)
                MESSAGES_TOTAL.labels(
                    message_type=msg_type, priority=priority, status='error'
                ).inc()

            return ValidationResult(
                is_valid=False,
                errors=[f"Runtime error: {e}"],
            )

    async def _run_handlers(self, message: AgentMessage) -> None:
        """Run all registered handlers for the message type."""
        handlers = self._handlers.get(message.message_type, [])
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)

    def _convert_to_rust_message(self, message: AgentMessage) -> Any:
        """Convert Python AgentMessage to Rust AgentMessage."""
        rust_msg = rust_bus.AgentMessage()  # type: ignore
        rust_msg.message_id = message.message_id
        rust_msg.conversation_id = message.conversation_id
        rust_msg.content = {k: str(v) for k, v in message.content.items()}
        rust_msg.payload = {k: str(v) for k, v in message.payload.items()}
        rust_msg.from_agent = message.from_agent
        rust_msg.to_agent = message.to_agent
        rust_msg.sender_id = message.sender_id
        rust_msg.message_type = message.message_type.name
        rust_msg.tenant_id = message.tenant_id
        rust_msg.priority = message.priority.name if hasattr(message.priority, "name") else str(message.priority)
        rust_msg.status = message.status.name
        rust_msg.constitutional_hash = message.constitutional_hash
        rust_msg.constitutional_validated = message.constitutional_validated
        rust_msg.created_at = message.created_at.isoformat()
        rust_msg.updated_at = message.updated_at.isoformat()
        return rust_msg

    def _convert_from_rust_result(self, rust_result: Any) -> ValidationResult:
        """Convert Rust ValidationResult to Python ValidationResult."""
        return ValidationResult(
            is_valid=rust_result.is_valid,
            errors=list(rust_result.errors) if hasattr(rust_result, 'errors') else [],
            warnings=list(rust_result.warnings) if hasattr(rust_result, 'warnings') else [],
            metadata=dict(rust_result.metadata) if hasattr(rust_result, 'metadata') else {},
            constitutional_hash=getattr(rust_result, 'constitutional_hash', CONSTITUTIONAL_HASH),
        )

    @property
    def processed_count(self) -> int:
        """Get count of successfully processed messages."""
        return self._processed_count

    @property
    def failed_count(self) -> int:
        """Get count of failed message processing attempts."""
        return self._failed_count

    def get_metrics(self) -> Dict[str, Any]:
        """Get processor metrics."""
        return {
            "processed_count": self._processed_count,
            "failed_count": self._failed_count,
            "handler_count": sum(len(h) for h in self._handlers.values()),
            "rust_enabled": self._rust_processor is not None,
            "dynamic_policy_enabled": self._use_dynamic_policy,
            "processing_strategy": self._processing_strategy.get_name(),
        }

    @property
    def processing_strategy(self) -> "ProcessingStrategy":
        """Get the processing strategy (DI component)."""
        return self._processing_strategy


class EnhancedAgentBus:
    """
    Enhanced agent communication bus with constitutional compliance.

    Provides:
    - Agent registration and discovery
    - Message routing with constitutional validation
    - Metrics and health monitoring
    - Optional Rust backend for high performance
    - Optional dynamic policy registry integration
    - Dependency injection support for testability

    Dependency Injection:
        The bus supports optional injection of registry, router, and validator
        implementations. If not provided, defaults are used for backward compatibility.

        Example:
            # Using custom registry
            custom_registry = RedisAgentRegistry(redis_url)
            bus = EnhancedAgentBus(registry=custom_registry)

            # Using all defaults (backward compatible)
            bus = EnhancedAgentBus()
    """

    def __init__(
        self,
        redis_url: str = DEFAULT_REDIS_URL,
        use_dynamic_policy: bool = False,
        use_kafka: bool = False,
        kafka_bootstrap_servers: str = "localhost:9092",
        # Dependency injection parameters
        registry: Optional[AgentRegistry] = None,
        router: Optional[MessageRouter] = None,
        validator: Optional[ValidationStrategy] = None,
        processor: Optional["MessageProcessor"] = None,
    ):
        """
        Initialize the Enhanced Agent Bus.

        Args:
            redis_url: Redis connection URL for message queuing
            use_dynamic_policy: Use dynamic policy registry instead of static hash
            use_kafka: Use Kafka as the event bus instead of Redis/Local queue
            kafka_bootstrap_servers: Kafka bootstrap servers
            registry: Optional custom AgentRegistry implementation
            router: Optional custom MessageRouter implementation
            validator: Optional custom ValidationStrategy implementation
            processor: Optional custom MessageProcessor instance
        """
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self.redis_url = redis_url
        self._use_dynamic_policy = use_dynamic_policy and POLICY_CLIENT_AVAILABLE
        self._use_kafka = use_kafka

        # Dependency injection with defaults for backward compatibility
        self._registry: AgentRegistry = registry or InMemoryAgentRegistry()
        self._router: MessageRouter = router or DirectMessageRouter()
        self._validator: ValidationStrategy = validator or ConstitutionalValidationStrategy()

        # Legacy dict for backward compatibility (delegates to registry)
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._processor = processor or MessageProcessor(use_dynamic_policy=use_dynamic_policy)
        self._running = False

        # Initialize Kafka bus if enabled
        if self._use_kafka:
            from .kafka_bus import KafkaEventBus
            self._kafka_bus = KafkaEventBus(bootstrap_servers=kafka_bootstrap_servers)
        else:
            self._kafka_bus = None

        # Initialize policy client if using dynamic validation
        if self._use_dynamic_policy:
            self._policy_client = get_policy_client()
        else:
            self._policy_client = None

        # Initialize circuit breaker for policy client calls
        self._policy_circuit_breaker = None
        if CIRCUIT_BREAKER_ENABLED and self._use_dynamic_policy:
            self._policy_circuit_breaker = get_circuit_breaker(
                'policy_registry',
                CircuitBreakerConfig(fail_max=3, reset_timeout=15)
            )

        self._metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "started_at": None,
        }

    async def start(self) -> None:
        """Start the agent bus."""
        self._running = True
        self._metrics["started_at"] = datetime.now(timezone.utc).isoformat()

        # Start Kafka bus if enabled
        if self._kafka_bus:
            await self._kafka_bus.start()

        # Initialize Prometheus service info
        if METRICS_ENABLED:
            set_service_info(
                service_name='enhanced_agent_bus',
                version='2.0.0',
                constitutional_hash=CONSTITUTIONAL_HASH
            )

        # Initialize core circuit breakers
        if CIRCUIT_BREAKER_ENABLED:
            initialize_core_circuit_breakers()
            logger.info("Circuit breakers initialized for core services")

        # Initialize policy client if using dynamic validation
        if self._policy_client is not None:
            try:
                await self._policy_client.initialize()
                public_key = await self._policy_client.get_current_public_key()
                hash_info = public_key[:16] if public_key else "dynamic"
            except Exception as e:
                logger.warning(f"Policy client initialization warning: {e}")
                hash_info = "dynamic"
            logger.info(f"EnhancedAgentBus started with dynamic policy (key: {hash_info})")
        else:
            logger.info(f"EnhancedAgentBus started with hash: {self.constitutional_hash}")

    async def stop(self) -> None:
        """Stop the agent bus gracefully."""
        self._running = False

        # Close policy client if active
        if self._policy_client is not None:
            try:
                await self._policy_client.close()
            except Exception as e:
                logger.warning(f"Error closing policy client: {e}")

        logger.info("EnhancedAgentBus stopped")

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str = "default",
        capabilities: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """
        Register an agent with the bus.

        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type/category of the agent
            capabilities: List of agent capabilities
            tenant_id: Tenant identifier for multi-tenant isolation

        Returns:
            True if registration successful
        """
        # SECURITY: In production, this would verify the agent's JWT/SVID
        # and extract the tenant_id from the token claims.

        constitutional_key = CONSTITUTIONAL_HASH

        # Get dynamic key if using policy registry
        if self._policy_client is not None:
            try:
                constitutional_key = await self._policy_client.get_current_public_key()
            except Exception as e:
                logger.debug(f"Could not get dynamic key: {e}")

        self._agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "capabilities": capabilities or [],
            "tenant_id": tenant_id,  # Store tenant_id for multi-tenant isolation
            "registered_at": datetime.now(timezone.utc),
            "constitutional_hash": constitutional_key,
            "status": "active",
        }
        logger.info(f"Agent registered: {agent_id} (type: {agent_type}, tenant: {tenant_id})")
        return True

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the bus.

        Returns:
            True if agent was found and removed
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")
            return True
        logger.warning(f"Agent not found for unregistration: {agent_id}")
        return False

    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered agent."""
        return self._agents.get(agent_id)

    async def send_message(self, message: AgentMessage) -> ValidationResult:
        """
        Send a message through the bus.

        Validates constitutional compliance before queuing.
        """
        # Validate constitutional compliance
        if self._policy_client is not None:
            try:
                validation_result = await self._policy_client.validate_message_signature(message)
                if not validation_result.is_valid:
                    self._metrics["messages_failed"] += 1
                    return validation_result
            except Exception as e:
                logger.error(f"Policy validation error: {e}")
                self._metrics["messages_failed"] += 1
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Policy validation error: {e}"],
                )
        else:
            # Static hash validation
            if message.constitutional_hash != CONSTITUTIONAL_HASH:
                self._metrics["messages_failed"] += 1
                return ValidationResult(
                    is_valid=False,
                    errors=["Constitutional hash validation failed"],
                )

        # Check if recipient exists (warning only)
        if message.to_agent and message.to_agent not in self._agents:
            logger.warning(f"Recipient agent not found: {message.to_agent}")

        self._metrics["messages_sent"] += 1
        await self._message_queue.put(message)

        return ValidationResult(is_valid=True)

    async def receive_message(self, timeout: float = 1.0) -> Optional[AgentMessage]:
        """
        Receive a message from the bus.

        Args:
            timeout: Maximum time to wait for a message (seconds)

        Returns:
            AgentMessage if available, None on timeout
        """
        try:
            message = await asyncio.wait_for(
                self._message_queue.get(),
                timeout=timeout,
            )
            self._metrics["messages_received"] += 1
            return message
        except asyncio.TimeoutError:
            return None

    async def broadcast_message(self, message: AgentMessage) -> Dict[str, ValidationResult]:
        """
        Broadcast a message to all registered agents within the same tenant.

        SECURITY: Enforces strict multi-tenant isolation.
        - Messages with tenant_id only reach agents in the same tenant
        - Messages without tenant_id only reach agents without tenant_id
        - Cross-tenant broadcast is explicitly denied

        Returns:
            Dict mapping agent_id to validation result
        """
        results = {}
        original_to_agent = message.to_agent
        skipped_agents = []

        for agent_id, info in self._agents.items():
            agent_tenant = info.get("tenant_id")

            # STRICT MULTI-TENANT ISOLATION:
            # 1. If message has tenant_id, only send to agents with SAME tenant_id
            # 2. If message has no tenant_id, only send to agents with no tenant_id
            # This prevents any cross-tenant data leakage
            if message.tenant_id:
                # Message is tenant-scoped - only same-tenant agents
                if agent_tenant != message.tenant_id:
                    skipped_agents.append(agent_id)
                    continue
            else:
                # Message has no tenant - only non-tenant agents receive it
                if agent_tenant:
                    skipped_agents.append(agent_id)
                    continue

            message.to_agent = agent_id
            results[agent_id] = await self.send_message(message)

        # Log isolation enforcement for audit
        if skipped_agents:
            logger.debug(
                f"Multi-tenant isolation: skipped {len(skipped_agents)} agents "
                f"for message tenant_id={message.tenant_id}"
            )

        message.to_agent = original_to_agent
        return results

    def get_registered_agents(self) -> List[str]:
        """Get list of registered agent IDs."""
        return list(self._agents.keys())

    def get_agents_by_type(self, agent_type: str) -> List[str]:
        """Get agent IDs filtered by type."""
        return [
            agent_id for agent_id, info in self._agents.items()
            if info.get("agent_type") == agent_type
        ]

    def get_agents_by_capability(self, capability: str) -> List[str]:
        """Get agent IDs that have a specific capability."""
        return [
            agent_id for agent_id, info in self._agents.items()
            if capability in info.get("capabilities", [])
        ]

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get bus metrics synchronously.

        For metrics including dynamic policy status, use get_metrics_async().
        """
        queue_size = self._message_queue.qsize()

        # Update Prometheus queue depth gauge
        if METRICS_ENABLED:
            MESSAGE_QUEUE_DEPTH.labels(
                queue_name='main', priority='all'
            ).set(queue_size)

        return {
            **self._metrics,
            "registered_agents": len(self._agents),
            "queue_size": queue_size,
            "is_running": self._running,
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "rust_enabled": USE_RUST,
            "dynamic_policy_enabled": self._use_dynamic_policy,
            "processor_metrics": self._processor.get_metrics(),
            "metrics_enabled": METRICS_ENABLED,
        }

    async def get_metrics_async(self) -> Dict[str, Any]:
        """
        Get comprehensive bus metrics asynchronously.

        Includes dynamic policy registry status check when enabled.
        """
        metrics = self.get_metrics()

        # Add policy registry status if available
        if self._policy_client is not None:
            try:
                health = await self._policy_client.health_check()
                metrics["policy_registry_status"] = health.get("status", "unknown")
            except Exception:
                metrics["policy_registry_status"] = "unavailable"

        # Add circuit breaker health
        if CIRCUIT_BREAKER_ENABLED:
            metrics["circuit_breaker_health"] = circuit_breaker_health_check()
        else:
            metrics["circuit_breaker_health"] = {"status": "disabled"}

        return metrics

    @property
    def processor(self) -> MessageProcessor:
        """Get the message processor."""
        return self._processor

    @property
    def is_running(self) -> bool:
        """Check if the bus is running."""
        return self._running

    @property
    def registry(self) -> AgentRegistry:
        """Get the agent registry (DI component)."""
        return self._registry

    @property
    def router(self) -> MessageRouter:
        """Get the message router (DI component)."""
        return self._router

    @property
    def validator(self) -> ValidationStrategy:
        """Get the validation strategy (DI component)."""
        return self._validator


# Module-level convenience functions
_default_bus: Optional[EnhancedAgentBus] = None


def get_agent_bus(
    redis_url: str = DEFAULT_REDIS_URL,
    use_dynamic_policy: bool = False,
) -> EnhancedAgentBus:
    """
    Get or create the default EnhancedAgentBus singleton.

    Args:
        redis_url: Redis URL (only used on first call)
        use_dynamic_policy: Use dynamic policy (only used on first call)
    """
    global _default_bus
    if _default_bus is None:
        _default_bus = EnhancedAgentBus(
            redis_url=redis_url,
            use_dynamic_policy=use_dynamic_policy,
        )
    return _default_bus


def reset_agent_bus() -> None:
    """Reset the default agent bus singleton (mainly for testing)."""
    global _default_bus
    _default_bus = None


__all__ = [
    # Constants
    "CONSTITUTIONAL_HASH",
    "USE_RUST",
    "DEFAULT_REDIS_URL",
    "METRICS_ENABLED",
    "CIRCUIT_BREAKER_ENABLED",
    # Core Classes
    "MessageProcessor",
    "EnhancedAgentBus",
    # Protocol Interfaces (DI)
    "AgentRegistry",
    "MessageRouter",
    "ValidationStrategy",
    "ProcessingStrategy",
    # Default Implementations (DI)
    "InMemoryAgentRegistry",
    "DirectMessageRouter",
    "ConstitutionalValidationStrategy",
    # Processing Strategies (DI)
    "PythonProcessingStrategy",
    "RustProcessingStrategy",
    "DynamicPolicyProcessingStrategy",
    # Functions
    "get_agent_bus",
    "reset_agent_bus",
]
