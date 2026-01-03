# Constitutional Hash: cdd01ef066bc6cf2
# ACGS-2 Example 04: End-to-End Governance Workflow
# Agent Actions Policy - Evaluates actions and calculates risk scores

package acgs2.agent_actions

import rego.v1

# =============================================================================
# ACTION RISK SCORING
# =============================================================================

# Base risk scores for each action type (0.0 to 1.0)
action_risk_scores := {
	"read_data": 0.2,
	"write_data": 0.5,
	"modify_config": 0.6,
	"deploy_model": 0.7,
	"delete_resource": 0.9,
	"access_pii": 0.8,
	"execute_code": 0.85,
}

# Environment multipliers adjust risk based on environment
environment_multipliers := {
	"development": 0.5,
	"staging": 0.75,
	"production": 1.0,
}

# =============================================================================
# RISK CALCULATION
# =============================================================================

# Get base risk for the action type
base_risk := risk if {
	action_type := input.action.type
	risk := action_risk_scores[action_type]
}

# Default to high risk if action type unknown
base_risk := 0.8 if {
	action_type := input.action.type
	not action_risk_scores[action_type]
}

# Get environment multiplier
env_multiplier := multiplier if {
	environment := input.context.environment
	multiplier := environment_multipliers[environment]
}

# Default to production multiplier if environment unknown
env_multiplier := 1.0 if {
	environment := input.context.environment
	not environment_multipliers[environment]
}

# Calculate resource sensitivity modifier
resource_modifier := modifier if {
	# Higher sensitivity for PII, customer data, or production databases
	contains(lower(input.action.resource), "pii")
	modifier := 1.2
} else := modifier if {
	contains(lower(input.action.resource), "customer")
	modifier := 1.15
} else := modifier if {
	contains(lower(input.action.resource), "database")
	input.context.environment == "production"
	modifier := 1.1
} else := 1.0

# Final risk score calculation (capped at 1.0)
risk_score := score if {
	raw_score := base_risk * env_multiplier * resource_modifier
	score := min([1.0, raw_score])
}

# =============================================================================
# RISK CATEGORIZATION
# =============================================================================

# Categorize risk level based on score
category := "low" if {
	risk_score <= 0.3
}

category := "medium" if {
	risk_score > 0.3
	risk_score <= 0.7
}

category := "high" if {
	risk_score > 0.7
	risk_score <= 0.9
}

category := "critical" if {
	risk_score > 0.9
}

# =============================================================================
# ACTION EVALUATION RULES
# =============================================================================

# Default deny - actions must be explicitly allowed
default allowed := false

# Read data actions - allowed with basic checks
allowed if {
	input.action.type == "read_data"
	resource_accessible
}

# Resource is accessible if it's not explicitly restricted
resource_accessible if {
	not resource_restricted
}

# Restricted resources require additional authorization
resource_restricted if {
	contains(lower(input.action.resource), "pii")
}

resource_restricted if {
	contains(lower(input.action.resource), "secret")
}

resource_restricted if {
	contains(lower(input.action.resource), "credential")
}

# Write data actions - allowed with validation
allowed if {
	input.action.type == "write_data"
	valid_write_operation
}

valid_write_operation if {
	# Must have a stated purpose
	input.action.parameters.purpose
	# Size must be reasonable (if specified)
	size_reasonable
}

size_reasonable if {
	# If size not specified, assume reasonable
	not input.action.parameters.size_bytes
}

size_reasonable if {
	# If specified, must be under 100MB
	size := input.action.parameters.size_bytes
	size <= 104857600
}

# Modify configuration - requires change ticket
allowed if {
	input.action.type == "modify_config"
	config_change_authorized
}

config_change_authorized if {
	# Must have change ticket
	input.action.parameters.change_ticket
	# Change type must be specified
	input.action.parameters.change_type
}

# Deploy model - requires validation and documentation
allowed if {
	input.action.type == "deploy_model"
	model_deployment_authorized
}

model_deployment_authorized if {
	# Model must be validated
	model_validated
	# Documentation must be complete
	documentation_complete
}

model_validated if {
	input.action.parameters.bias_tested == true
	input.action.parameters.version
}

documentation_complete if {
	input.action.parameters.documentation_complete == true
}

# PII access - requires valid purpose and legal basis
allowed if {
	input.action.type == "access_pii"
	pii_access_authorized
}

pii_access_authorized if {
	# Must have valid purpose
	input.action.parameters.purpose
	# Must have legal basis
	input.action.parameters.legal_basis
	# Purpose must be valid (checked in constitutional.rego)
	input.action.parameters.purpose != "training"
}

# Delete resource - requires strong justification
allowed if {
	input.action.type == "delete_resource"
	deletion_authorized
}

deletion_authorized if {
	# Must have change ticket
	input.action.parameters.change_ticket
	# Must have reason
	input.action.parameters.reason
	# Reason must not be empty
	input.action.parameters.reason != ""
}

# Execute code - highly restricted
allowed if {
	input.action.type == "execute_code"
	code_execution_authorized
}

code_execution_authorized if {
	# Must have strong justification
	input.action.parameters.justification
	input.action.parameters.justification != ""
	# Code must be provided for review
	input.action.parameters.code
	# Must not be in production without approval context
	code_execution_safe
}

code_execution_safe if {
	# Safe if not in production
	input.context.environment != "production"
}

code_execution_safe if {
	# Safe in production only with emergency justification
	input.context.environment == "production"
	input.action.parameters.justification == "emergency_patch"
}

# =============================================================================
# DENIAL REASONS
# =============================================================================

# Unknown action type
denial_reasons contains msg if {
	action_type := input.action.type
	not action_risk_scores[action_type]
	msg := sprintf("Unknown action type: %s (treating as high risk)", [action_type])
}

# Read data denials
denial_reasons contains msg if {
	input.action.type == "read_data"
	not allowed
	resource_restricted
	msg := sprintf("Access denied: resource '%s' is restricted and requires additional authorization", [input.action.resource])
}

# Write data denials
denial_reasons contains msg if {
	input.action.type == "write_data"
	not allowed
	not input.action.parameters.purpose
	msg := "Write operation requires a stated purpose"
}

denial_reasons contains msg if {
	input.action.type == "write_data"
	not allowed
	input.action.parameters.size_bytes
	input.action.parameters.size_bytes > 104857600
	msg := sprintf("Write operation size exceeds limit: %d bytes (max: 100MB)", [input.action.parameters.size_bytes])
}

# Modify config denials
denial_reasons contains msg if {
	input.action.type == "modify_config"
	not allowed
	not input.action.parameters.change_ticket
	msg := "Configuration changes require a change ticket"
}

denial_reasons contains msg if {
	input.action.type == "modify_config"
	not allowed
	not input.action.parameters.change_type
	msg := "Configuration changes require a specified change type"
}

# Deploy model denials
denial_reasons contains msg if {
	input.action.type == "deploy_model"
	not allowed
	not input.action.parameters.bias_tested
	msg := "Model deployment requires bias testing"
}

denial_reasons contains msg if {
	input.action.type == "deploy_model"
	not allowed
	input.action.parameters.bias_tested == false
	msg := "Model has not passed bias testing"
}

denial_reasons contains msg if {
	input.action.type == "deploy_model"
	not allowed
	not input.action.parameters.version
	msg := "Model deployment requires version specification"
}

denial_reasons contains msg if {
	input.action.type == "deploy_model"
	not allowed
	not input.action.parameters.documentation_complete
	msg := "Model deployment requires complete documentation"
}

denial_reasons contains msg if {
	input.action.type == "deploy_model"
	not allowed
	input.action.parameters.documentation_complete == false
	msg := "Model documentation is incomplete"
}

# PII access denials
denial_reasons contains msg if {
	input.action.type == "access_pii"
	not allowed
	not input.action.parameters.purpose
	msg := "PII access requires a stated purpose"
}

denial_reasons contains msg if {
	input.action.type == "access_pii"
	not allowed
	not input.action.parameters.legal_basis
	msg := "PII access requires a legal basis"
}

denial_reasons contains msg if {
	input.action.type == "access_pii"
	not allowed
	input.action.parameters.purpose == "training"
	msg := "PII access for training purposes is not permitted (constitutional violation)"
}

# Delete resource denials
denial_reasons contains msg if {
	input.action.type == "delete_resource"
	not allowed
	not input.action.parameters.change_ticket
	msg := "Resource deletion requires a change ticket"
}

denial_reasons contains msg if {
	input.action.type == "delete_resource"
	not allowed
	not input.action.parameters.reason
	msg := "Resource deletion requires a stated reason"
}

denial_reasons contains msg if {
	input.action.type == "delete_resource"
	not allowed
	input.action.parameters.reason == ""
	msg := "Resource deletion reason cannot be empty"
}

# Execute code denials
denial_reasons contains msg if {
	input.action.type == "execute_code"
	not allowed
	not input.action.parameters.justification
	msg := "Code execution requires justification"
}

denial_reasons contains msg if {
	input.action.type == "execute_code"
	not allowed
	input.action.parameters.justification == ""
	msg := "Code execution justification cannot be empty"
}

denial_reasons contains msg if {
	input.action.type == "execute_code"
	not allowed
	not input.action.parameters.code
	msg := "Code execution requires code to be provided for review"
}

denial_reasons contains msg if {
	input.action.type == "execute_code"
	not allowed
	input.context.environment == "production"
	input.action.parameters.justification != "emergency_patch"
	msg := "Code execution in production requires emergency justification"
}

# =============================================================================
# OUTPUT STRUCTURE
# =============================================================================

# Risk factors for transparency
factors := {
	"action_type_risk": base_risk,
	"environment_multiplier": env_multiplier,
	"resource_sensitivity": resource_modifier,
	"final_risk_score": risk_score,
}

# Complete evaluation result
result := {
	"allowed": allowed,
	"risk_score": risk_score,
	"category": category,
	"factors": factors,
	"denial_reasons": denial_reasons,
	"action_type": input.action.type,
	"environment": input.context.environment,
	"evaluated_at": time.now_ns(),
}
