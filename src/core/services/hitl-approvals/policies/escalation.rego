package hitl.escalation

import future.keywords.if
import future.keywords.in

# Default decision for escalation
default allow := false

# Constitutional hash for HITL approvals
constitutional_hash := "cdd01ef066bc6cf2"

# Escalation rules based on priority and time thresholds
escalation_rules := {
    "low": {
        "max_time_minutes": 240,  # 4 hours
        "max_escalations": 1,
        "next_level": 2
    },
    "medium": {
        "max_time_minutes": 120,  # 2 hours
        "max_escalations": 2,
        "next_level": 3
    },
    "high": {
        "max_time_minutes": 60,   # 1 hour
        "max_escalations": 3,
        "next_level": 4
    },
    "critical": {
        "max_time_minutes": 30,   # 30 minutes
        "max_escalations": 4,
        "next_level": 5
    }
}

# Emergency escalation rules
emergency_rules := {
    "security_breach": {
        "immediate_escalation": true,
        "target_level": 5,
        "notify_ciso": true
    },
    "system_failure": {
        "immediate_escalation": true,
        "target_level": 4,
        "notify_ops": true
    },
    "data_breach": {
        "immediate_escalation": true,
        "target_level": 5,
        "notify_legal": true
    }
}

# Allow escalation decision
allow if {
    # Verify constitutional hash
    input.constitutional_hash == constitutional_hash

    # Basic validation
    valid_request_id
    valid_current_level
    valid_priority

    # Check escalation rules
    can_escalate_based_on_rules
}

# Determine next level for escalation
next_level := escalation_rules[input.priority].next_level if {
    input.priority in escalation_rules
    can_escalate_based_on_rules
} else := input.current_level + 1  # Default increment

# Emergency escalation override
allow if {
    input.constitutional_hash == constitutional_hash
    emergency_escalation_allowed
    next_level := emergency_rules[input.context.emergency_type].target_level
}

# Escalation validation rules
can_escalate_based_on_rules if {
    rule := escalation_rules[input.priority]
    input.escalation_count < rule.max_escalations
}

can_escalate_based_on_rules if {
    # Time-based escalation
    rule := escalation_rules[input.priority]
    input.time_elapsed_minutes > rule.max_time_minutes
}

# Emergency escalation for critical scenarios
emergency_escalation_allowed if {
    input.context.emergency_type in emergency_rules
    emergency_rules[input.context.emergency_type].immediate_escalation == true
}

# Validation rules
valid_request_id if {
    input.request_id != ""
    count(input.request_id) > 0
}

valid_current_level if {
    is_number(input.current_level)
    input.current_level >= 1
    input.current_level <= 5
}

valid_priority if {
    input.priority in ["low", "medium", "high", "critical"]
}

# Escalation metadata for notifications
escalation_metadata := {
    "next_level": next_level,
    "escalation_reason": get_escalation_reason,
    "notify_roles": get_notify_roles,
    "urgency": get_urgency_level
}

get_escalation_reason := "timeout" if {
    rule := escalation_rules[input.priority]
    input.time_elapsed_minutes > rule.max_time_minutes
} else := "max_escalations_reached" if {
    rule := escalation_rules[input.priority]
    input.escalation_count >= rule.max_escalations
} else := "emergency" if {
    emergency_escalation_allowed
} else := "manual"

get_notify_roles := ["manager", "lead"] if {
    next_level == 2
} else := ["director", "vp"] if {
    next_level == 3
} else := ["executive", "ciso"] if {
    next_level == 4
} else := ["ciso", "admin"] if {
    next_level == 5
} else := ["admin"]

get_urgency_level := "high" if {
    input.priority in ["high", "critical"]
} else := "medium" if {
    input.priority == "medium"
} else := "low"

# Policy metadata
metadata := {
    "version": "1.0.0",
    "description": "HITL Approval Escalation Policy",
    "constitutional_hash": constitutional_hash,
    "max_approval_levels": 5,
    "supported_priorities": ["low", "medium", "high", "critical"],
    "emergency_types": ["security_breach", "system_failure", "data_breach"]
}
