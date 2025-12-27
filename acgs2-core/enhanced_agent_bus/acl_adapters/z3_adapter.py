"""
ACGS-2 Z3 SMT Solver Adapter
Constitutional Hash: cdd01ef066bc6cf2

ACL adapter for Z3 SMT solver integration with caching and timeout handling.
Used for formal verification of constitutional constraints.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .base import ACLAdapter, AdapterConfig, AdapterResult

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


@dataclass
class Z3AdapterConfig(AdapterConfig):
    """Z3-specific adapter configuration."""

    # Z3-specific settings
    z3_timeout_ms: int = 30000  # Z3 solver timeout (longer than adapter timeout)
    memory_limit_mb: int = 1024  # Memory limit for solver
    proof_enabled: bool = True  # Enable proof generation
    model_enabled: bool = True  # Enable model generation on sat

    # Cache settings optimized for Z3
    cache_enabled: bool = True
    cache_ttl_s: int = 3600  # 1 hour - proofs are deterministic

    # Override base settings
    timeout_ms: int = 35000  # Slightly longer than z3_timeout_ms
    max_retries: int = 1  # Z3 is deterministic, no point in many retries


@dataclass
class Z3Request:
    """Request to Z3 solver."""

    # SMT-LIB2 formula
    formula: str

    # Optional: specific assertions to check
    assertions: list[str] = field(default_factory=list)

    # Configuration overrides
    timeout_ms: Optional[int] = None
    get_model: bool = True
    get_proof: bool = False
    get_unsat_core: bool = False

    # Tracing
    trace_id: Optional[str] = None

    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = hashlib.sha256(
                f"{self.formula}:{self.assertions}".encode()
            ).hexdigest()[:16]


@dataclass
class Z3Response:
    """Response from Z3 solver."""

    # Result: sat, unsat, unknown
    result: str

    # Model if sat and requested
    model: Optional[dict[str, Any]] = None

    # Proof if unsat and requested
    proof: Optional[str] = None

    # Unsat core if unsat and requested
    unsat_core: Optional[list[str]] = None

    # Solver statistics
    statistics: dict[str, Any] = field(default_factory=dict)

    # Constitutional hash
    constitutional_hash: str = CONSTITUTIONAL_HASH

    # Tracing
    trace_id: Optional[str] = None

    @property
    def is_sat(self) -> bool:
        return self.result == "sat"

    @property
    def is_unsat(self) -> bool:
        return self.result == "unsat"

    @property
    def is_unknown(self) -> bool:
        return self.result == "unknown"

    def to_dict(self) -> dict:
        return {
            "result": self.result,
            "model": self.model,
            "proof": self.proof,
            "unsat_core": self.unsat_core,
            "statistics": self.statistics,
            "constitutional_hash": self.constitutional_hash,
            "trace_id": self.trace_id,
        }


class Z3Adapter(ACLAdapter[Z3Request, Z3Response]):
    """
    ACL adapter for Z3 SMT solver.

    Provides:
    - Async wrapper around Z3 solver
    - Caching of deterministic results
    - Timeout handling for long-running proofs
    - Memory-bounded execution
    - Graceful degradation to "unknown" result
    """

    def __init__(self, name: str = "z3", config: Z3AdapterConfig = None):
        super().__init__(name, config or Z3AdapterConfig())
        self.z3_config = config or Z3AdapterConfig()
        self._z3_available = self._check_z3_available()

        if not self._z3_available:
            logger.warning(
                f"[{CONSTITUTIONAL_HASH}] Z3 solver not available, "
                f"adapter will use fallback responses"
            )

    def _check_z3_available(self) -> bool:
        """Check if Z3 is available."""
        try:
            import z3  # noqa: F401

            return True
        except ImportError:
            return False

    async def _execute(self, request: Z3Request) -> Z3Response:
        """Execute Z3 solver call."""
        if not self._z3_available:
            # Return unknown when Z3 not available
            return Z3Response(
                result="unknown",
                statistics={"reason": "z3_not_available"},
                trace_id=request.trace_id,
            )

        # Run Z3 in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run_z3_sync, request)

    def _run_z3_sync(self, request: Z3Request) -> Z3Response:
        """Synchronous Z3 execution."""
        import z3

        try:
            # Create solver with timeout
            solver = z3.Solver()
            timeout_ms = request.timeout_ms or self.z3_config.z3_timeout_ms
            solver.set("timeout", timeout_ms)

            # Parse and add formula
            try:
                # Try parsing as SMT-LIB2
                assertions = z3.parse_smt2_string(request.formula)
                for assertion in assertions:
                    solver.add(assertion)
            except z3.Z3Exception:
                # Fallback: treat as single boolean expression
                logger.warning(
                    f"[{CONSTITUTIONAL_HASH}] Failed to parse SMT-LIB2, "
                    f"treating as expression"
                )
                return Z3Response(
                    result="unknown",
                    statistics={"reason": "parse_error"},
                    trace_id=request.trace_id,
                )

            # Add additional assertions
            for assertion_str in request.assertions:
                try:
                    parsed = z3.parse_smt2_string(assertion_str)
                    for a in parsed:
                        solver.add(a)
                except z3.Z3Exception:
                    pass

            # Check satisfiability
            check_result = solver.check()

            # Build response
            if check_result == z3.sat:
                model_dict = None
                if request.get_model:
                    model = solver.model()
                    model_dict = {str(d): str(model[d]) for d in model.decls()}

                return Z3Response(
                    result="sat",
                    model=model_dict,
                    statistics=self._extract_stats(solver),
                    trace_id=request.trace_id,
                )

            elif check_result == z3.unsat:
                proof = None
                unsat_core = None

                if request.get_proof:
                    try:
                        proof = str(solver.proof())
                    except z3.Z3Exception:
                        proof = "proof_unavailable"

                if request.get_unsat_core:
                    try:
                        unsat_core = [str(c) for c in solver.unsat_core()]
                    except z3.Z3Exception:
                        unsat_core = []

                return Z3Response(
                    result="unsat",
                    proof=proof,
                    unsat_core=unsat_core,
                    statistics=self._extract_stats(solver),
                    trace_id=request.trace_id,
                )

            else:
                return Z3Response(
                    result="unknown",
                    statistics=self._extract_stats(solver),
                    trace_id=request.trace_id,
                )

        except z3.Z3Exception as e:
            logger.error(f"[{CONSTITUTIONAL_HASH}] Z3 error: {e}")
            return Z3Response(
                result="unknown",
                statistics={"reason": "z3_error", "error": str(e)},
                trace_id=request.trace_id,
            )

    def _extract_stats(self, solver) -> dict:
        """Extract solver statistics."""
        try:
            stats = solver.statistics()
            return {str(k): stats.get_key_value(k) for k in range(len(stats))}
        except Exception:
            return {}

    def _validate_response(self, response: Z3Response) -> bool:
        """Validate Z3 response."""
        return response.result in ("sat", "unsat", "unknown")

    def _get_cache_key(self, request: Z3Request) -> str:
        """Generate cache key for Z3 request."""
        # Z3 is deterministic, so formula + assertions = unique result
        key_data = f"{request.formula}|{sorted(request.assertions)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _get_fallback_response(self, request: Z3Request) -> Optional[Z3Response]:
        """Fallback response when circuit open or Z3 unavailable."""
        # Return "unknown" with explanation
        return Z3Response(
            result="unknown",
            statistics={
                "reason": "fallback",
                "message": "Z3 adapter unavailable, returning unknown",
            },
            trace_id=request.trace_id,
        )


# Convenience functions for common Z3 operations
async def check_satisfiability(
    formula: str, adapter: Optional[Z3Adapter] = None
) -> AdapterResult[Z3Response]:
    """
    Check if formula is satisfiable.

    Args:
        formula: SMT-LIB2 formula string
        adapter: Optional adapter instance (creates new if not provided)

    Returns:
        AdapterResult with Z3Response
    """
    if adapter is None:
        adapter = Z3Adapter()

    request = Z3Request(formula=formula, get_model=True)
    return await adapter.call(request)


async def prove_property(
    property_formula: str,
    context_assertions: list[str] = None,
    adapter: Optional[Z3Adapter] = None,
) -> AdapterResult[Z3Response]:
    """
    Prove a property by checking unsatisfiability of negation.

    Args:
        property_formula: Formula to prove
        context_assertions: Additional context assertions
        adapter: Optional adapter instance

    Returns:
        AdapterResult with Z3Response (unsat = property holds)
    """
    if adapter is None:
        adapter = Z3Adapter()

    # Prove by checking negation is unsat
    negated_formula = f"(assert (not {property_formula}))"

    request = Z3Request(
        formula=negated_formula,
        assertions=context_assertions or [],
        get_proof=True,
        get_unsat_core=True,
    )
    return await adapter.call(request)
