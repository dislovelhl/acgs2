package hitl.routing

import future.keywords.if
import future.keywords.in

# Default decision for approval chain routing
default allow := false

# Constitutional hash for HITL approvals
constitutional_hash := "cdd01ef066bc6cf2"

# Chain ID mappings for different scenarios
chain_ids := {
    "standard": "chain_standard_approval",
    "high_risk": "chain_high_risk_approval",
    "critical": "chain_critical_approval",
    "financial": "chain_financial_approval",
    "security": "chain_security_approval",
    "compliance": "chain_compliance_approval"
}

# Priority to chain mapping
priority_chains := {
    "low": "chain_standard_approval",
    "medium": "chain_standard_approval",
    "high": "chain_high_risk_approval",
    "critical": "chain_critical_approval"
}

# Decision type to chain mapping
decision_type_chains := {
    "financial": "chain_financial_approval",
    "security": "chain_security_approval",
    "compliance": "chain_compliance_approval",
    "infrastructure": "chain_high_risk_approval",
    "data": "chain_high_risk_approval",
    "policy": "chain_compliance_approval"
}

# Allow routing decision with chain selection
allow if {
    # Verify constitutional hash
    input.constitutional_hash == constitutional_hash

    # Basic validation
    valid_decision_type
    valid_user_role
    valid_impact_level
}

# Determine appropriate approval chain
chain_id := chain_ids[selected_chain] if {
    selected_chain := select_chain
} else := "chain_standard_approval"  # Default fallback

# Chain selection logic
select_chain := decision_type_chains[input.decision_type] if {
    input.decision_type in decision_type_chains
} else := priority_chains[input.impact_level] if {
    input.impact_level in priority_chains
} else := "standard"

# Validation rules
valid_decision_type if {
    input.decision_type != ""
    count(input.decision_type) > 0
}

valid_user_role if {
    input.user_role in ["engineer", "analyst", "manager", "lead", "director", "vp", "executive", "ciso", "admin", "unknown"]
}

valid_impact_level if {
    input.impact_level in ["low", "medium", "high", "critical"]
}

# Additional context-based routing for complex scenarios
allow if {
    input.constitutional_hash == constitutional_hash
    complex_scenario_chain_selection
}

complex_scenario_chain_selection if {
    # High-impact financial decisions require executive approval
    input.decision_type == "financial"
    input.impact_level in ["high", "critical"]
    input.user_role in ["engineer", "analyst", "manager"]
    chain_id == "chain_critical_approval"
}

complex_scenario_chain_selection if {
    # Security incidents require immediate security team approval
    input.decision_type == "security"
    input.context.incident_type == "breach"
    chain_id == "chain_security_approval"
}

complex_scenario_chain_selection if {
    # Multi-tenant operations require compliance review
    input.tenant_id != "default"
    input.impact_level in ["high", "critical"]
    chain_id == "chain_compliance_approval"
}

# Policy metadata
metadata := {
    "version": "1.0.0",
    "description": "HITL Approval Chain Routing Policy",
    "constitutional_hash": constitutional_hash,
    "supported_decision_types": ["financial", "security", "compliance", "infrastructure", "data", "policy"],
    "supported_impact_levels": ["low", "medium", "high", "critical"],
    "supported_user_roles": ["engineer", "analyst", "manager", "lead", "director", "vp", "executive", "ciso", "admin"]
}
