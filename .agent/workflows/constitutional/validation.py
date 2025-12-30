"""
ACGS-2 Constitutional Validation Workflow
Constitutional Hash: cdd01ef066bc6cf2

Core validation workflow for constitutional compliance.
Implements multi-stage validation with audit trail.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ..base.result import WorkflowResult
from ..base.workflow import BaseWorkflow

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


logger = logging.getLogger(__name__)


class ValidationStage(Enum):
    """Stages of constitutional validation."""

    HASH_CHECK = "hash_check"
    INTEGRITY_CHECK = "integrity_check"
    POLICY_CHECK = "policy_check"
    COMPLIANCE_CHECK = "compliance_check"
    AUDIT_RECORD = "audit_record"


@dataclass
class ValidationResult:
    """Result of a validation stage."""

    stage: ValidationStage
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage": self.stage.value,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ConstitutionalValidationInput:
    """Input for constitutional validation workflow."""

    content: str
    content_hash: Optional[str] = None
    provided_constitutional_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    skip_policy_check: bool = False
    require_strict_compliance: bool = True


class ConstitutionalValidationWorkflow(BaseWorkflow):
    """
    Constitutional validation workflow.

    Implements a multi-stage validation pipeline:
    1. Hash Check - Verify constitutional hash
    2. Integrity Check - Verify content integrity
    3. Policy Check - Evaluate against OPA policies
    4. Compliance Check - Check constitutional compliance
    5. Audit Record - Record validation result

    Example:
        workflow = ConstitutionalValidationWorkflow()
        result = await workflow.run({
            "content": "message to validate",
            "content_hash": "abc123",
            "provided_constitutional_hash": "cdd01ef066bc6cf2"
        })
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
        opa_client: Optional[Any] = None,
        audit_service: Optional[Any] = None,
    ):
        """
        Initialize validation workflow.

        Args:
            workflow_id: Unique workflow identifier
            constitutional_hash: Expected constitutional hash
            opa_client: Optional OPA client for policy evaluation
            audit_service: Optional audit service for recording
        """
        super().__init__(
            workflow_id=workflow_id,
            workflow_name="constitutional_validation",
            constitutional_hash=constitutional_hash,
        )
        self.opa_client = opa_client
        self.audit_service = audit_service

    async def execute(self, input: Dict[str, Any]) -> WorkflowResult:
        """
        Execute constitutional validation workflow.

        Args:
            input: Validation input data

        Returns:
            WorkflowResult with validation outcome
        """
        validation_input = self._parse_input(input)
        validation_results: List[ValidationResult] = []
        all_passed = True

        try:
            # Stage 1: Hash Check
            hash_result = await self._check_constitutional_hash(validation_input)
            validation_results.append(hash_result)
            self.context.set_step_result(ValidationStage.HASH_CHECK.value, hash_result.to_dict())

            if not hash_result.passed:
                all_passed = False
                if validation_input.require_strict_compliance:
                    return self._create_failure_result(validation_results, "Hash check failed")

            # Stage 2: Integrity Check
            integrity_result = await self._check_integrity(validation_input)
            validation_results.append(integrity_result)
            self.context.set_step_result(
                ValidationStage.INTEGRITY_CHECK.value, integrity_result.to_dict()
            )

            if not integrity_result.passed:
                all_passed = False
                if validation_input.require_strict_compliance:
                    return self._create_failure_result(validation_results, "Integrity check failed")

            # Stage 3: Policy Check (Optional)
            if not validation_input.skip_policy_check:
                policy_result = await self._check_policies(validation_input)
                validation_results.append(policy_result)
                self.context.set_step_result(
                    ValidationStage.POLICY_CHECK.value, policy_result.to_dict()
                )

                if not policy_result.passed:
                    all_passed = False
                    if validation_input.require_strict_compliance:
                        return self._create_failure_result(
                            validation_results, "Policy check failed"
                        )

            # Stage 4: Compliance Check
            compliance_result = await self._check_compliance(validation_input, validation_results)
            validation_results.append(compliance_result)
            self.context.set_step_result(
                ValidationStage.COMPLIANCE_CHECK.value, compliance_result.to_dict()
            )

            if not compliance_result.passed:
                all_passed = False

            # Stage 5: Audit Record
            audit_result = await self._record_audit(
                validation_input, validation_results, all_passed
            )
            validation_results.append(audit_result)
            self.context.set_step_result(ValidationStage.AUDIT_RECORD.value, audit_result.to_dict())

            # Create final result
            return self._create_result(validation_results, all_passed)

        except Exception as e:
            logger.exception(f"Validation workflow error: {e}")
            return WorkflowResult.failure(
                workflow_id=self.workflow_id,
                errors=[f"Validation error: {e}"],
                execution_time_ms=self.context.get_elapsed_time_ms(),
                steps_completed=[r.stage.value for r in validation_results if r.passed],
                steps_failed=[r.stage.value for r in validation_results if not r.passed],
            )

    def _parse_input(self, input: Dict[str, Any]) -> ConstitutionalValidationInput:
        """Parse and validate input."""
        return ConstitutionalValidationInput(
            content=input.get("content", ""),
            content_hash=input.get("content_hash"),
            provided_constitutional_hash=input.get("provided_constitutional_hash"),
            metadata=input.get("metadata", {}),
            skip_policy_check=input.get("skip_policy_check", False),
            require_strict_compliance=input.get("require_strict_compliance", True),
        )

    async def _check_constitutional_hash(
        self, input: ConstitutionalValidationInput
    ) -> ValidationResult:
        """Check constitutional hash validity."""
        provided = input.provided_constitutional_hash or ""

        if provided == self.constitutional_hash:
            return ValidationResult(
                stage=ValidationStage.HASH_CHECK,
                passed=True,
                message="Constitutional hash verified",
                details={"expected": self.constitutional_hash, "provided": provided},
            )
        else:
            return ValidationResult(
                stage=ValidationStage.HASH_CHECK,
                passed=False,
                message="Constitutional hash mismatch",
                details={
                    "expected": self.constitutional_hash,
                    "provided": provided,
                    "action": "reject",
                },
            )

    async def _check_integrity(self, input: ConstitutionalValidationInput) -> ValidationResult:
        """Check content integrity."""
        if not input.content_hash:
            # No hash provided, compute one
            computed_hash = hashlib.sha256(input.content.encode()).hexdigest()[:16]
            return ValidationResult(
                stage=ValidationStage.INTEGRITY_CHECK,
                passed=True,
                message="Content hash computed (no verification possible)",
                details={"computed_hash": computed_hash, "verified": False},
            )

        # Verify provided hash
        computed_hash = hashlib.sha256(input.content.encode()).hexdigest()[
            : len(input.content_hash)
        ]

        if computed_hash == input.content_hash:
            return ValidationResult(
                stage=ValidationStage.INTEGRITY_CHECK,
                passed=True,
                message="Content integrity verified",
                details={"hash": input.content_hash, "verified": True},
            )
        else:
            return ValidationResult(
                stage=ValidationStage.INTEGRITY_CHECK,
                passed=False,
                message="Content integrity check failed",
                details={
                    "expected": input.content_hash,
                    "computed": computed_hash,
                    "action": "reject",
                },
            )

    async def _check_policies(self, input: ConstitutionalValidationInput) -> ValidationResult:
        """Check against OPA policies."""
        if not self.opa_client:
            return ValidationResult(
                stage=ValidationStage.POLICY_CHECK,
                passed=True,
                message="Policy check skipped (no OPA client)",
                details={"skipped": True},
            )

        try:
            # Call OPA for policy evaluation
            policy_result = await self.opa_client.evaluate(
                policy="constitutional/validation",
                input={
                    "content": input.content,
                    "metadata": input.metadata,
                    "constitutional_hash": self.constitutional_hash,
                },
            )

            return ValidationResult(
                stage=ValidationStage.POLICY_CHECK,
                passed=policy_result.get("allow", False),
                message=policy_result.get("message", "Policy evaluated"),
                details=policy_result,
            )

        except Exception as e:
            logger.warning(f"Policy check error: {e}")
            return ValidationResult(
                stage=ValidationStage.POLICY_CHECK,
                passed=False,
                message=f"Policy check error: {e}",
                details={"error": str(e)},
            )

    async def _check_compliance(
        self, input: ConstitutionalValidationInput, prior_results: List[ValidationResult]
    ) -> ValidationResult:
        """Check overall constitutional compliance."""
        # Count passed/failed stages
        passed_count = sum(1 for r in prior_results if r.passed)
        failed_count = sum(1 for r in prior_results if not r.passed)

        # Calculate compliance score
        total = passed_count + failed_count
        compliance_score = passed_count / total if total > 0 else 0.0

        # Strict mode requires 100% compliance
        threshold = 1.0 if input.require_strict_compliance else 0.8

        passed = compliance_score >= threshold

        return ValidationResult(
            stage=ValidationStage.COMPLIANCE_CHECK,
            passed=passed,
            message=f"Compliance score: {compliance_score:.2%}",
            details={
                "compliance_score": compliance_score,
                "threshold": threshold,
                "passed_stages": passed_count,
                "failed_stages": failed_count,
                "strict_mode": input.require_strict_compliance,
            },
        )

    async def _record_audit(
        self,
        input: ConstitutionalValidationInput,
        results: List[ValidationResult],
        all_passed: bool,
    ) -> ValidationResult:
        """Record validation in audit trail."""
        audit_record = {
            "workflow_id": self.workflow_id,
            "constitutional_hash": self.constitutional_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "all_passed": all_passed,
            "stages": [r.to_dict() for r in results],
            "metadata": input.metadata,
        }

        if self.audit_service:
            try:
                await self.audit_service.record(audit_record)
                return ValidationResult(
                    stage=ValidationStage.AUDIT_RECORD,
                    passed=True,
                    message="Audit record created",
                    details={"audit_id": audit_record.get("id")},
                )
            except Exception as e:
                logger.warning(f"Audit recording error: {e}")
                return ValidationResult(
                    stage=ValidationStage.AUDIT_RECORD,
                    passed=True,  # Don't fail workflow for audit errors
                    message=f"Audit recording failed: {e}",
                    details={"error": str(e)},
                )
        else:
            logger.debug(f"Audit record (no service): {audit_record}")
            return ValidationResult(
                stage=ValidationStage.AUDIT_RECORD,
                passed=True,
                message="Audit record logged (no service)",
                details={"local_only": True},
            )

    def _create_result(
        self, validation_results: List[ValidationResult], all_passed: bool
    ) -> WorkflowResult:
        """Create workflow result from validation results."""
        steps_completed = [r.stage.value for r in validation_results if r.passed]
        steps_failed = [r.stage.value for r in validation_results if not r.passed]

        if all_passed:
            return WorkflowResult.success(
                workflow_id=self.workflow_id,
                output={
                    "validated": True,
                    "stages": [r.to_dict() for r in validation_results],
                    "constitutional_hash": self.constitutional_hash,
                },
                execution_time_ms=self.context.get_elapsed_time_ms(),
                steps_completed=steps_completed,
            )
        else:
            return WorkflowResult.failure(
                workflow_id=self.workflow_id,
                errors=[r.message for r in validation_results if not r.passed],
                execution_time_ms=self.context.get_elapsed_time_ms(),
                steps_completed=steps_completed,
                steps_failed=steps_failed,
            )

    def _create_failure_result(
        self, validation_results: List[ValidationResult], reason: str
    ) -> WorkflowResult:
        """Create early failure result."""
        return WorkflowResult.failure(
            workflow_id=self.workflow_id,
            errors=[reason] + [r.message for r in validation_results if not r.passed],
            execution_time_ms=self.context.get_elapsed_time_ms(),
            steps_completed=[r.stage.value for r in validation_results if r.passed],
            steps_failed=[r.stage.value for r in validation_results if not r.passed],
        )


__all__ = [
    "ValidationStage",
    "ValidationResult",
    "ConstitutionalValidationInput",
    "ConstitutionalValidationWorkflow",
]
