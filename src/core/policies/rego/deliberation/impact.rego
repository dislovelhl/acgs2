# ACGS-2 Deliberation Impact Policy
# Constitutional Hash: cdd01ef066bc6cf2
#
# This policy defines routing rules for the deliberation layer,
# determining when messages require human review vs. fast-lane processing.

package acgs.deliberation

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# Constitutional Hash
constitutional_hash := "cdd01ef066bc6cf2"

# Default impact threshold for deliberation
default impact_threshold := 0.8

# Default routing is to fast lane (optimistic)
default route_to_deliberation := false

# Route to deliberation if any high-risk condition is met
route_to_deliberation if {
    high_impact_score
}

route_to_deliberation if {
    high_risk_action
}

route_to_deliberation if {
    sensitive_content_detected
}

route_to_deliberation if {
    constitutional_risk_detected
}

route_to_deliberation if {
    temporal_risk
}

route_to_deliberation if {
    resource_risk
}

route_to_deliberation if {
    forced_deliberation
}

# Check if impact score exceeds threshold
high_impact_score if {
    input.message.impact_score >= impact_threshold
}

# High-risk actions that always require deliberation
high_risk_actions := {
    "constitutional_update",
    "policy_change",
    "agent_termination",
    "security_override",
    "audit_log_access",
    "system_configuration_change",
    "credential_rotation",
    "tenant_migration"
}

high_risk_action if {
    # Extract action from message content
    action := input.message.content.action
    action in high_risk_actions
}

# High-risk message types
high_risk_message_types := {
    "governance_request",
    "constitutional_validation"
}

high_risk_action if {
    input.message.message_type in high_risk_message_types
}

# Detect sensitive content patterns
sensitive_content_detected if {
    # Check for financial operations
    financial_operation
}

sensitive_content_detected if {
    # Check for PII handling
    pii_detected
}

sensitive_content_detected if {
    # Check for security operations
    security_operation
}

# Financial operation detection
financial_operation if {
    content := input.message.content
    financial_keywords := {"payment", "transaction", "transfer", "withdraw", "deposit", "refund"}

    # Check if any keyword appears in content
    some keyword in financial_keywords
    contains_keyword(content, keyword)
}

# PII detection patterns
pii_detected if {
    content := input.message.content
    pii_fields := {"ssn", "credit_card", "passport", "driver_license", "tax_id"}

    # Check if any PII field is present
    some field in pii_fields
    content[field]
}

# Security operation detection
security_operation if {
    content := input.message.content
    security_keywords := {"authenticate", "authorize", "encrypt", "decrypt", "key_generation", "certificate"}

    # Check for security-related operations
    some keyword in security_keywords
    contains_keyword(content, keyword)
}

# Helper function to check if content contains keyword
contains_keyword(content, keyword) if {
    # Convert content to string representation
    content_str := sprintf("%v", [content])
    contains(lower(content_str), keyword)
}

# Constitutional risk detection
constitutional_risk_detected if {
    # Message attempts to modify constitutional hash
    input.message.content.constitutional_hash
    input.message.content.constitutional_hash != constitutional_hash
}

constitutional_risk_detected if {
    # Message has invalid constitutional hash
    input.message.constitutional_hash != constitutional_hash
}

# Multi-tenant risk detection
multi_tenant_risk if {
    # Cross-tenant operation attempt
    input.context.multi_tenant_enabled
    input.message.tenant_id != input.context.tenant_id
}

multi_tenant_risk if {
    # Tenant escalation attempt
    input.message.content.action == "tenant_escalation"
}

# Forced deliberation (manual override)
forced_deliberation if {
    input.message.content.force_deliberation == true
}

# Temporal Risk Detection
temporal_risk if {
    # Check if action is performed outside business hours (example: 00:00 - 06:00 UTC)
    # Rego time functions can parse RFC3339
    now_ns := time.now_ns()
    hour := time.date(now_ns)[3] # [Y, M, D, h, m, s, ns, tz]
    hour < 6 # High risk late night operations
}

temporal_risk if {
    # High frequency of critical actions from same agent
    input.context.action_frequency_score > 0.8
}

# Resource Risk Detection
resource_risk if {
    # High memory or CPU request for a single task
    input.message.content.resource_request.memory_mb > 4096
}

resource_risk if {
    input.message.content.resource_request.cpu_cores > 4
}

forced_deliberation if {
    input.context.force_deliberation == true
}

# Calculate effective impact score
effective_impact_score := score if {
    # Use provided impact score if available
    input.message.impact_score
    score := input.message.impact_score
} else := score if {
    # Calculate based on risk factors
    score := calculated_impact_score
}

# Calculate impact score based on risk factors
calculated_impact_score := score if {
    risk_factors := count_risk_factors

    # Base score of 0.5, increased by 0.1 per risk factor
    base_score := 0.5
    risk_increment := 0.1

    # Cap at 1.0
    raw_score := base_score + (risk_factors * risk_increment)
    score := min([raw_score, 1.0])
}

# Count active risk factors
count_risk_factors := num if {
    factors := [
        high_risk_action,
        sensitive_content_detected,
        constitutional_risk_detected,
        multi_tenant_risk,
        temporal_risk,
        resource_risk,
        forced_deliberation
    ]

    # Count true values
    true_factors := [f | f := factors[_]; f == true]
    num := count(true_factors)
}

# Routing decision
routing_decision := {
    "lane": lane,
    "impact_score": effective_impact_score,
    "requires_human_review": requires_human_review,
    "requires_multi_agent_vote": requires_multi_agent_vote,
    "timeout_seconds": timeout_seconds,
    "risk_factors": active_risk_factors,
    "constitutional_hash": constitutional_hash
}

# Determine routing lane
lane := "deliberation" if {
    route_to_deliberation
} else := "fast"

# Determine if human review is required
requires_human_review if {
    route_to_deliberation
    effective_impact_score >= 0.9
}

requires_human_review if {
    constitutional_risk_detected
}

requires_human_review if {
    forced_deliberation
}

# Determine if multi-agent voting is required
requires_multi_agent_vote if {
    route_to_deliberation
    effective_impact_score >= 0.95
}

requires_multi_agent_vote if {
    high_risk_action
    input.message.content.action in {"constitutional_update", "policy_change"}
}

# Determine deliberation timeout
timeout_seconds := 300 if {
    # Standard timeout: 5 minutes
    route_to_deliberation
    effective_impact_score < 0.95
} else := 600 if {
    # Extended timeout: 10 minutes for critical decisions
    route_to_deliberation
    effective_impact_score >= 0.95
} else := 30 if {
    # Fast lane: 30 seconds max
    not route_to_deliberation
}

# Active risk factors for audit logging
active_risk_factors contains factor if {
    high_impact_score
    factor := "high_impact_score"
}

active_risk_factors contains factor if {
    high_risk_action
    factor := "high_risk_action"
}

active_risk_factors contains factor if {
    sensitive_content_detected
    factor := "sensitive_content"
}

active_risk_factors contains factor if {
    constitutional_risk_detected
    factor := "constitutional_risk"
}

active_risk_factors contains factor if {
    multi_tenant_risk
    factor := "multi_tenant_risk"
}

active_risk_factors contains factor if {
    temporal_risk
    factor := "temporal_risk"
}

active_risk_factors contains factor if {
    resource_risk
    factor := "resource_risk"
}

active_risk_factors contains factor if {
    forced_deliberation
    factor := "forced_deliberation"
}

# Fast lane optimization - pre-approved patterns
fast_lane_approved if {
    not route_to_deliberation
    low_risk_pattern
}

# Low-risk patterns that can skip additional checks
low_risk_pattern if {
    # Heartbeat messages
    input.message.message_type == "heartbeat"
}

low_risk_pattern if {
    # Notifications with low impact
    input.message.message_type == "notification"
    effective_impact_score < 0.3
}

low_risk_pattern if {
    # Query responses
    input.message.message_type == "response"
    effective_impact_score < 0.5
}

# Deliberation queue priority
deliberation_priority := priority if {
    effective_impact_score >= 0.95
    priority := "critical"
} else := priority if {
    effective_impact_score >= 0.85
    priority := "high"
} else := priority if {
    priority := "normal"
}

# Deliberation metadata for audit trail
deliberation_metadata := {
    "routing_decision": routing_decision,
    "effective_impact_score": effective_impact_score,
    "deliberation_priority": deliberation_priority,
    "fast_lane_approved": fast_lane_approved,
    "active_risk_factors": active_risk_factors,
    "timestamp": time.now_ns(),
    "message_id": input.message.message_id,
    "constitutional_hash": constitutional_hash
}
