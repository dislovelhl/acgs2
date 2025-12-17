# ACGS-2 OPA Policies
# Constitutional Hash: cdd01ef066bc6cf2
#
# Sample policies for the Enhanced Agent Bus system.
# Load these into OPA server using the OPAClient.load_policy() method.

package acgs

import future.keywords.if
import future.keywords.in

# Constitutional hash constant
constitutional_hash := "cdd01ef066bc6cf2"

# ============================================================================
# Constitutional Validation
# ============================================================================

package acgs.constitutional

import future.keywords.if

default validate = false

# Validate constitutional hash presence and correctness
validate if {
    input.message.constitutional_hash == "cdd01ef066bc6cf2"
}

# Validate message structure
validate if {
    input.message.message_id
    input.message.from_agent
    input.message.to_agent
    input.message.constitutional_hash == "cdd01ef066bc6cf2"
}

# Return detailed validation result
allow := {
    "allow": validate,
    "reason": reason,
    "metadata": {
        "policy": "constitutional_validation",
        "version": "1.0.0"
    }
}

reason := "Valid constitutional hash and message structure" if validate
reason := sprintf("Invalid constitutional hash: %v", [input.message.constitutional_hash]) if {
    not validate
    input.message.constitutional_hash != "cdd01ef066bc6cf2"
}
reason := "Missing required message fields" if {
    not validate
    not input.message.message_id
}

# ============================================================================
# RBAC (Role-Based Access Control)
# ============================================================================

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

# ============================================================================
# Multi-Tenant Access Control
# ============================================================================

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

# ============================================================================
# Resource Access Control
# ============================================================================

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

# ============================================================================
# Rate Limiting
# ============================================================================

package acgs.ratelimit

import future.keywords.if

default allow = true

# Check if request exceeds rate limit
allow if {
    input.request_count < max_requests_per_window[input.context.role]
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Rate limits by role (requests per minute)
max_requests_per_window := {
    "admin": 1000,
    "operator": 500,
    "analyst": 200,
    "developer": 100,
    "service": 2000,
    "default": 50
}

# Reason for rate limit
deny_reason := sprintf("Rate limit exceeded: %v requests > %v allowed for role '%v'",
    [input.request_count, max_requests_per_window[input.context.role], input.context.role]) if {
    not allow
}

# ============================================================================
# Time-Based Access Control
# ============================================================================

package acgs.timebased

import future.keywords.if

default allow = true

# Check business hours for non-admin roles
allow if {
    input.context.role == "admin"
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

allow if {
    is_business_hours
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

allow if {
    input.context.after_hours_permission == true
    input.constitutional_hash == "cdd01ef066bc6cf2"
}

# Business hours check (9 AM - 6 PM, Mon-Fri)
is_business_hours if {
    hour := time.clock([time.now_ns()])[0]
    day := time.weekday([time.now_ns()])
    hour >= 9
    hour < 18
    day >= 1  # Monday
    day <= 5  # Friday
}

# ============================================================================
# Message Routing Policies
# ============================================================================

package acgs.routing

import future.keywords.if
import future.keywords.in

# Default routing based on message type
destination := {
    "agent": default_agent_for_type[input.message.message_type],
    "priority": input.message.priority
} if {
    input.message.constitutional_hash == "cdd01ef066bc6cf2"
}

# High priority messages go to high-priority queue
destination := {
    "agent": "high_priority_handler",
    "priority": "high",
    "queue": "priority"
} if {
    input.message.priority in ["high", "critical"]
    input.message.constitutional_hash == "cdd01ef066bc6cf2"
}

# Governance requests go to deliberation layer
destination := {
    "agent": "deliberation_layer",
    "priority": "high",
    "queue": "governance"
} if {
    input.message.message_type == "governance_request"
    input.message.constitutional_hash == "cdd01ef066bc6cf2"
}

# Default agent mapping by message type
default_agent_for_type := {
    "command": "command_processor",
    "query": "query_handler",
    "event": "event_dispatcher",
    "notification": "notification_service"
}

# ============================================================================
# Audit Logging Policies
# ============================================================================

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

# ============================================================================
# Compliance Policies
# ============================================================================

package acgs.compliance

import future.keywords.if

default compliant = true

# Check all compliance requirements
compliant if {
    has_constitutional_hash
    has_required_fields
    within_size_limits
    no_prohibited_content
}

has_constitutional_hash if {
    input.message.constitutional_hash == "cdd01ef066bc6cf2"
}

has_required_fields if {
    input.message.message_id
    input.message.from_agent
    input.message.to_agent
    input.message.message_type
}

within_size_limits if {
    count(input.message.content) < 10000  # Max 10KB message size
}

no_prohibited_content if {
    not contains_prohibited_terms
}

contains_prohibited_terms if {
    some term in prohibited_terms
    contains(lower(json.marshal(input.message.content)), term)
}

prohibited_terms := [
    "malicious",
    "exploit",
    "backdoor"
]

# Compliance violations
violations := [msg |
    not has_constitutional_hash
    msg := "Missing or invalid constitutional hash"
]

violations := [msg |
    not has_required_fields
    msg := "Missing required message fields"
]

violations := [msg |
    not within_size_limits
    msg := "Message size exceeds limits"
]

violations := [msg |
    contains_prohibited_terms
    msg := "Message contains prohibited content"
]
