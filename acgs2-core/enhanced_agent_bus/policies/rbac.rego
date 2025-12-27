package acgs.rbac

import future.keywords.if
import future.keywords.in

default allow = false

# Admin role - full access
allow if {
    input.context.role == "admin"
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Analyst role - read and query only
allow if {
    input.context.role == "analyst"
    input.action in ["read", "query"]
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Operator role - read and execute
allow if {
    input.context.role == "operator"
    input.action in ["read", "execute", "query"]
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Developer role - read, write, execute (non-production only)
allow if {
    input.context.role == "developer"
    input.context.environment != "production"
    input.action in ["read", "write", "execute", "query"]
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Service accounts - specific permissions
allow if {
    input.context.role == "service"
    input.agent_id in service_accounts
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Allowed service accounts
service_accounts := [
    "monitoring_agent",
    "backup_agent",
    "audit_agent"
]

# Reason for denial
deny_reason := "Invalid constitutional hash" if {
    input.constitutional_hash != "cdd01ef066bc6cf2"
}

deny_reason := sprintf("Role '%v' not authorized for action '%v'", [input.context.role, input.action]) if {
    not allow
    input.constitutional_hash == "cdd01ef066bc6cf2"
}
