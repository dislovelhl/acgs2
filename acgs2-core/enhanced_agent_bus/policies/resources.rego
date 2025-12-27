package acgs.resources

import future.keywords.if
import future.keywords.in

default allow = false

# Public resources - anyone can read
allow if {
    input.resource in public_resources
    input.action == "read"
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Protected resources - require specific clearance
allow if {
    input.resource in protected_resources
    input.context.clearance_level >= required_clearance[input.resource]
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Sensitive resources - admin only
allow if {
    input.resource in sensitive_resources
    input.context.role == "admin"
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Public resources
public_resources := [
    "public_documents",
    "public_data",
    "system_status"
]

# Protected resources with clearance requirements
protected_resources := [
    "financial_data",
    "user_pii",
    "internal_documents"
]

required_clearance := {
    "financial_data": 3,
    "user_pii": 2,
    "internal_documents": 1
}

# Sensitive resources
sensitive_resources := [
    "constitutional_settings",
    "encryption_keys",
    "admin_controls"
]
