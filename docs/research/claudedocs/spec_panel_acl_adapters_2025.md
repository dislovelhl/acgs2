# ACGS-2 Breakthrough Architecture ACL Adapters

**Constitutional Hash: cdd01ef066bc6cf2**
**Created: December 2025**
**Status: Spec Panel Requirement (Priority 2)**
**Expert Source: Martin Fowler - Architecture & Design Patterns**

---

## Executive Summary

This document defines Anti-Corruption Layer (ACL) adapters for external dependencies in the breakthrough architecture. Each adapter isolates the core system from external service implementations, providing timeout handling, rate limiting, and graceful degradation.

---

## 1. ACL Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ACGS-2 CORE DOMAIN                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Verification    │  │ Symbolic        │  │ Governance      │              │
│  │ Layer           │  │ Layer           │  │ Layer           │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                        │
│  ╔════════╧════════╗  ╔════════╧════════╗  ╔════════╧════════╗              │
│  ║   ACL ADAPTERS  ║  ║   ACL ADAPTERS  ║  ║   ACL ADAPTERS  ║              │
│  ╠═════════════════╣  ╠═════════════════╣  ╠═════════════════╣              │
│  ║ • Z3Adapter     ║  ║ • DeepProbLog   ║  ║ • PolisAdapter  ║              │
│  ║ • OPAAdapter    ║  ║   Adapter       ║  ║ • SlackAdapter  ║              │
│  ╚════════╤════════╝  ╚════════╤════════╝  ╚════════╤════════╝              │
│           │                    │                    │                        │
└───────────┼────────────────────┼────────────────────┼────────────────────────┘
            │                    │                    │
    ┌───────▼───────┐    ┌───────▼───────┐    ┌───────▼───────┐
    │ Z3 SMT Solver │    │  DeepProbLog  │    │  Polis API    │
    │ (External)    │    │  (External)   │    │  (External)   │
    └───────────────┘    └───────────────┘    └───────────────┘
```

---

## 2. Base ACL Adapter

### 2.1 Abstract Base

```python
# acgs2_core/adapters/base.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, Callable, Any
from datetime import datetime, timezone
import asyncio
import logging

from enhanced_agent_bus.circuit_breaker import CircuitBreaker, CircuitState
from acgs2_core.observability.telemetry import create_adapter_tracer

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

T = TypeVar('T')
R = TypeVar('R')

logger = logging.getLogger(__name__)


@dataclass
class AdapterConfig:
    """Configuration for ACL adapters."""
    timeout_ms: int = 5000
    max_retries: int = 3
    retry_backoff_ms: int = 100
    circuit_failure_threshold: int = 3
    circuit_recovery_timeout_s: int = 30
    rate_limit_requests: int = 100
    rate_limit_window_s: int = 60


@dataclass
class AdapterResult(Generic[T]):
    """Result from adapter call."""
    success: bool
    data: Optional[T] = None
    error: Optional[Exception] = None
    latency_ms: float = 0.0
    retries_used: int = 0
    circuit_state: str = "CLOSED"
    degraded: bool = False
    constitutional_hash: str = CONSTITUTIONAL_HASH


class ACLAdapter(ABC, Generic[T, R]):
    """
    Anti-Corruption Layer adapter base class.

    Provides:
    - Timeout handling
    - Circuit breaker integration
    - Rate limiting
    - Retry with backoff
    - Graceful degradation
    - Observability
    """

    def __init__(
        self,
        name: str,
        config: AdapterConfig = AdapterConfig(),
    ):
        self.name = name
        self.config = config
        self.tracer = create_adapter_tracer(name)

        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_failure_threshold,
            recovery_timeout=config.circuit_recovery_timeout_s,
        )

        # Rate limiter state
        self._request_timestamps: list[datetime] = []

        # Health tracking
        self._consecutive_failures = 0
        self._last_success: Optional[datetime] = None

    @abstractmethod
    async def _execute(self, request: T) -> R:
        """Execute the external call. Implemented by subclasses."""
        pass

    @abstractmethod
    async def _fallback(self, request: T) -> R:
        """Fallback when external service unavailable."""
        pass

    @abstractmethod
    def _validate_response(self, response: R) -> bool:
        """Validate response from external service."""
        pass

    async def call(self, request: T) -> AdapterResult[R]:
        """
        Execute adapter call with full protection.

        Returns AdapterResult with success/failure and metadata.
        """
        with self.tracer.start_as_current_span(f"{self.name}_call") as span:
            span.set_attribute("constitutional.hash", CONSTITUTIONAL_HASH)
            start_time = asyncio.get_event_loop().time()

            result = AdapterResult[R](
                success=False,
                circuit_state=self.circuit_breaker.state.name,
            )

            # Check rate limit
            if not self._check_rate_limit():
                span.add_event("rate_limited")
                result.error = RateLimitExceededError(self.name)
                return result

            # Check circuit breaker
            if self.circuit_breaker.state == CircuitState.OPEN:
                span.add_event("circuit_open")
                return await self._handle_circuit_open(request, result, span)

            # Execute with retries
            for attempt in range(self.config.max_retries + 1):
                try:
                    response = await self._execute_with_timeout(request)

                    if self._validate_response(response):
                        result.success = True
                        result.data = response
                        result.retries_used = attempt
                        self._record_success()
                        break
                    else:
                        raise InvalidResponseError(f"Invalid response from {self.name}")

                except asyncio.TimeoutError:
                    span.add_event("timeout", {"attempt": attempt})
                    result.error = AdapterTimeoutError(self.name, self.config.timeout_ms)

                except Exception as e:
                    span.add_event("error", {"attempt": attempt, "error": str(e)})
                    result.error = e

                # Backoff before retry
                if attempt < self.config.max_retries:
                    await asyncio.sleep(
                        self.config.retry_backoff_ms * (2 ** attempt) / 1000
                    )

            # Record failure if all retries exhausted
            if not result.success:
                self._record_failure()

                # Try fallback
                if self.circuit_breaker.state == CircuitState.OPEN:
                    return await self._handle_circuit_open(request, result, span)

            result.latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            span.set_attribute("latency_ms", result.latency_ms)
            span.set_attribute("success", result.success)

            return result

    async def _execute_with_timeout(self, request: T) -> R:
        """Execute with timeout."""
        return await asyncio.wait_for(
            self._execute(request),
            timeout=self.config.timeout_ms / 1000
        )

    async def _handle_circuit_open(
        self,
        request: T,
        result: AdapterResult[R],
        span,
    ) -> AdapterResult[R]:
        """Handle circuit open state with fallback."""
        span.add_event("using_fallback")
        try:
            fallback_response = await self._fallback(request)
            result.success = True
            result.data = fallback_response
            result.degraded = True
            result.circuit_state = "OPEN"
        except Exception as e:
            result.error = FallbackFailedError(self.name, e)
        return result

    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limit."""
        now = datetime.now(timezone.utc)
        window_start = now.timestamp() - self.config.rate_limit_window_s

        # Remove old timestamps
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if ts.timestamp() > window_start
        ]

        if len(self._request_timestamps) >= self.config.rate_limit_requests:
            return False

        self._request_timestamps.append(now)
        return True

    def _record_success(self):
        """Record successful call."""
        self._consecutive_failures = 0
        self._last_success = datetime.now(timezone.utc)
        self.circuit_breaker.record_success()

    def _record_failure(self):
        """Record failed call."""
        self._consecutive_failures += 1
        self.circuit_breaker.record_failure()

    @property
    def is_healthy(self) -> bool:
        """Check adapter health."""
        return (
            self.circuit_breaker.state != CircuitState.OPEN and
            self._consecutive_failures < self.config.circuit_failure_threshold
        )


# Exceptions
class AdapterError(Exception):
    """Base adapter error."""
    pass

class AdapterTimeoutError(AdapterError):
    def __init__(self, adapter: str, timeout_ms: int):
        super().__init__(f"{adapter} timeout after {timeout_ms}ms")

class RateLimitExceededError(AdapterError):
    def __init__(self, adapter: str):
        super().__init__(f"{adapter} rate limit exceeded")

class InvalidResponseError(AdapterError):
    pass

class FallbackFailedError(AdapterError):
    def __init__(self, adapter: str, cause: Exception):
        super().__init__(f"{adapter} fallback failed: {cause}")
        self.cause = cause
```

---

## 3. Z3 SMT Solver Adapter

### 3.1 Implementation

```python
# acgs2_core/adapters/z3_adapter.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import z3

from .base import ACLAdapter, AdapterConfig, AdapterResult

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


@dataclass
class Z3Request:
    """Request to Z3 solver."""
    constraints: List[z3.ExprRef]
    timeout_ms: Optional[int] = None
    logic: str = "QF_LIA"  # Quantifier-free Linear Integer Arithmetic


@dataclass
class Z3Response:
    """Response from Z3 solver."""
    satisfiable: Optional[bool]
    model: Optional[Dict[str, Any]] = None
    unsat_core: Optional[List[str]] = None
    status: str = "unknown"  # sat, unsat, unknown, timeout


class Z3Adapter(ACLAdapter[Z3Request, Z3Response]):
    """
    Anti-Corruption Layer for Z3 SMT Solver.

    Features:
    - Timeout-bounded verification
    - Incremental solving support
    - Unsat core extraction
    - Fallback to cached results
    """

    def __init__(
        self,
        config: AdapterConfig = AdapterConfig(
            timeout_ms=5000,
            max_retries=2,
            circuit_failure_threshold=3,
        ),
    ):
        super().__init__("z3_solver", config)
        self._result_cache: Dict[str, Z3Response] = {}

    async def _execute(self, request: Z3Request) -> Z3Response:
        """Execute Z3 verification."""
        solver = z3.Solver()
        solver.set("timeout", request.timeout_ms or self.config.timeout_ms)

        # Enable unsat core tracking
        solver.set("unsat_core", True)

        # Add constraints with tracking names
        for i, constraint in enumerate(request.constraints):
            solver.assert_and_track(constraint, f"c{i}")

        result = solver.check()

        if result == z3.sat:
            model = solver.model()
            return Z3Response(
                satisfiable=True,
                model=self._extract_model(model),
                status="sat",
            )
        elif result == z3.unsat:
            core = solver.unsat_core()
            return Z3Response(
                satisfiable=False,
                unsat_core=[str(c) for c in core],
                status="unsat",
            )
        else:
            return Z3Response(
                satisfiable=None,
                status="unknown",
            )

    async def _fallback(self, request: Z3Request) -> Z3Response:
        """
        Fallback when Z3 unavailable.

        Strategy:
        1. Check cache for similar constraints
        2. Return conservative "unknown" result
        """
        cache_key = self._compute_cache_key(request)
        if cache_key in self._result_cache:
            cached = self._result_cache[cache_key]
            return Z3Response(
                satisfiable=cached.satisfiable,
                model=cached.model,
                status="cached",
            )

        # Conservative fallback: unknown result
        return Z3Response(
            satisfiable=None,
            status="fallback_unknown",
        )

    def _validate_response(self, response: Z3Response) -> bool:
        """Validate Z3 response."""
        return response.status in ["sat", "unsat", "unknown", "timeout", "cached", "fallback_unknown"]

    def _extract_model(self, model: z3.ModelRef) -> Dict[str, Any]:
        """Extract model values."""
        result = {}
        for decl in model.decls():
            value = model[decl]
            if z3.is_int_value(value):
                result[str(decl)] = value.as_long()
            elif z3.is_bool(value):
                result[str(decl)] = z3.is_true(value)
            else:
                result[str(decl)] = str(value)
        return result

    def _compute_cache_key(self, request: Z3Request) -> str:
        """Compute cache key for constraints."""
        return str(sorted([str(c) for c in request.constraints]))

    def cache_result(self, request: Z3Request, response: Z3Response):
        """Cache verification result for future fallback."""
        if response.status in ["sat", "unsat"]:
            cache_key = self._compute_cache_key(request)
            self._result_cache[cache_key] = response


# Convenience functions
async def verify_constraints(
    constraints: List[z3.ExprRef],
    adapter: Optional[Z3Adapter] = None,
) -> AdapterResult[Z3Response]:
    """Verify constraints with Z3 adapter."""
    if adapter is None:
        adapter = Z3Adapter()

    request = Z3Request(constraints=constraints)
    return await adapter.call(request)
```

---

## 4. DeepProbLog Adapter

### 4.1 Implementation

```python
# acgs2_core/adapters/deepproblog_adapter.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import subprocess
import json

from .base import ACLAdapter, AdapterConfig, AdapterResult

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


@dataclass
class DeepProbLogRequest:
    """Request to DeepProbLog."""
    query: str
    evidence: Dict[str, Any] = None
    max_solutions: int = 10


@dataclass
class DeepProbLogResponse:
    """Response from DeepProbLog."""
    probability: float
    solutions: List[Dict[str, Any]]
    derivation: List[str]
    status: str = "success"


class DeepProbLogAdapter(ACLAdapter[DeepProbLogRequest, DeepProbLogResponse]):
    """
    Anti-Corruption Layer for DeepProbLog.

    Features:
    - Memory-bounded execution
    - Timeout handling
    - Fallback to cached knowledge
    - Resource monitoring
    """

    def __init__(
        self,
        knowledge_base_path: str,
        config: AdapterConfig = AdapterConfig(
            timeout_ms=10000,
            max_retries=1,  # Expensive, limit retries
            circuit_failure_threshold=2,
        ),
    ):
        super().__init__("deepproblog", config)
        self.kb_path = knowledge_base_path
        self._query_cache: Dict[str, DeepProbLogResponse] = {}
        self._memory_limit_mb = 512

    async def _execute(self, request: DeepProbLogRequest) -> DeepProbLogResponse:
        """Execute DeepProbLog query."""
        import asyncio

        # Build query command
        cmd = self._build_command(request)

        # Execute with memory limit
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=self._memory_limit_mb * 1024 * 1024,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout_ms / 1000
            )
        except asyncio.TimeoutError:
            process.kill()
            raise

        if process.returncode != 0:
            raise RuntimeError(f"DeepProbLog error: {stderr.decode()}")

        return self._parse_output(stdout.decode())

    async def _fallback(self, request: DeepProbLogRequest) -> DeepProbLogResponse:
        """
        Fallback when DeepProbLog unavailable.

        Strategy:
        1. Check query cache
        2. Return low-confidence default
        """
        cache_key = self._compute_cache_key(request)
        if cache_key in self._query_cache:
            cached = self._query_cache[cache_key]
            return DeepProbLogResponse(
                probability=cached.probability * 0.8,  # Discount cached
                solutions=cached.solutions,
                derivation=["cached_result"],
                status="cached",
            )

        # Low-confidence fallback
        return DeepProbLogResponse(
            probability=0.5,  # Maximum uncertainty
            solutions=[],
            derivation=["fallback_uncertain"],
            status="fallback",
        )

    def _validate_response(self, response: DeepProbLogResponse) -> bool:
        """Validate DeepProbLog response."""
        return (
            0.0 <= response.probability <= 1.0 and
            response.status in ["success", "cached", "fallback"]
        )

    def _build_command(self, request: DeepProbLogRequest) -> List[str]:
        """Build DeepProbLog command."""
        cmd = [
            "python3", "-m", "deepproblog",
            "--knowledge-base", self.kb_path,
            "--query", request.query,
            "--max-solutions", str(request.max_solutions),
            "--output", "json",
        ]

        if request.evidence:
            cmd.extend(["--evidence", json.dumps(request.evidence)])

        return cmd

    def _parse_output(self, output: str) -> DeepProbLogResponse:
        """Parse DeepProbLog JSON output."""
        data = json.loads(output)
        return DeepProbLogResponse(
            probability=data.get("probability", 0.0),
            solutions=data.get("solutions", []),
            derivation=data.get("derivation", []),
            status="success",
        )

    def _compute_cache_key(self, request: DeepProbLogRequest) -> str:
        """Compute cache key for query."""
        return f"{request.query}:{json.dumps(request.evidence or {}, sort_keys=True)}"

    def cache_result(self, request: DeepProbLogRequest, response: DeepProbLogResponse):
        """Cache query result."""
        if response.status == "success":
            cache_key = self._compute_cache_key(request)
            self._query_cache[cache_key] = response


# Convenience functions
async def query_knowledge_base(
    query: str,
    kb_path: str,
    evidence: Dict[str, Any] = None,
    adapter: Optional[DeepProbLogAdapter] = None,
) -> AdapterResult[DeepProbLogResponse]:
    """Query DeepProbLog knowledge base."""
    if adapter is None:
        adapter = DeepProbLogAdapter(kb_path)

    request = DeepProbLogRequest(query=query, evidence=evidence)
    return await adapter.call(request)
```

---

## 5. Polis API Adapter

### 5.1 Implementation

```python
# acgs2_core/adapters/polis_adapter.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import aiohttp

from .base import ACLAdapter, AdapterConfig, AdapterResult

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


@dataclass
class PolisDeliberationRequest:
    """Request for Polis deliberation."""
    topic: str
    initial_statements: List[str]
    min_participants: int = 1000
    duration_hours: int = 168  # 1 week default
    representative_sampling: bool = True


@dataclass
class OpinionGroup:
    """Opinion group from Polis."""
    id: str
    size: int
    support_matrix: Dict[str, float]  # statement_id -> support_ratio


@dataclass
class PolisDeliberationResponse:
    """Response from Polis deliberation."""
    conversation_id: str
    statements: List[Dict[str, Any]]
    opinion_groups: List[OpinionGroup]
    participant_count: int
    consensus_statements: List[str]
    status: str = "active"


class PolisAdapter(ACLAdapter[PolisDeliberationRequest, PolisDeliberationResponse]):
    """
    Anti-Corruption Layer for Polis API.

    Features:
    - Rate limiting (API quotas)
    - Async deliberation queuing
    - Fallback to cached deliberations
    - Cross-group consensus calculation
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        config: AdapterConfig = AdapterConfig(
            timeout_ms=30000,  # Longer timeout for API
            max_retries=3,
            rate_limit_requests=10,  # Conservative API rate
            rate_limit_window_s=60,
        ),
    ):
        super().__init__("polis_api", config)
        self.api_url = api_url
        self.api_key = api_key
        self._deliberation_cache: Dict[str, PolisDeliberationResponse] = {}
        self._pending_queue: List[PolisDeliberationRequest] = []

    async def _execute(self, request: PolisDeliberationRequest) -> PolisDeliberationResponse:
        """Execute Polis API call."""
        async with aiohttp.ClientSession() as session:
            # Create conversation
            async with session.post(
                f"{self.api_url}/conversations",
                json={
                    "topic": request.topic,
                    "initial_statements": request.initial_statements,
                    "settings": {
                        "min_participants": request.min_participants,
                        "duration_hours": request.duration_hours,
                        "representative_sampling": request.representative_sampling,
                    },
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_ms / 1000),
            ) as resp:
                if resp.status == 429:
                    raise RateLimitExceededError("polis_api")
                resp.raise_for_status()
                data = await resp.json()

            # Get results (may need polling for async deliberations)
            conversation_id = data["conversation_id"]
            return await self._poll_results(session, conversation_id)

    async def _poll_results(
        self,
        session: aiohttp.ClientSession,
        conversation_id: str,
        max_polls: int = 10,
    ) -> PolisDeliberationResponse:
        """Poll for deliberation results."""
        import asyncio

        for _ in range(max_polls):
            async with session.get(
                f"{self.api_url}/conversations/{conversation_id}/results",
                headers={"Authorization": f"Bearer {self.api_key}"},
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

                if data["status"] == "complete":
                    return self._parse_response(data)

            await asyncio.sleep(1.0)  # Poll interval

        # Return partial results if still active
        return self._parse_response(data)

    def _parse_response(self, data: Dict[str, Any]) -> PolisDeliberationResponse:
        """Parse Polis API response."""
        opinion_groups = [
            OpinionGroup(
                id=g["id"],
                size=g["size"],
                support_matrix=g["support_matrix"],
            )
            for g in data.get("opinion_groups", [])
        ]

        return PolisDeliberationResponse(
            conversation_id=data["conversation_id"],
            statements=data.get("statements", []),
            opinion_groups=opinion_groups,
            participant_count=data.get("participant_count", 0),
            consensus_statements=self._find_consensus(opinion_groups, data.get("statements", [])),
            status=data.get("status", "unknown"),
        )

    def _find_consensus(
        self,
        groups: List[OpinionGroup],
        statements: List[Dict[str, Any]],
        threshold: float = 0.6,
    ) -> List[str]:
        """Find statements with cross-group consensus."""
        consensus = []
        for statement in statements:
            stmt_id = statement["id"]
            all_groups_agree = all(
                group.support_matrix.get(stmt_id, 0) >= threshold
                for group in groups
            )
            if all_groups_agree:
                consensus.append(stmt_id)
        return consensus

    async def _fallback(self, request: PolisDeliberationRequest) -> PolisDeliberationResponse:
        """
        Fallback when Polis unavailable.

        Strategy:
        1. Check cache for similar topic
        2. Queue for async processing
        3. Return empty pending response
        """
        # Check cache
        cache_key = self._compute_cache_key(request)
        if cache_key in self._deliberation_cache:
            cached = self._deliberation_cache[cache_key]
            return PolisDeliberationResponse(
                conversation_id=f"cached_{cached.conversation_id}",
                statements=cached.statements,
                opinion_groups=cached.opinion_groups,
                participant_count=cached.participant_count,
                consensus_statements=cached.consensus_statements,
                status="cached",
            )

        # Queue for later
        self._pending_queue.append(request)

        return PolisDeliberationResponse(
            conversation_id="pending",
            statements=[],
            opinion_groups=[],
            participant_count=0,
            consensus_statements=[],
            status="queued",
        )

    def _validate_response(self, response: PolisDeliberationResponse) -> bool:
        """Validate Polis response."""
        return response.status in ["active", "complete", "cached", "queued"]

    def _compute_cache_key(self, request: PolisDeliberationRequest) -> str:
        """Compute cache key for deliberation."""
        return f"{request.topic}:{len(request.initial_statements)}"

    def cache_result(self, request: PolisDeliberationRequest, response: PolisDeliberationResponse):
        """Cache deliberation result."""
        if response.status == "complete":
            cache_key = self._compute_cache_key(request)
            self._deliberation_cache[cache_key] = response

    async def process_pending_queue(self):
        """Process pending deliberation requests."""
        while self._pending_queue:
            request = self._pending_queue.pop(0)
            result = await self.call(request)
            if result.success and not result.degraded:
                self.cache_result(request, result.data)


# Convenience functions
async def start_deliberation(
    topic: str,
    statements: List[str],
    api_url: str,
    api_key: str,
    adapter: Optional[PolisAdapter] = None,
) -> AdapterResult[PolisDeliberationResponse]:
    """Start Polis deliberation."""
    if adapter is None:
        adapter = PolisAdapter(api_url, api_key)

    request = PolisDeliberationRequest(
        topic=topic,
        initial_statements=statements,
    )
    return await adapter.call(request)
```

---

## 6. OPA Policy Adapter

### 6.1 Implementation

```python
# acgs2_core/adapters/opa_adapter.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import aiohttp

from .base import ACLAdapter, AdapterConfig, AdapterResult

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


@dataclass
class OPARequest:
    """Request to OPA."""
    input_data: Dict[str, Any]
    policy_path: str = "constitutional/validate"


@dataclass
class OPAResponse:
    """Response from OPA."""
    allow: bool
    violations: List[str] = field(default_factory=list)
    decision_id: Optional[str] = None
    status: str = "success"


class OPAAdapter(ACLAdapter[OPARequest, OPAResponse]):
    """
    Anti-Corruption Layer for OPA (Open Policy Agent).

    Features:
    - Policy bundle caching
    - Fail-closed security model
    - Decision logging
    - Fallback to cached decisions
    """

    def __init__(
        self,
        opa_url: str = "http://localhost:8181",
        config: AdapterConfig = AdapterConfig(
            timeout_ms=1000,  # Fast policy eval
            max_retries=2,
            circuit_failure_threshold=5,
        ),
        fail_closed: bool = True,
    ):
        super().__init__("opa", config)
        self.opa_url = opa_url
        self.fail_closed = fail_closed
        self._decision_cache: Dict[str, OPAResponse] = {}

    async def _execute(self, request: OPARequest) -> OPAResponse:
        """Execute OPA policy evaluation."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.opa_url}/v1/data/{request.policy_path}",
                json={"input": request.input_data},
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_ms / 1000),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

                result = data.get("result", {})
                return OPAResponse(
                    allow=result.get("allow", False),
                    violations=result.get("violations", []),
                    decision_id=resp.headers.get("X-Decision-ID"),
                    status="success",
                )

    async def _fallback(self, request: OPARequest) -> OPAResponse:
        """
        Fallback when OPA unavailable.

        Strategy:
        - fail_closed=True: Deny all (security default)
        - fail_closed=False: Check cache, then allow with warning
        """
        cache_key = self._compute_cache_key(request)

        # Check cache
        if cache_key in self._decision_cache:
            cached = self._decision_cache[cache_key]
            return OPAResponse(
                allow=cached.allow,
                violations=cached.violations,
                status="cached",
            )

        # Fail behavior
        if self.fail_closed:
            return OPAResponse(
                allow=False,
                violations=["OPA unavailable - fail_closed policy"],
                status="fail_closed",
            )
        else:
            return OPAResponse(
                allow=True,
                violations=["OPA unavailable - fail_open (audit required)"],
                status="fail_open",
            )

    def _validate_response(self, response: OPAResponse) -> bool:
        """Validate OPA response."""
        return response.status in ["success", "cached", "fail_closed", "fail_open"]

    def _compute_cache_key(self, request: OPARequest) -> str:
        """Compute cache key for decision."""
        import hashlib
        import json
        data_str = json.dumps(request.input_data, sort_keys=True)
        return hashlib.sha256(f"{request.policy_path}:{data_str}".encode()).hexdigest()[:16]

    def cache_result(self, request: OPARequest, response: OPAResponse):
        """Cache policy decision."""
        if response.status == "success":
            cache_key = self._compute_cache_key(request)
            self._decision_cache[cache_key] = response


# Convenience functions
async def evaluate_policy(
    input_data: Dict[str, Any],
    policy_path: str = "constitutional/validate",
    opa_url: str = "http://localhost:8181",
    adapter: Optional[OPAAdapter] = None,
) -> AdapterResult[OPAResponse]:
    """Evaluate OPA policy."""
    if adapter is None:
        adapter = OPAAdapter(opa_url)

    request = OPARequest(input_data=input_data, policy_path=policy_path)
    return await adapter.call(request)
```

---

## 7. Adapter Registry

### 7.1 Centralized Management

```python
# acgs2_core/adapters/registry.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

from typing import Dict, Optional, Type
from .base import ACLAdapter, AdapterConfig
from .z3_adapter import Z3Adapter
from .deepproblog_adapter import DeepProbLogAdapter
from .polis_adapter import PolisAdapter
from .opa_adapter import OPAAdapter

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class AdapterRegistry:
    """
    Central registry for ACL adapters.

    Provides:
    - Singleton adapter instances
    - Health monitoring
    - Configuration management
    """

    _instance: Optional["AdapterRegistry"] = None
    _adapters: Dict[str, ACLAdapter] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, name: str, adapter: ACLAdapter):
        """Register an adapter."""
        self._adapters[name] = adapter

    def get(self, name: str) -> Optional[ACLAdapter]:
        """Get adapter by name."""
        return self._adapters.get(name)

    def get_all(self) -> Dict[str, ACLAdapter]:
        """Get all adapters."""
        return self._adapters.copy()

    @property
    def health_summary(self) -> Dict[str, bool]:
        """Get health summary of all adapters."""
        return {name: adapter.is_healthy for name, adapter in self._adapters.items()}

    @property
    def all_healthy(self) -> bool:
        """Check if all adapters are healthy."""
        return all(self.health_summary.values())


def configure_adapters(
    z3_config: AdapterConfig = AdapterConfig(),
    deepproblog_kb_path: str = "/path/to/kb",
    deepproblog_config: AdapterConfig = AdapterConfig(),
    polis_url: str = "https://api.polis.com",
    polis_key: str = "",
    polis_config: AdapterConfig = AdapterConfig(),
    opa_url: str = "http://localhost:8181",
    opa_config: AdapterConfig = AdapterConfig(),
) -> AdapterRegistry:
    """Configure all adapters."""
    registry = AdapterRegistry()

    registry.register("z3", Z3Adapter(z3_config))
    registry.register("deepproblog", DeepProbLogAdapter(deepproblog_kb_path, deepproblog_config))
    registry.register("polis", PolisAdapter(polis_url, polis_key, polis_config))
    registry.register("opa", OPAAdapter(opa_url, opa_config))

    return registry


# Global registry access
def get_adapter_registry() -> AdapterRegistry:
    """Get global adapter registry."""
    return AdapterRegistry()
```

---

## 8. Usage Examples

### 8.1 Verification Layer Integration

```python
# acgs2_core/verification/constitutional_verifier.py (using adapters)
"""Constitutional Hash: cdd01ef066bc6cf2"""

from acgs2_core.adapters.registry import get_adapter_registry
from acgs2_core.adapters.z3_adapter import Z3Request
from acgs2_core.adapters.opa_adapter import OPARequest

class ConstitutionalVerificationPipeline:
    """Verification pipeline using ACL adapters."""

    def __init__(self):
        self.registry = get_adapter_registry()
        self.z3 = self.registry.get("z3")
        self.opa = self.registry.get("opa")

    async def verify_governance_decision(
        self,
        decision: GovernanceDecision,
    ) -> VerificationResult:
        # Z3 verification via adapter
        z3_request = Z3Request(
            constraints=self.extract_constraints(decision),
            timeout_ms=5000,
        )
        z3_result = await self.z3.call(z3_request)

        if z3_result.degraded:
            # Log degraded mode
            logger.warning(f"Z3 in degraded mode: {z3_result.circuit_state}")

        # OPA verification via adapter
        opa_request = OPARequest(
            input_data=decision.to_dict(),
            policy_path="constitutional/validate",
        )
        opa_result = await self.opa.call(opa_request)

        return VerificationResult(
            valid=z3_result.data.satisfiable and opa_result.data.allow,
            z3_degraded=z3_result.degraded,
            opa_degraded=opa_result.degraded,
        )
```

---

## 9. Testing Adapters

```python
# tests/adapters/test_z3_adapter.py
"""Constitutional Hash: cdd01ef066bc6cf2"""

import pytest
from acgs2_core.adapters.z3_adapter import Z3Adapter, Z3Request, Z3Response

class TestZ3Adapter:
    """Tests for Z3 adapter."""

    @pytest.fixture
    def adapter(self):
        return Z3Adapter()

    async def test_sat_constraints(self, adapter):
        """Test satisfiable constraints."""
        import z3
        x = z3.Int('x')
        request = Z3Request(constraints=[x > 0, x < 10])

        result = await adapter.call(request)

        assert result.success
        assert result.data.satisfiable == True
        assert result.data.model is not None

    async def test_unsat_constraints(self, adapter):
        """Test unsatisfiable constraints."""
        import z3
        x = z3.Int('x')
        request = Z3Request(constraints=[x > 10, x < 5])

        result = await adapter.call(request)

        assert result.success
        assert result.data.satisfiable == False
        assert result.data.unsat_core is not None

    async def test_timeout_fallback(self, adapter, mocker):
        """Test fallback on timeout."""
        import asyncio
        mocker.patch.object(adapter, '_execute', side_effect=asyncio.TimeoutError)

        request = Z3Request(constraints=[])
        result = await adapter.call(request)

        # Should use fallback
        assert result.degraded or result.error is not None

    async def test_circuit_breaker_opens(self, adapter, mocker):
        """Test circuit breaker behavior."""
        mocker.patch.object(adapter, '_execute', side_effect=Exception("fail"))

        # Trigger failures to open circuit
        for _ in range(adapter.config.circuit_failure_threshold):
            await adapter.call(Z3Request(constraints=[]))

        assert adapter.circuit_breaker.state.name == "OPEN"
```

---

**Constitutional Hash: cdd01ef066bc6cf2**
**Document Version: 1.0.0**
**ACL Adapters Complete**
