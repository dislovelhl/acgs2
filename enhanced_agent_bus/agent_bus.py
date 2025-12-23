"""
ACGS-2 Enhanced Agent Bus - Agent Bus Implementation
Constitutional Hash: cdd01ef066bc6cf2

Agent communication bus with constitutional compliance, multi-tenant isolation,
and comprehensive metrics instrumentation.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

# Import Prometheus metrics with fallback
try:
    from shared.metrics import (
        MESSAGE_QUEUE_DEPTH,
        set_service_info,
    )
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False

# Import OpenTelemetry with fallback
try:
    from opentelemetry import trace, metrics
    OTEL_ENABLED = True
    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)

    QUEUE_DEPTH = meter.create_up_down_counter(
        "acgs2.queue.depth",
        description="Current message queue depth",
        unit="1"
    )
except ImportError:
    OTEL_ENABLED = False
    tracer = None
    meter = None
    QUEUE_DEPTH = None

# Import circuit breaker with fallback
try:
    from shared.circuit_breaker import (
        get_circuit_breaker,
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
        MessageStatus,
        CONSTITUTIONAL_HASH,
    )
    from .validators import ValidationResult
    from .interfaces import AgentRegistry, MessageRouter, ValidationStrategy
    from .registry import (
        InMemoryAgentRegistry,
        DirectMessageRouter,
        StaticHashValidationStrategy,
        DynamicPolicyValidationStrategy,
        OPAValidationStrategy,
    )
except ImportError:
    from models import (
        AgentMessage,
        MessageType,
        MessageStatus,
        CONSTITUTIONAL_HASH,
    )
    from validators import ValidationResult
    from interfaces import AgentRegistry, MessageRouter, ValidationStrategy
    from registry import (
        InMemoryAgentRegistry,
        DirectMessageRouter,
        StaticHashValidationStrategy,
        DynamicPolicyValidationStrategy,
        OPAValidationStrategy,
    )

# Import centralized Redis config with fallback
try:
    from shared.redis_config import get_redis_url
    DEFAULT_REDIS_URL = get_redis_url()
except ImportError:
    DEFAULT_REDIS_URL = "redis://localhost:6379"

# Import policy client for dynamic validation
try:
    from .policy_client import get_policy_client, PolicyClient
    POLICY_CLIENT_AVAILABLE = True
except ImportError:
    POLICY_CLIENT_AVAILABLE = False
    PolicyClient = None

    def get_policy_client(fail_closed: Optional[bool] = None):
        return None

# Import Deliberation Layer
try:
    try:
        from .deliberation_layer.voting_service import VotingService, VotingStrategy
        from .deliberation_layer.deliberation_queue import DeliberationQueue
    except ImportError:
        from deliberation_layer.voting_service import VotingService, VotingStrategy
        from deliberation_layer.deliberation_queue import DeliberationQueue
    DELIBERATION_AVAILABLE = True
except ImportError:
    DELIBERATION_AVAILABLE = False

# Import Crypto Service for identity validation
try:
    from services.policy_registry.app.services.crypto_service import CryptoService
    CRYPTO_AVAILABLE = True
except ImportError:
    try:
        from ..services.crypto_service import CryptoService
        CRYPTO_AVAILABLE = True
    except ImportError:
        CRYPTO_AVAILABLE = False
        CryptoService = None

# Import settings for security config
try:
    from shared.config import settings
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    settings = None

# Import Audit Client
try:
    from shared.audit_client import AuditClient
    AUDIT_CLIENT_AVAILABLE = True
except ImportError:
    try:
        from .audit_client import AuditClient
        AUDIT_CLIENT_AVAILABLE = True
    except ImportError:
        AUDIT_CLIENT_AVAILABLE = False
        AuditClient = None

# Import OPA client
try:
    from .opa_client import get_opa_client, OPAClient
    OPA_CLIENT_AVAILABLE = True
except ImportError:
    OPA_CLIENT_AVAILABLE = False
    OPAClient = None
    def get_opa_client(): return None

# Import Rust implementation
try:
    import enhanced_agent_bus_rust as rust_bus
    USE_RUST = True
except ImportError:
    USE_RUST = False
    rust_bus = None

# Import MessageProcessor
try:
    from .message_processor import MessageProcessor
except ImportError:
    from message_processor import MessageProcessor

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
        """
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self.redis_url = redis_url
        self._use_dynamic_policy = use_dynamic_policy and POLICY_CLIENT_AVAILABLE
        self._use_kafka = use_kafka
        self._policy_fail_closed = policy_fail_closed
        self._use_rust = use_rust

        # Initialize policy client if using dynamic validation
        if self._use_dynamic_policy:
            self._policy_client = get_policy_client(fail_closed=policy_fail_closed)
        else:
            self._policy_client = None

        # Initialize OPA client
        self._opa_client = get_opa_client()

        # Dependency injection with defaults for backward compatibility
        if registry:
            self._registry = registry
        elif use_redis_registry:
            try:
                from .registry import RedisAgentRegistry
            except ImportError:
                from registry import RedisAgentRegistry
            self._registry = RedisAgentRegistry(redis_url=redis_url)
        else:
            self._registry = InMemoryAgentRegistry()

        self._router: MessageRouter = router or DirectMessageRouter()

        # Set validator with preference: injected > OPA > dynamic policy > static hash
        if validator:
            self._validator = validator
        elif self._use_dynamic_policy and self._opa_client:
            self._validator = OPAValidationStrategy(opa_client=self._opa_client)
        elif self._use_dynamic_policy and self._policy_client:
            self._validator = DynamicPolicyValidationStrategy(policy_client=self._policy_client)
        else:
            self._validator = StaticHashValidationStrategy(strict=True)

        # Initialize Audit Client
        if AUDIT_CLIENT_AVAILABLE:
            self._audit_client = AuditClient(service_url=audit_service_url)
        else:
            self._audit_client = None

        # Legacy dict for backward compatibility (delegates to registry)
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._processor = processor or MessageProcessor(
            use_dynamic_policy=use_dynamic_policy,
            policy_fail_closed=policy_fail_closed,
            processing_strategy=None,
            audit_client=self._audit_client,
            use_rust=self._use_rust
        )
        self._running = False

        # Initialize Kafka bus if enabled
        if self._use_kafka:
            from .kafka_bus import KafkaEventBus
            self._kafka_bus = KafkaEventBus(bootstrap_servers=kafka_bootstrap_servers)
        else:
            self._kafka_bus = None

        if CIRCUIT_BREAKER_ENABLED and self._use_dynamic_policy:
            self._policy_circuit_breaker = get_circuit_breaker(
                'policy_registry',
                CircuitBreakerConfig(fail_max=3, reset_timeout=15)
            )

        # Initialize Deliberation Layer
        if DELIBERATION_AVAILABLE:
            self._voting_service = VotingService()
            self._deliberation_queue = DeliberationQueue()
        else:
            self._voting_service = None
            self._deliberation_queue = None

        self._kafka_consumer_task: Optional[asyncio.Task] = None

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
            if self._use_kafka:
                self._kafka_consumer_task = asyncio.create_task(self._poll_kafka_messages())

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

        logger.info("EnhancedAgentBus stopped")

    async def register_agent(
        self,
        agent_id: str,
        agent_type: str = "default",
        capabilities: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> bool:
        """Register an agent with the bus.

        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type/category of the agent
            capabilities: List of agent capabilities
            tenant_id: Tenant identifier for multi-tenant isolation
            auth_token: JWT authentication token for identity verification

        Returns:
            True if registration successful
        """
        # SECURITY: Verify the agent's JWT/SVID identity
        if auth_token and CRYPTO_AVAILABLE and CONFIG_AVAILABLE:
            try:
                public_key = settings.security.jwt_public_key if hasattr(settings.security, 'jwt_public_key') else CONSTITUTIONAL_HASH
                payload = CryptoService.verify_agent_token(auth_token, public_key)

                # Extract and validate identity
                token_agent_id = payload.get("agent_id")
                token_tenant_id = payload.get("tenant_id")

                if token_agent_id != agent_id:
                    logger.warning(f"Registration failed: agent_id mismatch ({agent_id} vs {token_agent_id})")
                    return False

                if tenant_id and token_tenant_id != tenant_id:
                    logger.warning(f"Registration failed: tenant_id mismatch ({tenant_id} vs {token_tenant_id})")
                    return False

                # Trust the token's claims
                tenant_id = token_tenant_id
                capabilities = payload.get("capabilities", capabilities)
                logger.info(f"Agent identity verified via token for {agent_id}")
            except Exception as e:
                logger.error(f"Agent registration identity validation error: {e}")
                return False
        elif auth_token:
            logger.warning("Auth token provided but CryptoService or Config not available")
        elif self._use_dynamic_policy:
            # Require identity in dynamic mode
            logger.warning(f"Registration rejected: Auth token required for agent {agent_id} in dynamic mode")
            return False

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
        }
        logger.info(f"Agent registered: {agent_id} (type: {agent_type}, tenant: {tenant_id})")
        return True

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
                    "tenant.id": message.tenant_id or "default"
                }
            ):
                return await self._do_send_message(message)
        else:
            return await self._do_send_message(message)

    async def _do_send_message(self, message: AgentMessage) -> ValidationResult:
        """Internal message sending logic."""
        if OTEL_ENABLED and QUEUE_DEPTH:
            QUEUE_DEPTH.add(1, {"tenant_id": message.tenant_id or "default"})

        try:
            # Multi-tenant isolation check
            tenant_errors = self._validate_tenant_consistency(message)
            if tenant_errors:
                self._metrics["messages_failed"] += 1
                message.status = MessageStatus.FAILED
                return ValidationResult(is_valid=False, errors=tenant_errors)

            # Constitutional validation using processor
            result = await self._processor.process(message)

            # Audit reporting (asynchronous fire-and-forget)
            if self._audit_client:
                asyncio.create_task(self._audit_client.report_validation(result))

            # Deliberation Logic (Impact Scoring)
            if self._deliberation_queue and result.metadata.get("impact_score", 0.0) >= 0.8:
                logger.info(f"Message {message.message_id} diverted to deliberation (Score: {result.metadata['impact_score']})")
                await self._deliberation_queue.enqueue(message, metadata={"impact_score": result.metadata["impact_score"]})
                result.status = MessageStatus.PENDING_DELIBERATION
                return result

            if result.is_valid:
                # Dispatch via Kafka if enabled
                if self._kafka_bus:
                    success = await self._kafka_bus.send_message(message)
                    if not success:
                        self._metrics["messages_failed"] += 1
                        return ValidationResult(is_valid=False, errors=["Kafka delivery failed"])

                # Route locally for immediate handlers
                await self._router.route(message, self._registry)

                # Deliver to internal queue if Kafka is not enabled
                if not self._use_kafka:
                    await self._message_queue.put(message)

                # Check if recipient exists (warning only)
                if message.to_agent and message.to_agent not in self._agents:
                    logger.debug(f"Recipient agent not found locally: {message.to_agent}")

                self._metrics["messages_sent"] += 1
            else:
                self._metrics["messages_failed"] += 1

            return result
        finally:
            if OTEL_ENABLED and QUEUE_DEPTH:
                QUEUE_DEPTH.add(-1, {"tenant_id": message.tenant_id or "default"})

    @staticmethod
    def _normalize_tenant_id(tenant_id: Optional[str]) -> Optional[str]:
        """Normalize tenant identifiers to a canonical optional value."""
        return tenant_id or None

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

        for agent_id, info in self._agents.items():
            agent_tenant = info.get("tenant_id")

            # STRICT MULTI-TENANT ISOLATION
            if message.tenant_id:
                if agent_tenant != message.tenant_id:
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
        """Get bus metrics synchronously.

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
