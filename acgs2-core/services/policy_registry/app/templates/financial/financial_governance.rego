package acgs.financial.governance

# Financial AI Governance Policy
# Constitutional Hash: cdd01ef066bc6cf2

default allow = false

# Rules for financial transactions
allow {
    input.action == "transaction"
    input.amount < 10000
    input.user_role == "financial_analyst"
}

allow {
    input.action == "transaction"
    input.amount >= 10000
    input.user_role == "financial_manager"
    input.mfa_verified == true
}

# Data privacy rules (GDPR/PCI-DSS)
deny {
    input.contains_pii == true
    not input.encryption_enabled
}

# Audit requirements
require_audit {
    input.amount > 50000
}
