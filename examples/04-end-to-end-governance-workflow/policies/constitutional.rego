# Constitutional Hash: cdd01ef066bc6cf2
# ACGS-2 Example 04: End-to-End Governance Workflow
# Constitutional Policy - Validates actions against constitutional principles

package acgs2.constitutional

import rego.v1

# =============================================================================
# CONSTITUTIONAL HASH VALIDATION
# =============================================================================

# The expected constitutional hash that must match input
expected_hash := "cdd01ef066bc6cf2"

# =============================================================================
# MAIN DECISION RULES
# =============================================================================

# Default deny - constitutional validation must be explicit
default valid := false

# Valid if hash matches AND no principles are violated
valid if {
	hash_valid
	count(principles_violated) == 0
}

# =============================================================================
# HASH VALIDATION
# =============================================================================

# Hash is valid if it matches the expected constitutional hash
hash_valid if {
	input.context.constitutional_hash == expected_hash
}

# =============================================================================
# CONSTITUTIONAL PRINCIPLES
# =============================================================================

# Principle 1: Transparency
# Actions must be auditable and explainable
# Required: action type and requester identification
transparency_principle if {
	input.action.type
	input.requester.id
	input.requester.role
}

# Principle 2: Accountability
# Actions must have an identified responsible party with clear role
accountability_principle if {
	input.requester.id
	input.requester.type
	# Requester must be an identified entity (not anonymous)
	input.requester.id != ""
	input.requester.id != "anonymous"
}

# Principle 3: Privacy Protection
# PII access must be limited to necessary and lawful purposes
privacy_principle if {
	not violates_privacy
}

# Privacy violation: accessing PII for training without consent
violates_privacy if {
	input.action.type == "access_pii"
	input.action.parameters.purpose == "training"
}

# Privacy violation: accessing PII without stating purpose
violates_privacy if {
	input.action.type == "access_pii"
	not input.action.parameters.purpose
}

# Privacy violation: accessing PII for unauthorized purposes
violates_privacy if {
	input.action.type == "access_pii"
	input.action.parameters.purpose
	not valid_pii_purpose(input.action.parameters.purpose)
}

# Valid PII purposes (lawful and necessary)
valid_pii_purpose(purpose) if {
	purpose in ["analytics", "compliance", "user_request", "legal_requirement", "security_investigation"]
}

# Principle 4: Data Minimization
# Only access data needed for the stated purpose
data_minimization_principle if {
	not violates_data_minimization
}

# Data minimization violation: accessing all data when scope could be limited
violates_data_minimization if {
	input.action.type in ["read_data", "access_pii"]
	input.action.parameters.scope == "all"
	not input.action.parameters.justification
}

# Data minimization violation: no time bounds on historical data access
violates_data_minimization if {
	input.action.type in ["read_data", "access_pii"]
	input.action.parameters.include_historical == true
	not input.action.parameters.time_range
}

# Principle 5: Human Oversight
# High-risk actions must be subject to human review
# Note: This principle checks if oversight CAPABILITY exists, not if approval happened
# Actual HITL approval is handled by the hitl_approval.rego policy
human_oversight_principle if {
	not violates_human_oversight
}

# Human oversight violation: attempting to bypass oversight for sensitive actions
violates_human_oversight if {
	input.action.type in ["delete_resource", "deploy_model", "execute_code"]
	input.context.environment == "production"
	input.action.parameters.bypass_review == true
}

# Principle 6: Fairness
# Actions must not discriminate or introduce bias
fairness_principle if {
	not violates_fairness
}

# Fairness violation: deploying models without bias testing
violates_fairness if {
	input.action.type == "deploy_model"
	input.action.parameters.bias_tested == false
}

# Fairness violation: accessing data in ways that could enable discrimination
violates_fairness if {
	input.action.type == "access_pii"
	input.action.parameters.purpose == "targeting"
	not input.action.parameters.fairness_reviewed
}

# =============================================================================
# PRINCIPLE TRACKING
# =============================================================================

# Collect all principles that passed
principles_passed contains "Transparency" if {
	transparency_principle
}

principles_passed contains "Accountability" if {
	accountability_principle
}

principles_passed contains "Privacy Protection" if {
	privacy_principle
}

principles_passed contains "Data Minimization" if {
	data_minimization_principle
}

principles_passed contains "Human Oversight" if {
	human_oversight_principle
}

principles_passed contains "Fairness" if {
	fairness_principle
}

# Collect all principles that were violated
principles_violated contains "Transparency" if {
	not transparency_principle
}

principles_violated contains "Accountability" if {
	not accountability_principle
}

principles_violated contains "Privacy Protection" if {
	violates_privacy
}

principles_violated contains "Data Minimization" if {
	violates_data_minimization
}

principles_violated contains "Human Oversight" if {
	violates_human_oversight
}

principles_violated contains "Fairness" if {
	violates_fairness
}

# =============================================================================
# DENIAL REASONS
# =============================================================================

# Hash mismatch
denial_reasons contains msg if {
	not hash_valid
	input.context.constitutional_hash
	msg := sprintf("Constitutional hash mismatch: expected %s, got %s", [expected_hash, input.context.constitutional_hash])
}

denial_reasons contains msg if {
	not hash_valid
	not input.context.constitutional_hash
	msg := sprintf("Missing constitutional hash in context (expected: %s)", [expected_hash])
}

# Transparency violations
denial_reasons contains msg if {
	not transparency_principle
	not input.action.type
	msg := "Transparency violation: missing action type"
}

denial_reasons contains msg if {
	not transparency_principle
	not input.requester.id
	msg := "Transparency violation: missing requester ID"
}

denial_reasons contains msg if {
	not transparency_principle
	not input.requester.role
	msg := "Transparency violation: missing requester role"
}

# Accountability violations
denial_reasons contains msg if {
	not accountability_principle
	input.requester.id in ["", "anonymous"]
	msg := "Accountability violation: anonymous requesters not permitted"
}

denial_reasons contains msg if {
	not accountability_principle
	not input.requester.type
	msg := "Accountability violation: missing requester type"
}

# Privacy violations
denial_reasons contains msg if {
	violates_privacy
	input.action.type == "access_pii"
	input.action.parameters.purpose == "training"
	msg := "Privacy violation: PII cannot be used for model training without explicit consent"
}

denial_reasons contains msg if {
	violates_privacy
	input.action.type == "access_pii"
	not input.action.parameters.purpose
	msg := "Privacy violation: PII access requires a stated purpose"
}

denial_reasons contains msg if {
	violates_privacy
	input.action.type == "access_pii"
	input.action.parameters.purpose
	not valid_pii_purpose(input.action.parameters.purpose)
	msg := sprintf("Privacy violation: '%s' is not a valid PII access purpose (allowed: analytics, compliance, user_request, legal_requirement, security_investigation)", [input.action.parameters.purpose])
}

# Data minimization violations
denial_reasons contains msg if {
	violates_data_minimization
	input.action.parameters.scope == "all"
	not input.action.parameters.justification
	msg := "Data minimization violation: accessing all data requires justification"
}

denial_reasons contains msg if {
	violates_data_minimization
	input.action.parameters.include_historical == true
	not input.action.parameters.time_range
	msg := "Data minimization violation: historical data access requires time range specification"
}

# Human oversight violations
denial_reasons contains msg if {
	violates_human_oversight
	input.action.parameters.bypass_review == true
	msg := sprintf("Human oversight violation: cannot bypass review for %s in production", [input.action.type])
}

# Fairness violations
denial_reasons contains msg if {
	violates_fairness
	input.action.type == "deploy_model"
	input.action.parameters.bias_tested == false
	msg := "Fairness violation: models must undergo bias testing before deployment"
}

denial_reasons contains msg if {
	violates_fairness
	input.action.type == "access_pii"
	input.action.parameters.purpose == "targeting"
	not input.action.parameters.fairness_reviewed
	msg := "Fairness violation: PII access for targeting requires fairness review"
}

# =============================================================================
# OUTPUT STRUCTURE
# =============================================================================

# Complete validation result with all details
result := {
	"valid": valid,
	"hash_valid": hash_valid,
	"expected_hash": expected_hash,
	"principles_passed": principles_passed,
	"principles_violated": principles_violated,
	"denial_reasons": denial_reasons,
	"total_principles": 6,
	"passed_count": count(principles_passed),
	"violated_count": count(principles_violated),
}
