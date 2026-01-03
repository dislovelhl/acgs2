package data.rbac

import rego.v1

# Role-Based Access Control (RBAC) Policy - Role hierarchy and permissions
# ACGS-2 Example: Developer onboarding - Data access control
# Demonstrates: role hierarchy, permission levels, role validation

# Role hierarchy: admin > manager > analyst > viewer
# Higher numeric value = more permissions
role_hierarchy := {
	"admin": 4,
	"manager": 3,
	"analyst": 2,
	"viewer": 1,
}

# Valid roles for input validation
valid_roles := {"admin", "manager", "analyst", "viewer"}

# Check if user has a valid role
valid_role if {
	input.user.role
	role_hierarchy[input.user.role]
}

# Get the user's permission level (0 if invalid/missing)
user_level := level if {
	valid_role
	level := role_hierarchy[input.user.role]
} else := 0

# Check if user is at least a specific role
is_admin if {
	user_level >= role_hierarchy["admin"]
}

is_manager_or_above if {
	user_level >= role_hierarchy["manager"]
}

is_analyst_or_above if {
	user_level >= role_hierarchy["analyst"]
}

is_viewer_or_above if {
	user_level >= role_hierarchy["viewer"]
}

# Role-based action permissions
# Admins can perform any action
can_admin if {
	is_admin
}

# Managers can read, write, but not delete
can_write if {
	is_manager_or_above
	input.action == "write"
}

can_write if {
	is_admin
	input.action == "delete"
}

# Analysts can read and analyze
can_analyze if {
	is_analyst_or_above
	input.action == "analyze"
}

# Everyone can read
can_read if {
	is_viewer_or_above
	input.action == "read"
}
