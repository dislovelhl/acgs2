# ACGS-2 Agent Bus Authorization Policy
# Constitutional Hash: cdd01ef066bc6cf2
#
# This policy enforces role-based access control (RBAC) and
# action-based authorization for the Enhanced Agent Bus.

package acgs.agent_bus.authz

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# Default deny - All actions must be explicitly authorized
default allow := false
default deny := true

# Allow action if it passes all authorization checks
allow if {
    valid_agent_role
    authorized_action
    authorized_target
    rate_limit_check
    security_context_valid
    zk_attest_valid
    alignment_check_pass
}

# Validate agent role exists and is active
valid_agent_role if {
    # Agent must have a role
    input.agent.role

    # Role must be defined in policy data
    data.agent_roles[input.agent.role]

    # Agent must be active
    input.agent.status == "active"
}

# Check if action is authorized for the agent's role
authorized_action if {
    # Get allowed actions for this role
    allowed_actions := data.agent_roles[input.agent.role].allowed_actions

    # Check if requested action is allowed
    input.action in allowed_actions
}

# System admins can perform any action
authorized_action if {
    input.agent.role == "system_admin"
}

# Check if agent can access the target resource
authorized_target if {
    # Get target agent/resource
    target := input.target

    # Allow if agent is targeting itself
    target.agent_id == input.agent.agent_id
}

# Allow if agent has permission to access target
authorized_target if {
    # Get target access rules for role
    access_rules := data.agent_roles[input.agent.role].target_access

    # Check if access pattern matches
    target_matches_rule
}

# Target matching logic
target_matches_rule if {
    access_rules := data.agent_roles[input.agent.role].target_access

    # Check if "all" access is granted
    "all" in access_rules
}

target_matches_rule if {
    access_rules := data.agent_roles[input.agent.role].target_access

    # Check if specific agent type is allowed
    input.target.agent_type in access_rules
}

# System admins can access any target
authorized_target if {
    input.agent.role == "system_admin"
}

# Rate limit check - prevent abuse
rate_limit_check if {
    # Get rate limit for role
    rate_limit := data.agent_roles[input.agent.role].rate_limit_per_minute

    # Check current rate from context
    current_rate := input.context.current_rate

    # Ensure under limit
    current_rate < rate_limit
}

# No rate limit for system operations
rate_limit_check if {
    input.agent.role == "system_admin"
}

# No rate limit if not tracking
rate_limit_check if {
    not input.context.current_rate
}

# Validate security context
security_context_valid if {
    # Security context must exist
    is_object(input.security_context)

    # Tenant isolation check
    tenant_isolation_valid

    # Authentication token valid
    auth_token_valid
}

# Tenant isolation validation
tenant_isolation_valid if {
    # If multi-tenant mode is enabled
    input.context.multi_tenant_enabled

    # Agent and target must be in same tenant
    input.agent.tenant_id == input.target.tenant_id
}

# Allow if not in multi-tenant mode
tenant_isolation_valid if {
    not input.context.multi_tenant_enabled
}

# System admins can cross tenants
tenant_isolation_valid if {
    input.agent.role == "system_admin"
}

# Authentication token validation
auth_token_valid if {
    # Token must be present
    input.security_context.auth_token

    # Token must not be expired
    not token_expired
}

token_expired if {
    token_expiry := input.security_context.token_expiry
    now := time.now_ns()
    expiry := time.parse_rfc3339_ns(token_expiry)
    now > expiry
}

# System agents don't need tokens
auth_token_valid if {
    input.agent.role == "system_admin"
}

# Message type authorization
authorized_message_type if {
    # Get allowed message types for role
    allowed_types := data.agent_roles[input.agent.role].allowed_message_types

    # Check if message type is allowed
    input.message_type in allowed_types
}

# System admins can send any message type
authorized_message_type if {
    input.agent.role == "system_admin"
}

# Capability-based authorization
has_capability(capability) if {
    capabilities := data.agent_roles[input.agent.role].capabilities
    capability in capabilities
}

# Authorization for specific actions

# Register agent action
allow_register_agent if {
    input.action == "register_agent"
    has_capability("agent_management")
}

# Send message action
allow_send_message if {
    input.action == "send_message"
    has_capability("messaging")
    authorized_message_type
}

# Broadcast message action
allow_broadcast_message if {
    input.action == "broadcast_message"
    has_capability("broadcast")
}

# Query agents action
allow_query_agents if {
    input.action == "query_agents"
    has_capability("discovery")
}

# Governance request action
allow_governance_request if {
    input.action == "governance_request"
    has_capability("governance")
}

# Deliberation submission action
allow_submit_deliberation if {
    input.action == "submit_deliberation"
    has_capability("deliberation")
}

# Metrics access action
allow_metrics_access if {
    input.action == "get_metrics"
    has_capability("monitoring")
}

# Audit log access action
allow_audit_access if {
    input.action == "audit_access"
    has_capability("audit")
}

# Constitutional update action - highly restricted
allow_constitutional_update if {
    input.action == "constitutional_update"
    input.agent.role == "system_admin"
    has_capability("constitutional_admin")
}

# Authorization violations for audit logging
violations contains msg if {
    not valid_agent_role
    msg := sprintf("Invalid or inactive agent role: %s (status: %s)",
        [input.agent.role, input.agent.status])
}

violations contains msg if {
    not authorized_action
    input.agent.role != "system_admin"
    msg := sprintf("Agent role '%s' not authorized for action '%s'",
        [input.agent.role, input.action])
}

violations contains msg if {
    not authorized_target
    msg := sprintf("Agent '%s' not authorized to access target '%s'",
        [input.agent.agent_id, input.target.agent_id])
}

violations contains msg if {
    not rate_limit_check
    input.agent.role != "system_admin"
    rate_limit := data.agent_roles[input.agent.role].rate_limit_per_minute
    msg := sprintf("Rate limit exceeded: %d requests/minute (limit: %d)",
        [input.context.current_rate, rate_limit])
}

violations contains msg if {
    not tenant_isolation_valid
    msg := sprintf("Tenant isolation violation: agent tenant '%s' cannot access target tenant '%s'",
        [input.agent.tenant_id, input.target.tenant_id])
}

violations contains msg if {
    token_expired
    msg := sprintf("Authentication token expired at %s",
        [input.security_context.token_expiry])
}

# ZK Attestation check (MACI)
zk_attest_valid if {
    input.security_context.zk_proof
    # Logic to verify ZK proof would go here (simulated for now)
    true
}

# Alignment Score Check
alignment_check_pass if {
    input.context.alignment_score
    input.context.alignment_score > 0.98
}

# Authorization metadata for audit trail
authorization_metadata := {
    "authorized": allow,
    "agent_id": input.agent.agent_id,
    "agent_role": input.agent.role,
    "action": input.action,
    "target": input.target.agent_id,
    "violations": violations,
    "timestamp": time.now_ns(),
    "constitutional_hash": "cdd01ef066bc6cf2",
    "alignment_score": input.context.alignment_score,
    "zk_verified": zk_attest_valid
}
