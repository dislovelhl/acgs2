package hitl.authorization

import future.keywords.if
import future.keywords.in

# Default decision for authorization
default allow := false

# Constitutional hash for HITL approvals
constitutional_hash := "cdd01ef066bc6cf2"

# Role hierarchy and permissions
role_hierarchy := {
    "engineer": 1,
    "analyst": 2,
    "manager": 3,
    "lead": 4,
    "director": 5,
    "vp": 6,
    "executive": 7,
    "ciso": 8,
    "admin": 9
}

# Action permissions by role level
action_permissions := {
    "approve": {
        "min_level": 2,  # Analyst level can approve
        "max_level": 9   # Up to admin
    },
    "reject": {
        "min_level": 2,  # Analyst level can reject
        "max_level": 9   # Up to admin
    },
    "escalate": {
        "min_level": 1,  # Engineer level can escalate
        "max_level": 9   # Up to admin
    },
    "delegate": {
        "min_level": 3,  # Manager level can delegate
        "max_level": 9   # Up to admin
    }
}

# Required approvers for different approval levels
required_approvers := {
    1: ["engineer", "analyst"],          # Level 1: Basic approvals
    2: ["manager", "lead"],              # Level 2: Managerial review
    3: ["director", "vp"],               # Level 3: Executive review
    4: ["executive", "ciso"],            # Level 4: Critical decisions
    5: ["ciso", "admin"]                 # Level 5: Emergency/security
}

# Allow authorization decision
allow if {
    # Verify constitutional hash
    input.constitutional_hash == constitutional_hash

    # Basic validation
    valid_user_role
    valid_action
    valid_resource

    # Check role-based permissions
    has_required_role_level
    action_allowed_for_role
}

# Additional context-based authorization
allow if {
    input.constitutional_hash == constitutional_hash
    contextual_authorization
}

# Role level validation
has_required_role_level if {
    user_level := role_hierarchy[input.user_role]
    user_level >= action_permissions[input.action].min_level
}

has_required_role_level if {
    user_level := role_hierarchy[input.user_role]
    user_level <= action_permissions[input.action].max_level
}

# Action permission validation
action_allowed_for_role if {
    input.action in action_permissions
    user_level := role_hierarchy[input.user_role]
    required_min := action_permissions[input.action].min_level
    required_max := action_permissions[input.action].max_level
    user_level >= required_min
    user_level <= required_max
}

# Validation rules
valid_user_role if {
    input.user_role in role_hierarchy
}

valid_action if {
    input.action in ["approve", "reject", "escalate", "delegate"]
}

valid_resource if {
    input.resource != ""
    count(input.resource) > 0
}

# Contextual authorization for complex scenarios
contextual_authorization if {
    # CISOs can approve any security-related decision
    input.user_role == "ciso"
    input.context.request_priority in ["high", "critical"]
    input.context.decision_type == "security"
}

contextual_authorization if {
    # Executives can approve high-priority business decisions
    input.user_role == "executive"
    input.context.request_priority in ["high", "critical"]
    input.context.decision_type in ["financial", "compliance"]
}

contextual_authorization if {
    # Admins have universal approval authority
    input.user_role == "admin"
}

# Emergency override for critical systems
contextual_authorization if {
    input.context.emergency_override == true
    input.context.emergency_justification != ""
    input.user_role in ["ciso", "executive", "admin"]
}

# Required approvers for specific approval levels
required_approvers_for_level[level] := roles if {
    level := input.current_level
    roles := required_approvers[level]
} else := ["admin"]  # Default fallback

# Policy metadata
metadata := {
    "version": "1.0.0",
    "description": "HITL Approval Authorization Policy",
    "constitutional_hash": constitutional_hash,
    "supported_actions": ["approve", "reject", "escalate", "delegate"],
    "role_hierarchy": role_hierarchy,
    "max_approval_levels": 5
}
