"""
ACGS-2 Enhanced Agent Bus - Agent Bus Implementation
Constitutional Hash: cdd01ef066bc6cf2

Agent communication bus with constitutional compliance, multi-tenant isolation,
and comprehensive metrics instrumentation.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import BusConfiguration

# Use centralized imports module for optional dependencies
from .imports import (
    AUDIT_CLIENT_AVAILABLE,
    CIRCUIT_BREAKER_ENABLED,
    CONFIG_AVAILABLE,
    CRYPTO_AVAILABLE,
    DEFAULT_REDIS_URL,
    DELIBERATION_AVAILABLE,
    # Prometheus
    MESSAGE_QUEUE_DEPTH,
    METERING_AVAILABLE,
    # Feature flags
    METRICS_ENABLED,
    OTEL_ENABLED,
    POLICY_CLIENT_AVAILABLE,
    QUEUE_DEPTH,
    USE_RUST,
    # Audit
    AuditClient,
    CircuitBreakerConfig,
    # Crypto
    CryptoService,
    DeliberationQueue,
    VotingService,
    circuit_breaker_health_check,
    # Circuit breaker
    get_circuit_breaker,
    # OPA
    get_opa_client,
    # Policy client
    get_policy_client,
    initialize_core_circuit_breakers,
    set_service_info,
    # Settings
    settings,
    # OpenTelemetry
    tracer,
)

# Use centralized metering manager
from .metering_manager import create_metering_manager

# Core package imports with fallback
try:
    from .interfaces import AgentRegistry, MessageRouter, ValidationStrategy
    from .models import (
        CONSTITUTIONAL_HASH,
        AgentMessage,
        MessageStatus,
        MessageType,
    )
    from .registry import (
        DirectMessageRouter,
        DynamicPolicyValidationStrategy,
        InMemoryAgentRegistry,
        OPAValidationStrategy,
        StaticHashValidationStrategy,
    )
    from .validators import ValidationResult
except ImportError:
    from interfaces import AgentRegistry, MessageRouter, ValidationStrategy
    from models import (
        CONSTITUTIONAL_HASH,
        AgentMessage,
        MessageStatus,
        MessageType,
    )
    from registry import (
        DirectMessageRouter,
        DynamicPolicyValidationStrategy,
        InMemoryAgentRegistry,
        OPAValidationStrategy,
        StaticHashValidationStrategy,
    )
    from validators import ValidationResult

# Import MessageProcessor
try:
    from .message_processor import MessageProcessor
except ImportError:
    from message_processor import MessageProcessor

# MACI role separation enforcement (optional)
try:
    from .maci_enforcement import (
        MACIEnforcer,
        MACIRole,
        MACIRoleNotAssignedError,
        MACIRoleRegistry,
        MACIRoleViolationError,
    )

    MACI_AVAILABLE = True
except ImportError:
    MACI_AVAILABLE = False
    MACIRole = None  # type: ignore

logger = logging.getLogger(__name__)


class EnhancedAgentBus:
    """Enhanced agent communication bus with constitutional compliance.

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
        policy_fail_closed: bool = False,
        use_kafka: bool = False,
        use_redis_registry: bool = False,
        kafka_bootstrap_servers: str = "localhost:9092",
        audit_service_url: str = "http://localhost:8001",
        registry: Optional[AgentRegistry] = None,
        router: Optional[MessageRouter] = None,
        validator: Optional[ValidationStrategy] = None,
        processor: Optional[MessageProcessor] = None,
        use_rust: bool = True,
        enable_metering: bool = True,
        metering_config: Optional[Any] = None,
        # SECURITY FIX (audit finding 2025-12): MACI enabled by default
        enable_maci: bool = True,
        maci_strict_mode: bool = True,
    ):
        """Initialize the Enhanced Agent Bus.

        Args:
            redis_url: Redis connection URL for message queuing
            use_dynamic_policy: Use dynamic policy registry instead of static hash
            policy_fail_closed: Fail closed on policy registry errors
            use_kafka: Use Kafka as the event bus instead of Redis/Local queue
            use_redis_registry: Use Redis-based distributed agent registry
            kafka_bootstrap_servers: Kafka bootstrap servers
            registry: Optional custom AgentRegistry implementation
            router: Optional custom MessageRouter implementation
            validator: Optional custom ValidationStrategy implementation
            processor: Optional custom MessageProcessor instance
            use_rust: Whether to prefer Rust backend when available
            enable_metering: Enable production billing metering
            metering_config: Optional metering configuration
            enable_maci: Enable MACI role separation enforcement (default True per audit)
            maci_strict_mode: If True, fail-closed on MACI errors
        """
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self.redis_url = redis_url
        self._use_dynamic_policy = use_dynamic_policy and POLICY_CLIENT_AVAILABLE
        self._use_kafka = use_kafka
        self._policy_fail_closed = policy_fail_closed
        self._use_rust = use_rust

        # Initialize clients
        self._policy_client = self._init_policy_client(policy_fail_closed)
        self._opa_client = get_opa_client()
        self._audit_client = self._init_audit_client(audit_service_url)

        # Dependency injection with defaults
        self._registry = self._init_registry(registry, use_redis_registry, redis_url)
        self._router: MessageRouter = router or DirectMessageRouter()
        self._validator = self._init_validator(validator)

        # Legacy dict for backward compatibility (delegates to registry)
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()

        # Initialize metering using MeteringManager
        self._metering_manager = create_metering_manager(
            enable_metering=enable_metering and METERING_AVAILABLE,
            metering_config=metering_config,
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

        # Initialize MACI role separation enforcement
        self._enable_maci = enable_maci and MACI_AVAILABLE
        self._maci_strict_mode = maci_strict_mode
        self._maci_registry: Optional[MACIRoleRegistry] = None
        self._maci_enforcer: Optional[MACIEnforcer] = None
        if self._enable_maci:
            self._maci_registry = MACIRoleRegistry()
            self._maci_enforcer = MACIEnforcer(
                registry=self._maci_registry,
                strict_mode=maci_strict_mode,
            )
            logger.info("MACI role separation enforcement enabled (strict=%s)", maci_strict_mode)

        self._processor = processor or MessageProcessor(
            use_dynamic_policy=use_dynamic_policy,
            policy_fail_closed=policy_fail_closed,
            processing_strategy=None,
            audit_client=self._audit_client,
            use_rust=self._use_rust,
            metering_hooks=self._metering_manager.hooks,
            enable_metering=enable_metering,
            enable_maci=self._enable_maci,
            maci_registry=self._maci_registry,
            maci_enforcer=self._maci_enforcer,
            maci_strict_mode=maci_strict_mode,
        )
        self._running = False

        # Initialize Kafka bus if enabled
        self._kafka_bus = self._init_kafka(use_kafka, kafka_bootstrap_servers)

        # Initialize circuit breaker for policy registry
        if CIRCUIT_BREAKER_ENABLED and self._use_dynamic_policy:
            self._policy_circuit_breaker = get_circuit_breaker(
                "policy_registry", CircuitBreakerConfig(fail_max=3, reset_timeout=15)
            )

        # Initialize Deliberation Layer
        self._voting_service = VotingService() if DELIBERATION_AVAILABLE else None
        self._deliberation_queue = DeliberationQueue() if DELIBERATION_AVAILABLE else None

        self._kafka_consumer_task: Optional[asyncio.Task] = None

        self._metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "started_at": None,
        }

    @classmethod
    def from_config(cls, config: BusConfiguration) -> "EnhancedAgentBus":
        """Create an EnhancedAgentBus from a BusConfiguration object.

        This factory method provides a cleaner interface for complex configurations
        by accepting a single configuration object instead of many individual parameters.

        Example:
            # Using default configuration
            bus = EnhancedAgentBus.from_config(BusConfiguration())

            # Using testing configuration
            bus = EnhancedAgentBus.from_config(BusConfiguration.for_testing())

            # Using production configuration
            bus = EnhancedAgentBus.from_config(BusConfiguration.for_production())

            # Using environment configuration
            bus = EnhancedAgentBus.from_config(BusConfiguration.from_environment())

            # Using custom configuration with builder pattern
            config = BusConfiguration(use_dynamic_policy=True).with_registry(my_registry)
            bus = EnhancedAgentBus.from_config(config)

        Args:
            config: BusConfiguration object containing all settings

        Returns:
            Configured EnhancedAgentBus instance
        """
        return cls(
            redis_url=config.redis_url,
            use_dynamic_policy=config.use_dynamic_policy,
            policy_fail_closed=config.policy_fail_closed,
            use_kafka=config.use_kafka,
            use_redis_registry=config.use_redis_registry,
            kafka_bootstrap_servers=config.kafka_bootstrap_servers,
            audit_service_url=config.audit_service_url,
            registry=config.registry,
            router=config.router,
            validator=config.validator,
            processor=config.processor,
            use_rust=config.use_rust,
            enable_metering=config.enable_metering,
            metering_config=config.metering_config,
            enable_maci=config.enable_maci,
            maci_strict_mode=config.maci_strict_mode,
        )

    def _init_policy_client(self, policy_fail_closed: bool) -> Optional[Any]:
        """Initialize policy client if using dynamic validation."""
        if self._use_dynamic_policy:
            return get_policy_client(fail_closed=policy_fail_closed)
        return None

    def _init_audit_client(self, audit_service_url: str) -> Optional[Any]:
        """Initialize audit client if available."""
        if AUDIT_CLIENT_AVAILABLE:
            return AuditClient(service_url=audit_service_url)
        return None

    def _redact_error_message(self, error: Exception) -> str:
        """Redact sensitive information from error messages (VULN-008)."""
        import re

        error_msg = str(error)

        # 1. Redact potential URLs/URIs with various protocols (e.g. postgres://, redis://)
        redacted = re.sub(r'[a-zA-Z0-9+.-]+://[^\s<>"]+', "[REDACTED_URI]", error_msg)

        # 2. Redact common credential patterns (e.g. key=...) BEFORE path redaction
        redacted = re.sub(
            r"(?i)(key|secret|token|password|auth|pwd)=[^ \b\n\r\t,;]+", r"\1=[REDACTED]", redacted
        )

        # 3. Redact absolute file paths (Unix-style)
        # Avoid redacting solitary slashes or very short paths
        redacted = re.sub(r"/(?:[a-zA-Z0-9._-]+/)+[a-zA-Z0-9._-]+", "[REDACTED_PATH]", redacted)

        return redacted

    def _init_registry(
        self,
        registry: Optional[AgentRegistry],
        use_redis_registry: bool,
        redis_url: str,
    ) -> AgentRegistry:
        """Initialize agent registry with fallback to defaults."""
        if registry:
            return registry
        if use_redis_registry:
            try:
                from .registry import RedisAgentRegistry
            except ImportError:
                from registry import RedisAgentRegistry
            return RedisAgentRegistry(redis_url=redis_url)
        return InMemoryAgentRegistry()

    def _init_validator(
        self,
        validator: Optional[ValidationStrategy],
    ) -> ValidationStrategy:
        """Initialize validation strategy with preference ordering."""
        if validator:
            return validator
        if self._use_dynamic_policy and self._opa_client:
            return OPAValidationStrategy(opa_client=self._opa_client)
        if self._use_dynamic_policy and self._policy_client:
            return DynamicPolicyValidationStrategy(policy_client=self._policy_client)
        return StaticHashValidationStrategy(strict=True)

    def _init_kafka(
        self,
        use_kafka: bool,
        kafka_bootstrap_servers: str,
    ) -> Optional[Any]:
        """Initialize Kafka bus if enabled."""
        if use_kafka:
            from .kafka_bus import KafkaEventBus

            return KafkaEventBus(bootstrap_servers=kafka_bootstrap_servers)
        return None

    async def start(self) -> None:
        """Start the agent bus."""
        self._running = True
        self._metrics["started_at"] = datetime.now(timezone.utc).isoformat()

        # Start metering manager
        await self._metering_manager.start()

        # Start Kafka bus if enabled
        if self._kafka_bus:
            await self._kafka_bus.start()
            if self._use_kafka:
                self._kafka_consumer_task = asyncio.create_task(self._poll_kafka_messages())

        # Initialize Prometheus service info
        if METRICS_ENABLED and set_service_info:
            set_service_info(
                service_name="enhanced_agent_bus",
                version="2.0.0",
                constitutional_hash=CONSTITUTIONAL_HASH,
            )

        # Initialize core circuit breakers
        if CIRCUIT_BREAKER_ENABLED and initialize_core_circuit_breakers:
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
        """Stop the agent bus and clean up resources."""
        self._running = False

        # Close Kafka consumer
        if self._kafka_consumer_task:
            self._kafka_consumer_task.cancel()
            try:
                await self._kafka_consumer_task
            except asyncio.CancelledError:
                pass

        if self._kafka_bus:
            await self._kafka_bus.stop()

        # Stop metering manager
        await self._metering_manager.stop()

        logger.info("EnhancedAgentBus stopped")

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str = "default",
        capabilities: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        maci_role: Optional[Any] = None,
    ) -> bool:
        """Register an agent with the bus.

        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type/category of the agent
            capabilities: List of agent capabilities
            tenant_id: Tenant identifier for multi-tenant isolation
            auth_token: JWT authentication token for identity verification
            maci_role: MACI role (EXECUTIVE/LEGISLATIVE/JUDICIAL) for role separation

        Returns:
            True if registration successful
        """
        # SECURITY: Verify the agent's JWT/SVID identity
        validated_tenant, validated_capabilities = await self._validate_agent_identity(
            agent_id, tenant_id, capabilities, auth_token
        )
        if validated_tenant is False:
            return False

        # SANITIZATION (VULN-005): Normalize and validate tenant identity
        from .security.tenant_validator import TenantValidator

        normalized_tenant, is_valid = TenantValidator.sanitize_and_validate(
            validated_tenant or tenant_id
        )

        if tenant_id and not is_valid:
            logger.error(f"Agent registration rejected: invalid tenant_id format '{tenant_id}'")
            return False

        validated_tenant = normalized_tenant

        if validated_tenant is not None:
            tenant_id = validated_tenant
        if validated_capabilities is not None:
            capabilities = validated_capabilities

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
            "tenant_id": tenant_id,
            "registered_at": datetime.now(timezone.utc),
            "constitutional_hash": constitutional_key,
            "status": "active",
            "maci_role": maci_role.value if maci_role else None,
        }

        # Register with MACI if enabled and role provided
        if self._enable_maci and maci_role is not None and self._maci_registry is not None:
            try:
                await self._maci_registry.register_agent(
                    agent_id=agent_id,
                    role=maci_role,
                    metadata={"capabilities": capabilities or []},
                )
                logger.info(f"Agent registered with MACI: {agent_id} (role: {maci_role.value})")
            except Exception as e:
                logger.warning(f"Failed to register agent with MACI: {e}")
                if self._maci_strict_mode:
                    # Remove from regular registry on MACI failure in strict mode
                    del self._agents[agent_id]
                    return False

        logger.info(f"Agent registered: {agent_id} (type: {agent_type}, tenant: {tenant_id})")
        return True

    async def _validate_agent_identity(
        self,
        agent_id: str,
        tenant_id: Optional[str],
        capabilities: Optional[List[str]],
        auth_token: Optional[str],
    ) -> tuple:
        """Validate agent identity using JWT token.

        Returns:
            Tuple of (validated_tenant_id, validated_capabilities)
            Returns (False, None) if validation fails
        """
        if auth_token and CRYPTO_AVAILABLE and CONFIG_AVAILABLE:
            try:
                public_key = (
                    settings.security.jwt_public_key
                    if hasattr(settings.security, "jwt_public_key")
                    else CONSTITUTIONAL_HASH
                )
                payload = CryptoService.verify_agent_token(auth_token, public_key)

                # Extract and validate identity
                token_agent_id = payload.get("agent_id")
                token_tenant_id = payload.get("tenant_id")

                if token_agent_id != agent_id:
                    logger.warning(
                        f"Registration failed: agent_id mismatch ({agent_id} vs {token_agent_id})"
                    )
                    return (False, None)

                if tenant_id and token_tenant_id != tenant_id:
                    logger.warning(
                        f"Registration failed: tenant_id mismatch ({tenant_id} vs {token_tenant_id})"
                    )
                    return (False, None)

                logger.info(f"Agent identity verified via token for {agent_id}")
                return (token_tenant_id, payload.get("capabilities", capabilities))
            except Exception as e:
                logger.error(f"Agent registration identity validation error: {e}")
                return (False, None)
        elif auth_token:
            logger.warning("Auth token provided but CryptoService or Config not available")
        elif self._use_dynamic_policy:
            logger.warning(
                f"Registration rejected: Auth token required for agent {agent_id} in dynamic mode"
            )
            return (False, None)

        return (None, None)

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the bus.

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
        """Send a message through the bus.

        Validates constitutional compliance before queuing.
        """
        if OTEL_ENABLED and tracer:
            with tracer.start_as_current_span(
                "bus.send_message",
                attributes={
                    "message.id": message.message_id,
                    "agent.from": message.from_agent,
                    "agent.to": message.to_agent,
                    "tenant.id": message.tenant_id or "default",
                },
            ):
                return await self._do_send_message(message)
        else:
            return await self._do_send_message(message)

    async def _do_send_message(self, message: AgentMessage) -> ValidationResult:
        """Internal message sending logic with validation and routing."""
        # SANITIZATION (VULN-005): Normalize and validate tenant identity
        from .security.tenant_validator import TenantValidator

        normalized_tenant, is_valid = TenantValidator.sanitize_and_validate(message.tenant_id)
        if message.tenant_id and not is_valid:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid tenant_id format: {message.tenant_id}"],
                constitutional_hash=self.constitutional_hash,
            )
        message.tenant_id = normalized_tenant

        message_start = time.perf_counter()

        if OTEL_ENABLED and QUEUE_DEPTH:
            QUEUE_DEPTH.add(1, {"tenant_id": message.tenant_id or "default"})

        try:
            # Step 1: Multi-tenant isolation check
            tenant_errors = self._validate_tenant_consistency(message)
            if tenant_errors:
                return self._handle_tenant_failure(message, tenant_errors, message_start)

            # Step 2: Constitutional validation with fallback
            result = await self._perform_validation(message)

            # Step 3: Audit reporting (fire-and-forget)
            if self._audit_client:
                asyncio.create_task(self._audit_client.report_validation(result))

            # Step 4: Check for high-impact deliberation
            if self._requires_deliberation(result):
                return await self._handle_deliberation(message, result, message_start)

            # Step 5: Route and deliver valid messages
            if result.is_valid:
                await self._route_and_deliver(message)
                self._metrics["messages_sent"] += 1
            else:
                self._metrics["messages_failed"] += 1

            # Step 6: Meter the message
            self._metering_manager.record_agent_message(
                message, result.is_valid, (time.perf_counter() - message_start) * 1000
            )

            return result
        finally:
            if OTEL_ENABLED and QUEUE_DEPTH:
                QUEUE_DEPTH.add(-1, {"tenant_id": message.tenant_id or "default"})

    def _handle_tenant_failure(
        self,
        message: AgentMessage,
        errors: List[str],
        start_time: float,
    ) -> ValidationResult:
        """Handle tenant validation failure."""
        self._metrics["messages_failed"] += 1
        message.status = MessageStatus.FAILED
        self._metering_manager.record_agent_message(
            message, False, (time.perf_counter() - start_time) * 1000
        )
        return ValidationResult(is_valid=False, errors=errors)

    async def _perform_validation(self, message: AgentMessage) -> ValidationResult:
        """Perform constitutional validation with DEGRADED mode fallback."""
        try:
            return await self._processor.process(message)
        except Exception as e:
            logger.warning(
                f"MessageProcessor failed: {e}. Falling back to DEGRADED_MODE safety lock."
            )
            # Fallback to local static hash validation (Degraded Mode)
            fallback_strategy = StaticHashValidationStrategy(strict=True)
            is_valid, error = await fallback_strategy.validate(message)
            result = ValidationResult(is_valid=is_valid)
            if error:
                result.add_error(error)
            result.metadata["governance_mode"] = "DEGRADED"
            # SECURITY (VULN-008): Redact error details before returning to environment
            result.metadata["fallback_reason"] = self._redact_error_message(e)
            return result

    def _requires_deliberation(self, result: ValidationResult) -> bool:
        """Check if message requires deliberation based on impact score."""
        return (
            self._deliberation_queue is not None and result.metadata.get("impact_score", 0.0) >= 0.8
        )

    async def _handle_deliberation(
        self,
        message: AgentMessage,
        result: ValidationResult,
        start_time: float,
    ) -> ValidationResult:
        """Handle high-impact message by diverting to deliberation queue."""
        impact_score = result.metadata.get("impact_score", 0.8)
        logger.info(
            f"Message {message.message_id} diverted to deliberation (Score: {impact_score})"
        )
        await self._deliberation_queue.enqueue(message, metadata={"impact_score": impact_score})
        result.status = MessageStatus.PENDING_DELIBERATION
        self._metering_manager.record_deliberation_request(
            message, impact_score, (time.perf_counter() - start_time) * 1000
        )
        return result

    async def _route_and_deliver(self, message: AgentMessage) -> bool:
        """Route and deliver a validated message."""
        # Dispatch via Kafka if enabled
        if self._kafka_bus:
            success = await self._kafka_bus.send_message(message)
            if not success:
                self._metrics["messages_failed"] += 1
                return False

        # Route locally for immediate handlers
        await self._router.route(message, self._registry)

        # Deliver to internal queue if Kafka is not enabled
        if not self._use_kafka:
            await self._message_queue.put(message)

        # Check if recipient exists (warning only)
        if message.to_agent and message.to_agent not in self._agents:
            logger.debug(f"Recipient agent not found locally: {message.to_agent}")

        return True

    @staticmethod
    def _normalize_tenant_id(tenant_id: Optional[str]) -> Optional[str]:
        """Normalize tenant identifiers to a canonical optional value."""
        from .security.tenant_validator import TenantValidator

        return TenantValidator.normalize(tenant_id)

    @staticmethod
    def _format_tenant_id(tenant_id: Optional[str]) -> str:
        """Format tenant identifiers for logging and validation messages."""
        return tenant_id if tenant_id else "none"

    def _validate_tenant_consistency(self, message: AgentMessage) -> List[str]:
        """Validate tenant_id consistency for sender/recipient before delivery."""
        errors: List[str] = []
        message_tenant = self._normalize_tenant_id(message.tenant_id)

        if message.from_agent and message.from_agent in self._agents:
            sender_tenant = self._normalize_tenant_id(
                self._agents[message.from_agent].get("tenant_id")
            )
            if sender_tenant != message_tenant:
                errors.append(
                    "Tenant mismatch: message tenant_id "
                    f"'{self._format_tenant_id(message_tenant)}' does not match "
                    f"sender tenant_id '{self._format_tenant_id(sender_tenant)}'"
                )

        if message.to_agent and message.to_agent in self._agents:
            recipient_tenant = self._normalize_tenant_id(
                self._agents[message.to_agent].get("tenant_id")
            )
            if recipient_tenant != message_tenant:
                errors.append(
                    "Tenant mismatch: message tenant_id "
                    f"'{self._format_tenant_id(message_tenant)}' does not match "
                    f"recipient tenant_id '{self._format_tenant_id(recipient_tenant)}'"
                )

        return errors

    async def receive_message(self, timeout: float = 1.0) -> Optional[AgentMessage]:
        """Receive a message from the bus.

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

    async def _poll_kafka_messages(self):
        """Background task to poll messages from Kafka for registered tenants."""
        if not self._kafka_bus:
            return

        logger.info("Starting Kafka message polling task")

        async def kafka_handler(msg_data: Dict[str, Any]):
            try:
                message = AgentMessage.from_dict(msg_data)
                await self._message_queue.put(message)
            except Exception as e:
                logger.error(f"Failed to process message from Kafka: {e}")

        message_types = list(MessageType)
        await self._kafka_bus.subscribe("default", message_types, kafka_handler)

        while self._running:
            await asyncio.sleep(1)

    async def broadcast_message(self, message: AgentMessage) -> Dict[str, ValidationResult]:
        """Broadcast a message to all registered agents within the same tenant.

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

        # Normalize message tenant_id for consistent comparison
        message_tenant = self._normalize_tenant_id(message.tenant_id)

        for agent_id, info in self._agents.items():
            # Agent tenant_id is already normalized during registration
            agent_tenant = info.get("tenant_id")

            # STRICT MULTI-TENANT ISOLATION
            if message_tenant:
                if agent_tenant != message_tenant:
                    skipped_agents.append(agent_id)
                    continue
            else:
                if agent_tenant:
                    skipped_agents.append(agent_id)
                    continue

            message.to_agent = agent_id
            results[agent_id] = await self.send_message(message)

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
            agent_id
            for agent_id, info in self._agents.items()
            if info.get("agent_type") == agent_type
        ]

    def get_agents_by_capability(self, capability: str) -> List[str]:
        """Get agent IDs that have a specific capability."""
        return [
            agent_id
            for agent_id, info in self._agents.items()
            if capability in info.get("capabilities", [])
        ]

    def get_metrics(self) -> Dict[str, Any]:
        """Get bus metrics synchronously.

        For metrics including dynamic policy status, use get_metrics_async().
        """
        queue_size = self._message_queue.qsize()

        # Update Prometheus queue depth gauge
        if METRICS_ENABLED and MESSAGE_QUEUE_DEPTH:
            MESSAGE_QUEUE_DEPTH.labels(queue_name="main", priority="all").set(queue_size)

        metrics = {
            **self._metrics,
            "registered_agents": len(self._agents),
            "queue_size": queue_size,
            "is_running": self._running,
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "rust_enabled": USE_RUST,
            "dynamic_policy_enabled": self._use_dynamic_policy,
            "processor_metrics": self._processor.get_metrics(),
            "metrics_enabled": METRICS_ENABLED,
            "metering_enabled": self._metering_manager.is_enabled,
        }

        # Include metering metrics if available
        metering_metrics = self._metering_manager.get_metrics()
        if metering_metrics:
            metrics["metering_metrics"] = metering_metrics

        return metrics

    async def get_metrics_async(self) -> Dict[str, Any]:
        """Get comprehensive bus metrics asynchronously.

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
        if CIRCUIT_BREAKER_ENABLED and circuit_breaker_health_check:
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

    @property
    def maci_enabled(self) -> bool:
        """Check if MACI role separation is enabled."""
        return self._enable_maci

    @property
    def maci_registry(self) -> Optional[MACIRoleRegistry]:
        """Get the MACI role registry for external registration."""
        return self._maci_registry

    @property
    def maci_enforcer(self) -> Optional[MACIEnforcer]:
        """Get the MACI enforcer for validation."""
        return self._maci_enforcer


# Module-level convenience functions
_default_bus: Optional[EnhancedAgentBus] = None


def get_agent_bus(
    redis_url: str = DEFAULT_REDIS_URL,
    use_dynamic_policy: bool = False,
) -> EnhancedAgentBus:
    """Get or create the default EnhancedAgentBus singleton.

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
