package acgs.multitenant

import future.keywords.if

default allow = false

# Same tenant access - always allowed
allow if {
    input.agent_tenant_id == input.resource_tenant_id
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Cross-tenant access with explicit permission
allow if {
    input.context.cross_tenant_permission == true
    input.context.source_tenant_id in allowed_source_tenants
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Global admin can access all tenants
allow if {
    input.context.role == "global_admin"
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Allowed source tenants for cross-tenant access
allowed_source_tenants := [
    "tenant_admin",
    "tenant_monitoring",
    "tenant_audit"
]
