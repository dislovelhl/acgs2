# Constitutional Hash: cdd01ef066bc6cf2
# ACGS-2 Example 04: End-to-End Governance Workflow
# HITL Approval Policy - Determines when human approval is required

package acgs2.hitl

import rego.v1

# =============================================================================
# HITL THRESHOLDS
# =============================================================================

# Risk threshold above which HITL approval is required
# Actions with risk_score >= 0.7 will require human review
risk_threshold := 0.7

# =============================================================================
# MAIN DECISION RULES
# =============================================================================

# Default deny - HITL not required unless explicitly triggered
default hitl_required := false

# HITL required if risk score exceeds threshold
hitl_required if {
	input.risk_score >= risk_threshold
}

# HITL required for specific action types (always-require approval)
hitl_required if {
	always_require_approval
}

# =============================================================================
# ALWAYS-REQUIRE APPROVAL RULES
# =============================================================================

# Deploy model to production always requires approval
always_require_approval if {
	input.action.type == "deploy_model"
	input.context.environment == "production"
}

# Deleting resources always requires approval (high risk of data loss)
always_require_approval if {
	input.action.type == "delete_resource"
}

# Accessing PII always requires approval (privacy compliance)
always_require_approval if {
	input.action.type == "access_pii"
}

# Executing code in any environment requires approval (security risk)
always_require_approval if {
	input.action.type == "execute_code"
}

# =============================================================================
# REVIEWER ASSIGNMENT - REQUIRED EXPERTISE
# =============================================================================

# Determine required reviewer expertise based on action type
# Default to senior_devops if no specific expertise required
default required_expertise := "senior_devops"

# ML Safety Specialist for model deployments
required_expertise := "ml_safety_specialist" if {
	input.action.type == "deploy_model"
}

# Data Protection Officer for PII access
required_expertise := "data_protection_officer" if {
	input.action.type == "access_pii"
}

# Security Lead for configuration changes
required_expertise := "security_lead" if {
	input.action.type == "modify_config"
}

# Security Lead for code execution
required_expertise := "security_lead" if {
	input.action.type == "execute_code"
}

# Senior DevOps for resource deletion
required_expertise := "senior_devops" if {
	input.action.type == "delete_resource"
}

# =============================================================================
# TIMEOUT CONFIGURATION
# =============================================================================

# Timeout duration based on risk level
# Higher risk actions get more time for thorough review

# 2 hours (7200 seconds) for medium-high risk (0.7-0.8)
timeout_seconds := 7200 if {
	input.risk_score >= risk_threshold
	input.risk_score < 0.8
}

# 4 hours (14400 seconds) for high-critical risk (0.8+)
timeout_seconds := 14400 if {
	input.risk_score >= 0.8
}

# Default 2 hours if risk score not available but HITL required
timeout_seconds := 7200 if {
	hitl_required
	not input.risk_score
}

# =============================================================================
# ESCALATION RULES
# =============================================================================

# Determine escalation target for high-risk or timeout scenarios
# Returns null if no escalation needed

default escalation_to := null

# Escalate critical risk actions to security director
escalation_to := "security_director" if {
	input.risk_score >= 0.9
}

# Escalate high-risk PII access to compliance officer
escalation_to := "compliance_officer" if {
	input.action.type == "access_pii"
	input.risk_score >= 0.8
}

# Escalate production model deployments with high risk
escalation_to := "ml_director" if {
	input.action.type == "deploy_model"
	input.context.environment == "production"
	input.risk_score >= 0.85
}

# Escalate production deletions with critical risk
escalation_to := "cto" if {
	input.action.type == "delete_resource"
	input.context.environment == "production"
	input.risk_score >= 0.95
}

# =============================================================================
# RATIONALE GENERATION
# =============================================================================

# Generate human-readable rationale for why HITL is required

# Risk-based rationale
rationale := msg if {
	hitl_required
	input.risk_score >= risk_threshold
	not always_require_approval
	msg := sprintf("Risk score %.2f exceeds threshold %.2f, requiring human review", [input.risk_score, risk_threshold])
}

# Action-based rationale: Production model deployment
rationale := msg if {
	always_require_approval
	input.action.type == "deploy_model"
	input.context.environment == "production"
	msg := "Production model deployments always require human approval for safety validation"
}

# Action-based rationale: Resource deletion
rationale := msg if {
	always_require_approval
	input.action.type == "delete_resource"
	msg := "Resource deletion operations always require human approval to prevent data loss"
}

# Action-based rationale: PII access
rationale := msg if {
	always_require_approval
	input.action.type == "access_pii"
	msg := "PII access always requires human approval for privacy compliance (GDPR, HIPAA)"
}

# Action-based rationale: Code execution
rationale := msg if {
	always_require_approval
	input.action.type == "execute_code"
	msg := "Code execution always requires human approval for security validation"
}

# Combined rationale: Both risk and action type
rationale := msg if {
	hitl_required
	always_require_approval
	input.risk_score >= risk_threshold
	msg := sprintf("%s action with risk score %.2f requires mandatory human review", [input.action.type, input.risk_score])
}

# Default rationale if none of the above match
rationale := "Human approval required based on governance policy" if {
	hitl_required
	not input.risk_score
}

# =============================================================================
# APPROVAL PRIORITY
# =============================================================================

# Determine priority level for approval queue
# Higher priority = faster review required

default priority := "normal"

# Critical priority for high-risk actions
priority := "critical" if {
	input.risk_score >= 0.9
}

# High priority for production operations
priority := "high" if {
	input.context.environment == "production"
	input.risk_score >= 0.7
}

# High priority for PII operations
priority := "high" if {
	input.action.type == "access_pii"
}

# Medium priority for staging high-risk actions
priority := "medium" if {
	input.context.environment == "staging"
	input.risk_score >= 0.7
}

# =============================================================================
# BYPASS DETECTION
# =============================================================================

# Detect and flag attempts to bypass HITL approval

bypass_attempted := true if {
	input.action.parameters.bypass_review == true
	hitl_required
}

bypass_warning := msg if {
	bypass_attempted
	msg := "WARNING: Attempt to bypass required human review detected and blocked"
}

# =============================================================================
# OUTPUT STRUCTURE
# =============================================================================

# Complete HITL determination result
result := output if {
	hitl_required
	output := {
		"hitl_required": true,
		"required_expertise": required_expertise,
		"timeout_seconds": timeout_seconds,
		"escalation_to": escalation_to,
		"rationale": rationale,
		"priority": priority,
		"bypass_attempted": bypass_attempted,
		"action_type": input.action.type,
		"environment": input.context.environment,
		"risk_score": input.risk_score,
	}
}

# HITL not required - minimal output
result := output if {
	not hitl_required
	output := {
		"hitl_required": false,
		"rationale": "Action does not meet HITL approval criteria",
		"action_type": input.action.type,
		"environment": input.context.environment,
		"risk_score": input.risk_score,
	}
}
