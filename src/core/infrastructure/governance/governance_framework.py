"""
ACGS-2 Governance Framework
Constitutional Hash: cdd01ef066bc6cf2

Provides core governance framework initialization, state management,
policy loading, and audit trail capabilities for constitutional AI governance.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class GovernanceState(Enum):
    """Governance framework state."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    SUSPENDED = "suspended"
    SHUTDOWN = "shutdown"


class PolicyLoadStatus(Enum):
    """Policy loading status."""

    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    OUTDATED = "outdated"


@dataclass
class GovernanceConfiguration:
    """Governance framework configuration."""

    constitutional_hash: str
    tenant_id: str = "default"
    environment: str = "development"

    # Policy configuration
    policy_refresh_interval: int = 300  # 5 minutes
    policy_cache_ttl: int = 3600  # 1 hour
    max_policy_size_kb: int = 1024  # 1 MB

    # Audit configuration
    audit_enabled: bool = True
    audit_retention_days: int = 90
    audit_buffer_size: int = 100
    audit_flush_interval: int = 30  # seconds

    # Performance configuration
    max_concurrent_evaluations: int = 100
    evaluation_timeout_ms: int = 5000
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_time: int = 60

    # Feature flags
    enable_ml_scoring: bool = True
    enable_blockchain_anchoring: bool = True
    enable_human_review_escalation: bool = True
    strict_mode: bool = False

    def validate(self) -> bool:
        """Validate configuration values."""
        if not self.constitutional_hash or len(self.constitutional_hash) < 8:
            raise ValueError("Invalid constitutional hash")
        if self.policy_refresh_interval < 10:
            raise ValueError("Policy refresh interval must be at least 10 seconds")
        if self.max_concurrent_evaluations < 1:
            raise ValueError("Max concurrent evaluations must be at least 1")
        if self.evaluation_timeout_ms < 100:
            raise ValueError("Evaluation timeout must be at least 100ms")
        return True


@dataclass
class AuditEntry:
    """Audit trail entry."""

    id: str
    timestamp: datetime
    action: str
    actor_id: str
    resource_type: str
    resource_id: str
    outcome: str
    constitutional_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tenant_id: str = "default"


@dataclass
class Policy:
    """Policy definition."""

    id: str
    name: str
    version: str
    content: str
    policy_type: str
    constitutional_hash: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuditTrailManager:
    """Manages governance audit trails."""

    def __init__(self, config: GovernanceConfiguration):
        self.config = config
        self._buffer: List[AuditEntry] = []
        self._lock = threading.Lock()
        self._flush_thread: Optional[asyncio.Task] = None
        self._running = False
        self._persistence_handler: Optional[Callable[[List[AuditEntry]], bool]] = None

    def start(self) -> None:
        """Start the audit trail manager."""
        if self._running:
            return

        self._running = True
        if self.config.audit_enabled:
            import asyncio
            self._flush_thread = asyncio.create_task(self._background_flush_loop())
            logger.info("Audit trail manager started")

    def stop(self) -> None:
        """Stop the audit trail manager."""
        self._running = False
        if self._flush_thread:
            self._flush_thread.cancel()
            try:
                # We don't necessarily need to await here if called from synchronous cleanup,
                # but in async context it should be awaited.
                pass
            except asyncio.CancelledError:
                pass
        # Final flush
        self._flush_buffer()
        logger.info("Audit trail manager stopped")

    def record(
        self,
        action: str,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        outcome: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Record an audit entry."""
        if not self.config.audit_enabled:
            return None

        entry = AuditEntry(
            id=f"audit-{int(time.time() * 1000000)}",
            timestamp=datetime.now(timezone.utc),
            action=action,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            constitutional_hash=self.config.constitutional_hash,
            metadata=metadata or {},
            tenant_id=self.config.tenant_id,
        )

        with self._lock:
            self._buffer.append(entry)

            # Auto-flush if buffer is full
            if len(self._buffer) >= self.config.audit_buffer_size:
                self._flush_buffer()

        return entry

    def get_entries(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Retrieve audit entries with optional filtering."""
        with self._lock:
            entries = list(self._buffer)

        # Apply filters
        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]
        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]
        if action:
            entries = [e for e in entries if e.action == action]
        if actor_id:
            entries = [e for e in entries if e.actor_id == actor_id]

        # Sort by timestamp descending and limit
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def set_persistence_handler(self, handler: Callable[[List[AuditEntry]], bool]) -> None:
        """Set a custom persistence handler for audit entries."""
        self._persistence_handler = handler

    def _flush_buffer(self) -> None:
        """Flush buffered entries to persistent storage."""
        with self._lock:
            if not self._buffer:
                return

            entries_to_flush = list(self._buffer)
            self._buffer.clear()

        if self._persistence_handler:
            try:
                success = self._persistence_handler(entries_to_flush)
                if not success:
                    logger.warning("Failed to persist audit entries")
                    # Re-add to buffer on failure
                    with self._lock:
                        self._buffer.extend(entries_to_flush)
            except Exception as e:
                logger.error(f"Error flushing audit buffer: {e}")
                with self._lock:
                    self._buffer.extend(entries_to_flush)

    async def _background_flush_loop(self) -> None:
        """Background loop for periodic buffer flushing."""
        import asyncio
        while self._running:
            try:
                await asyncio.sleep(self.config.audit_flush_interval)
                self._flush_buffer()
            except Exception as e:
                logger.error(f"Background flush error: {e}")
                await asyncio.sleep(5)  # Back off on errors


class PolicyLoader:
    """Loads and manages governance policies."""

    def __init__(self, config: GovernanceConfiguration):
        self.config = config
        self._policies: Dict[str, Policy] = {}
        self._lock = threading.Lock()
        self._status = PolicyLoadStatus.NOT_LOADED
        self._last_refresh: Optional[datetime] = None
        self._policy_source: Optional[Callable[[], List[Dict]]] = None
        self._refresh_thread: Optional[asyncio.Task] = None
        self._running = False

    @property
    def status(self) -> PolicyLoadStatus:
        """Get current policy load status."""
        return self._status

    @property
    def policy_count(self) -> int:
        """Get number of loaded policies."""
        with self._lock:
            return len(self._policies)

    def start(self) -> None:
        """Start the policy loader."""
        if self._running:
            return

        self._running = True
        import asyncio
        self._refresh_thread = asyncio.create_task(self._background_refresh_loop())
        logger.info("Policy loader started")

    def stop(self) -> None:
        """Stop the policy loader."""
        self._running = False
        if self._refresh_thread:
            self._refresh_thread.cancel()
        logger.info("Policy loader stopped")

    def set_policy_source(self, source: Callable[[], List[Dict]]) -> None:
        """Set the policy source function."""
        self._policy_source = source

    async def load_policies(self) -> bool:
        """Load policies from the configured source."""
        self._status = PolicyLoadStatus.LOADING

        try:
            if self._policy_source:
                policy_data = self._policy_source()
            else:
                policy_data = await self._load_default_policies()

            with self._lock:
                self._policies.clear()
                for data in policy_data:
                    policy = self._parse_policy(data)
                    if policy:
                        self._policies[policy.id] = policy

            self._status = PolicyLoadStatus.LOADED
            self._last_refresh = datetime.now(timezone.utc)
            logger.info(f"Loaded {len(self._policies)} policies")
            return True

        except Exception as e:
            self._status = PolicyLoadStatus.FAILED
            logger.error(f"Failed to load policies: {e}")
            return False

    async def _load_default_policies(self) -> List[Dict]:
        """Load default policies from configuration."""
        # Default policies can be loaded from files, environment, etc.
        return [
            {
                "id": "default-governance",
                "name": "Default Governance Policy",
                "version": "1.0.0",
                "content": "package governance.default\ndefault allow = false",
                "policy_type": "rego",
                "is_active": True,
                "priority": 0,
            }
        ]

    def _parse_policy(self, data: Dict) -> Optional[Policy]:
        """Parse policy data into a Policy object."""
        try:
            now = datetime.now(timezone.utc)
            return Policy(
                id=data["id"],
                name=data["name"],
                version=data.get("version", "1.0.0"),
                content=data["content"],
                policy_type=data.get("policy_type", "rego"),
                constitutional_hash=self.config.constitutional_hash,
                created_at=data.get("created_at", now),
                updated_at=data.get("updated_at", now),
                is_active=data.get("is_active", True),
                priority=data.get("priority", 0),
                metadata=data.get("metadata", {}),
            )
        except KeyError as e:
            logger.error(f"Missing required policy field: {e}")
            return None

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        with self._lock:
            return self._policies.get(policy_id)

    def get_active_policies(self) -> List[Policy]:
        """Get all active policies sorted by priority."""
        with self._lock:
            active = [p for p in self._policies.values() if p.is_active]
            active.sort(key=lambda p: p.priority, reverse=True)
            return active

    def add_policy(self, policy: Policy) -> bool:
        """Add or update a policy."""
        # Validate policy size
        content_size_kb = len(policy.content.encode("utf-8")) / 1024
        if content_size_kb > self.config.max_policy_size_kb:
            logger.error(f"Policy {policy.id} exceeds max size")
            return False

        with self._lock:
            self._policies[policy.id] = policy

        logger.info(f"Added/updated policy: {policy.id}")
        return True

    def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy by ID."""
        with self._lock:
            if policy_id in self._policies:
                del self._policies[policy_id]
                logger.info(f"Removed policy: {policy_id}")
                return True
        return False

    async def _background_refresh_loop(self) -> None:
        """Background loop for periodic policy refresh."""
        import asyncio
        while self._running:
            try:
                await asyncio.sleep(self.config.policy_refresh_interval)

                # Check if refresh is needed
                if self._should_refresh():
                    await self.load_policies()

            except Exception as e:
                logger.error(f"Policy refresh error: {e}")
                await asyncio.sleep(30)  # Back off on errors

    def _should_refresh(self) -> bool:
        """Check if policies should be refreshed."""
        if not self._last_refresh:
            return True

        elapsed = (datetime.now(timezone.utc) - self._last_refresh).total_seconds()
        return elapsed >= self.config.policy_cache_ttl


class GovernanceFramework:
    """Main governance framework for constitutional AI governance."""

    def __init__(self, config: GovernanceConfiguration):
        config.validate()

        self.config = config
        self._state = GovernanceState.UNINITIALIZED
        self._state_lock = threading.Lock()

        # Core components
        self.policy_loader = PolicyLoader(config)
        self.audit_manager = AuditTrailManager(config)

        # Circuit breaker state
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None

        # Callbacks
        self._state_change_callbacks: List[Callable[[GovernanceState], None]] = []

    @property
    def state(self) -> GovernanceState:
        """Get current framework state."""
        return self._state

    @property
    def is_ready(self) -> bool:
        """Check if framework is ready for operations."""
        return self._state == GovernanceState.READY

    @property
    def constitutional_hash(self) -> str:
        """Get the constitutional hash."""
        return self.config.constitutional_hash

    def _set_state(self, new_state: GovernanceState) -> None:
        """Update framework state and notify callbacks."""
        with self._state_lock:
            old_state = self._state
            self._state = new_state

        if old_state != new_state:
            logger.info(f"Governance state: {old_state.value} -> {new_state.value}")
            for callback in self._state_change_callbacks:
                try:
                    callback(new_state)
                except Exception as e:
                    logger.error(f"State change callback error: {e}")

    def on_state_change(self, callback: Callable[[GovernanceState], None]) -> None:
        """Register a state change callback."""
        self._state_change_callbacks.append(callback)

    async def initialize(self) -> bool:
        """Initialize the governance framework."""
        if self._state != GovernanceState.UNINITIALIZED:
            logger.warning(f"Framework already in state: {self._state.value}")
            return self._state == GovernanceState.READY

        self._set_state(GovernanceState.INITIALIZING)

        try:
            # Start components
            self.audit_manager.start()
            self.policy_loader.start()

            # Load initial policies
            if await self.policy_loader.load_policies():
                self._set_state(GovernanceState.READY)

                # Record initialization
                self.audit_manager.record(
                    action="GOVERNANCE_INITIALIZED",
                    actor_id="system",
                    resource_type="governance_framework",
                    resource_id=self.config.constitutional_hash,
                    outcome="success",
                )

                logger.info("Governance framework initialized successfully")
                return True
            else:
                # Policies failed to load - enter degraded mode
                self._set_state(GovernanceState.DEGRADED)
                logger.warning("Governance framework in degraded mode - policies failed to load")
                return False

        except Exception as e:
            self._set_state(GovernanceState.DEGRADED)
            logger.error(f"Governance initialization failed: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the governance framework gracefully."""
        if self._state == GovernanceState.SHUTDOWN:
            return

        logger.info("Shutting down governance framework")

        # Record shutdown
        self.audit_manager.record(
            action="GOVERNANCE_SHUTDOWN",
            actor_id="system",
            resource_type="governance_framework",
            resource_id=self.config.constitutional_hash,
            outcome="success",
        )

        # Stop components
        self.policy_loader.stop()
        self.audit_manager.stop()

        self._set_state(GovernanceState.SHUTDOWN)
        logger.info("Governance framework shutdown complete")

    def suspend(self) -> bool:
        """Suspend governance operations."""
        if self._state not in (GovernanceState.READY, GovernanceState.DEGRADED):
            return False

        self._set_state(GovernanceState.SUSPENDED)

        self.audit_manager.record(
            action="GOVERNANCE_SUSPENDED",
            actor_id="system",
            resource_type="governance_framework",
            resource_id=self.config.constitutional_hash,
            outcome="success",
        )

        return True

    def resume(self) -> bool:
        """Resume governance operations."""
        if self._state != GovernanceState.SUSPENDED:
            return False

        # Check if we should be in degraded mode
        if self.policy_loader.status != PolicyLoadStatus.LOADED:
            self._set_state(GovernanceState.DEGRADED)
        else:
            self._set_state(GovernanceState.READY)

        self.audit_manager.record(
            action="GOVERNANCE_RESUMED",
            actor_id="system",
            resource_type="governance_framework",
            resource_id=self.config.constitutional_hash,
            outcome="success",
        )

        return True

    def record_failure(self) -> bool:
        """Record a failure for circuit breaker."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.config.circuit_breaker_threshold:
            logger.warning("Circuit breaker threshold reached - entering degraded mode")
            self._set_state(GovernanceState.DEGRADED)
            return True
        return False

    def record_success(self) -> None:
        """Record a success to reset circuit breaker."""
        self._failure_count = max(0, self._failure_count - 1)

        # Check if we can recover from degraded mode
        if self._state == GovernanceState.DEGRADED:
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.circuit_breaker_reset_time:
                    if self.policy_loader.status == PolicyLoadStatus.LOADED:
                        logger.info("Circuit breaker reset - returning to ready state")
                        self._set_state(GovernanceState.READY)
                        self._failure_count = 0

    def get_status(self) -> Dict[str, Any]:
        """Get current framework status."""
        return {
            "state": self._state.value,
            "constitutional_hash": self.config.constitutional_hash,
            "tenant_id": self.config.tenant_id,
            "environment": self.config.environment,
            "policy_count": self.policy_loader.policy_count,
            "policy_status": self.policy_loader.status.value,
            "audit_enabled": self.config.audit_enabled,
            "strict_mode": self.config.strict_mode,
            "failure_count": self._failure_count,
            "is_ready": self.is_ready,
        }


# Global instance
_governance_framework: Optional[GovernanceFramework] = None
_init_lock = threading.Lock()


async def initialize_governance(
    config: GovernanceConfiguration,
) -> GovernanceFramework:
    """Initialize the global governance framework."""
    global _governance_framework

    with _init_lock:
        if _governance_framework is None:
            _governance_framework = GovernanceFramework(config)
            await _governance_framework.initialize()
        elif _governance_framework.config.constitutional_hash != config.constitutional_hash:
            # Different constitutional hash - reinitialize
            await _governance_framework.shutdown()
            _governance_framework = GovernanceFramework(config)
            await _governance_framework.initialize()

    return _governance_framework


def get_governance_framework() -> Optional[GovernanceFramework]:
    """Get the global governance framework instance."""
    return _governance_framework


async def shutdown_governance() -> None:
    """Shutdown the global governance framework."""
    global _governance_framework

    with _init_lock:
        if _governance_framework:
            await _governance_framework.shutdown()
            _governance_framework = None
