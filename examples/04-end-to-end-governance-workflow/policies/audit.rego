# Constitutional Hash: cdd01ef066bc6cf2
# ACGS-2 Example 04: End-to-End Governance Workflow
# Audit Policy - Defines what should be logged and compliance metadata

package acgs2.audit

import rego.v1

# =============================================================================
# AUDIT LOGGING REQUIREMENTS
# =============================================================================

# Default behavior: Always log governance decisions
# All actions should be logged for accountability and compliance
default should_log := true

# =============================================================================
# RETENTION PERIOD CALCULATION
# =============================================================================

# Retention periods are based on data sensitivity and regulatory requirements
# Longer retention for sensitive data and compliance requirements

# 7 years (2555 days) for PII access - GDPR/HIPAA compliance
retention_days := 2555 if {
	input.action.type == "access_pii"
}

# 7 years for health-related data - HIPAA compliance
retention_days := 2555 if {
	contains(lower(input.action.resource), "health")
}

# 7 years for financial data - SOX/PCI compliance
retention_days := 2555 if {
	contains(lower(input.action.resource), "financial")
}

# 7 years for any denied action - security audit trail
retention_days := 2555 if {
	input.decision == "deny"
}

# 3 years (1095 days) for production environment - operational compliance
retention_days := 1095 if {
	input.context.environment == "production"
	not extended_retention_required
}

# 1 year (365 days) for other environments - default retention
retention_days := 365 if {
	not extended_retention_required
	input.context.environment != "production"
}

# Default to 1 year if environment not specified
retention_days := 365 if {
	not input.context.environment
	not extended_retention_required
}

# Helper rule to check if extended retention is required
extended_retention_required if {
	input.action.type == "access_pii"
}

extended_retention_required if {
	contains(lower(input.action.resource), "health")
}

extended_retention_required if {
	contains(lower(input.action.resource), "financial")
}

extended_retention_required if {
	input.decision == "deny"
}

# =============================================================================
# COMPLIANCE TAGGING
# =============================================================================

# Compliance tags help identify which regulatory frameworks apply
# Multiple tags can apply to a single action

# SOC2 - System and Organization Controls (production operations)
compliance_tags contains "SOC2" if {
	input.context.environment == "production"
}

# SOC2 - All denials for security audit
compliance_tags contains "SOC2" if {
	input.decision == "deny"
}

# SOC2 - High-risk actions requiring HITL
compliance_tags contains "SOC2" if {
	input.hitl_required == true
}

# GDPR - General Data Protection Regulation (PII access)
compliance_tags contains "GDPR" if {
	input.action.type == "access_pii"
}

# GDPR - Any action on customer data
compliance_tags contains "GDPR" if {
	contains(lower(input.action.resource), "customer")
}

# GDPR - Any action on personal data
compliance_tags contains "GDPR" if {
	contains(lower(input.action.resource), "personal")
}

# HIPAA - Health Insurance Portability and Accountability Act
compliance_tags contains "HIPAA" if {
	contains(lower(input.action.resource), "health")
}

# HIPAA - Medical or patient data
compliance_tags contains "HIPAA" if {
	contains(lower(input.action.resource), "medical")
}

compliance_tags contains "HIPAA" if {
	contains(lower(input.action.resource), "patient")
}

# PCI-DSS - Payment Card Industry Data Security Standard
compliance_tags contains "PCI-DSS" if {
	contains(lower(input.action.resource), "payment")
}

compliance_tags contains "PCI-DSS" if {
	contains(lower(input.action.resource), "card")
}

compliance_tags contains "PCI-DSS" if {
	contains(lower(input.action.resource), "financial")
}

# ISO 27001 - Information Security Management
compliance_tags contains "ISO27001" if {
	input.action.type == "modify_config"
	input.context.environment == "production"
}

compliance_tags contains "ISO27001" if {
	input.action.type == "delete_resource"
}

# =============================================================================
# LOG DETAIL LEVEL
# =============================================================================

# Log detail level determines how much information to capture
# More detailed logging for sensitive or denied actions

# Detailed logging for all denials (need to understand why actions were blocked)
log_level := "detailed" if {
	input.decision == "deny"
}

# Detailed logging for HITL-required actions (need full context for human review)
log_level := "detailed" if {
	input.hitl_required == true
}

# Detailed logging for high-risk actions (risk >= 0.7)
log_level := "detailed" if {
	input.risk_score >= 0.7
}

# Detailed logging for production environment changes
log_level := "detailed" if {
	input.context.environment == "production"
	production_change_action
}

# Detailed logging for PII access
log_level := "detailed" if {
	input.action.type == "access_pii"
}

# Detailed logging for any compliance-tagged action
log_level := "detailed" if {
	count(compliance_tags) > 0
}

# Summary logging for low-risk approved actions
log_level := "summary" if {
	input.risk_score < 0.3
	input.decision == "allow"
	not input.hitl_required
}

# Default to normal logging if none of the above apply
log_level := "normal" if {
	not input.decision == "deny"
	not input.hitl_required
	input.risk_score >= 0.3
	input.risk_score < 0.7
}

# =============================================================================
# METADATA INCLUSION
# =============================================================================

# Include full metadata for compliance-tagged actions
default include_metadata := false

include_metadata if {
	count(compliance_tags) > 0
}

# Include metadata for production environment
include_metadata if {
	input.context.environment == "production"
}

# Include metadata for HITL actions
include_metadata if {
	input.hitl_required == true
}

# Include metadata for denied actions
include_metadata if {
	input.decision == "deny"
}

# Include metadata for high-risk actions
include_metadata if {
	input.risk_score >= 0.7
}

# =============================================================================
# SENSITIVE DATA DETECTION
# =============================================================================

# Identify if the action involves sensitive data that requires extra logging care
sensitive_data_involved if {
	input.action.type == "access_pii"
}

sensitive_data_involved if {
	contains(lower(input.action.resource), "health")
}

sensitive_data_involved if {
	contains(lower(input.action.resource), "medical")
}

sensitive_data_involved if {
	contains(lower(input.action.resource), "financial")
}

sensitive_data_involved if {
	contains(lower(input.action.resource), "payment")
}

sensitive_data_involved if {
	contains(lower(input.action.resource), "personal")
}

sensitive_data_involved if {
	contains(lower(input.action.resource), "customer")
}

# =============================================================================
# HELPER RULES
# =============================================================================

# Production change actions that need detailed logging
production_change_action if {
	input.action.type == "modify_config"
}

production_change_action if {
	input.action.type == "deploy_model"
}

production_change_action if {
	input.action.type == "delete_resource"
}

production_change_action if {
	input.action.type == "execute_code"
}

# String helper for case-insensitive contains
lower(s) := lower_s if {
	lower_s := lower(s)
}

# =============================================================================
# RESULT STRUCTURE
# =============================================================================

# Main result that includes all audit requirements
result := {
	"should_log": should_log,
	"retention_days": retention_days,
	"compliance_tags": compliance_tags,
	"log_level": log_level,
	"include_metadata": include_metadata,
	"sensitive_data": sensitive_data_involved,
	"action_type": input.action.type,
	"environment": input.context.environment,
	"decision": input.decision,
}
