package hello

import rego.v1

# Hello World Policy - Basic role-based access control
# ACGS-2 Example: Developer onboarding quickstart
# Demonstrates: default deny, role conditions, action-based rules

default allow := false

# Rule 1: Admins can perform any action
allow if {
	input.user.role == "admin"
}

# Rule 2: Developers can only read resources
allow if {
	input.user.role == "developer"
	input.action == "read"
}

# Helper rule: Generate denial reasons for debugging
denial_reasons contains msg if {
	not allow
	not input.user.role
	msg := "Missing user role in input"
}

denial_reasons contains msg if {
	not allow
	input.user.role
	input.user.role != "admin"
	input.user.role != "developer"
	msg := sprintf("Unknown role: %s", [input.user.role])
}

denial_reasons contains msg if {
	not allow
	input.user.role == "developer"
	input.action != "read"
	msg := sprintf("Developers can only read, attempted: %s", [input.action])
}
