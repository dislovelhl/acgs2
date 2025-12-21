package acgs.templates.govtech

import future.keywords.if
import future.keywords.in

# Govtech Policy - FedRAMP Compliance Template
# Focus: Data sovereignty, boundary protection, and strict access control.

default allow = false

# Allow if requester is within the authorized government boundary
allow if {
    input.security_context.boundary == "US-GOV-CLOUD"
    input.message_type != "sensitive_data_export"
}

# Deny if action involves data exfiltration outside the US boundary
deny_exfiltration if {
    input.action == "export"
    not input.destination_region == "us-gov"
}

# Deny access to classified material without top-secret clearance
deny_classified if {
    input.payload.classification == "TOP_SECRET"
    not input.security_context.clearance == "TS/SCI"
}

# Metadata for compliance reporting
compliance_metadata := {
    "framework": "FedRAMP High / NIST SP 800-53",
    "controls": ["AC-2", "AC-3", "SC-7"],
    "description": "Government Cloud Security and Sovereignty"
}
