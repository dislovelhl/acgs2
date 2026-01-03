package acgs.healthcare.governance

# Healthcare AI Governance Policy (HIPAA Aligned)
# Constitutional Hash: cdd01ef066bc6cf2

default allow = false

# Access to PHI (Protected Health Information)
allow {
    input.action == "access_phi"
    input.user_role == "doctor"
    input.patient_consent == true
}

allow {
    input.action == "access_phi"
    input.user_role == "nurse"
    input.emergency_mode == true
}

# Data de-identification
require_deid {
    input.action == "research_export"
}

# Audit trail for HIPAA
require_logging {
    input.resource_type == "patient_record"
}
