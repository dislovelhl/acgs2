# ACGS-2 API Reference

> **Constitutional Hash**: `cdd01ef066bc6cf2` > **Version**: 3.0.0
> **Base URL**: `http://localhost:8000` (Policy Registry), `http://localhost:8080` (Agent Bus)
> **Last Updated**: 2026-01-04

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Policy Registry API](#policy-registry-api)
4. [Agent Bus API](#agent-bus-api)
5. [Audit Service API](#audit-service-api)
6. [HITL Approvals API](#hitl-approvals-api)
7. [ML Governance API](#ml-governance-api)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)

---

## Overview

ACGS-2 provides RESTful APIs for all core services. All APIs:

- Require authentication via JWT tokens
- Validate constitutional hash (`cdd01ef066bc6cf2`)
- Support multi-tenant isolation
- Return standardized JSON responses
- Include comprehensive error handling

### Base URLs

| Service         | Base URL                | Port | Description                 |
| --------------- | ----------------------- | ---- | --------------------------- |
| Policy Registry | `http://localhost:8000` | 8000 | Policy management           |
| Agent Bus       | `http://localhost:8080` | 8080 | Agent communication         |
| Audit Service   | `http://localhost:8084` | 8084 | Audit logging               |
| HITL Approvals  | `http://localhost:8081` | 8081 | Human-in-the-loop workflows |
| ML Governance   | `http://localhost:8000` | 8000 | ML model management         |

### Common Headers

All requests must include:

```http
Content-Type: application/json
Authorization: Bearer <jwt-token>
X-Constitutional-Hash: cdd01ef066bc6cf2
X-Tenant-ID: <tenant-id>
X-Request-ID: <unique-request-id>
```

### Response Format

All responses follow this structure:

```json
{
  "status": "success|error",
  "data": { ... },
  "meta": {
    "request_id": "req-123",
    "timestamp": "2024-01-15T10:30:00Z",
    "constitutional_hash": "cdd01ef066bc6cf2"
  },
  "errors": []
}
```

---

## Authentication

### Login

Obtain a JWT token by authenticating with username and password.

**Endpoint**: `POST /api/v1/auth/login`

**Request**:

```json
{
  "username": "user@example.com",
  "password": "password"
}
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "refresh-token-here"
  }
}
```

### Refresh Token

Refresh an expired access token.

**Endpoint**: `POST /api/v1/auth/refresh`

**Request**:

```json
{
  "refresh_token": "refresh-token-here"
}
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "access_token": "new-access-token",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

---

## Policy Registry API

### List Policies

Get all policies for the current tenant.

**Endpoint**: `GET /api/v1/policies/`

**Query Parameters**:

| Parameter | Type    | Required | Description                                |
| --------- | ------- | -------- | ------------------------------------------ |
| `status`  | string  | No       | Filter by status (DRAFT, ACTIVE, ARCHIVED) |
| `limit`   | integer | No       | Maximum number of results (default: 100)   |
| `offset`  | integer | No       | Pagination offset (default: 0)             |

**Response**:

```json
{
  "status": "success",
  "data": {
    "policies": [
      {
        "id": "policy-001",
        "name": "constitutional_ai_safety",
        "status": "ACTIVE",
        "current_version": "1.0.0",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ],
    "total": 1,
    "limit": 100,
    "offset": 0
  }
}
```

### Create Policy

Create a new policy in DRAFT status.

**Endpoint**: `POST /api/v1/policies/`

**Required Roles**: `tenant_admin`, `system_admin`

**Request**:

```json
{
  "name": "constitutional_ai_safety",
  "content": {
    "max_response_length": 1000,
    "allowed_topics": ["science", "technology"],
    "prohibited_content": ["harmful_instructions"]
  },
  "format": "json",
  "description": "AI safety constitutional principles"
}
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "id": "policy-001",
    "name": "constitutional_ai_safety",
    "status": "DRAFT",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get Policy

Get policy metadata by ID.

**Endpoint**: `GET /api/v1/policies/{policy_id}`

**Response**:

```json
{
  "status": "success",
  "data": {
    "id": "policy-001",
    "name": "constitutional_ai_safety",
    "status": "ACTIVE",
    "current_version": "1.0.0",
    "versions": ["1.0.0"],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### List Policy Versions

Get all versions of a policy.

**Endpoint**: `GET /api/v1/policies/{policy_id}/versions`

**Response**:

```json
{
  "status": "success",
  "data": {
    "versions": [
      {
        "version": "1.0.0",
        "status": "ACTIVE",
        "created_at": "2024-01-15T10:30:00Z",
        "signature": {
          "public_key": "base64-public-key",
          "signature": "base64-signature",
          "verified": true
        }
      }
    ]
  }
}
```

### Create Policy Version

Create and sign a new policy version.

**Endpoint**: `POST /api/v1/policies/{policy_id}/versions`

**Required Roles**: `tenant_admin`, `system_admin`

**Request**:

```json
{
  "content": {
    "max_response_length": 2000,
    "allowed_topics": ["science", "technology", "medicine"]
  },
  "version": "1.1.0",
  "private_key_b64": "base64-encoded-private-key",
  "public_key_b64": "base64-encoded-public-key"
}
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "version": "1.1.0",
    "status": "DRAFT",
    "signature": {
      "public_key": "base64-public-key",
      "signature": "base64-signature",
      "verified": true
    },
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get Policy Content

Get policy content with A/B testing support.

**Endpoint**: `GET /api/v1/policies/{policy_id}/content`

**Query Parameters**:

| Parameter   | Type   | Required | Description                       |
| ----------- | ------ | -------- | --------------------------------- |
| `client_id` | string | Yes      | Client identifier for A/B testing |
| `version`   | string | No       | Specific version to retrieve      |

**Response**:

```json
{
  "status": "success",
  "data": {
    "policy_id": "policy-001",
    "version": "1.0.0",
    "content": {
      "max_response_length": 1000,
      "allowed_topics": ["science", "technology"],
      "prohibited_content": ["harmful_instructions"]
    },
    "signature": {
      "public_key": "base64-public-key",
      "signature": "base64-signature",
      "verified": true
    }
  }
}
```

### Upload Bundle

Upload a policy bundle file.

**Endpoint**: `POST /api/v1/bundles/`

**Required Roles**: `tenant_admin`, `system_admin`

**Request**: `multipart/form-data`

```
bundle: <file>
description: "Policy bundle for production"
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "bundle_id": "bundle-001",
    "digest": "sha256:abc123...",
    "size": 1024,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Agent Bus API

### Register Agent

Register a new agent with capabilities.

**Endpoint**: `POST /api/v2/agents/register`

**Request**:

```json
{
  "agent_id": "governance-agent",
  "agent_type": "governance",
  "capabilities": ["policy_validation", "compliance_check"],
  "maci_role": "EXECUTIVE"
}
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "agent_id": "governance-agent",
    "registered_at": "2024-01-15T10:30:00Z"
  }
}
```

### Send Message

Send a message through the agent bus.

**Endpoint**: `POST /api/v2/messages/send`

**Request**:

```json
{
  "message_type": "COMMAND",
  "content": {
    "action": "validate",
    "policy_id": "P001"
  },
  "from_agent": "governance-agent",
  "to_agent": "audit-agent",
  "priority": "HIGH",
  "constitutional_hash": "cdd01ef066bc6cf2"
}
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "message_id": "msg-001",
    "status": "delivered",
    "routed_to_deliberation": false,
    "impact_score": 0.3,
    "delivered_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Audit Service API

### Create Audit Log

Create an audit log entry.

**Endpoint**: `POST /api/v1/audit/logs`

**Request**:

```json
{
  "event_type": "policy_change",
  "actor": "user@example.com",
  "resource": "policy-001",
  "action": "update",
  "details": {
    "old_version": "1.0.0",
    "new_version": "1.1.0"
  }
}
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "log_id": "log-001",
    "merkle_root": "abc123...",
    "blockchain_tx": "tx-001",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Query Audit Logs

Query audit logs with filters.

**Endpoint**: `GET /api/v1/audit/logs`

**Query Parameters**:

| Parameter    | Type     | Required | Description                    |
| ------------ | -------- | -------- | ------------------------------ |
| `start_time` | ISO 8601 | No       | Start time filter              |
| `end_time`   | ISO 8601 | No       | End time filter                |
| `event_type` | string   | No       | Filter by event type           |
| `actor`      | string   | No       | Filter by actor                |
| `limit`      | integer  | No       | Maximum results (default: 100) |
| `offset`     | integer  | No       | Pagination offset              |

**Response**:

```json
{
  "status": "success",
  "data": {
    "logs": [
      {
        "log_id": "log-001",
        "event_type": "policy_change",
        "actor": "user@example.com",
        "resource": "policy-001",
        "action": "update",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "total": 1,
    "limit": 100,
    "offset": 0
  }
}
```

---

## HITL Approvals API

### Create Approval Request

Create a human-in-the-loop approval request. The system will dynamically resolve the appropriate approval chain via OPA policies if `chain_id` is omitted.

**Endpoint**: `POST /hitl/approvals/requests`

**Request**:

```json
{
  "decision_id": "policy_activation_001",
  "tenant_id": "tenant_1",
  "requested_by": "user@example.com",
  "title": "Activate High Risk Policy",
  "priority": "HIGH",
  "context": {
    "policy_id": "policy-001",
    "version": "1.1.0"
  },
  "chain_id": null,
  "description": "Approval required for policy activation with score > 0.8"
}
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "id": "req-001",
    "status": "pending",
    "chain_id": "chain-abc-123",
    "requested_by": "user@example.com",
    "created_at": "2026-01-06T10:30:00Z"
  }
}
```

### Submit Approval Decision

Submit an approval or rejection decision. Authorization is validated via OPA policies.

**Endpoint**: `POST /hitl/approvals/requests/{request_id}/decisions`

**Request**:

```json
{
  "approver_id": "approver_1",
  "decision": "approved",
  "rationale": "Policy changes are safe and compliant",
  "context": {
    "approver_role": "compliance_officer"
  }
}
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "id": "req-001",
    "status": "approved",
    "updated_at": "2026-01-06T10:35:00Z"
  }
}
```

---

## ML Governance API

### Register Model

Register an ML model for governance.

**Endpoint**: `POST /api/v1/ml-governance/models`

**Request**:

```json
{
  "model_id": "impact-scorer-v1",
  "model_type": "classification",
  "framework": "scikit-learn",
  "version": "1.0.0",
  "metadata": {
    "accuracy": 0.95,
    "training_data": "dataset-v1"
  }
}
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "model_id": "impact-scorer-v1",
    "status": "registered",
    "registered_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get Prediction

Get a prediction from a registered model.

**Endpoint**: `POST /api/v1/ml-governance/models/{model_id}/predict`

**Request**:

```json
{
  "features": {
    "message_length": 500,
    "complexity_score": 0.7
  }
}
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "prediction": 0.65,
    "confidence": 0.92,
    "model_version": "1.0.0"
  }
}
```

---

## Error Handling

### Error Response Format

```json
{
  "status": "error",
  "error": {
    "code": "POLICY_NOT_FOUND",
    "message": "Policy with ID policy-001 not found",
    "details": {
      "policy_id": "policy-001"
    }
  },
  "meta": {
    "request_id": "req-123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Error Codes

| Code                      | HTTP Status | Description                             |
| ------------------------- | ----------- | --------------------------------------- |
| `AUTHENTICATION_REQUIRED` | 401         | Authentication token missing or invalid |
| `AUTHORIZATION_DENIED`    | 403         | Insufficient permissions                |
| `RESOURCE_NOT_FOUND`      | 404         | Requested resource not found            |
| `VALIDATION_ERROR`        | 400         | Request validation failed               |
| `CONSTITUTIONAL_ERROR`    | 400         | Constitutional hash mismatch            |
| `RATE_LIMIT_EXCEEDED`     | 429         | Rate limit exceeded                     |
| `INTERNAL_ERROR`          | 500         | Internal server error                   |

---

## Rate Limiting

Rate limits are enforced at multiple levels:

| Scope    | Limit          | Window   |
| -------- | -------------- | -------- |
| IP       | 1000 requests  | 1 minute |
| Tenant   | 10000 requests | 1 minute |
| User     | 1000 requests  | 1 minute |
| Endpoint | Varies         | 1 minute |

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248000
```

---

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 3.0.0
**Last Updated**: 2026-01-04
