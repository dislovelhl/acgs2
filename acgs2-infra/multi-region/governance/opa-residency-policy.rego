package acgs2.multi_region.residency

import data.tenants
import data.regions
import data.compliance_rules

# Default deny for data residency violations
default allow_data_access = false
default allow_data_transfer = false
default allow_cross_region = false

# Allow data access within the same region as tenant residency
allow_data_access {
    tenant := tenants[input.tenant_id]
    tenant.region == input.request_region
    not violates_compliance_rules(tenant, input)
}

# Allow data access for global tenants with proper controls
allow_data_access {
    tenant := tenants[input.tenant_id]
    tenant["global-data-access"] == true
    input.data_classification != "sensitive"
    input.audit_logged == true
    input.user_authenticated == true
}

# Allow cross-region data transfers for backup and DR
allow_data_transfer {
    tenant := tenants[input.tenant_id]
    input.destination_region == tenant.backup_regions[_]
    input.purpose == "backup"
    input.encryption_enabled == true
    input.audit_logged == true
}

# Allow cross-region access for GDPR compliance with proper safeguards
allow_cross_region {
    tenant := tenants[input.tenant_id]
    tenant.compliance[_] == "GDPR"
    input.destination_region != tenant.region
    input.legal_basis == "consent"
    input.data_minimization_applied == true
    input.privacy_by_design == true
    input.audit_logged == true
}

# Deny access that violates GDPR data residency
deny_gdpr_violation {
    tenant := tenants[input.tenant_id]
    tenant.compliance[_] == "GDPR"
    input.request_region != tenant.region
    not input.gdpr_exception_applies
}

# Deny access that violates CCPA requirements
deny_ccpa_violation {
    tenant := tenants[input.tenant_id]
    tenant.compliance[_] == "CCPA"
    input.data_sale == true
    input.user_opted_out == true
}

# Deny access that violates PIPL data localization
deny_pipl_violation {
    tenant := tenants[input.tenant_id]
    tenant.compliance[_] == "PIPL"
    input.request_region != tenant.region
    input.data_contains_personal_info == true
}

# Deny access that violates HIPAA requirements
deny_hipaa_violation {
    tenant := tenants[input.tenant_id]
    tenant.compliance[_] == "HIPAA"
    input.encryption_enabled == false
    input.data_classification == "PHI"
}

# Helper function to check if request violates tenant compliance rules
violates_compliance_rules(tenant, input) {
    compliance_violation := deny_gdpr_violation
    compliance_violation.tenant_id == tenant.id
}

violates_compliance_rules(tenant, input) {
    compliance_violation := deny_ccpa_violation
    compliance_violation.tenant_id == tenant.id
}

violates_compliance_rules(tenant, input) {
    compliance_violation := deny_pipl_violation
    compliance_violation.tenant_id == tenant.id
}

violates_compliance_rules(tenant, input) {
    compliance_violation := deny_hipaa_violation
    compliance_violation.tenant_id == tenant.id
}

# Audit logging requirement for sensitive data access
requires_audit_log {
    input.data_classification == "sensitive"
}

requires_audit_log {
    input.data_classification == "PHI"
}

requires_audit_log {
    input.cross_region_access == true
}

# Data retention policies based on compliance framework
data_retention_period[period] {
    tenant := tenants[input.tenant_id]
    tenant.compliance[_] == "GDPR"
    input.data_purpose == "marketing"
    period := "24_months"
}

data_retention_period[period] {
    tenant := tenants[input.tenant_id]
    tenant.compliance[_] == "GDPR"
    input.data_purpose == "contract"
    period := "7_years"
}

data_retention_period[period] {
    tenant := tenants[input.tenant_id]
    tenant.compliance[_] == "CCPA"
    period := "2_years"
}

# Encryption requirements for sensitive data
requires_encryption {
    input.data_classification == "sensitive"
}

requires_encryption {
    input.data_classification == "PHI"
}

requires_encryption {
    input.cross_region_transfer == true
}

# Access control policies
allow_tenant_access {
    input.tenant_id == input.resource_tenant_id
}

allow_admin_access {
    input.user_role == "admin"
    input.audit_logged == true
    input.mfa_verified == true
}

# Multi-region failover policies
allow_failover_access {
    input.failover_mode == true
    input.source_region_unavailable == true
    input.encryption_enabled == true
    input.audit_logged == true
}

# Decision logging for compliance auditing
decision_log[log] {
    log := {
        "timestamp": time.now_ns(),
        "tenant_id": input.tenant_id,
        "user_id": input.user_id,
        "resource": input.resource,
        "action": input.action,
        "decision": allow_data_access,
        "region": input.request_region,
        "compliance_frameworks": tenants[input.tenant_id].compliance,
        "data_classification": input.data_classification,
        "audit_required": requires_audit_log
    }
}

# Policy version and metadata
policy_info := {
    "version": "1.0.0",
    "last_updated": "2025-01-02T10:00:00Z",
    "frameworks_supported": ["GDPR", "CCPA", "PIPL", "HIPAA"],
    "regions_supported": ["us-east-1", "eu-west-1", "cn-north-1", "ap-southeast-1"]
}
