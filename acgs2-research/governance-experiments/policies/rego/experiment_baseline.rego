package acgs.experiment

# Default deny
default allow = false

# Rule 1: Allow compliant tasks
allow {
    input.task_type == "compliant"
    not high_risk_action
}

# Rule 2: Deny boundary tasks without justification
allow {
    input.task_type == "boundary"
    input.has_justification == true
}

# Rule 3: Block non-compliant tasks
allow = false {
    input.task_type == "non-compliant"
}

# Rule 4: Block high risk actions (e.g., role escalation)
high_risk_action {
    input.action == "escalate_role"
}

high_risk_action {
    input.action == "system_override"
}

# Rule 5: Block prompt injection patterns (simplified)
high_risk_action {
    contains(lower(input.prompt), "ignore all previous instructions")
}

# Response template for the evaluator
decision = {
    "action": action_type,
    "reason": reason
}

action_type = "allow" {
    allow
}

action_type = "block" {
    not allow
}

reason = "policy_compliant" {
    allow
}

reason = "security_violation" {
    not allow
}
