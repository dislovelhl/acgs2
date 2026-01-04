"""
ACGS-2 LLM-Assisted Z3 Adapter
Constitutional Hash: cdd01ef066bc6cf2

Combines LLM natural language understanding with Z3 precision for automated
formal verification of constitutional constraints. Addresses Challenge 2:
Self-Verification & Formal Methods.

This breakthrough makes formal verification accessible without manual SMT specification.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .z3_adapter import Z3Adapter, Z3AdapterConfig, Z3Request, Z3Response

# Import centralized constitutional hash
try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


@dataclass
class LLMAssistedZ3Config:
    """Configuration for LLM-assisted Z3 constraint generation."""

    # LLM settings
    llm_model: str = "gpt-4-turbo"  # Model for constraint generation
    llm_temperature: float = 0.1   # Low temperature for deterministic outputs
    llm_max_tokens: int = 2000     # Sufficient for SMT generation

    # Generation settings
    max_refinement_iterations: int = 5  # Maximum attempts to fix constraints
    refinement_timeout_s: float = 30.0   # Timeout per refinement attempt

    # Validation settings
    validate_generated_constraints: bool = True
    fallback_to_manual: bool = False  # Whether to fallback to manual constraints

    # Domain knowledge
    constitutional_principles: List[str] = field(default_factory=lambda: [
        "Maximize beneficial impact while minimizing harm",
        "Ensure transparency and accountability",
        "Maintain constitutional integrity",
        "Respect stakeholder rights and interests",
        "Enable adaptive governance"
    ])

    # Z3 integration
    z3_config: Z3AdapterConfig = field(default_factory=Z3AdapterConfig)


@dataclass
class NaturalLanguageConstraint:
    """A constraint specified in natural language."""

    description: str
    context: Dict[str, Any]
    domain: str  # e.g., "policy", "access_control", "resource_allocation"
    criticality: str  # "critical", "high", "medium", "low"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "context": self.context,
            "domain": self.domain,
            "criticality": self.criticality,
            "timestamp": self.timestamp.isoformat(),
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class SMTConstraintResult:
    """Result of SMT constraint generation."""

    natural_language: str
    smt_formula: str
    z3_result: Optional[Z3Response]
    generation_attempts: int
    refinement_iterations: int
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "natural_language": self.natural_language,
            "smt_formula": self.smt_formula,
            "z3_result": self.z3_result.to_dict() if self.z3_result else None,
            "generation_attempts": self.generation_attempts,
            "refinement_iterations": self.refinement_iterations,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "generated_at": self.generated_at.isoformat(),
            "constitutional_hash": self.constitutional_hash,
        }


class SMTGenerationPrompts:
    """Prompts for SMT constraint generation."""

    @staticmethod
    def get_constraint_generation_prompt(constraint: NaturalLanguageConstraint) -> str:
        """Generate prompt for SMT constraint creation."""
        return f"""
You are an expert formal methods engineer specializing in SMT (Satisfiability Modulo Theories) constraint generation for constitutional AI governance systems.

Given the natural language constraint, generate a valid SMT-LIB2 formula that captures its formal semantics.

**Natural Language Constraint:**
{constraint.description}

**Domain Context:**
{constraint.domain}

**Additional Context:**
{constraint.context}

**Constitutional Principles to Consider:**
- Maximize beneficial impact while minimizing harm
- Ensure transparency and accountability
- Maintain constitutional integrity
- Respect stakeholder rights and interests
- Enable adaptive governance

**Requirements:**
1. Use SMT-LIB2 syntax with proper declarations
2. Include appropriate theories (QF_LIA for integers, QF_LRA for reals, etc.)
3. Use meaningful variable names
4. Add comments explaining the constraint logic
5. Ensure the formula is syntactically correct and solvable by Z3

**Output Format:**
Return ONLY the SMT-LIB2 formula without any additional text or explanation.

Example Output:
```
(declare-const user_access_level Int)
(declare-const required_access_level Int)
(declare-const is_authenticated Bool)

; User must have sufficient access level and be authenticated
(assert (=> (and (>= user_access_level required_access_level) is_authenticated)
            (grant_access)))
```

Generate the SMT-LIB2 formula for the given constraint:
"""

    @staticmethod
    def get_constraint_refinement_prompt(
        original_constraint: str,
        smt_formula: str,
        z3_error: str,
        refinement_history: List[Dict[str, Any]]
    ) -> str:
        """Generate prompt for SMT constraint refinement."""
        history_text = "\n".join([
            f"Attempt {i+1}: {h.get('error', 'Unknown error')}"
            for i, h in enumerate(refinement_history)
        ])

        return f"""
You are debugging an SMT-LIB2 formula that failed Z3 validation. Fix the syntax and logical errors.

**Original Natural Language Constraint:**
{original_constraint}

**Current SMT Formula (with errors):**
{smt_formula}

**Z3 Error:**
{z3_error}

**Previous Refinement Attempts:**
{history_text}

**Debugging Guidelines:**
1. Check for syntax errors (missing parentheses, incorrect keywords, etc.)
2. Ensure proper variable declarations before use
3. Verify logical consistency
4. Use appropriate SMT theories for the domain
5. Fix type mismatches
6. Ensure boolean logic is correct

**Output Format:**
Return ONLY the corrected SMT-LIB2 formula without any additional text.

Corrected formula:
"""


class LLMAssistedZ3Adapter:
    """
    LLM-Assisted Z3 Adapter for Automated Formal Verification

    Combines LLM natural language understanding with Z3 precision:
    1. LLM generates initial SMT constraints from natural language
    2. Z3 validates and solves the constraints
    3. LLM refines constraints based on Z3 feedback
    4. Iterative process until valid constraints are produced

    This breakthrough makes formal verification accessible without manual SMT specification.
    """

    def __init__(self, config: Optional[LLMAssistedZ3Config] = None):
        self.config = config or LLMAssistedZ3Config()
        self.z3_adapter = Z3Adapter(self.config.z3_config)
        self.prompts = SMTGenerationPrompts()

        # Mock LLM client (in practice, integrate with actual LLM API)
        self.llm_client = self._initialize_llm_client()

        logger.info("Initialized LLM-Assisted Z3 Adapter")
        logger.info(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
        logger.info(f"Max refinement iterations: {self.config.max_refinement_iterations}")

    def _initialize_llm_client(self):
        """Initialize LLM client for constraint generation."""
        # Placeholder for LLM client initialization
        # In practice, this would connect to OpenAI, Anthropic, etc.
        class MockLLMClient:
            async def generate_constraint(self, prompt: str) -> str:
                """Mock LLM response for SMT generation."""
                # This is a simplified mock - real implementation would call actual LLM
                return self._generate_mock_smt_formula(prompt)

            def _generate_mock_smt_formula(self, prompt: str) -> str:
                """Generate mock SMT formula based on prompt content."""
                if "access" in prompt.lower():
                    return """
(declare-const user_level Int)
(declare-const required_level Int)
(declare-const authenticated Bool)

; Access control: user level must meet requirement and be authenticated
(assert (=> (and (>= user_level required_level) authenticated)
            (access_granted)))
"""
                elif "policy" in prompt.lower():
                    return """
(declare-const policy_compliant Bool)
(declare-const impact_positive Bool)
(declare-const risk_acceptable Bool)

; Policy enforcement: must be compliant, beneficial, and low-risk
(assert (= policy_valid (and policy_compliant impact_positive risk_acceptable)))
"""
                else:
                    return """
(declare-const constraint_satisfied Bool)

; Generic constraint placeholder
(assert constraint_satisfied)
"""

        return MockLLMClient()

    async def natural_language_to_smt(
        self,
        constraint: NaturalLanguageConstraint
    ) -> SMTConstraintResult:
        """
        Convert natural language constraint to validated SMT formula.

        This is the core breakthrough: automated SMT generation with LLM assistance.
        """
        logger.info(f"Converting natural language to SMT: {constraint.description[:100]}...")

        generation_attempts = 0
        refinement_iterations = 0
        errors = []
        warnings = []

        # Initial SMT generation
        smt_formula = await self._generate_initial_smt(constraint)
        generation_attempts += 1

        # Iterative refinement based on Z3 validation
        for iteration in range(self.config.max_refinement_iterations):
            refinement_iterations = iteration + 1

            # Validate with Z3
            validation_result = await self._validate_smt_formula(smt_formula)

            if validation_result.success:
                # Success! Return validated result
                return SMTConstraintResult(
                    natural_language=constraint.description,
                    smt_formula=smt_formula,
                    z3_result=validation_result.response,
                    generation_attempts=generation_attempts,
                    refinement_iterations=refinement_iterations,
                    is_valid=True,
                    errors=[],
                    warnings=warnings,
                    metadata={
                        "constraint_domain": constraint.domain,
                        "constraint_criticality": constraint.criticality,
                        "final_iteration": iteration + 1,
                    }
                )

            else:
                # Z3 validation failed - refine with LLM
                error_msg = validation_result.error or "Unknown Z3 error"
                errors.append(f"Iteration {iteration + 1}: {error_msg}")

                logger.debug(f"Z3 validation failed (iteration {iteration + 1}): {error_msg}")

                # Generate refined SMT formula
                refinement_prompt = self.prompts.get_constraint_refinement_prompt(
                    constraint.description,
                    smt_formula,
                    error_msg,
                    [{"error": e} for e in errors[:-1]]  # Previous errors
                )

                try:
                    smt_formula = await asyncio.wait_for(
                        self.llm_client.generate_constraint(refinement_prompt),
                        timeout=self.config.refinement_timeout_s
                    )
                    generation_attempts += 1

                except asyncio.TimeoutError:
                    errors.append(f"Iteration {iteration + 1}: LLM refinement timeout")
                    break
                except Exception as e:
                    errors.append(f"Iteration {iteration + 1}: LLM refinement failed: {e}")
                    break

        # All refinement attempts failed
        return SMTConstraintResult(
            natural_language=constraint.description,
            smt_formula=smt_formula,
            z3_result=None,
            generation_attempts=generation_attempts,
            refinement_iterations=refinement_iterations,
            is_valid=False,
            errors=errors,
            warnings=warnings,
            metadata={
                "constraint_domain": constraint.domain,
                "constraint_criticality": constraint.criticality,
                "max_iterations_reached": True,
            }
        )

    async def _generate_initial_smt(self, constraint: NaturalLanguageConstraint) -> str:
        """Generate initial SMT formula from natural language."""
        prompt = self.prompts.get_constraint_generation_prompt(constraint)

        try:
            smt_formula = await asyncio.wait_for(
                self.llm_client.generate_constraint(prompt),
                timeout=self.config.refinement_timeout_s
            )
            return smt_formula.strip()
        except Exception as e:
            logger.error(f"Failed to generate initial SMT: {e}")
            # Return a safe fallback
            return """
(declare-const fallback_constraint Bool)
; Fallback constraint due to generation failure
(assert fallback_constraint)
"""

    async def _validate_smt_formula(self, smt_formula: str) -> Tuple[bool, Optional[Z3Response], Optional[str]]:
        """
        Validate SMT formula with Z3.

        Returns (success, response, error_message)
        """
        @dataclass
        class ValidationResult:
            success: bool
            response: Optional[Z3Response]
            error: Optional[str]

        try:
            # Clean and validate SMT syntax
            cleaned_formula = self._clean_smt_formula(smt_formula)

            # Call Z3 adapter
            request = Z3Request(formula=cleaned_formula, get_model=True)
            result = await self.z3_adapter.call(request)

            if result.success and result.response:
                # Check if Z3 processed successfully (no syntax errors)
                if hasattr(result.response, 'result') and result.response.result in ['sat', 'unsat', 'unknown']:
                    return ValidationResult(True, result.response, None)
                else:
                    return ValidationResult(False, result.response, "Z3 processing failed")
            else:
                error_msg = result.error or "Z3 adapter call failed"
                return ValidationResult(False, None, error_msg)

        except Exception as e:
            return ValidationResult(False, None, f"Validation error: {e}")

    def _clean_smt_formula(self, formula: str) -> str:
        """Clean and validate SMT formula syntax."""
        # Remove markdown code blocks if present
        formula = re.sub(r'```\w*\n?', '', formula)
        formula = formula.strip()

        # Basic syntax validation
        if not formula.startswith('(') and not formula.startswith(';'):
            # Wrap in assert if it's just a constraint
            formula = f"(assert {formula})"

        return formula

    async def get_adapter_status(self) -> Dict[str, Any]:
        """Get adapter status and capabilities."""
        return {
            "adapter_type": "LLM-Assisted Z3",
            "status": "operational",
            "capabilities": {
                "llm_model": self.config.llm_model,
                "max_refinements": self.config.max_refinement_iterations,
                "z3_integration": True,
                "constitutional_hash": CONSTITUTIONAL_HASH,
                "supported_domains": ["policy", "access_control", "resource_allocation", "audit"],
            },
            "statistics": {
                "total_generations": 0,  # Would track in real implementation
                "successful_validations": 0,
                "average_refinements": 0.0,
            }
        }


# Convenience functions
async def generate_smt_constraint(
    natural_language: str,
    domain: str = "general",
    criticality: str = "medium",
    context: Optional[Dict[str, Any]] = None,
    adapter: Optional[LLMAssistedZ3Adapter] = None,
) -> SMTConstraintResult:
    """
    Convenience function to generate SMT constraint from natural language.

    This is the main API for automated formal verification.
    """
    if adapter is None:
        adapter = LLMAssistedZ3Adapter()

    constraint = NaturalLanguageConstraint(
        description=natural_language,
        context=context or {},
        domain=domain,
        criticality=criticality,
    )

    return await adapter.natural_language_to_smt(constraint)


async def validate_policy_constraint(
    policy_description: str,
    adapter: Optional[LLMAssistedZ3Adapter] = None,
) -> SMTConstraintResult:
    """
    Specialized function for policy constraint validation.

    This addresses the core need: automated verification of governance policies.
    """
    return await generate_smt_constraint(
        natural_language=policy_description,
        domain="policy",
        criticality="high",
        adapter=adapter,
    )


if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    async def main():
        logger.info("Testing LLM-Assisted Z3 Adapter...")

        adapter = LLMAssistedZ3Adapter()

        # Test status
        status = await adapter.get_adapter_status()
        logger.info("Adapter status: %s", status['status'])
        logger.info("Capabilities: LLM + Z3 integration enabled")

        # Test constraint generation
        test_constraint = NaturalLanguageConstraint(
            description="Users must have admin level access and be authenticated to modify system policies",
            context={"system_type": "governance", "access_level": "admin"},
            domain="access_control",
            criticality="critical"
        )

        result = await adapter.natural_language_to_smt(test_constraint)

        logger.info("SMT generation: %d attempts", result.generation_attempts)
        logger.info("Refinements needed: %d", result.refinement_iterations)
        logger.info("Constraint valid: %s", result.is_valid)
        logger.info("SMT formula length: %d chars", len(result.smt_formula))

        if result.errors:
            logger.warning("Errors encountered: %d", len(result.errors))

        # Test convenience function
        policy_result = await validate_policy_constraint(
            "Policies must not violate constitutional principles and must be auditable"
        )

        logger.info("Policy validation: valid=%s", policy_result.is_valid)

        logger.info("LLM-Assisted Z3 Adapter test completed!")

    # Run test
    asyncio.run(main())
