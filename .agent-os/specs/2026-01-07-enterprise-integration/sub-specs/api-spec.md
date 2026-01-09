# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2026-01-07-enterprise-integration/spec.md

> Created: 2026-01-07
> Version: 1.0.0
> Constitutional Hash: cdd01ef066bc6cf2

## API Overview

All enterprise integration APIs follow REST conventions with JSON request/response bodies. Authentication required for all endpoints (JWT with MACI role validation). Constitutional hash validation enforced on all state-changing operations.

**Base URL:** `https://api.acgs2.com/v1`

## Endpoints

### Tenant Management

#### POST /tenants

Create a new tenant.

**Purpose:** Provision a new isolated tenant with dedicated resources and configuration.

**Authentication:** Required (MACI role: EXECUTIVE or higher)

**Request Body:**

```json
{
  "tenant_name": "Acme Corporation",
  "tenant_slug": "acme-corp",
  "admin_email": "admin@acme.com",
  "billing_plan": "enterprise",
  "max_requests_per_minute": 5000,
  "max_storage_gb": 100,
  "max_concurrent_connections": 500,
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

**Response (201 Created):**

```json
{
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "tenant_name": "Acme Corporation",
  "tenant_slug": "acme-corp",
  "status": "active",
  "created_at": "2026-01-07T10:30:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2",
  "api_endpoint": "https://acme-corp.api.acgs2.com"
}
```

**Errors:**

- `400 Bad Request` - Invalid tenant_slug format or duplicate name/slug
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Insufficient MACI role permissions
- `409 Conflict` - Tenant with same slug already exists

#### GET /tenants

List all tenants (admin only).

**Purpose:** Retrieve list of all tenants for administration.

**Authentication:** Required (MACI role: AUDITOR or JUDICIAL)

**Query Parameters:**

- `status` (optional): Filter by status (active, suspended, deactivated)
- `limit` (optional, default 50): Max results per page
- `offset` (optional, default 0): Pagination offset

**Response (200 OK):**

```json
{
  "tenants": [
    {
      "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
      "tenant_name": "Acme Corporation",
      "tenant_slug": "acme-corp",
      "status": "active",
      "created_at": "2026-01-07T10:30:00Z"
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

#### GET /tenants/{tenant_id}

Get tenant details.

**Purpose:** Retrieve detailed information about a specific tenant.

**Authentication:** Required (tenant admin or system admin)

**Response (200 OK):**

```json
{
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "tenant_name": "Acme Corporation",
  "tenant_slug": "acme-corp",
  "status": "active",
  "max_requests_per_minute": 5000,
  "max_storage_gb": 100,
  "max_concurrent_connections": 500,
  "admin_email": "admin@acme.com",
  "billing_plan": "enterprise",
  "created_at": "2026-01-07T10:30:00Z",
  "updated_at": "2026-01-07T10:30:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2",
  "usage_stats": {
    "current_requests_per_minute": 387,
    "current_storage_gb": 15.3,
    "current_connections": 42
  }
}
```

#### PATCH /tenants/{tenant_id}

Update tenant configuration.

**Purpose:** Modify tenant settings (quotas, status, admin email).

**Authentication:** Required (tenant admin)

**Request Body:**

```json
{
  "status": "suspended",
  "max_requests_per_minute": 10000,
  "admin_email": "new-admin@acme.com"
}
```

**Response (200 OK):**

```json
{
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "updated_fields": ["status", "max_requests_per_minute", "admin_email"],
  "updated_at": "2026-01-07T11:45:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

#### DELETE /tenants/{tenant_id}

Deactivate a tenant (soft delete).

**Purpose:** Deactivate tenant with 30-day grace period before data purge.

**Authentication:** Required (system admin only)

**Query Parameters:**

- `immediate` (optional, default false): Skip grace period and delete immediately

**Response (202 Accepted):**

```json
{
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "deactivated",
  "deactivated_at": "2026-01-07T12:00:00Z",
  "data_purge_scheduled": "2026-02-06T12:00:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

### Enterprise Integration Management

#### POST /tenants/{tenant_id}/integrations

Configure a new enterprise integration.

**Purpose:** Add LDAP, SSO, SIEM, or other enterprise integration to tenant.

**Authentication:** Required (tenant admin)

**Request Body (LDAP example):**

```json
{
  "integration_type": "ldap",
  "integration_name": "Corporate LDAP",
  "config": {
    "server_url": "ldaps://ldap.acme.com:636",
    "base_dn": "dc=acme,dc=com",
    "bind_dn": "cn=acgs2,ou=services,dc=acme,dc=com",
    "bind_password": "secret123",
    "user_search_filter": "(uid={username})",
    "group_search_filter": "(memberUid={username})",
    "tls_verify": true,
    "connection_pool_size": 10
  },
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

**Response (201 Created):**

```json
{
  "integration_id": "789e4567-e89b-12d3-a456-426614174999",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "integration_type": "ldap",
  "integration_name": "Corporate LDAP",
  "enabled": true,
  "health_status": "unknown",
  "created_at": "2026-01-07T13:00:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

**Errors:**

- `400 Bad Request` - Invalid configuration for integration type
- `409 Conflict` - Integration with same name already exists for tenant

#### GET /tenants/{tenant_id}/integrations

List all enterprise integrations for a tenant.

**Purpose:** Retrieve all configured integrations with health status.

**Authentication:** Required (tenant user)

**Query Parameters:**

- `integration_type` (optional): Filter by type (ldap, saml, kafka, etc.)
- `enabled` (optional): Filter by enabled status (true/false)

**Response (200 OK):**

```json
{
  "integrations": [
    {
      "integration_id": "789e4567-e89b-12d3-a456-426614174999",
      "integration_type": "ldap",
      "integration_name": "Corporate LDAP",
      "enabled": true,
      "health_status": "healthy",
      "last_health_check": "2026-01-07T13:55:00Z"
    },
    {
      "integration_id": "789e4567-e89b-12d3-a456-426614175000",
      "integration_type": "saml",
      "integration_name": "Okta SSO",
      "enabled": true,
      "health_status": "healthy",
      "last_health_check": "2026-01-07T13:54:00Z"
    }
  ],
  "total": 2
}
```

#### GET /tenants/{tenant_id}/integrations/{integration_id}

Get integration details.

**Purpose:** Retrieve full configuration and status of an integration.

**Authentication:** Required (tenant admin)

**Response (200 OK):**

```json
{
  "integration_id": "789e4567-e89b-12d3-a456-426614174999",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "integration_type": "ldap",
  "integration_name": "Corporate LDAP",
  "enabled": true,
  "health_status": "healthy",
  "config": {
    "server_url": "ldaps://ldap.acme.com:636",
    "base_dn": "dc=acme,dc=com",
    "bind_dn": "cn=acgs2,ou=services,dc=acme,dc=com",
    "bind_password": "***REDACTED***",
    "user_search_filter": "(uid={username})",
    "group_search_filter": "(memberUid={username})",
    "tls_verify": true,
    "connection_pool_size": 10
  },
  "created_at": "2026-01-07T13:00:00Z",
  "updated_at": "2026-01-07T13:00:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

#### POST /tenants/{tenant_id}/integrations/{integration_id}/test

Test integration connectivity.

**Purpose:** Verify integration configuration works correctly.

**Authentication:** Required (tenant admin)

**Response (200 OK):**

```json
{
  "integration_id": "789e4567-e89b-12d3-a456-426614174999",
  "test_result": "success",
  "test_details": {
    "connection_established": true,
    "authentication_successful": true,
    "test_query_executed": true,
    "latency_ms": 45
  },
  "tested_at": "2026-01-07T14:00:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

**Errors:**

- `503 Service Unavailable` - Integration endpoint unreachable
- `401 Unauthorized` - Integration credentials invalid

#### PATCH /tenants/{tenant_id}/integrations/{integration_id}

Update integration configuration.

**Purpose:** Modify integration settings or credentials.

**Authentication:** Required (tenant admin)

**Request Body:**

```json
{
  "enabled": false,
  "config": {
    "bind_password": "newSecret456"
  }
}
```

**Response (200 OK):**

```json
{
  "integration_id": "789e4567-e89b-12d3-a456-426614174999",
  "updated_fields": ["enabled", "config.bind_password"],
  "updated_at": "2026-01-07T14:30:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

#### DELETE /tenants/{tenant_id}/integrations/{integration_id}

Remove an enterprise integration.

**Purpose:** Delete integration configuration (archived for audit).

**Authentication:** Required (tenant admin)

**Response (204 No Content)**

### MACI Role Mapping

#### POST /tenants/{tenant_id}/role-mappings

Create a role mapping rule.

**Purpose:** Map enterprise groups/attributes to MACI roles.

**Authentication:** Required (tenant admin)

**Request Body:**

```json
{
  "integration_id": "789e4567-e89b-12d3-a456-426614174999",
  "source_type": "ldap_group",
  "source_value": "cn=executives,ou=groups,dc=acme,dc=com",
  "maci_role": "EXECUTIVE",
  "priority": 10,
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

**Response (201 Created):**

```json
{
  "mapping_id": "456e7890-e89b-12d3-a456-426614174111",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "integration_id": "789e4567-e89b-12d3-a456-426614174999",
  "source_type": "ldap_group",
  "source_value": "cn=executives,ou=groups,dc=acme,dc=com",
  "maci_role": "EXECUTIVE",
  "priority": 10,
  "created_at": "2026-01-07T15:00:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

#### GET /tenants/{tenant_id}/role-mappings

List all role mappings for a tenant.

**Purpose:** Retrieve configured MACI role mapping rules.

**Authentication:** Required (tenant user)

**Response (200 OK):**

```json
{
  "role_mappings": [
    {
      "mapping_id": "456e7890-e89b-12d3-a456-426614174111",
      "source_type": "ldap_group",
      "source_value": "cn=executives,ou=groups,dc=acme,dc=com",
      "maci_role": "EXECUTIVE",
      "priority": 10
    }
  ],
  "total": 1
}
```

### Migration Management

#### POST /tenants/{tenant_id}/migrations

Create a migration job.

**Purpose:** Start a legacy system migration (policy conversion, log import, etc.)

**Authentication:** Required (tenant admin)

**Request Body:**

```json
{
  "job_type": "policy_conversion",
  "source_system": "LegacyGovernanceV1",
  "source_config": {
    "policy_file_path": "/data/legacy-policies.json",
    "format": "json",
    "validation_mode": "strict"
  },
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

**Response (202 Accepted):**

```json
{
  "job_id": "999e4567-e89b-12d3-a456-426614174222",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_type": "policy_conversion",
  "job_status": "pending",
  "created_at": "2026-01-07T16:00:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2",
  "status_url": "/tenants/123e4567-e89b-12d3-a456-426614174000/migrations/999e4567-e89b-12d3-a456-426614174222"
}
```

#### GET /tenants/{tenant_id}/migrations/{job_id}

Get migration job status.

**Purpose:** Check progress and results of migration job.

**Authentication:** Required (tenant user)

**Response (200 OK):**

```json
{
  "job_id": "999e4567-e89b-12d3-a456-426614174222",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "job_type": "policy_conversion",
  "job_status": "running",
  "total_items": 150,
  "processed_items": 87,
  "successful_items": 82,
  "failed_items": 5,
  "progress_percentage": 58,
  "started_at": "2026-01-07T16:01:00Z",
  "estimated_completion": "2026-01-07T16:15:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

#### GET /tenants/{tenant_id}/migrations/{job_id}/results

Get migration job results.

**Purpose:** Retrieve detailed conversion report and errors.

**Authentication:** Required (tenant user)

**Response (200 OK):**

```json
{
  "job_id": "999e4567-e89b-12d3-a456-426614174222",
  "job_status": "completed",
  "total_items": 150,
  "successful_items": 145,
  "failed_items": 5,
  "result_summary": {
    "converted_policies": 145,
    "constitutional_compliance_rate": 0.97,
    "warnings": 12,
    "errors": 5
  },
  "failed_items_details": [
    {
      "item_id": "legacy-policy-42",
      "error": "Invalid syntax in policy condition",
      "recommendation": "Manual review required"
    }
  ],
  "download_url": "/tenants/123e4567-e89b-12d3-a456-426614174000/migrations/999e4567-e89b-12d3-a456-426614174222/report.pdf",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

#### DELETE /tenants/{tenant_id}/migrations/{job_id}

Cancel a running migration job.

**Purpose:** Stop in-progress migration job.

**Authentication:** Required (tenant admin)

**Response (200 OK):**

```json
{
  "job_id": "999e4567-e89b-12d3-a456-426614174222",
  "job_status": "cancelled",
  "processed_items": 87,
  "cancelled_at": "2026-01-07T16:10:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

### Tenant Audit Log

#### GET /tenants/{tenant_id}/audit-log

Query tenant audit log.

**Purpose:** Retrieve audit trail for compliance and troubleshooting.

**Authentication:** Required (tenant admin or AUDITOR role)

**Query Parameters:**

- `start_time` (required): ISO 8601 timestamp for range start
- `end_time` (required): ISO 8601 timestamp for range end
- `event_category` (optional): Filter by category (authentication, governance, etc.)
- `actor_id` (optional): Filter by actor
- `result` (optional): Filter by result (success, failure, denied)
- `limit` (optional, default 100): Max results
- `offset` (optional, default 0): Pagination offset

**Response (200 OK):**

```json
{
  "audit_events": [
    {
      "audit_id": "111e4567-e89b-12d3-a456-426614174333",
      "timestamp": "2026-01-07T16:30:15Z",
      "event_type": "policy.evaluate",
      "event_category": "governance",
      "actor_id": "agent-executive-01",
      "actor_type": "agent",
      "action": "evaluate_policy",
      "result": "success",
      "target_resource": "policy/critical-data-access",
      "constitutional_validation_passed": true,
      "constitutional_hash": "cdd01ef066bc6cf2"
    }
  ],
  "total": 1245,
  "limit": 100,
  "offset": 0
}
```

#### GET /tenants/{tenant_id}/audit-log/export

Export audit log for compliance reporting.

**Purpose:** Download audit log in various formats (CSV, JSON, PDF).

**Authentication:** Required (tenant admin)

**Query Parameters:**

- `start_time` (required): ISO 8601 timestamp
- `end_time` (required): ISO 8601 timestamp
- `format` (optional, default json): Export format (json, csv, pdf)
- `event_category` (optional): Filter by category

**Response (200 OK):**

```json
{
  "export_id": "exp_123456",
  "status": "processing",
  "estimated_completion": "2026-01-07T16:45:00Z",
  "download_url": null,
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

### Legacy System Migration

#### POST /tenants/{tenant_id}/migrations

Start a new migration job from a legacy system.

**Purpose:** Initiate the process of importing policies and logs from a supported legacy AI governance system.

**Authentication:** Required (MACI role: EXECUTIVE or higher)

**Request Body:**

```json
{
  "source_system": "legacy-ai-gov-v1",
  "source_config": {
    "api_url": "https://legacy.internal.com",
    "auth_token": "secret-token"
  },
  "migration_type": "full",
  "shadow_mode_days": 14,
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

**Response (202 Accepted):**

```json
{
  "job_id": "mig_abc123",
  "status": "pending",
  "created_at": "2026-01-07T14:20:00Z",
  "estimated_completion": "2026-01-07T15:00:00Z"
}
```

#### GET /tenants/{tenant_id}/migrations/{job_id}

Get migration job status and results.

**Response (200 OK):**

```json
{
  "job_id": "mig_abc123",
  "status": "completed",
  "progress_percentage": 100,
  "policies_converted": 45,
  "logs_imported": 1250,
  "errors": [],
  "completed_at": "2026-01-07T14:45:00Z",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

## Authentication & Authorization

All API endpoints require JWT authentication with Bearer token:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

JWT claims must include:

- `tenant_id`: Tenant identifier for RLS enforcement
- `maci_role`: MACI role for permission checking
- `sub`: User or agent identifier
- `constitutional_hash`: Must match `cdd01ef066bc6cf2`

## Error Responses

Standard error response format:

```json
{
  "error": {
    "code": "INVALID_TENANT_SLUG",
    "message": "Tenant slug must contain only lowercase letters, numbers, and hyphens",
    "details": {
      "field": "tenant_slug",
      "value": "Invalid_Slug",
      "constraint": "^[a-z0-9-]+$"
    },
    "constitutional_hash": "cdd01ef066bc6cf2"
  }
}
```

## Rate Limiting

Per-tenant rate limits enforced via HTTP headers:

```
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4987
X-RateLimit-Reset: 1704646800
```

## Webhooks

Tenants can configure webhooks for integration events:

**POST /tenants/{tenant_id}/webhooks**

```json
{
  "webhook_url": "https://acme.com/acgs2-events",
  "events": [
    "policy.updated",
    "migration.completed",
    "integration.health_changed"
  ],
  "secret": "webhook_secret_for_signature_verification"
}
```

Webhook payloads include constitutional hash for verification.
