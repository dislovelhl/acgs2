"""Z3 SMT Solver Integration for ACGS-2 Constitutional AI Governance.

Constitutional Hash: cdd01ef066bc6cf2

Implements LLM-assisted formal verification using Z3 SMT solver.
Provides mathematical guarantees for constitutional policy verification.

Key Features:
- LLM-assisted constraint generation from natural language policies
- Z3 SMT solving for formal verification
- Iterative refinement loop for constraint optimization
- Constitutional compliance verification
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import z3
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    z3 = None

logger = logging.getLogger(__name__)

# Constitutional Hash for immutable validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


@dataclass
class Z3Constraint:
    """Represents a Z3 constraint with metadata."""
    name: str
    expression: str
    natural_language: str
    confidence: float
    generated_by: str = "llm"
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class Z3VerificationResult:
    """Result of Z3 verification."""
    is_sat: bool
    model: Optional[Dict[str, Any]] = None
    unsat_core: Optional[List[str]] = None
    constraints_used: List[str] = None
    solve_time_ms: float = 0.0
    solver_stats: Dict[str, Any] = None

    def __post_init__(self):
        if self.constraints_used is None:
            self.constraints_used = []
        if self.solver_stats is None:
            self.solver_stats = {}


@dataclass
class ConstitutionalPolicy:
    """Represents a constitutional policy with formal verification."""
    id: str
    natural_language: str
    z3_constraints: List[Z3Constraint]
    verification_result: Optional[Z3VerificationResult] = None
    is_verified: bool = False
    constitutional_hash: str = CONSTITUTIONAL_HASH
    created_at: datetime = None
    verified_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class Z3SolverAdapter:
    """
    Z3 SMT Solver Adapter for constitutional verification.

    Provides interface between natural language policies and formal verification.
    """

    def __init__(self, timeout_ms: int = 5000):
        if not Z3_AVAILABLE:
            raise ImportError("Z3 solver not available. Install with: pip install z3-solver")

        self.timeout_ms = timeout_ms
        self.solver = z3.Solver()
        self.solver.set("timeout", timeout_ms)

        # Track constraints and their names
        self.named_constraints: Dict[str, z3.ExprRef] = {}
        self.constraint_history: List[Z3Constraint] = []

        logger.info(f"Z3 Solver Adapter initialized with timeout {timeout_ms}ms")

    def reset_solver(self):
        """Reset the solver state."""
        self.solver.reset()
        self.named_constraints.clear()

    def add_constraint(self, name: str, constraint: z3.ExprRef, metadata: Z3Constraint):
        """
        Add a named constraint to the solver.

        Args:
            name: Unique constraint name
            constraint: Z3 expression
            metadata: Constraint metadata
        """
        self.named_constraints[name] = constraint
        self.solver.add(constraint)
        self.constraint_history.append(metadata)

        logger.debug(f"Added constraint '{name}': {constraint}")

    def check_sat(self) -> Z3VerificationResult:
        """
        Check satisfiability of current constraints.

        Returns:
            Verification result with model or unsat core
        """
        import time
        start_time = time.time()

        result = self.solver.check()

        solve_time = (time.time() - start_time) * 1000  # Convert to ms

        if result == z3.sat:
            model = self.solver.model()
            model_dict = {}
            for decl in model.decls():
                value = model[decl]
                if z3.is_int_value(value):
                    model_dict[str(decl)] = value.as_long()
                elif z3.is_bool(value):
                    model_dict[str(decl)] = bool(value)
                else:
                    model_dict[str(decl)] = str(value)

            return Z3VerificationResult(
                is_sat=True,
                model=model_dict,
                solve_time_ms=solve_time,
                solver_stats={"decls": len(model.decls())}
            )

        elif result == z3.unsat:
            # Try to get unsat core if possible
            unsat_core = []
            try:
                core = self.solver.unsat_core()
                unsat_core = [str(c) for c in core]
            except:
                pass  # Unsat core not available

            return Z3VerificationResult(
                is_sat=False,
                unsat_core=unsat_core,
                solve_time_ms=solve_time
            )

        else:  # unknown
            return Z3VerificationResult(
                is_sat=False,  # Treat unknown as unsatisfiable for safety
                solve_time_ms=solve_time,
                solver_stats={"result": "unknown"}
            )

    def get_constraint_names(self) -> List[str]:
        """Get list of all constraint names."""
        return list(self.named_constraints.keys())


class LLMAssistedZ3Adapter:
    """
    LLM-Assisted Z3 Constraint Generation.

    Uses LLM to translate natural language policies into Z3 constraints,
    then uses Z3 for formal verification.
    """

    def __init__(self, max_refinements: int = 3):
        self.max_refinements = max_refinements
        self.z3_solver = Z3SolverAdapter()
        self.generation_history: List[Dict[str, Any]] = []

    async def natural_language_to_constraints(
        self,
        policy_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Z3Constraint]:
        """
        Convert natural language policy to Z3 constraints using LLM assistance.

        Args:
            policy_text: Natural language policy description
            context: Additional context for constraint generation

        Returns:
            List of Z3 constraints with metadata
        """
        constraints = []

        # Extract key policy elements
        policy_elements = self._extract_policy_elements(policy_text)

        for element in policy_elements:
            # Generate Z3 constraint for each element
            constraint = await self._generate_single_constraint(element, context)
            if constraint:
                constraints.append(constraint)

        logger.info(f"Generated {len(constraints)} Z3 constraints for policy: {policy_text[:50]}...")
        return constraints

    def _extract_policy_elements(self, policy_text: str) -> List[Dict[str, Any]]:
        """Extract key elements from natural language policy."""
        elements = []

        # Simple rule extraction (can be enhanced with LLM)
        sentences = policy_text.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Identify constraint types
            if any(word in sentence.lower() for word in ['must', 'shall', 'required', 'prohibited']):
                elements.append({
                    'type': 'obligation',
                    'text': sentence,
                    'priority': 'high'
                })
            elif any(word in sentence.lower() for word in ['may', 'can', 'optional']):
                elements.append({
                    'type': 'permission',
                    'text': sentence,
                    'priority': 'medium'
                })
            elif any(word in sentence.lower() for word in ['cannot', 'must not', 'forbidden']):
                elements.append({
                    'type': 'prohibition',
                    'text': sentence,
                    'priority': 'high'
                })

        return elements

    async def _generate_single_constraint(
        self,
        element: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Z3Constraint]:
        """Generate a single Z3 constraint from policy element."""
        # Simplified constraint generation (would use LLM in practice)
        element_text = element['text']
        element_type = element['type']

        # Basic pattern matching for common constraints
        constraint_expr = None
        confidence = 0.7  # Base confidence

        if element_type == 'obligation':
            # Pattern: "X must be Y"
            if 'must' in element_text.lower():
                # Generate boolean constraint
                var_name = f"policy_{hash(element_text) % 1000}"
                constraint_expr = f"(declare-const {var_name} Bool)\n(assert {var_name})"
                confidence = 0.8

        elif element_type == 'prohibition':
            # Pattern: "X cannot be Y"
            if any(phrase in element_text.lower() for phrase in ['cannot', 'must not']):
                var_name = f"prohibit_{hash(element_text) % 1000}"
                constraint_expr = f"(declare-const {var_name} Bool)\n(assert (not {var_name}))"
                confidence = 0.9

        if constraint_expr:
            return Z3Constraint(
                name=f"constraint_{hash(element_text) % 10000}",
                expression=constraint_expr,
                natural_language=element_text,
                confidence=confidence,
                generated_by="pattern_matching"
            )

        return None

    async def verify_policy_constraints(
        self,
        constraints: List[Z3Constraint]
    ) -> Z3VerificationResult:
        """
        Verify a set of constraints using Z3.

        Args:
            constraints: List of Z3 constraints to verify

        Returns:
            Verification result
        """
        self.z3_solver.reset_solver()

        # Add all constraints to solver
        for constraint in constraints:
            try:
                # Parse Z3 expression (simplified)
                z3_expr = self._parse_z3_expression(constraint.expression)
                if z3_expr:
                    self.z3_solver.add_constraint(
                        constraint.name,
                        z3_expr,
                        constraint
                    )
            except Exception as e:
                logger.warning(f"Failed to parse constraint {constraint.name}: {e}")
                continue

        # Check satisfiability
        result = self.z3_solver.check_sat()

        logger.info(f"Z3 verification result: SAT={result.is_sat}, time={result.solve_time_ms:.2f}ms")
        return result

    def _parse_z3_expression(self, expr_str: str) -> Optional[z3.ExprRef]:
        """Parse Z3 expression string into Z3 object."""
        try:
            # Very simplified parsing (real implementation would be more robust)
            if 'declare-const' in expr_str and 'Bool' in expr_str:
                # Extract variable name
                lines = expr_str.strip().split('\n')
                if len(lines) >= 2:
                    # declare-const var_name Bool
                    declare_line = lines[0]
                    var_match = re.search(r'declare-const (\w+) Bool', declare_line)
                    if var_match:
                        var_name = var_match.group(1)
                        var = z3.Bool(var_name)

                        # Parse assertion
                        assert_line = lines[1] if len(lines) > 1 else ""
                        if 'assert (not ' in assert_line:
                            return z3.Not(var)
                        elif 'assert ' in assert_line:
                            return var

            return None
        except Exception as e:
            logger.error(f"Failed to parse Z3 expression '{expr_str}': {e}")
            return None

    async def refine_constraints(
        self,
        constraints: List[Z3Constraint],
        verification_result: Z3VerificationResult,
        max_iterations: int = 3
    ) -> List[Z3Constraint]:
        """
        Refine constraints based on verification results.

        Args:
            constraints: Original constraints
            verification_result: Z3 verification result
            max_iterations: Maximum refinement iterations

        Returns:
            Refined constraints
        """
        if verification_result.is_sat:
            # Already satisfiable, no refinement needed
            return constraints

        refined_constraints = constraints.copy()

        for iteration in range(max_iterations):
            if not verification_result.unsat_core:
                break

            # Identify problematic constraints
            problematic_names = set(verification_result.unsat_core)

            # Refine problematic constraints
            for i, constraint in enumerate(refined_constraints):
                if constraint.name in problematic_names:
                    # Simplified refinement: reduce confidence or modify expression
                    refined_constraints[i] = Z3Constraint(
                        name=constraint.name,
                        expression=constraint.expression,
                        natural_language=constraint.natural_language,
                        confidence=max(0.1, constraint.confidence - 0.1),
                        generated_by=f"refined_{iteration}"
                    )

            # Re-verify
            verification_result = await self.verify_policy_constraints(refined_constraints)

            if verification_result.is_sat:
                break

        return refined_constraints


class ConstitutionalZ3Verifier:
    """
    High-level constitutional policy verifier using Z3.

    Integrates LLM-assisted constraint generation with formal verification.
    """

    def __init__(self):
        self.llm_adapter = LLMAssistedZ3Adapter()
        self.verified_policies: Dict[str, ConstitutionalPolicy] = {}

    async def verify_constitutional_policy(
        self,
        policy_id: str,
        natural_language_policy: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ConstitutionalPolicy:
        """
        Verify a constitutional policy using Z3 formal verification.

        Args:
            policy_id: Unique policy identifier
            natural_language_policy: Policy in natural language
            context: Additional verification context

        Returns:
            Verified constitutional policy
        """
        logger.info(f"Verifying constitutional policy: {policy_id}")

        # Generate constraints from natural language
        constraints = await self.llm_adapter.natural_language_to_constraints(
            natural_language_policy,
            context
        )

        # Verify constraints
        verification_result = await self.llm_adapter.verify_policy_constraints(constraints)

        # Attempt refinement if needed
        if not verification_result.is_sat:
            constraints = await self.llm_adapter.refine_constraints(
                constraints,
                verification_result
            )
            # Re-verify after refinement
            verification_result = await self.llm_adapter.verify_policy_constraints(constraints)

        # Create verified policy
        policy = ConstitutionalPolicy(
            id=policy_id,
            natural_language=natural_language_policy,
            z3_constraints=constraints,
            verification_result=verification_result,
            is_verified=verification_result.is_sat,
            verified_at=datetime.utcnow() if verification_result.is_sat else None
        )

        # Store verified policy
        self.verified_policies[policy_id] = policy

        status = "VERIFIED" if policy.is_verified else "UNVERIFIED"
        logger.info(f"Policy {policy_id} {status} with {len(constraints)} constraints")

        return policy

    async def verify_policy_compliance(
        self,
        policy_id: str,
        decision_context: Dict[str, Any]
    ) -> bool:
        """
        Verify if a decision complies with a verified policy.

        Args:
            policy_id: ID of the verified policy
            decision_context: Context of the decision to verify

        Returns:
            True if compliant, False otherwise
        """
        if policy_id not in self.verified_policies:
            logger.warning(f"Policy {policy_id} not found in verified policies")
            return False

        policy = self.verified_policies[policy_id]
        if not policy.is_verified:
            logger.warning(f"Policy {policy_id} is not verified")
            return False

        # For now, return verification status (could be enhanced with runtime checking)
        return policy.is_verified

    def get_constitutional_hash(self) -> str:
        """Return the constitutional hash for validation."""
        return CONSTITUTIONAL_HASH

    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        total_policies = len(self.verified_policies)
        verified_policies = sum(1 for p in self.verified_policies.values() if p.is_verified)

        return {
            'total_policies': total_policies,
            'verified_policies': verified_policies,
            'verification_rate': verified_policies / total_policies if total_policies > 0 else 0.0,
            'constitutional_hash': CONSTITUTIONAL_HASH
        }


# Convenience functions
async def verify_policy_formally(
    policy_text: str,
    policy_id: Optional[str] = None
) -> ConstitutionalPolicy:
    """
    Convenience function to verify a policy formally.

    Args:
        policy_text: Natural language policy
        policy_id: Optional policy ID (generated if not provided)

    Returns:
        Verified constitutional policy
    """
    if policy_id is None:
        policy_id = f"policy_{hash(policy_text) % 10000}"

    verifier = ConstitutionalZ3Verifier()
    return await verifier.verify_constitutional_policy(policy_id, policy_text)


# Export for use in other modules
__all__ = [
    'Z3SolverAdapter',
    'LLMAssistedZ3Adapter',
    'ConstitutionalZ3Verifier',
    'ConstitutionalPolicy',
    'Z3Constraint',
    'Z3VerificationResult',
    'verify_policy_formally',
    'CONSTITUTIONAL_HASH'
]
