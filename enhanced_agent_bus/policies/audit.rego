package acgs.audit

import future.keywords.if
import future.keywords.in

# Determine if action should be audited
should_audit := true if {
    input.action in audited_actions
}

should_audit := true if {
    input.resource in sensitive_resources
}

should_audit := true if {
    input.context.role == "admin"
}

# Actions that require audit logging
audited_actions := [
    "write",
    "delete",
    "execute",
    "admin"
]

# Sensitive resources requiring audit
sensitive_resources := [
    "constitutional_settings",
    "user_data",
    "encryption_keys",
    "admin_controls"
]

# Audit level determination
audit_level := "critical" if {
    input.action in ["delete", "admin"]
    input.resource in sensitive_resources
}

audit_level := "high" if {
    input.action == "write"
    input.resource in sensitive_resources
}

audit_level := "medium" if {
    input.action in audited_actions
}

audit_level := "low" if {
    not audit_level
}
