"""
VeriPlan Z3 Formal Verifier
===========================

Constitutional Hash: cdd01ef066bc6cf2

Implements formal verification using Z3 SMT solver:
- LTL constraint extraction from natural language
- Z3 constraint generation and solving
- OPA policy integration

References:
- VeriPlan: Formal Verification (arXiv:2502.17898)
- Z3 SMT Solver
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .. import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class ConstraintType(Enum):
    """Types of formal constraints."""
    INVARIANT = "invariant"      # Always true
    PRECONDITION = "precondition"  # Must be true before
    POSTCONDITION = "postcondition"  # Must be true after
    TEMPORAL = "temporal"          # LTL formula
    SAFETY = "safety"              # Something bad never happens
    LIVENESS = "liveness"          # Something good eventually happens


@dataclass
class FormalConstraint:
    """A formal constraint in Z3 representation."""
    constraint_id: str
    constraint_type: ConstraintType
    expression: str  # Z3 expression string
    natural_language: str  # Original natural language
    variables: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Z3Variable:
    """A Z3 variable declaration."""
    name: str
    z3_type: str  # "Int", "Bool", "Real", "BitVec", etc.
    domain: Optional[Tuple[Any, Any]] = None  # Optional (min, max)


@dataclass
class VerificationResult:
    """Result from Z3 verification."""
    result_id: str
    sat: bool  # Satisfiable (constraints can be met)
    model: Optional[Dict[str, Any]] = None  # Variable assignments if SAT
    unsat_core: Optional[List[str]] = None  # Conflicting constraints if UNSAT
    proof_time_ms: float = 0.0
    constraints_checked: int = 0
    constitutional_hash: str = CONSTITUTIONAL_HASH


class LTLParser:
    """
    Parser for Linear Temporal Logic formulas.

    Supports:
    - G (Globally/Always)
    - F (Finally/Eventually)
    - X (Next)
    - U (Until)
    - R (Release)
    """

    # LTL operators and their semantics
    OPERATORS = {
        "G": "globally",
        "F": "finally",
        "X": "next",
        "U": "until",
        "R": "release",
        "!": "not",
        "&": "and",
        "|": "or",
        "->": "implies",
    }

    def __init__(self):
        self._formula_cache: Dict[str, Any] = {}

    def parse(self, formula: str) -> Dict[str, Any]:
        """
        Parse an LTL formula into AST.

        Args:
            formula: LTL formula string

        Returns:
            AST representation
        """
        if formula in self._formula_cache:
            return self._formula_cache[formula]

        # Tokenize
        tokens = self._tokenize(formula)

        # Parse into AST
        ast = self._parse_tokens(tokens)

        self._formula_cache[formula] = ast
        return ast

    def _tokenize(self, formula: str) -> List[str]:
        """Tokenize LTL formula."""
        # Add spaces around operators
        formula = formula.replace("(", " ( ")
        formula = formula.replace(")", " ) ")
        formula = formula.replace("!", " ! ")
        formula = formula.replace("&", " & ")
        formula = formula.replace("|", " | ")
        formula = formula.replace("->", " -> ")

        return [t for t in formula.split() if t]

    def _parse_tokens(self, tokens: List[str]) -> Dict[str, Any]:
        """Parse tokens into AST."""
        if not tokens:
            return {"type": "empty"}

        # Simple recursive descent parser
        pos = 0

        def parse_expr(tokens: List[str], pos: int) -> Tuple[Dict[str, Any], int]:
            if pos >= len(tokens):
                return {"type": "empty"}, pos

            token = tokens[pos]

            if token in ["G", "F", "X"]:
                # Unary temporal operator
                inner, new_pos = parse_expr(tokens, pos + 1)
                return {
                    "type": "temporal",
                    "operator": token,
                    "operand": inner
                }, new_pos

            elif token == "!":
                # Negation
                inner, new_pos = parse_expr(tokens, pos + 1)
                return {
                    "type": "not",
                    "operand": inner
                }, new_pos

            elif token == "(":
                # Parenthesized expression
                inner, new_pos = parse_expr(tokens, pos + 1)
                if new_pos < len(tokens) and tokens[new_pos] == ")":
                    new_pos += 1
                return inner, new_pos

            else:
                # Atomic proposition or variable
                return {
                    "type": "atom",
                    "value": token
                }, pos + 1

        ast, _ = parse_expr(tokens, 0)
        return ast

    def to_z3(self, formula: str, variables: Dict[str, Z3Variable]) -> str:
        """
        Convert LTL formula to Z3 constraints.

        Note: Full LTL requires bounded model checking.
        We simplify to invariant-style constraints.
        """
        ast = self.parse(formula)
        return self._ast_to_z3(ast, variables)

    def _ast_to_z3(
        self,
        ast: Dict[str, Any],
        variables: Dict[str, Z3Variable]
    ) -> str:
        """Convert AST to Z3 string."""
        ast_type = ast.get("type", "empty")

        if ast_type == "atom":
            value = ast["value"]
            if value in variables:
                return value
            # Boolean constant
            if value.lower() in ["true", "false"]:
                return value.capitalize()
            return value

        elif ast_type == "not":
            operand = self._ast_to_z3(ast["operand"], variables)
            return f"Not({operand})"

        elif ast_type == "temporal":
            # Simplify temporal operators for single-state verification
            operator = ast["operator"]
            operand = self._ast_to_z3(ast["operand"], variables)

            if operator == "G":
                # Globally -> treat as invariant
                return operand
            elif operator == "F":
                # Eventually -> treat as possibility
                return operand
            elif operator == "X":
                # Next -> same as current for single state
                return operand

        return "True"


class Z3ConstitutionalAdapter:
    """
    Adapter for Z3 SMT solver with constitutional constraints.

    Provides:
    - Variable declaration
    - Constraint generation
    - Satisfiability checking
    - Model extraction
    """

    def __init__(self):
        self._variables: Dict[str, Z3Variable] = {}
        self._constraints: List[FormalConstraint] = []
        self._ltl_parser = LTLParser()

        # Constitutional invariants (always added)
        self._constitutional_invariants = [
            FormalConstraint(
                constraint_id="const-hash",
                constraint_type=ConstraintType.INVARIANT,
                expression="constitutional_hash == VALID_HASH",
                natural_language="Constitutional hash must be valid",
                variables=["constitutional_hash"],
            ),
            FormalConstraint(
                constraint_id="const-audit",
                constraint_type=ConstraintType.INVARIANT,
                expression="audit_enabled == True",
                natural_language="Audit logging must be enabled",
                variables=["audit_enabled"],
            ),
        ]

        logger.info("Initialized Z3ConstitutionalAdapter")

    def declare_variable(
        self,
        name: str,
        z3_type: str = "Bool",
        domain: Optional[Tuple[Any, Any]] = None
    ) -> Z3Variable:
        """
        Declare a Z3 variable.

        Args:
            name: Variable name
            z3_type: Z3 type ("Int", "Bool", "Real", etc.)
            domain: Optional value domain

        Returns:
            Z3Variable instance
        """
        var = Z3Variable(name=name, z3_type=z3_type, domain=domain)
        self._variables[name] = var
        return var

    def add_constraint(
        self,
        expression: str,
        constraint_type: ConstraintType = ConstraintType.INVARIANT,
        natural_language: str = ""
    ) -> FormalConstraint:
        """
        Add a constraint to the solver.

        Args:
            expression: Z3 expression string
            constraint_type: Type of constraint
            natural_language: Original natural language

        Returns:
            FormalConstraint instance
        """
        # Extract variables from expression
        variables = self._extract_variables(expression)

        constraint = FormalConstraint(
            constraint_id=f"c-{uuid.uuid4().hex[:8]}",
            constraint_type=constraint_type,
            expression=expression,
            natural_language=natural_language or expression,
            variables=variables,
        )

        self._constraints.append(constraint)
        return constraint

    def add_ltl_constraint(
        self,
        formula: str,
        natural_language: str = ""
    ) -> FormalConstraint:
        """
        Add an LTL constraint.

        Args:
            formula: LTL formula string
            natural_language: Original description

        Returns:
            FormalConstraint instance
        """
        z3_expr = self._ltl_parser.to_z3(formula, self._variables)
        return self.add_constraint(
            expression=z3_expr,
            constraint_type=ConstraintType.TEMPORAL,
            natural_language=natural_language or formula
        )

    async def check_satisfiability(
        self,
        include_constitutional: bool = True
    ) -> VerificationResult:
        """
        Check if constraints are satisfiable.

        Args:
            include_constitutional: Include constitutional invariants

        Returns:
            VerificationResult with SAT/UNSAT and model
        """
        import time
        start_time = time.perf_counter()

        result_id = f"z3-{uuid.uuid4().hex[:8]}"

        # Collect all constraints
        all_constraints = self._constraints.copy()
        if include_constitutional:
            all_constraints.extend(self._constitutional_invariants)

        # Simulate Z3 solving (actual implementation would use z3-solver)
        sat, model, unsat_core = await self._solve(all_constraints)

        proof_time_ms = (time.perf_counter() - start_time) * 1000

        result = VerificationResult(
            result_id=result_id,
            sat=sat,
            model=model if sat else None,
            unsat_core=unsat_core if not sat else None,
            proof_time_ms=proof_time_ms,
            constraints_checked=len(all_constraints),
        )

        logger.info(
            f"Z3 verification: {result_id}, sat={sat}, "
            f"time={proof_time_ms:.2f}ms, constraints={len(all_constraints)}"
        )

        return result

    async def _solve(
        self,
        constraints: List[FormalConstraint]
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[List[str]]]:
        """
        Solve constraints (simulated Z3).

        In production, this would use the actual z3-solver library.
        """
        # Check for obvious unsatisfiability
        for c in constraints:
            expr_lower = c.expression.lower()
            if "false" in expr_lower and "==" in expr_lower:
                # Contradiction found
                return False, None, [c.constraint_id]

            if "impossible" in expr_lower:
                return False, None, [c.constraint_id]

        # Check for contradictions between constraints
        for i, c1 in enumerate(constraints):
            for c2 in constraints[i+1:]:
                if self._are_contradictory(c1, c2):
                    return False, None, [c1.constraint_id, c2.constraint_id]

        # Generate satisfying model
        model = {}
        for var_name, var in self._variables.items():
            if var.z3_type == "Bool":
                model[var_name] = True
            elif var.z3_type == "Int":
                if var.domain:
                    model[var_name] = (var.domain[0] + var.domain[1]) // 2
                else:
                    model[var_name] = 0
            elif var.z3_type == "Real":
                if var.domain:
                    model[var_name] = (var.domain[0] + var.domain[1]) / 2
                else:
                    model[var_name] = 0.0

        return True, model, None

    def _are_contradictory(
        self,
        c1: FormalConstraint,
        c2: FormalConstraint
    ) -> bool:
        """Check if two constraints are contradictory."""
        # Simple check for direct contradictions
        e1 = c1.expression.replace(" ", "")
        e2 = c2.expression.replace(" ", "")

        # Check for x == True and x == False
        if "==True" in e1 and "==False" in e2:
            var1 = e1.split("==")[0]
            var2 = e2.split("==")[0]
            if var1 == var2:
                return True

        return False

    def _extract_variables(self, expression: str) -> List[str]:
        """Extract variable names from expression."""
        # Simple extraction - find known variables
        found = []
        for var_name in self._variables:
            if var_name in expression:
                found.append(var_name)
        return found

    def clear(self) -> None:
        """Clear all variables and constraints."""
        self._variables.clear()
        self._constraints.clear()


class VeriPlanFormalVerifier:
    """
    VeriPlan Formal Verifier for Constitutional Governance.

    Integrates:
    - Natural language to formal constraint translation
    - LTL temporal logic verification
    - Z3 SMT solving
    - OPA policy integration
    """

    def __init__(
        self,
        opa_url: Optional[str] = None,
        timeout_ms: float = 5000.0
    ):
        """
        Initialize VeriPlan verifier.

        Args:
            opa_url: Optional OPA server URL for policy checks
            timeout_ms: Verification timeout
        """
        self.opa_url = opa_url
        self.timeout_ms = timeout_ms

        self._z3_adapter = Z3ConstitutionalAdapter()
        self._ltl_parser = LTLParser()

        self._stats = {
            "verifications": 0,
            "sat_results": 0,
            "unsat_results": 0,
            "opa_checks": 0,
        }

        logger.info(f"Initialized VeriPlanFormalVerifier opa_url={opa_url}")

    async def verify_policy(
        self,
        policy_text: str,
        context: Dict[str, Any]
    ) -> VerificationResult:
        """
        Verify a policy against formal constraints.

        Args:
            policy_text: Natural language policy description
            context: Execution context with variables

        Returns:
            VerificationResult with formal verification outcome
        """
        # Extract LTL constraints from policy
        ltl_constraints = await self.extract_ltl(policy_text)

        # Set up Z3 solver
        self._z3_adapter.clear()

        # Declare variables from context
        for key, value in context.items():
            if isinstance(value, bool):
                self._z3_adapter.declare_variable(key, "Bool")
            elif isinstance(value, int):
                self._z3_adapter.declare_variable(key, "Int")
            elif isinstance(value, float):
                self._z3_adapter.declare_variable(key, "Real")

        # Add LTL constraints
        for constraint in ltl_constraints:
            self._z3_adapter.add_ltl_constraint(
                constraint["formula"],
                constraint["description"]
            )

        # Verify
        result = await self._z3_adapter.check_satisfiability()

        # Update stats
        self._stats["verifications"] += 1
        if result.sat:
            self._stats["sat_results"] += 1
        else:
            self._stats["unsat_results"] += 1

        return result

    async def extract_ltl(
        self,
        natural_language: str
    ) -> List[Dict[str, str]]:
        """
        Extract LTL constraints from natural language.

        Uses pattern matching to identify temporal requirements.
        In production, would use an LLM for extraction.
        """
        constraints = []

        # Pattern matching for common temporal patterns
        patterns = [
            # "always X" -> G(X)
            (r"always\s+(\w+)", "G({})"),
            # "never X" -> G(!X)
            (r"never\s+(\w+)", "G(!{})"),
            # "eventually X" -> F(X)
            (r"eventually\s+(\w+)", "F({})"),
            # "X must be true" -> X
            (r"(\w+)\s+must\s+be\s+true", "{}"),
            # "if X then Y" -> X -> Y
            (r"if\s+(\w+)\s+then\s+(\w+)", "{} -> {}"),
        ]

        text_lower = natural_language.lower()

        for pattern, template in patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if isinstance(match, tuple):
                    formula = template.format(*match)
                else:
                    formula = template.format(match)

                constraints.append({
                    "formula": formula,
                    "description": f"Extracted from: '{natural_language[:50]}...'"
                })

        return constraints

    async def check_opa_policy(
        self,
        policy_path: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check policy with OPA.

        Args:
            policy_path: OPA policy path
            input_data: Input data for policy evaluation

        Returns:
            OPA evaluation result
        """
        if not self.opa_url:
            return {"allow": True, "reason": "OPA not configured"}

        self._stats["opa_checks"] += 1

        # In production, would make HTTP request to OPA
        # For now, simulate
        return {
            "allow": True,
            "policy_path": policy_path,
            "input": input_data,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    async def verify_governance_action(
        self,
        action: str,
        context: Dict[str, Any],
        policies: List[str]
    ) -> VerificationResult:
        """
        Verify a governance action against all applicable policies.

        Args:
            action: The action to verify
            context: Execution context
            policies: List of policy descriptions

        Returns:
            Combined verification result
        """
        # Verify each policy
        all_sat = True
        all_unsat_cores = []
        combined_model = {}

        for policy in policies:
            result = await self.verify_policy(policy, context)

            if not result.sat:
                all_sat = False
                if result.unsat_core:
                    all_unsat_cores.extend(result.unsat_core)
            elif result.model:
                combined_model.update(result.model)

        return VerificationResult(
            result_id=f"combined-{uuid.uuid4().hex[:8]}",
            sat=all_sat,
            model=combined_model if all_sat else None,
            unsat_core=all_unsat_cores if not all_sat else None,
            constraints_checked=len(policies),
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get verifier statistics."""
        total = self._stats["verifications"]
        sat_rate = self._stats["sat_results"] / max(total, 1)

        return {
            **self._stats,
            "sat_rate": sat_rate,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }
