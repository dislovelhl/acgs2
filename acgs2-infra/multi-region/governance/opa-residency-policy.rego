# ACGS-2 Tenant Data Residency Policy
# Constitutional Hash: cdd01ef066bc6cf2
#
# This policy enforces tenant data residency requirements for multi-region
# deployments. It validates:
# - Pod placement matches tenant's designated region
# - Cross-region access is blocked for restricted tenants
# - Compliance frameworks requirements are met (GDPR, PIPL, FedRAMP, etc.)
# - Data replication follows residency policies
#
# Input Schema:
#   tenant_id: string (required) - Tenant identifier
#   requested_region: string (required) - Target region for operation
#   operation: string (required) - One of: deploy, access, replicate, migrate
#   resource_type: string (optional) - One of: pod, service, data, secret
#   source_region: string (optional) - Source region for cross-region operations
#   namespace_labels: object (optional) - Kubernetes namespace labels
#
# Output Schema:
#   allow: boolean - Whether the operation is permitted
#   reason: string - Human-readable explanation
#   violations: array - List of policy violations
#   compliance_checks: object - Results of compliance framework checks

package acgs.residency

import future.keywords.if
import future.keywords.in
import future.keywords.contains

# =============================================================================
# DEFAULT RULES
# =============================================================================

# Default deny - all operations must be explicitly authorized
default allow := false

# =============================================================================
# TENANT CONFIGURATION DATA
# =============================================================================
# This data would be loaded from the tenant-residency-config ConfigMap
# via OPA's bundle mechanism or external data API

# Tenant to region mappings
tenant_regions := {
    "eu-enterprise-001": "eu-west-1",
    "eu-healthcare-002": "eu-west-1",
    "eu-financial-003": "eu-west-1",
    "us-enterprise-001": "us-east-1",
    "us-government-002": "us-east-1",
    "us-healthcare-003": "us-east-1",
    "cn-enterprise-001": "cn-north-1",
    "cn-financial-002": "cn-north-1",
    "ap-enterprise-001": "ap-southeast-1",
    "jp-enterprise-001": "ap-northeast-1",
    "global-enterprise-001": "us-east-1"
}

# Tenants that allow cross-region access
cross_region_allowed := {
    "us-enterprise-001",
    "us-healthcare-003",
    "ap-enterprise-001",
    "jp-enterprise-001",
    "global-enterprise-001"
}

# Tenant failover regions
tenant_failover_regions := {
    "us-enterprise-001": ["us-west-2"],
    "us-healthcare-003": ["us-west-2"],
    "ap-enterprise-001": ["ap-northeast-1"],
    "jp-enterprise-001": ["ap-southeast-1"],
    "global-enterprise-001": ["eu-west-1", "ap-southeast-1"]
}

# Tenant compliance frameworks
tenant_compliance := {
    "eu-enterprise-001": ["GDPR", "EU-AI-Act"],
    "eu-healthcare-002": ["GDPR", "EU-AI-Act", "HIPAA-EU"],
    "eu-financial-003": ["GDPR", "EU-AI-Act", "PSD2"],
    "us-enterprise-001": ["SOC2", "NIST-RMF"],
    "us-government-002": ["FedRAMP", "NIST-RMF", "ITAR"],
    "us-healthcare-003": ["HIPAA", "HITECH", "SOC2"],
    "cn-enterprise-001": ["PIPL", "CSL", "MLPS"],
    "cn-financial-002": ["PIPL", "CSL", "MLPS", "CBRC"],
    "ap-enterprise-001": ["PDPA", "ISO27001"],
    "jp-enterprise-001": ["APPI", "ISO27001"],
    "global-enterprise-001": ["SOC2", "ISO27001"]
}

# Compliance framework allowed regions
compliance_allowed_regions := {
    "GDPR": ["eu-west-1"],
    "EU-AI-Act": ["eu-west-1"],
    "PIPL": ["cn-north-1"],
    "CSL": ["cn-north-1"],
    "HIPAA": ["us-east-1", "us-west-2"],
    "FedRAMP": ["us-east-1"],
    "SOC2": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"],
    "NIST-RMF": ["us-east-1", "us-west-2"],
    "PDPA": ["ap-southeast-1"],
    "APPI": ["ap-northeast-1"]
}

# Compliance framework prohibited regions
compliance_prohibited_regions := {
    "GDPR": ["cn-north-1"],
    "PIPL": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"],
    "FedRAMP": ["eu-west-1", "cn-north-1", "ap-southeast-1", "ap-northeast-1"]
}

# Region to data residency zone mapping
region_zones := {
    "us-east-1": "us",
    "us-west-2": "us",
    "eu-west-1": "eu",
    "cn-north-1": "cn",
    "ap-southeast-1": "ap",
    "ap-northeast-1": "ap"
}

# =============================================================================
# MAIN AUTHORIZATION RULE
# =============================================================================

# Allow operation if all checks pass
allow if {
    tenant_exists
    region_valid
    operation_authorized
    compliance_checks_pass
    not any_violation
}

# =============================================================================
# TENANT VALIDATION
# =============================================================================

# Check if tenant exists in configuration
tenant_exists if {
    input.tenant_id
    tenant_regions[input.tenant_id]
}

# Get tenant's designated region
tenant_region := tenant_regions[input.tenant_id]

# Check if tenant allows cross-region
tenant_allows_cross_region if {
    input.tenant_id in cross_region_allowed
}

# Get tenant's failover regions
tenant_failover := regions if {
    regions := tenant_failover_regions[input.tenant_id]
} else := []

# =============================================================================
# REGION VALIDATION
# =============================================================================

# Region is valid if it matches tenant's designated region
region_valid if {
    input.requested_region == tenant_region
}

# Region is valid if it's an allowed failover region for cross-region tenants
region_valid if {
    tenant_allows_cross_region
    input.requested_region in tenant_failover
}

# Get requested region zone
requested_zone := region_zones[input.requested_region]

# Get tenant's home zone
tenant_zone := region_zones[tenant_region]

# =============================================================================
# OPERATION AUTHORIZATION
# =============================================================================

# Deploy operation - must be in correct region
operation_authorized if {
    input.operation == "deploy"
    region_valid
}

# Access operation - check cross-region rules
operation_authorized if {
    input.operation == "access"
    access_allowed
}

# Replicate operation - check replication rules
operation_authorized if {
    input.operation == "replicate"
    replication_allowed
}

# Migrate operation - not allowed for restricted tenants
operation_authorized if {
    input.operation == "migrate"
    migration_allowed
}

# Access is allowed within same region
access_allowed if {
    not input.source_region
    region_valid
}

# Access is allowed from same region
access_allowed if {
    input.source_region
    input.source_region == input.requested_region
}

# Cross-region access for allowed tenants
access_allowed if {
    input.source_region
    input.source_region != input.requested_region
    tenant_allows_cross_region
    input.requested_region in tenant_failover
}

# Replication is allowed to failover regions only
replication_allowed if {
    tenant_allows_cross_region
    input.requested_region in tenant_failover
}

# Replication to same region always allowed
replication_allowed if {
    input.requested_region == tenant_region
}

# Migration requires explicit cross-region permission
migration_allowed if {
    tenant_allows_cross_region
    input.requested_region in tenant_failover
}

# =============================================================================
# COMPLIANCE FRAMEWORK CHECKS
# =============================================================================

# All compliance checks must pass
compliance_checks_pass if {
    count(compliance_violations) == 0
}

# Get tenant's compliance frameworks
tenant_frameworks := tenant_compliance[input.tenant_id]

# Check if requested region is allowed by all compliance frameworks
compliance_violations contains msg if {
    some framework in tenant_frameworks
    allowed := compliance_allowed_regions[framework]
    allowed
    not input.requested_region in allowed
    msg := sprintf("Compliance violation: %s requires region in %v, got %s",
        [framework, allowed, input.requested_region])
}

# Check if requested region is prohibited by any compliance framework
compliance_violations contains msg if {
    some framework in tenant_frameworks
    prohibited := compliance_prohibited_regions[framework]
    prohibited
    input.requested_region in prohibited
    msg := sprintf("Compliance violation: %s prohibits region %s",
        [framework, input.requested_region])
}

# GDPR-specific: cross-border transfer check
compliance_violations contains msg if {
    "GDPR" in tenant_frameworks
    input.operation in ["replicate", "migrate"]
    input.requested_region != tenant_region
    not input.requested_region in ["eu-west-1"]
    msg := "GDPR violation: Cross-border data transfer to non-EU region requires legal basis"
}

# PIPL-specific: strict data localization
compliance_violations contains msg if {
    "PIPL" in tenant_frameworks
    input.operation in ["replicate", "migrate", "access"]
    input.requested_region != "cn-north-1"
    msg := "PIPL violation: Personal data must remain within mainland China"
}

# FedRAMP-specific: US-only operations
compliance_violations contains msg if {
    "FedRAMP" in tenant_frameworks
    not startswith(input.requested_region, "us-")
    msg := "FedRAMP violation: Operations must occur within US regions only"
}

# =============================================================================
# NAMESPACE LABEL VALIDATION
# =============================================================================

# Validate namespace labels match tenant configuration
namespace_labels_valid if {
    not input.namespace_labels
}

namespace_labels_valid if {
    input.namespace_labels
    input.namespace_labels["data-residency"] == tenant_zone
    input.namespace_labels["tenant-id"] == input.tenant_id
}

namespace_label_violations contains msg if {
    input.namespace_labels
    input.namespace_labels["data-residency"] != tenant_zone
    msg := sprintf("Namespace label mismatch: data-residency should be '%s', got '%s'",
        [tenant_zone, input.namespace_labels["data-residency"]])
}

namespace_label_violations contains msg if {
    input.namespace_labels
    input.namespace_labels["tenant-id"] != input.tenant_id
    msg := sprintf("Namespace label mismatch: tenant-id should be '%s', got '%s'",
        [input.tenant_id, input.namespace_labels["tenant-id"]])
}

# =============================================================================
# VIOLATIONS COLLECTION
# =============================================================================

# Collect all violations for audit logging
violations contains msg if {
    not tenant_exists
    msg := sprintf("Unknown tenant: '%s' not found in residency configuration",
        [input.tenant_id])
}

violations contains msg if {
    tenant_exists
    not region_valid
    msg := sprintf("Region violation: tenant '%s' must operate in '%s', requested '%s'",
        [input.tenant_id, tenant_region, input.requested_region])
}

violations contains msg if {
    some v in compliance_violations
    msg := v
}

violations contains msg if {
    some v in namespace_label_violations
    msg := v
}

violations contains msg if {
    input.operation == "migrate"
    not tenant_allows_cross_region
    msg := sprintf("Migration denied: tenant '%s' does not allow cross-region operations",
        [input.tenant_id])
}

violations contains msg if {
    input.operation in ["replicate", "access"]
    input.source_region
    input.source_region != input.requested_region
    not tenant_allows_cross_region
    msg := sprintf("Cross-region %s denied: tenant '%s' restricts operations to home region",
        [input.operation, input.tenant_id])
}

# Check if there are any violations
any_violation if {
    count(violations) > 0
}

# =============================================================================
# OUTPUT HELPERS
# =============================================================================

# Reason for the decision
reason := msg if {
    allow
    msg := sprintf("Operation '%s' allowed for tenant '%s' in region '%s'",
        [input.operation, input.tenant_id, input.requested_region])
} else := msg if {
    not tenant_exists
    msg := sprintf("Tenant '%s' not found in residency configuration", [input.tenant_id])
} else := msg if {
    not region_valid
    msg := sprintf("Region '%s' not allowed for tenant '%s' (home: %s)",
        [input.requested_region, input.tenant_id, tenant_region])
} else := msg if {
    not compliance_checks_pass
    msg := sprintf("Compliance check failed: %v", [compliance_violations])
} else := msg if {
    msg := sprintf("Operation denied for tenant '%s'", [input.tenant_id])
}

# Compliance check results
compliance_check_results := {
    "frameworks": tenant_frameworks,
    "region_allowed": region_valid,
    "cross_region_allowed": tenant_allows_cross_region,
    "failover_regions": tenant_failover,
    "violations": compliance_violations
}

# Full authorization response
authorization_response := {
    "allow": allow,
    "reason": reason,
    "violations": violations,
    "compliance_checks": compliance_check_results,
    "tenant_id": input.tenant_id,
    "requested_region": input.requested_region,
    "operation": input.operation,
    "home_region": tenant_region,
    "constitutional_hash": "cdd01ef066bc6cf2"
}

# =============================================================================
# UNIT TESTS
# =============================================================================
# OPA test convention: test_* functions return true on success

# Test: EU tenant can deploy to EU region
test_eu_tenant_deploy_eu_region if {
    allow with input as {
        "tenant_id": "eu-enterprise-001",
        "requested_region": "eu-west-1",
        "operation": "deploy"
    }
}

# Test: EU tenant cannot deploy to US region
test_eu_tenant_deploy_us_region_denied if {
    not allow with input as {
        "tenant_id": "eu-enterprise-001",
        "requested_region": "us-east-1",
        "operation": "deploy"
    }
}

# Test: China tenant strictly localized
test_china_tenant_localization if {
    not allow with input as {
        "tenant_id": "cn-enterprise-001",
        "requested_region": "us-east-1",
        "operation": "deploy"
    }
}

# Test: China tenant can deploy to China region
test_china_tenant_deploy_china if {
    allow with input as {
        "tenant_id": "cn-enterprise-001",
        "requested_region": "cn-north-1",
        "operation": "deploy"
    }
}

# Test: US tenant with cross-region can access failover
test_us_tenant_failover_access if {
    allow with input as {
        "tenant_id": "us-enterprise-001",
        "requested_region": "us-west-2",
        "operation": "access",
        "source_region": "us-east-1"
    }
}

# Test: US government tenant cannot access non-US region
test_us_gov_tenant_non_us_denied if {
    not allow with input as {
        "tenant_id": "us-government-002",
        "requested_region": "eu-west-1",
        "operation": "deploy"
    }
}

# Test: Global tenant can replicate to failover regions
test_global_tenant_replication if {
    allow with input as {
        "tenant_id": "global-enterprise-001",
        "requested_region": "eu-west-1",
        "operation": "replicate"
    }
}

# Test: Unknown tenant denied
test_unknown_tenant_denied if {
    not allow with input as {
        "tenant_id": "unknown-tenant",
        "requested_region": "us-east-1",
        "operation": "deploy"
    }
}

# Test: EU tenant GDPR compliance prevents US replication
test_gdpr_cross_border_violation if {
    not allow with input as {
        "tenant_id": "eu-enterprise-001",
        "requested_region": "us-east-1",
        "operation": "replicate"
    }
}

# Test: Japan tenant can failover to Singapore
test_japan_tenant_failover if {
    allow with input as {
        "tenant_id": "jp-enterprise-001",
        "requested_region": "ap-southeast-1",
        "operation": "access",
        "source_region": "ap-northeast-1"
    }
}

# Test: PIPL prevents any cross-border operation
test_pipl_strict_localization if {
    violations_result := violations with input as {
        "tenant_id": "cn-enterprise-001",
        "requested_region": "ap-southeast-1",
        "operation": "replicate"
    }
    count(violations_result) > 0
}

# Test: FedRAMP tenant restricted to US
test_fedramp_us_only if {
    not allow with input as {
        "tenant_id": "us-government-002",
        "requested_region": "eu-west-1",
        "operation": "access"
    }
}

# Test: Namespace labels validation
test_namespace_labels_valid if {
    namespace_labels_valid with input as {
        "tenant_id": "eu-enterprise-001",
        "requested_region": "eu-west-1",
        "operation": "deploy",
        "namespace_labels": {
            "data-residency": "eu",
            "tenant-id": "eu-enterprise-001"
        }
    }
}

# Test: Namespace labels mismatch detected
test_namespace_labels_mismatch if {
    result := namespace_label_violations with input as {
        "tenant_id": "eu-enterprise-001",
        "requested_region": "eu-west-1",
        "operation": "deploy",
        "namespace_labels": {
            "data-residency": "us",
            "tenant-id": "eu-enterprise-001"
        }
    }
    count(result) > 0
}

# Test: Same region access always allowed
test_same_region_access if {
    allow with input as {
        "tenant_id": "eu-enterprise-001",
        "requested_region": "eu-west-1",
        "operation": "access",
        "source_region": "eu-west-1"
    }
}

# Test: Migration denied for restricted tenant
test_migration_denied_restricted if {
    not allow with input as {
        "tenant_id": "eu-enterprise-001",
        "requested_region": "us-east-1",
        "operation": "migrate"
    }
}

# Test: Migration allowed for global tenant to failover region
test_migration_allowed_global if {
    allow with input as {
        "tenant_id": "global-enterprise-001",
        "requested_region": "eu-west-1",
        "operation": "migrate"
    }
}
