# ACGS-2 Constitutional Validation Policy
# Constitutional Hash: cdd01ef066bc6cf2
#
# This policy enforces constitutional compliance for all messages
# in the Enhanced Agent Bus system.

package acgs.constitutional

import future.keywords.if
import future.keywords.in

# Constitutional Hash - Required for all operations
constitutional_hash := "cdd01ef066bc6cf2"

# Default deny - All messages must explicitly pass validation
default allow := false
default deny := true

# Allow message if it passes all constitutional checks
allow if {
    valid_constitutional_hash
    valid_message_structure
    valid_agent_permissions
    valid_tenant_isolation
    valid_priority_escalation
    valid_payload_size
    valid_rate_limit
    valid_capabilities
    pii_redacted
}

# Validate constitutional hash matches required value
valid_constitutional_hash if {
    input.message.constitutional_hash == constitutional_hash
}

# Validate message has required structure
valid_message_structure if {
    # Message must have required fields
    input.message.message_id
    input.message.conversation_id
    input.message.from_agent
    input.message.message_type

    # Message type must be valid
    input.message.message_type in valid_message_types

    # Content must be present
    is_object(input.message.content)

    # Timestamps must be valid
    valid_timestamps
}

# Valid message types from the system
valid_message_types := {
    "command",
    "query",
    "response",
    "event",
    "notification",
    "heartbeat",
    "governance_request",
    "governance_response",
    "constitutional_validation",
    "task_request",
    "task_response"
}

# Validate timestamps are properly formatted
valid_timestamps if {
    input.message.created_at
    input.message.updated_at

    # Ensure created_at is before or equal to updated_at
    time.parse_rfc3339_ns(input.message.created_at) <= time.parse_rfc3339_ns(input.message.updated_at)
}

# Validate agent has permission to send this message type
valid_agent_permissions if {
    # Get agent role from input context
    agent_role := input.context.agent_role

    # Get allowed message types for this role
    allowed_types := data.agent_permissions[agent_role].allowed_message_types

    # Check if message type is allowed for this agent role
    input.message.message_type in allowed_types
}

# Alternative permission check when agent is system admin
valid_agent_permissions if {
    input.context.agent_role == "system_admin"
}

# Validate tenant isolation
valid_tenant_isolation if {
    # If message has tenant_id, validate it matches agent's tenant
    input.message.tenant_id != ""
    input.message.tenant_id == input.context.tenant_id
}

# Allow messages without tenant_id (single-tenant mode)
valid_tenant_isolation if {
    input.message.tenant_id == ""
    not input.context.multi_tenant_enabled
}

# Validate priority escalation rules
valid_priority_escalation if {
    # Get message priority (0=CRITICAL, 1=HIGH, 2=NORMAL, 3=LOW)
    priority := to_number(input.message.priority)

    # Check if agent can send at this priority level
    max_priority := data.agent_permissions[input.context.agent_role].max_priority

    # Lower number = higher priority, so priority must be >= max_priority
    priority >= max_priority
}

# Allow critical priority for system_admin regardless of rules
valid_priority_escalation if {
    input.context.agent_role == "system_admin"
}

# Validate payload size (Max 1MB by default)
valid_payload_size if {
    # Estimate size using strings.count or similar if possible in Rego
    # Alternatively, expect input.context.payload_size_kb
    size_kb := input.context.payload_size_kb
    size_kb <= 1024
}

# Allow larger payloads for system_admin
valid_payload_size if {
    input.context.agent_role == "system_admin"
}

# Validate rate limit
valid_rate_limit if {
    not input.context.rate_limit_exceeded
}

# Allow system_admin to bypass rate limits
valid_rate_limit if {
    input.context.agent_role == "system_admin"
}

# Validate agent capabilities for specific tasks
valid_capabilities if {
    required_caps := input.message.content.required_capabilities
    count(required_caps) == 0
}

valid_capabilities if {
    required_caps := input.message.content.required_capabilities
    count(required_caps) > 0
    agent_caps := input.context.agent_capabilities
    # Check if all required caps are in agent caps
    count({cap | cap := required_caps[_]; cap in agent_caps}) == count(required_caps)
}

# Validation errors - provide detailed feedback
violations[msg] {
    not valid_constitutional_hash
    msg := sprintf("Constitutional hash mismatch: expected %s, got %s",
        [constitutional_hash, input.message.constitutional_hash])
}

violations[msg] {
    not input.message.message_id
    msg := "Missing required field: message_id"
}

violations[msg] {
    not input.message.from_agent
    msg := "Missing required field: from_agent"
}

violations[msg] {
    not input.message.message_type in valid_message_types
    msg := sprintf("Invalid message_type: %s. Must be one of: %v",
        [input.message.message_type, valid_message_types])
}

violations[msg] {
    not valid_agent_permissions
    input.context.agent_role != "system_admin"
    msg := sprintf("Agent role '%s' not permitted to send message type '%s'",
        [input.context.agent_role, input.message.message_type])
}

violations[msg] {
    input.message.tenant_id != ""
    input.message.tenant_id != input.context.tenant_id
    msg := sprintf("Tenant isolation violation: message tenant '%s' does not match agent tenant '%s'",
        [input.message.tenant_id, input.context.tenant_id])
}

violations[msg] {
    not valid_priority_escalation
    input.context.agent_role != "system_admin"
    priority := to_number(input.message.priority)
    max_priority := data.agent_permissions[input.context.agent_role].max_priority
    msg := sprintf("Priority escalation violation: agent role '%s' cannot send priority %d (max: %d)",
        [input.context.agent_role, priority, max_priority])
}

violations[msg] {
    not valid_payload_size
    msg := sprintf("Payload size limit exceeded: %d KB (max 1024 KB)", [input.context.payload_size_kb])
}

violations[msg] {
    not valid_rate_limit
    msg := "Rate limit exceeded for agent"
}

violations[msg] {
    not valid_capabilities
    msg := "Agent lacks required capabilities for this operation"
}

# Message expiration check
message_expired if {
    input.message.expires_at
    now := time.now_ns()
    expiry := time.parse_rfc3339_ns(input.message.expires_at)
    now > expiry
}

violations[msg] {
    message_expired
    msg := sprintf("Message has expired at %s", [input.message.expires_at])
}

# Constitutional validation status
constitutional_validated if {
    allow
    not message_expired
}

# PII Safeguards - ensure PII is redacted if not authorized
pii_redacted if {
    not input.message.content.contains_pii
}

pii_redacted if {
    input.message.content.contains_pii
    input.context.agent_role == "system_admin"
}

# Compliance metadata for audit trail
compliance_metadata := {
    "constitutional_hash": constitutional_hash,
    "validated": constitutional_validated,
    "validation_timestamp": time.now_ns(),
    "violations": violations,
    "message_id": input.message.message_id,
    "agent_role": input.context.agent_role,
    "pii_safe": pii_redacted
}
