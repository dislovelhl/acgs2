package ai.model.risk

import rego.v1

# Risk Assessment Policy - AI model risk categorization
# ACGS-2 Example: Developer onboarding - AI model approval workflow
# Demonstrates: risk thresholds, category classification, threshold configuration

# Risk thresholds (configurable via data)
default low_threshold := 0.3

default high_threshold := 0.7

# Risk category determination based on score
category := "low" if {
	input.model.risk_score <= low_threshold
}

category := "medium" if {
	input.model.risk_score > low_threshold
	input.model.risk_score <= high_threshold
}

category := "high" if {
	input.model.risk_score > high_threshold
}

# Default category when risk_score is missing
default category := "unknown"

# Boolean helpers for easy rule composition
is_low_risk if {
	category == "low"
}

is_medium_risk if {
	category == "medium"
}

is_high_risk if {
	category == "high"
}

# Risk score validation
valid_risk_score if {
	input.model.risk_score >= 0
	input.model.risk_score <= 1
}

# Risk assessment result with full details
assessment := {
	"category": category,
	"score": input.model.risk_score,
	"low_threshold": low_threshold,
	"high_threshold": high_threshold,
	"requires_review": is_high_risk,
	"valid": valid_risk_score,
} if {
	input.model.risk_score
}

# Violation messages for invalid risk scores
violation contains msg if {
	input.model.risk_score < 0
	msg := sprintf("Invalid risk score: %v (must be >= 0)", [input.model.risk_score])
}

violation contains msg if {
	input.model.risk_score > 1
	msg := sprintf("Invalid risk score: %v (must be <= 1)", [input.model.risk_score])
}

violation contains msg if {
	not input.model.risk_score
	msg := "Missing risk_score in model input"
}
