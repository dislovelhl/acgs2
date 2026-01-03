package ai.model.approval

import rego.v1

# AI Model Approval Policy - Governance decision logic
# ACGS-2 Example: Developer onboarding - AI model approval workflow
# Demonstrates: multi-factor approval, compliance checks, reviewer approval

# Import risk assessment for category determination
import data.ai.model.risk

# Default deny - explicit approval required
default allowed := false

# Rule 1: Low-risk models with compliance can be auto-approved
allowed if {
	risk.is_low_risk
	compliance_passed
}

# Rule 2: Medium-risk models require full compliance for staging
allowed if {
	risk.is_medium_risk
	compliance_passed
	not is_production
}

# Rule 3: Medium-risk models in production need reviewer approval
allowed if {
	risk.is_medium_risk
	compliance_passed
	is_production
	reviewer_approved
}

# Rule 4: High-risk models always require reviewer approval
allowed if {
	risk.is_high_risk
	compliance_passed
	reviewer_approved
}

# Compliance checks - all required fields must be true
compliance_passed if {
	input.compliance.bias_tested == true
	input.compliance.documentation_complete == true
	input.compliance.security_reviewed == true
}

# Environment detection
is_production if {
	input.deployment.environment == "production"
}

# Reviewer approval status
reviewer_approved if {
	input.reviewer.id
	input.reviewer.approved == true
}

# Approval status with full context
status := {
	"allowed": allowed,
	"risk_category": risk.category,
	"compliance_passed": compliance_passed,
	"reviewer_approved": reviewer_approved,
	"environment": input.deployment.environment,
	"denial_reasons": denial_reasons,
}

# Denial reason collection for debugging
denial_reasons contains msg if {
	not allowed
	not risk.valid_risk_score
	msg := "Invalid or missing risk score"
}

denial_reasons contains msg if {
	not allowed
	risk.valid_risk_score
	not compliance_passed
	not input.compliance.bias_tested
	msg := "Bias testing not completed"
}

denial_reasons contains msg if {
	not allowed
	risk.valid_risk_score
	not compliance_passed
	not input.compliance.documentation_complete
	msg := "Documentation incomplete"
}

denial_reasons contains msg if {
	not allowed
	risk.valid_risk_score
	not compliance_passed
	not input.compliance.security_reviewed
	msg := "Security review not completed"
}

denial_reasons contains msg if {
	not allowed
	risk.is_high_risk
	compliance_passed
	not reviewer_approved
	msg := "High-risk model requires reviewer approval"
}

denial_reasons contains msg if {
	not allowed
	risk.is_medium_risk
	is_production
	compliance_passed
	not reviewer_approved
	msg := "Medium-risk model in production requires reviewer approval"
}

denial_reasons contains msg if {
	not allowed
	risk.category == "unknown"
	msg := "Unable to determine risk category"
}
