package acgs.admission.residency

# OPA Residency Policy for Multi-Region Compliance
# Constitutional Hash: cdd01ef066bc6cf2

import rego.v1

# Deny pod if it doesn't match tenant data residency
deny contains msg if {
    input.request.kind.kind == "Pod"
    tenant_id := input.request.object.metadata.labels["tenant-id"]

    # Get required region for tenant
    required_region := data.tenant_residency[tenant_id].region

    # Get current cluster region
    current_region := input.request.object.metadata.labels["region"]

    required_region != current_region
    msg := sprintf("Tenant %v data residency violation: requires %v but found in %v", [tenant_id, required_region, current_region])
}
