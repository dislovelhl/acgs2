package acgs.templates.healthcare

import future.keywords.if
import future.keywords.in

# Healthcare Policy - HIPAA Compliance Template
# Focus: PHI protection, minimal necessary disclosure, and auditability.

default allow = false

# Allow if it's a standard inquiry and user is a medical professional
allow if {
    input.message_type == "inquiry"
    input.security_context.role in ["doctor", "nurse", "paramedic"]
    not requires_phi_access
}

# Deny access to PHI (Protected Health Information) without specific consent
deny_phi_unauthorized if {
    requires_phi_access
    not input.security_context.consent_verified == true
}

# Deny deletion of medical records
deny_record_deletion if {
    input.tools[_].name == "delete_medical_record"
}

# Check if PHI is involved
requires_phi_access if {
    input.tools[_].name in ["read_patient_full_history", "export_health_id", "access_genomic_data"]
}

# Metadata for compliance reporting
compliance_metadata := {
    "framework": "HIPAA 1996",
    "controls": ["Privacy Rule", "Security Rule 164.306"],
    "description": "Patient Health Information Privacy and Security"
}
