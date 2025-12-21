package acgs.templates.fintech

import future.keywords.if
import future.keywords.in

# Fintech Policy - PCI-DSS Compliance Template
# Focus: Transaction safety, cardholder data protection, and high-value transfer oversight.

default allow = false

# Allow if it's a low-value transaction and not a critical error
allow if {
    input.message_type != "critical"
    input.payload.amount < 1000
    not high_risk_action
}

# Deny if requesting cardholder data without specific authorization
deny_card_data if {
    input.tools[_].name == "read_card_data"
    not input.security_context.role == "pci-auditor"
}

# Deny high-value transfers without multi-party approval
deny_high_value_unapproved if {
    input.payload.amount >= 10000
    count(input.approvals) < 2
}

# Risk detection Patterns
high_risk_action if {
    input.tools[_].name in ["delete_ledger", "bypass_fraud_detection", "export_private_keys"]
}

# Metadata for compliance reporting
compliance_metadata := {
    "framework": "PCI-DSS v4.0",
    "controls": ["6.4.2", "6.4.3", "10.2.1"],
    "description": "Financial Transaction Safety and Data Privacy"
}
