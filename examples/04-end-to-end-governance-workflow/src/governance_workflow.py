#!/usr/bin/env python3
"""
Governance Workflow Orchestrator for ACGS-2

Main orchestrator that coordinates the complete end-to-end governance workflow:
1. Constitutional validation (constitutional.rego)
2. Action evaluation and risk assessment (agent_actions.rego)
3. HITL determination (hitl_approval.rego)
4. Human approval workflow (if required)
5. Audit logging (audit.rego + PostgreSQL)
6. Final decision response

This module integrates OPAClient, AuditLogger, and HITLHandler to provide
a complete governance decision-making pipeline.

Usage:
    from src.governance_workflow import GovernanceWorkflow, GovernanceDecision
    from src.opa_client import OPAClient, OPAConfig
    from src.audit_logger import AuditLogger, DatabaseConfig
    from src.hitl_handler import HITLHandler, HITLConfig

    # Initialize components
    opa = OPAClient(OPAConfig(url="http://localhost:8181"))
    audit = AuditLogger(DatabaseConfig(password="secret"))
    hitl = HITLHandler(HITLConfig())

    # Create workflow orchestrator
    workflow = GovernanceWorkflow(opa, audit, hitl)

    # Evaluate an action
    decision = workflow.evaluate_action({
        "action": {"type": "deploy_model", "resource": "prod/model-v2"},
        "requester": {"id": "agent-001", "type": "ai_agent"},
        "context": {"environment": "production"}
    })

    print(f"Decision: {decision.decision}")
    print(f"Audit ID: {decision.audit_id}")

Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.audit_logger import AuditEntry, AuditLogger
from src.hitl_handler import HITLHandler
from src.opa_client import OPAClient, OPAConnectionError, OPAPolicyError

# Configure logging
logger = logging.getLogger(__name__)


# Custom exceptions for governance workflow errors
class GovernanceWorkflowError(Exception):
    """Base exception for governance workflow errors"""

    pass


class GovernanceValidationError(GovernanceWorkflowError):
    """Raised when validation fails"""

    pass


class GovernanceEvaluationError(GovernanceWorkflowError):
    """Raised when policy evaluation fails"""

    pass


@dataclass
class GovernanceDecision:
    """
    Final governance decision response.

    This dataclass encapsulates the complete decision result including
    risk assessment, HITL workflow details, audit trail reference,
    and denial reasons (if applicable).
    """

    # Final decision
    decision: str  # "allow" or "deny"
    audit_id: UUID  # Reference to audit log entry

    # Risk assessment details
    risk_assessment: dict  # Full risk evaluation from agent_actions.rego
    risk_score: float  # Calculated risk score (0.0-1.0)
    risk_category: str  # Risk category (low, medium, high, critical)

    # Constitutional validation
    constitutional_valid: bool  # Whether action passed constitutional validation
    constitutional_violations: list[str]  # List of violated principles

    # HITL workflow details
    hitl_required: bool  # Whether HITL approval was required
    hitl_workflow: dict | None  # HITL workflow details (if applicable)

    # Decision metadata
    denial_reasons: list[str]  # Reasons for denial (if denied)
    processing_time_ms: float  # Total processing time in milliseconds
    metadata: dict  # Additional metadata and context

    def to_dict(self) -> dict:
        """Convert decision to dictionary for JSON serialization"""
        return {
            "decision": self.decision,
            "audit_id": str(self.audit_id),
            "risk_assessment": {
                "risk_score": self.risk_score,
                "risk_category": self.risk_category,
                "details": self.risk_assessment,
            },
            "constitutional": {
                "valid": self.constitutional_valid,
                "violations": self.constitutional_violations,
            },
            "hitl": {
                "required": self.hitl_required,
                "workflow": self.hitl_workflow,
            },
            "denial_reasons": self.denial_reasons,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata,
        }


class GovernanceWorkflow:
    """
    Orchestrates the complete end-to-end governance workflow.

    This class coordinates policy evaluation, HITL approvals, and audit logging
    to provide comprehensive governance decision-making for AI agent actions.

    The workflow consists of 6 steps:
    1. Constitutional validation - Verify action complies with constitutional principles
    2. Action evaluation - Assess risk and determine if action is allowed
    3. HITL determination - Check if human approval is required
    4. Approval handling - Process HITL workflow if needed
    5. Audit logging - Record decision to immutable audit trail
    6. Decision response - Return final decision with full context

    Attributes:
        opa: OPAClient instance for policy evaluation
        audit: AuditLogger instance for audit trail logging
        hitl: HITLHandler instance for human approval workflow
    """

    def __init__(
        self,
        opa_client: OPAClient,
        audit_logger: AuditLogger,
        hitl_handler: HITLHandler,
    ):
        """
        Initialize governance workflow orchestrator.

        Args:
            opa_client: OPAClient instance for policy evaluation
            audit_logger: AuditLogger instance for audit logging
            hitl_handler: HITLHandler instance for HITL workflow

        Raises:
            ValueError: If any required component is None
        """
        if opa_client is None:
            raise ValueError("opa_client is required")
        if audit_logger is None:
            raise ValueError("audit_logger is required")
        if hitl_handler is None:
            raise ValueError("hitl_handler is required")

        self.opa = opa_client
        self.audit = audit_logger
        self.hitl = hitl_handler

        logger.info("Governance workflow orchestrator initialized")

    def evaluate_action(self, action_request: dict) -> GovernanceDecision:
        """
        Main entry point: evaluate an action through the full governance workflow.

        This method orchestrates the complete workflow from constitutional validation
        through final decision and audit logging. It handles all error cases and
        ensures consistent logging regardless of the decision path.

        Args:
            action_request: Complete action request with structure:
                {
                    "action": {"type": "...", "resource": "...", "parameters": {}},
                    "requester": {"id": "...", "type": "...", "role": "..."},
                    "context": {"environment": "...", "constitutional_hash": "..."}
                }

        Returns:
            GovernanceDecision with complete decision details

        Raises:
            GovernanceWorkflowError: If workflow execution fails
        """
        start_time = time.time()
        logger.info(f"Evaluating action: {action_request.get('action', {}).get('type', 'unknown')}")

        # Initialize tracking variables
        constitutional_valid = False
        constitutional_violations = []
        action_allowed = False
        risk_score = 0.0
        risk_assessment = {}
        hitl_required = False
        hitl_info = {}
        hitl_workflow_result = None
        denial_reasons = []
        final_decision = "deny"  # Default deny

        try:
            # Step 1: Validate constitutional compliance
            logger.debug("Step 1: Validating constitutional compliance")
            constitutional_valid, constitutional_violations = self._validate_constitution(
                action_request
            )

            if not constitutional_valid:
                # Early exit: Constitutional violation
                denial_reasons.extend(constitutional_violations)
                logger.warning(
                    f"Constitutional validation failed: {len(constitutional_violations)} violations"
                )
            else:
                # Step 2: Evaluate action and assess risk
                logger.debug("Step 2: Evaluating action and assessing risk")
                action_allowed, risk_score, risk_assessment = self._evaluate_action(action_request)

                if not action_allowed:
                    # Early exit: Policy denial
                    denial_reasons = risk_assessment.get("denial_reasons", [])
                    logger.warning(f"Action evaluation denied: {denial_reasons}")
                else:
                    # Step 3: Determine if HITL approval required
                    logger.debug("Step 3: Determining HITL requirement")
                    hitl_required, hitl_info = self._determine_hitl(action_request, risk_score)

                    if hitl_required:
                        # Step 4: Handle HITL approval workflow
                        logger.debug("Step 4: Processing HITL approval workflow")
                        hitl_approved, hitl_workflow_result = self._handle_approval(
                            action_request, hitl_info
                        )

                        if hitl_approved:
                            final_decision = "allow"
                            logger.info(
                                f"Action approved by HITL reviewer: {hitl_workflow_result.get('reviewer_id')}"
                            )
                        else:
                            final_decision = "deny"
                            denial_reasons.append(
                                hitl_workflow_result.get(
                                    "decision_note", "Denied by human reviewer"
                                )
                            )
                            logger.warning(f"Action denied by HITL reviewer: {denial_reasons[-1]}")
                    else:
                        # Auto-approved (no HITL required)
                        final_decision = "allow"
                        logger.info(f"Action auto-approved (risk score: {risk_score:.3f})")

            # Step 5: Log decision to audit trail
            logger.debug("Step 5: Logging decision to audit trail")
            audit_id = self._log_decision(
                action_request=action_request,
                decision=final_decision,
                risk_score=risk_score,
                risk_assessment=risk_assessment,
                constitutional_valid=constitutional_valid,
                constitutional_violations=constitutional_violations,
                hitl_required=hitl_required,
                hitl_workflow=hitl_workflow_result,
                denial_reasons=denial_reasons,
            )

            # Step 6: Build final decision response
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            logger.debug("Step 6: Building decision response")

            decision = self._build_decision_response(
                decision=final_decision,
                audit_id=audit_id,
                risk_score=risk_score,
                risk_assessment=risk_assessment,
                constitutional_valid=constitutional_valid,
                constitutional_violations=constitutional_violations,
                hitl_required=hitl_required,
                hitl_workflow=hitl_workflow_result,
                denial_reasons=denial_reasons,
                processing_time=processing_time,
            )

            logger.info(
                f"Workflow complete: {final_decision} (processing time: {processing_time:.2f}ms)"
            )
            return decision

        except Exception as e:
            # Handle any unexpected errors
            logger.error(f"Governance workflow error: {e}", exc_info=True)

            # Log the error to audit trail
            processing_time = (time.time() - start_time) * 1000
            error_message = f"Workflow error: {str(e)}"
            denial_reasons.append(error_message)

            try:
                audit_id = self._log_decision(
                    action_request=action_request,
                    decision="deny",
                    risk_score=risk_score,
                    risk_assessment=risk_assessment,
                    constitutional_valid=constitutional_valid,
                    constitutional_violations=constitutional_violations,
                    hitl_required=hitl_required,
                    hitl_workflow=None,
                    denial_reasons=denial_reasons,
                )
            except Exception as audit_error:
                logger.error(f"Failed to log error to audit trail: {audit_error}")
                audit_id = None

            # Return error decision
            return self._build_decision_response(
                decision="deny",
                audit_id=audit_id,
                risk_score=risk_score,
                risk_assessment=risk_assessment,
                constitutional_valid=constitutional_valid,
                constitutional_violations=constitutional_violations,
                hitl_required=hitl_required,
                hitl_workflow=None,
                denial_reasons=denial_reasons,
                processing_time=processing_time,
            )

    def _validate_constitution(self, action_request: dict) -> tuple[bool, list[str]]:
        """
        Step 1: Validate action against constitutional principles.

        Evaluates the action_request against constitutional.rego policy to ensure
        it complies with all constitutional principles.

        Args:
            action_request: Complete action request dictionary

        Returns:
            Tuple of (valid: bool, violations: list[str])
            - valid: True if action passes constitutional validation
            - violations: List of violated principles (empty if valid)

        Raises:
            GovernanceEvaluationError: If policy evaluation fails
        """
        try:
            result = self.opa.evaluate_policy(
                policy_path="acgs2/constitutional/validate",
                input_data=action_request,
            )

            # Extract result from OPA response
            policy_result = result.get("result", {})
            valid = policy_result.get("valid", False)
            violations = policy_result.get("denial_reasons", [])

            logger.debug(f"Constitutional validation: valid={valid}, violations={len(violations)}")
            return valid, violations

        except (OPAConnectionError, OPAPolicyError) as e:
            logger.error(f"Constitutional validation failed: {e}")
            raise GovernanceEvaluationError(
                f"Failed to validate constitutional compliance: {e}"
            ) from e

    def _evaluate_action(self, action_request: dict) -> tuple[bool, float, dict]:
        """
        Step 2: Evaluate action and calculate risk score.

        Evaluates the action_request against agent_actions.rego policy to determine
        if the action is allowed and calculate its risk score.

        Args:
            action_request: Complete action request dictionary

        Returns:
            Tuple of (allowed: bool, risk_score: float, assessment: dict)
            - allowed: True if action is permitted by policy
            - risk_score: Calculated risk score (0.0-1.0)
            - assessment: Complete risk assessment details

        Raises:
            GovernanceEvaluationError: If policy evaluation fails
        """
        try:
            result = self.opa.evaluate_policy(
                policy_path="acgs2/agent_actions/evaluate",
                input_data=action_request,
            )

            # Extract result from OPA response
            policy_result = result.get("result", {})
            allowed = policy_result.get("allowed", False)
            risk_score = policy_result.get("risk_score", 0.0)

            logger.debug(f"Action evaluation: allowed={allowed}, risk_score={risk_score:.3f}")
            return allowed, risk_score, policy_result

        except (OPAConnectionError, OPAPolicyError) as e:
            logger.error(f"Action evaluation failed: {e}")
            raise GovernanceEvaluationError(f"Failed to evaluate action: {e}") from e

    def _determine_hitl(self, action_request: dict, risk_score: float) -> tuple[bool, dict]:
        """
        Step 3: Determine if human-in-the-loop approval is required.

        Evaluates against hitl_approval.rego policy to determine if the action
        requires human review based on risk score and action type.

        Args:
            action_request: Complete action request dictionary
            risk_score: Calculated risk score from action evaluation

        Returns:
            Tuple of (required: bool, hitl_info: dict)
            - required: True if HITL approval is needed
            - hitl_info: HITL workflow details (expertise, timeout, escalation, etc.)

        Raises:
            GovernanceEvaluationError: If policy evaluation fails
        """
        try:
            # Add risk_score to input for HITL policy
            hitl_input = {**action_request, "risk_score": risk_score}

            result = self.opa.evaluate_policy(
                policy_path="acgs2/hitl/determine",
                input_data=hitl_input,
            )

            # Extract result from OPA response
            policy_result = result.get("result", {})
            required = policy_result.get("hitl_required", False)

            logger.debug(f"HITL determination: required={required}")
            return required, policy_result

        except (OPAConnectionError, OPAPolicyError) as e:
            logger.error(f"HITL determination failed: {e}")
            raise GovernanceEvaluationError(f"Failed to determine HITL requirement: {e}") from e

    def _handle_approval(self, action_request: dict, hitl_info: dict) -> tuple[bool, dict]:
        """
        Step 4: Handle human-in-the-loop approval workflow.

        Creates an approval request, simulates the review process, and waits
        for the reviewer decision.

        Args:
            action_request: Complete action request dictionary
            hitl_info: HITL workflow details from policy evaluation

        Returns:
            Tuple of (approved: bool, workflow_result: dict)
            - approved: True if reviewer approved the action
            - workflow_result: Complete HITL workflow details including decision

        Raises:
            GovernanceWorkflowError: If HITL workflow fails
        """
        try:
            # Create approval request
            approval_request = self.hitl.create_approval_request(
                action_request=action_request,
                risk_score=hitl_info.get("risk_score", 0.0),
                required_expertise=hitl_info.get("required_expertise", "senior_devops"),
                timeout_seconds=hitl_info.get("timeout_seconds", 7200),
                priority=hitl_info.get("priority", "normal"),
            )

            logger.info(f"Created HITL approval request: {approval_request.request_id}")

            # Simulate reviewer assignment and decision
            reviewer_id = self.hitl.assign_reviewer(approval_request.required_expertise)
            logger.debug(f"Assigned reviewer: {reviewer_id}")

            # Simulate review process
            decision = self.hitl.simulate_review(approval_request, reviewer_id)

            # Build workflow result
            workflow_result = {
                "request_id": str(approval_request.request_id),
                "approved": decision.approved,
                "reviewer_id": decision.reviewer_id,
                "reviewer_role": decision.reviewer_role,
                "decision_note": decision.decision_note,
                "reviewed_at": decision.reviewed_at.isoformat(),
                "review_duration_seconds": decision.review_duration_seconds,
                "escalated": decision.escalated,
                "escalated_to": decision.escalated_to,
            }

            logger.info(
                f"HITL review completed: approved={decision.approved}, reviewer={decision.reviewer_id}"
            )
            return decision.approved, workflow_result

        except Exception as e:
            logger.error(f"HITL approval workflow failed: {e}")
            raise GovernanceWorkflowError(f"Failed to process HITL approval: {e}") from e

    def _log_decision(
        self,
        action_request: dict,
        decision: str,
        risk_score: float,
        risk_assessment: dict,
        constitutional_valid: bool,
        constitutional_violations: list[str],
        hitl_required: bool,
        hitl_workflow: dict | None,
        denial_reasons: list[str],
    ) -> UUID | None:
        """
        Step 5: Log governance decision to audit trail.

        Records the complete decision chain to the immutable audit log with
        full context, risk assessment, and compliance metadata.

        Args:
            action_request: Original action request
            decision: Final decision ("allow" or "deny")
            risk_score: Calculated risk score
            risk_assessment: Complete risk assessment details
            constitutional_valid: Constitutional validation result
            constitutional_violations: List of constitutional violations
            hitl_required: Whether HITL was required
            hitl_workflow: HITL workflow details (if applicable)
            denial_reasons: List of denial reasons (if denied)

        Returns:
            UUID of the audit log entry, or None if logging fails

        Raises:
            GovernanceWorkflowError: If audit logging fails critically
        """
        try:
            # Evaluate audit policy to get retention and compliance metadata
            audit_input = {
                **action_request,
                "decision": decision,
                "risk_score": risk_score,
                "hitl_required": hitl_required,
            }

            audit_policy_result = self.opa.evaluate_policy(
                policy_path="acgs2/audit/requirements",
                input_data=audit_input,
            )

            audit_requirements = audit_policy_result.get("result", {})

            # Extract action details
            action = action_request.get("action", {})
            requester = action_request.get("requester", {})
            context = action_request.get("context", {})

            # Create audit entry
            entry = AuditEntry(
                timestamp=datetime.now(UTC),
                action_type=action.get("type", "unknown"),
                requester_id=requester.get("id", "unknown"),
                requester_type=requester.get("type"),
                resource=action.get("resource", ""),
                resource_type=action.get("parameters", {}).get("resource_type"),
                decision=decision,
                environment=context.get("environment"),
                risk_score=risk_score,
                risk_category=risk_assessment.get("category", "unknown"),
                constitutional_valid=constitutional_valid,
                constitutional_violations=constitutional_violations,
                hitl_required=hitl_required,
                hitl_decision=hitl_workflow,
                denial_reasons=denial_reasons if denial_reasons else None,
                compliance_tags=audit_requirements.get("compliance_tags", []),
                retention_days=audit_requirements.get("retention_days", 365),
                log_level=audit_requirements.get("log_level", "normal"),
                metadata={
                    "risk_factors": risk_assessment.get("factors", {}),
                    "session_id": context.get("session_id"),
                    "constitutional_hash": context.get("constitutional_hash"),
                },
            )

            # Log to audit trail
            audit_id = self.audit.log_decision(entry)
            logger.info(f"Decision logged to audit trail: {audit_id}")
            return audit_id

        except Exception as e:
            logger.error(f"Failed to log decision to audit trail: {e}")
            # Don't fail the workflow on audit logging errors
            return None

    def _build_decision_response(
        self,
        decision: str,
        audit_id: UUID | None,
        risk_score: float,
        risk_assessment: dict,
        constitutional_valid: bool,
        constitutional_violations: list[str],
        hitl_required: bool,
        hitl_workflow: dict | None,
        denial_reasons: list[str],
        processing_time: float,
    ) -> GovernanceDecision:
        """
        Step 6: Build final governance decision response.

        Constructs a comprehensive GovernanceDecision object with all context,
        risk assessment, HITL details, and audit trail reference.

        Args:
            decision: Final decision ("allow" or "deny")
            audit_id: UUID of audit log entry
            risk_score: Calculated risk score
            risk_assessment: Complete risk assessment details
            constitutional_valid: Constitutional validation result
            constitutional_violations: List of constitutional violations
            hitl_required: Whether HITL was required
            hitl_workflow: HITL workflow details (if applicable)
            denial_reasons: List of denial reasons (if denied)
            processing_time: Total workflow processing time in milliseconds

        Returns:
            GovernanceDecision instance with complete decision details
        """
        return GovernanceDecision(
            decision=decision,
            audit_id=audit_id,
            risk_assessment=risk_assessment,
            risk_score=risk_score,
            risk_category=risk_assessment.get("category", "unknown"),
            constitutional_valid=constitutional_valid,
            constitutional_violations=constitutional_violations,
            hitl_required=hitl_required,
            hitl_workflow=hitl_workflow,
            denial_reasons=denial_reasons,
            processing_time_ms=processing_time,
            metadata={
                "workflow_version": "1.0.0",
                "constitutional_hash": "cdd01ef066bc6cf2",
            },
        )
