package data.access

import rego.v1

# Data Access Control Policy - Sensitivity-based access with ABAC
# ACGS-2 Example: Developer onboarding - Data access control
# Demonstrates: data sensitivity levels, ABAC patterns, context-based access

# Import RBAC for role hierarchy
import data.rbac

# Data sensitivity levels: higher value = more restricted
sensitivity_levels := {
	"public": 1,
	"internal": 2,
	"confidential": 3,
	"restricted": 4,
}

# Valid sensitivity classifications
valid_sensitivity := {"public", "internal", "confidential", "restricted"}

# Default deny - explicit access grant required
default allow := false

# Rule 1: Admins can access all data regardless of sensitivity
allow if {
	rbac.is_admin
}

# Rule 2: Access based on role hierarchy vs data sensitivity
# User's role level must meet or exceed data sensitivity level
allow if {
	rbac.valid_role
	valid_sensitivity_level
	rbac.user_level >= data_sensitivity_level
}

# Rule 3: Department-based access (ABAC pattern)
# Users can access internal/public data owned by their department
allow if {
	rbac.valid_role
	input.user.department
	input.resource.owner == input.user.department
	data_sensitivity_level <= sensitivity_levels["internal"]
}

# Check if resource has valid sensitivity level
valid_sensitivity_level if {
	input.resource.sensitivity
	sensitivity_levels[input.resource.sensitivity]
}

# Get data sensitivity level (defaults to highest if not specified)
data_sensitivity_level := level if {
	valid_sensitivity_level
	level := sensitivity_levels[input.resource.sensitivity]
} else := 4

# Access status with full context for API responses
status := {
	"allowed": allow,
	"user_role": input.user.role,
	"user_level": rbac.user_level,
	"data_sensitivity": input.resource.sensitivity,
	"data_level": data_sensitivity_level,
	"denial_reasons": denial_reasons,
}

# Denial reason collection for debugging
denial_reasons contains msg if {
	not allow
	not input.user.role
	msg := "Missing user role in input"
}

denial_reasons contains msg if {
	not allow
	input.user.role
	not rbac.valid_role
	msg := sprintf("Invalid role: %s. Valid roles: admin, manager, analyst, viewer", [input.user.role])
}

denial_reasons contains msg if {
	not allow
	not input.resource.sensitivity
	msg := "Missing resource sensitivity level in input"
}

denial_reasons contains msg if {
	not allow
	input.resource.sensitivity
	not valid_sensitivity_level
	msg := sprintf("Invalid sensitivity: %s. Valid levels: public, internal, confidential, restricted", [input.resource.sensitivity])
}

denial_reasons contains msg if {
	not allow
	rbac.valid_role
	valid_sensitivity_level
	rbac.user_level < data_sensitivity_level
	msg := sprintf("Insufficient permissions: %s (level %d) cannot access %s data (level %d)",
		[input.user.role, rbac.user_level, input.resource.sensitivity, data_sensitivity_level])
}
