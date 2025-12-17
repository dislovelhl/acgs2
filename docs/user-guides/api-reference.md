# ACGS-2 API Reference - User Guide

**Constitutional Hash: `cdd01ef066bc6cf2`**

This guide covers the REST APIs provided by ACGS-2 services, including the Policy Registry, Audit Service, and other microservices. All APIs require constitutional compliance and implement cryptographic signature verification.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Policy Registry API](#policy-registry-api)
4. [Audit Service API](#audit-service-api)
5. [Constitutional Retrieval API](#constitutional-retrieval-api)
6. [Search Platform API](#search-platform-api)
7. [WebSocket Real-time API](#websocket-real-time-api)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)
10. [SDKs and Client Libraries](#sdks-and-client-libraries)

---

## Overview

### Base URLs

| Service | Default URL | Description |
|---------|-------------|-------------|
| Policy Registry | `http://localhost:8001` | Policy management |
| Audit Service | `http://localhost:8002` | Audit logging |
| Search Platform | `http://localhost:9080` | Code/document search |
| Retrieval System | `http://localhost:8003` | Constitutional document retrieval |

### Common Headers

All requests should include:

```http
Content-Type: application/json
X-Constitutional-Hash: cdd01ef066bc6cf2
X-Tenant-ID: your-tenant-id
X-Request-ID: unique-request-id
```

### Response Format

All responses follow a standard format:

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

## Authentication & Authorization

### API Key Authentication

```http
Authorization: Bearer your-api-key
```

### Tenant Isolation

All requests must include a tenant identifier for multi-tenant isolation:

```http
X-Tenant-ID: tenant-abc-123
```

### Constitutional Compliance

Every request is validated against the constitutional hash:

```http
X-Constitutional-Hash: cdd01ef066bc6cf2
```

---

## Policy Registry API

The Policy Registry manages constitutional policies with versioning and cryptographic signatures.

### Base URL: `/api/v1/policies`

### List All Policies

```http
GET /api/v1/policies/
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status: `active`, `draft`, `retired` |

**Response:**

```json
{
  "status": "success",
  "data": [
    {
      "policy_id": "pol-abc-123",
      "name": "data-privacy-policy",
      "description": "Data privacy and protection guidelines",
      "status": "active",
      "format": "json",
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

**Example:**

```bash
curl -X GET "http://localhost:8001/api/v1/policies/?status=active" \
  -H "Authorization: Bearer your-api-key" \
  -H "X-Constitutional-Hash: cdd01ef066bc6cf2"
```

---

### Create Policy

```http
POST /api/v1/policies/
```

**Request Body:**

```json
{
  "name": "security-policy",
  "content": {
    "rules": [
      {"id": "rule-001", "type": "required", "field": "encryption"}
    ]
  },
  "format": "json",
  "description": "Security compliance policy"
}
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "policy_id": "pol-xyz-789",
    "name": "security-policy",
    "description": "Security compliance policy",
    "status": "draft",
    "format": "json",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

**Example:**

```bash
curl -X POST "http://localhost:8001/api/v1/policies/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -H "X-Constitutional-Hash: cdd01ef066bc6cf2" \
  -d '{
    "name": "security-policy",
    "content": {"rules": []},
    "format": "json"
  }'
```

---

### Get Policy

```http
GET /api/v1/policies/{policy_id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `policy_id` | string | Policy identifier |

**Response:**

```json
{
  "status": "success",
  "data": {
    "policy_id": "pol-abc-123",
    "name": "data-privacy-policy",
    "description": "Data privacy guidelines",
    "status": "active",
    "format": "json",
    "created_at": "2024-01-15T10:00:00Z"
  }
}
```

---

### List Policy Versions

```http
GET /api/v1/policies/{policy_id}/versions
```

**Response:**

```json
{
  "status": "success",
  "data": [
    {
      "version_id": "ver-001",
      "version": "1.0.0",
      "status": "retired",
      "content_hash": "sha256:abc123...",
      "created_at": "2024-01-10T10:00:00Z"
    },
    {
      "version_id": "ver-002",
      "version": "1.1.0",
      "status": "active",
      "content_hash": "sha256:def456...",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

---

### Create Policy Version

```http
POST /api/v1/policies/{policy_id}/versions
```

**Request Body:**

```json
{
  "content": {
    "rules": [
      {"id": "rule-001", "type": "required", "field": "encryption"},
      {"id": "rule-002", "type": "optional", "field": "logging"}
    ]
  },
  "version": "1.2.0",
  "private_key_b64": "base64-encoded-private-key",
  "public_key_b64": "base64-encoded-public-key",
  "ab_test_group": "A"
}
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "version_id": "ver-003",
    "policy_id": "pol-abc-123",
    "version": "1.2.0",
    "status": "draft",
    "content_hash": "sha256:ghi789...",
    "signature": {
      "algorithm": "ed25519",
      "signature": "base64-signature",
      "key_fingerprint": "fp:abc123"
    },
    "ab_test_group": "A",
    "created_at": "2024-01-15T11:00:00Z"
  }
}
```

---

### Get Policy Version

```http
GET /api/v1/policies/{policy_id}/versions/{version}
```

---

### Activate Policy Version

```http
PUT /api/v1/policies/{policy_id}/activate
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `version` | string | Version to activate (e.g., "1.2.0") |

**Response:**

```json
{
  "status": "success",
  "data": {
    "message": "Policy pol-abc-123 version 1.2.0 activated"
  }
}
```

---

### Verify Policy Signature

```http
POST /api/v1/policies/{policy_id}/verify
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `version` | string | Version to verify |

**Response:**

```json
{
  "status": "success",
  "data": {
    "policy_id": "pol-abc-123",
    "version": "1.2.0",
    "signature_valid": true
  }
}
```

---

### Get Policy Content (with A/B Testing)

```http
GET /api/v1/policies/{policy_id}/content
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `client_id` | string | Client ID for A/B test routing |

**Response:**

```json
{
  "status": "success",
  "data": {
    "rules": [
      {"id": "rule-001", "type": "required", "field": "encryption"}
    ]
  }
}
```

---

## Audit Service API

The Audit Service provides immutable audit logging with Merkle tree verification.

### Base URL: `/api/v1/audit`

### Add Audit Entry

```http
POST /api/v1/audit/entries
```

**Request Body:**

```json
{
  "validation_result": {
    "is_valid": true,
    "errors": [],
    "warnings": ["Minor formatting issue"],
    "metadata": {
      "policy_id": "pol-abc-123",
      "agent_id": "agent-001"
    },
    "constitutional_hash": "cdd01ef066bc6cf2"
  }
}
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "entry_hash": "sha256:abc123...",
    "timestamp": 1705312200.123,
    "batch_id": null
  }
}
```

---

### Get Ledger Statistics

```http
GET /api/v1/audit/stats
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "total_entries": 15432,
    "current_batch_size": 45,
    "batch_size_limit": 100,
    "batches_committed": 154,
    "current_root_hash": "sha256:merkle_root_hash"
  }
}
```

---

### Verify Audit Entry

```http
POST /api/v1/audit/verify
```

**Request Body:**

```json
{
  "entry_hash": "sha256:abc123...",
  "merkle_proof": [
    ["sha256:sibling1...", true],
    ["sha256:sibling2...", false]
  ],
  "root_hash": "sha256:merkle_root_hash"
}
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "verified": true,
    "entry_hash": "sha256:abc123..."
  }
}
```

---

### Get Batch Entries

```http
GET /api/v1/audit/batches/{batch_id}/entries
```

**Response:**

```json
{
  "status": "success",
  "data": [
    {
      "entry_hash": "sha256:entry1...",
      "timestamp": 1705312200.123,
      "validation_result": { ... },
      "merkle_proof": [...]
    }
  ]
}
```

---

### Prepare Blockchain Transaction

```http
POST /api/v1/audit/batches/{batch_id}/blockchain
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "batch_id": "batch_154_1705312200",
    "root_hash": "sha256:merkle_root...",
    "entry_count": 100,
    "timestamp": 1705312200,
    "entries_hashes": ["sha256:entry1...", "sha256:entry2..."]
  }
}
```

---

## Constitutional Retrieval API

The Retrieval System provides RAG-based document retrieval for constitutional precedents.

### Base URL: `/api/v1/retrieval`

### Index Documents

```http
POST /api/v1/retrieval/index
```

**Request Body:**

```json
{
  "documents": [
    {
      "content": "Constitutional provision text...",
      "metadata": {
        "doc_type": "constitution",
        "chapter": "Rights",
        "article": "Article 14"
      }
    }
  ]
}
```

---

### Search Similar Documents

```http
POST /api/v1/retrieval/search
```

**Request Body:**

```json
{
  "query": "privacy rights digital age",
  "limit": 10,
  "filters": {
    "doc_type": "precedent"
  }
}
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "results": [
      {
        "id": "doc-001",
        "score": 0.89,
        "relevance_score": 0.92,
        "payload": {
          "content": "Relevant constitutional text...",
          "doc_type": "precedent",
          "court": "Supreme Court",
          "date": "2023-05-15"
        }
      }
    ]
  }
}
```

---

### Retrieve Precedents

```http
POST /api/v1/retrieval/precedents
```

**Request Body:**

```json
{
  "case_description": "Data breach affecting user privacy...",
  "legal_domain": "privacy",
  "limit": 10
}
```

---

### Retrieve Constitutional Provisions

```http
POST /api/v1/retrieval/provisions
```

**Request Body:**

```json
{
  "query": "freedom of expression online",
  "constitutional_rights": ["free_speech", "privacy"],
  "limit": 5
}
```

---

### Hybrid Search

```http
POST /api/v1/retrieval/hybrid
```

**Request Body:**

```json
{
  "query": "data protection compliance",
  "keyword_filters": ["GDPR", "consent"],
  "semantic_weight": 0.7,
  "keyword_weight": 0.3,
  "limit": 10
}
```

---

## Search Platform API

High-performance code and document search.

### Base URL: `/api/v1/search`

### Quick Search

```http
GET /api/v1/search?pattern=TODO&max_results=100
```

---

### Full Search

```http
POST /api/v1/search
```

**Request Body:**

```json
{
  "id": "search-request-uuid",
  "pattern": "validate_.*policy",
  "domain": "code",
  "scope": {
    "repos": ["main"],
    "paths": ["src/", "services/"],
    "file_types": ["py", "rs"],
    "include_globs": ["**/*.py"],
    "exclude_globs": ["**/test_*"]
  },
  "options": {
    "case_sensitive": false,
    "regex": true,
    "max_results": 1000,
    "context_lines": 3,
    "timeout_ms": 30000
  }
}
```

**Response:**

```json
{
  "id": "search-request-uuid",
  "results": [
    {
      "file": "src/validators.py",
      "line_number": 42,
      "column": 4,
      "line_content": "def validate_user_policy(policy):",
      "match_text": "validate_user_policy",
      "context_before": ["# Policy validation", ""],
      "context_after": ["    '''Validate user policy'''"],
      "metadata": {
        "language": "python"
      }
    }
  ],
  "stats": {
    "total_matches": 15,
    "files_matched": 8,
    "files_searched": 245,
    "bytes_searched": 1048576,
    "duration_ms": 127,
    "truncated": false
  }
}
```

---

### Streaming Search

```http
GET /api/v1/search/stream?pattern=error&domain=logs
```

**Response (Server-Sent Events):**

```
event: started
data: {"search_id": "search-123"}

event: match
data: {"file": "logs/app.log", "line_number": 100, "line_content": "ERROR: ..."}

event: progress
data: {"files_searched": 50, "matches_found": 5}

event: completed
data: {"total_matches": 25, "duration_ms": 500}
```

---

### Health Check

```http
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "workers": {
    "search": {"status": "healthy", "count": 8},
    "index": {"status": "healthy", "count": 2}
  }
}
```

---

### Platform Statistics

```http
GET /api/v1/stats
```

**Response:**

```json
{
  "total_workers": 10,
  "healthy_workers": 10,
  "active_searches": 3,
  "total_searches": 15432,
  "avg_latency_ms": 125.5
}
```

---

## WebSocket Real-time API

Real-time policy updates and notifications.

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8001/ws');

ws.onopen = () => {
  // Subscribe to policy updates
  ws.send(JSON.stringify({
    action: 'subscribe',
    channel: 'policy_updates',
    policy_ids: ['pol-abc-123', 'pol-xyz-789']
  }));
};
```

### Message Types

**Subscription:**
```json
{
  "action": "subscribe",
  "channel": "policy_updates",
  "policy_ids": ["pol-abc-123"]
}
```

**Policy Update Notification:**
```json
{
  "type": "policy_update",
  "data": {
    "policy_id": "pol-abc-123",
    "version": "1.2.0",
    "event": "version_activated",
    "content_hash": "sha256:abc123...",
    "timestamp": "2024-01-15T11:00:00Z"
  }
}
```

**Unsubscribe:**
```json
{
  "action": "unsubscribe",
  "channel": "policy_updates"
}
```

---

## Error Handling

### Error Response Format

```json
{
  "status": "error",
  "data": null,
  "errors": [
    {
      "code": "POLICY_NOT_FOUND",
      "message": "Policy pol-xyz-999 not found",
      "field": "policy_id",
      "details": {}
    }
  ],
  "meta": {
    "request_id": "req-123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Validation failed |
| `CONSTITUTIONAL_VIOLATION` | 422 | Constitutional hash invalid |
| `SIGNATURE_INVALID` | 422 | Cryptographic signature invalid |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

### Example Error Handling

```python
import httpx

async def get_policy(policy_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://localhost:8001/api/v1/policies/{policy_id}",
            headers={"X-Constitutional-Hash": "cdd01ef066bc6cf2"}
        )

        if response.status_code == 404:
            raise PolicyNotFoundError(policy_id)
        elif response.status_code == 422:
            data = response.json()
            for error in data["errors"]:
                if error["code"] == "CONSTITUTIONAL_VIOLATION":
                    raise ConstitutionalViolationError(error["message"])
        elif response.status_code >= 500:
            raise ServiceUnavailableError()

        response.raise_for_status()
        return response.json()["data"]
```

---

## Rate Limiting

### Limits

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Read (GET) | 1000 | 1 minute |
| Write (POST/PUT/DELETE) | 100 | 1 minute |
| Search | 50 | 1 minute |
| WebSocket | 10 connections | per client |

### Rate Limit Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1705313400
```

### Rate Limit Exceeded Response

```json
{
  "status": "error",
  "errors": [
    {
      "code": "RATE_LIMITED",
      "message": "Rate limit exceeded. Retry after 45 seconds.",
      "details": {
        "retry_after": 45,
        "limit": 1000,
        "reset_at": "2024-01-15T10:35:00Z"
      }
    }
  ]
}
```

---

## SDKs and Client Libraries

### Python SDK

```python
from acgs2_client import ACGS2Client

async def main():
    client = ACGS2Client(
        base_url="http://localhost:8001",
        api_key="your-api-key",
        tenant_id="tenant-abc"
    )

    # List policies
    policies = await client.policies.list(status="active")

    # Create policy
    policy = await client.policies.create(
        name="new-policy",
        content={"rules": []},
        format="json"
    )

    # Search code
    results = await client.search.code(
        pattern="validate",
        paths=["src/"]
    )

    await client.close()
```

### JavaScript/TypeScript SDK

```typescript
import { ACGS2Client } from '@acgs2/client';

const client = new ACGS2Client({
  baseUrl: 'http://localhost:8001',
  apiKey: 'your-api-key',
  tenantId: 'tenant-abc'
});

// List policies
const policies = await client.policies.list({ status: 'active' });

// Subscribe to updates
client.ws.subscribe('policy_updates', (event) => {
  console.log('Policy updated:', event.data);
});
```

### cURL Examples

```bash
# List policies
curl -X GET "http://localhost:8001/api/v1/policies/" \
  -H "Authorization: Bearer your-api-key" \
  -H "X-Constitutional-Hash: cdd01ef066bc6cf2" \
  -H "X-Tenant-ID: tenant-abc"

# Create policy
curl -X POST "http://localhost:8001/api/v1/policies/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -H "X-Constitutional-Hash: cdd01ef066bc6cf2" \
  -d '{"name": "test", "content": {}, "format": "json"}'

# Search code
curl -X POST "http://localhost:9080/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"pattern": "TODO", "domain": "code", "options": {"max_results": 50}}'
```

---

## Next Steps

- [Enhanced Agent Bus Guide](./enhanced-agent-bus.md) - Messaging infrastructure
- [Search Platform Guide](./search-platform.md) - Search capabilities
- [Constitutional Framework](./constitutional-framework.md) - Governance system
