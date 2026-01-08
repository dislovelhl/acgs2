# ACGS-2 Multi-Tenant Deployment Guide

> **Constitutional Hash**: `cdd01ef066bc6cf2`
> **Version**: 1.0.0
> **Status**: Stable
> **Last Updated**: 2026-01-03

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Configuration](#configuration)
5. [Deployment](#deployment)
6. [End-to-End Verification](#end-to-end-verification)
7. [API Reference](#api-reference)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Security Considerations](#security-considerations)

---

## Overview

This guide covers the deployment and operation of ACGS-2's multi-tenant isolation capabilities for enterprise SaaS deployments. The multi-tenant isolation system provides:

- **Namespace-Based Tenant Isolation**: Each tenant operates in a dedicated Kubernetes namespace (`tenant-{tenant_id}`)
- **Tenant-Specific Rate Limiting**: Configurable request rate limits per tenant with Redis-backed sliding window algorithm
- **Resource Quota Enforcement**: CPU, memory, and storage quotas enforced at the Kubernetes namespace level
- **Cross-Tenant Access Prevention**: Architectural design ensures tenant A cannot access tenant B's data
- **Tenant-Scoped Audit Logs**: All API actions logged with tenant_id and strict access controls

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| Tenant Context Middleware | `shared/security/tenant_context.py` | X-Tenant-ID header extraction and validation |
| Rate Limiter | `shared/security/rate_limiter.py` | Tenant-specific rate limiting with Redis backend |
| K8s Resource Manager | `shared/infrastructure/k8s_manager.py` | Kubernetes namespace and quota management |
| Tenant Audit Logger | `shared/logging/audit_logger.py` | Tenant-scoped audit logging |
| Tenant Configuration | `shared/config/tenant_config.py` | Pydantic models for tenant quota configuration |

---

## Prerequisites

### Required Infrastructure

| Service | Version | Purpose |
|---------|---------|---------|
| Kubernetes | >= 1.28 | Container orchestration with namespace isolation |
| Redis | >= 7.0 | Rate limiting backend and audit log storage |
| Kafka | >= 3.0 | Event streaming (optional) |
| OPA | >= 0.60.0 | Policy enforcement |

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| kubectl | >= 1.28 | Kubernetes management |
| Helm | >= 3.13.0 | Chart deployment |
| Python | >= 3.11 | Runtime environment |

### Python Dependencies

Ensure the following packages are installed:

```bash
pip install kubernetes>=28.0.0
pip install pydantic-settings>=2.0.0
pip install redis>=5.0.0
pip install fastapi>=0.115.6
```

### RBAC Requirements

The service account running ACGS-2 requires the following Kubernetes permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: acgs2-tenant-manager
rules:
  - apiGroups: [""]
    resources: ["namespaces"]
    verbs: ["create", "get", "list", "watch", "delete"]
  - apiGroups: [""]
    resources: ["resourcequotas", "limitranges"]
    verbs: ["create", "get", "list", "watch", "update", "delete"]
  - apiGroups: ["networking.k8s.io"]
    resources: ["networkpolicies"]
    verbs: ["create", "get", "list", "watch", "update", "delete"]
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Load Balancer                                  │
│                      (X-Tenant-ID Required)                             │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                        FastAPI Application                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              TenantContextMiddleware                              │   │
│  │     (Extracts & validates X-Tenant-ID from all requests)         │   │
│  └───────────────────────────┬──────────────────────────────────────┘   │
│                              │                                           │
│  ┌───────────────────────────▼──────────────────────────────────────┐   │
│  │              RateLimitMiddleware                                  │   │
│  │     (Per-tenant rate limits via Redis sliding window)            │   │
│  └───────────────────────────┬──────────────────────────────────────┘   │
│                              │                                           │
│  ┌───────────────────────────▼──────────────────────────────────────┐   │
│  │              API Endpoints                                        │   │
│  │     (All operations scoped to tenant_id)                         │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
           │                    │                    │
    ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
    │   Redis     │     │ Kubernetes  │     │   Audit     │
    │ Rate Limits │     │  API Server │     │   Logger    │
    │             │     │             │     │ (per-tenant)│
    └─────────────┘     └──────┬──────┘     └─────────────┘
                               │
    ┌──────────────────────────┼──────────────────────────┐
    │           Kubernetes Cluster                         │
    │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │
    │  │tenant-a    │  │tenant-b    │  │tenant-c    │    │
    │  │  namespace │  │  namespace │  │  namespace │    │
    │  │            │  │            │  │            │    │
    │  │ ResourceQ  │  │ ResourceQ  │  │ ResourceQ  │    │
    │  │ LimitRange │  │ LimitRange │  │ LimitRange │    │
    │  │ NetPolicy  │  │ NetPolicy  │  │ NetPolicy  │    │
    │  └────────────┘  └────────────┘  └────────────┘    │
    └─────────────────────────────────────────────────────┘
```

### Isolation Layers

1. **Application Layer**: TenantContextMiddleware validates X-Tenant-ID on every request
2. **Rate Limiting Layer**: Per-tenant quotas enforced via Redis sliding window
3. **Infrastructure Layer**: Kubernetes namespaces with ResourceQuota, LimitRange, NetworkPolicy
4. **Audit Layer**: All operations logged with tenant scope; cross-tenant queries blocked

---

## Configuration

### Environment Variables

Add these to your `.env` file or Kubernetes ConfigMap:

```bash
# Tenant Configuration
TENANT_ID=acgs-dev                          # Default tenant for development
TENANT_ENABLED=true                         # Enable multi-tenant mode
K8S_NAMESPACE_PREFIX=tenant-                # Namespace prefix for tenants

# Resource Quotas (Default values for new tenants)
TENANT_DEFAULT_CPU_QUOTA=2                  # CPU cores
TENANT_DEFAULT_MEMORY_QUOTA=4Gi             # Memory limit
TENANT_DEFAULT_STORAGE_QUOTA=20Gi           # Storage limit
TENANT_DEFAULT_MAX_PODS=50                  # Maximum pods per namespace
TENANT_DEFAULT_MAX_PVCS=10                  # Maximum PVCs per namespace

# Rate Limiting
RATE_LIMIT_TENANT_REQUESTS=1000             # Requests per window
RATE_LIMIT_TENANT_WINDOW=60                 # Window in seconds
RATE_LIMIT_TENANT_BURST=1.2                 # Burst multiplier
RATE_LIMIT_ENABLED=true                     # Enable rate limiting
RATE_LIMIT_FAIL_OPEN=true                   # Allow requests when Redis unavailable

# Redis Configuration
REDIS_URL=redis://redis:6379/0              # Redis connection URL

# Tenant Context Middleware
TENANT_CONTEXT_ENABLED=true                 # Enable tenant extraction
TENANT_CONTEXT_REQUIRED=true                # Require X-Tenant-ID header
TENANT_HEADER_NAME=X-Tenant-ID              # Header name for tenant ID
TENANT_FAIL_OPEN=false                      # Reject requests without tenant ID

# Kubernetes Configuration
K8S_RETRY_ATTEMPTS=3                        # Retry attempts for K8s operations
K8S_RETRY_DELAY=1.0                         # Retry delay in seconds
K8S_FAIL_SAFE=true                          # Continue when K8s unavailable

# Audit Logging
AUDIT_ENABLED=true                          # Enable audit logging
AUDIT_USE_REDIS=false                       # Use Redis for audit storage
AUDIT_RETENTION_DAYS=90                     # Days to retain audit logs
AUDIT_ENABLE_REDACTION=true                 # Redact sensitive fields
```

### Helm Values Configuration

Update `deploy/helm/acgs2/values.yaml`:

```yaml
# Multi-Tenant Quota Configuration
tenantQuotas:
  enabled: true

  namespace:
    prefix: "tenant-"
    labels:
      managed-by: "acgs2"
      isolation-level: "namespace"

  defaults:
    cpu: "2"
    memory: "4Gi"
    storage: "20Gi"
    maxPVCs: 10
    maxPods: 50

  rateLimits:
    requestsPerWindow: 1000
    windowSeconds: 60
    algorithm: "sliding_window"
    burstMultiplier: 1.2

  enforcement:
    mode: "strict"
    failOpen: false
    retryAttempts: 3

  # Per-tenant overrides
  overrides:
    premium-tenant:
      cpu: "8"
      memory: "16Gi"
      storage: "100Gi"
      maxPVCs: 50
      maxPods: 200
      rateLimits:
        requestsPerWindow: 10000
    basic-tenant:
      cpu: "1"
      memory: "2Gi"
      storage: "10Gi"
      maxPVCs: 5
      maxPods: 20

  networkPolicy:
    enabled: true
    denyCrossTenant: true
    allowedEgress:
      - kafka
      - redis
      - opa

  auditLogging:
    enabled: true
    usageReportingInterval: "5m"
    usageAlertThreshold: 80
```

---

## Deployment

### Step 1: Start Required Services

```bash
# Start Redis (required for rate limiting)
docker-compose up -d redis

# Start Kafka (optional, for event streaming)
docker-compose up -d kafka zookeeper

# Start OPA (required for policy enforcement)
docker-compose up -d opa

# Verify services are running
docker-compose ps
```

### Step 2: Deploy ACGS-2 with Multi-Tenant Support

```bash
# Create namespace
kubectl create namespace acgs2

# Create secrets
kubectl create secret generic acgs2-redis-credentials \
  --from-literal=url='redis://redis:6379/0' \
  -n acgs2

# Deploy with Helm
helm upgrade --install acgs2 ./deploy/helm/acgs2 \
  --namespace acgs2 \
  --set tenantQuotas.enabled=true \
  --set global.constitutional_hash=cdd01ef066bc6cf2 \
  --wait \
  --timeout 10m
```

### Step 3: Create Test Tenants

Use the K8s Resource Manager to provision tenant namespaces:

```python
from shared.infrastructure.k8s_manager import K8sResourceManager

# Create manager instance
manager = K8sResourceManager()

# Provision tenant with custom quotas
results = await manager.provision_tenant(
    tenant_id="test-tenant-a",
    cpu="4",
    memory="8Gi",
    storage="50Gi",
    max_pods=100,
    create_network_policy=True,
    create_limit_range=True,
)

# Verify all resources created
for resource, result in results.items():
    print(f"{resource}: {result.status.value} - {result.message}")
```

Or using kubectl directly:

```bash
# Create tenant namespace manually
kubectl create namespace tenant-test-a
kubectl label namespace tenant-test-a \
  tenant-id=test-a \
  managed-by=acgs2 \
  constitutional-hash=cdd01ef066bc6cf2

# Apply resource quota
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-test-a
  labels:
    tenant-id: test-a
    managed-by: acgs2
spec:
  hard:
    requests.cpu: "2"
    requests.memory: "4Gi"
    limits.cpu: "2"
    limits.memory: "4Gi"
    persistentvolumeclaims: "10"
    requests.storage: "20Gi"
    pods: "50"
EOF
```

---

## End-to-End Verification

### Verification Checklist

Follow these steps to verify the complete multi-tenant isolation system:

#### 1. Start All Services

```bash
# Verify Redis is running
redis-cli ping
# Expected: PONG

# Verify Kafka is running (optional)
kafka-topics.sh --bootstrap-server localhost:9092 --list

# Verify OPA is running
curl http://localhost:8181/health
# Expected: {"status":"ok"}

# Verify ACGS-2 API is running
curl http://localhost:8000/health
# Expected: {"status":"healthy",...}
```

#### 2. Create Test Tenants with Different Quotas

```bash
# Create premium tenant namespace
kubectl create namespace tenant-premium-test
kubectl apply -f - <<EOF
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-premium-test
spec:
  hard:
    requests.cpu: "8"
    requests.memory: "16Gi"
    pods: "200"
EOF

# Create basic tenant namespace
kubectl create namespace tenant-basic-test
kubectl apply -f - <<EOF
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-basic-test
spec:
  hard:
    requests.cpu: "1"
    requests.memory: "2Gi"
    pods: "20"
EOF

# Verify namespaces exist
kubectl get namespace | grep tenant-
```

#### 3. Verify Namespace Isolation in Kubernetes

```bash
# Check namespaces have correct labels
kubectl get namespace tenant-premium-test -o yaml | grep -A5 labels
# Expected: tenant-id: premium-test, managed-by: acgs2

# Check ResourceQuota applied
kubectl describe resourcequota tenant-quota -n tenant-premium-test
# Expected: CPU: 8, Memory: 16Gi

# Verify pods in one namespace cannot access services in another
kubectl run -n tenant-basic-test test-pod --image=busybox --rm -it -- \
  wget -q -O- http://service.tenant-premium-test.svc.cluster.local 2>&1
# Expected: Connection refused or timeout (NetworkPolicy blocks cross-tenant traffic)
```

#### 4. Test Rate Limit Enforcement Per Tenant

```bash
# Test rate limiting for tenant-a (1000 requests/minute limit)
for i in {1..1100}; do
  response=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "X-Tenant-ID: tenant-a" \
    http://localhost:8000/api/v1/messages)
  if [ "$response" = "429" ]; then
    echo "Rate limit hit at request $i"
    break
  fi
done
# Expected: Rate limit hit around request 1001

# Verify tenant-b is not affected by tenant-a's rate limit
curl -s -H "X-Tenant-ID: tenant-b" http://localhost:8000/api/v1/messages
# Expected: 200 OK (tenant-b has independent quota)
```

#### 5. Verify Audit Log Tenant Scoping

```bash
# Create audit entries for different tenants
curl -X POST http://localhost:8000/api/v1/resources \
  -H "X-Tenant-ID: tenant-a" \
  -H "Content-Type: application/json" \
  -d '{"name": "resource-a"}'

curl -X POST http://localhost:8000/api/v1/resources \
  -H "X-Tenant-ID: tenant-b" \
  -H "Content-Type: application/json" \
  -d '{"name": "resource-b"}'

# Query audit logs as tenant-a
curl -H "X-Tenant-ID: tenant-a" \
  http://localhost:8000/api/v1/audit-logs
# Expected: Only logs for tenant-a (not tenant-b)

# Attempt to query tenant-b logs as tenant-a (should fail)
curl -H "X-Tenant-ID: tenant-a" \
  "http://localhost:8000/api/v1/audit-logs?target_tenant=tenant-b"
# Expected: 403 Forbidden or empty result
```

#### 6. Confirm Cross-Tenant Access Prevention

```bash
# Create a resource as tenant-a
curl -X POST http://localhost:8000/api/v1/resources \
  -H "X-Tenant-ID: tenant-a" \
  -H "Content-Type: application/json" \
  -d '{"id": "res-123", "name": "secret-resource"}'
# Expected: 201 Created

# Attempt to access tenant-a's resource as tenant-b
curl -H "X-Tenant-ID: tenant-b" \
  http://localhost:8000/api/v1/resources/res-123
# Expected: 403 Forbidden or 404 Not Found

# Test missing X-Tenant-ID header (should be rejected)
curl http://localhost:8000/api/v1/resources
# Expected: 400 Bad Request - Missing required header: X-Tenant-ID

# Test invalid tenant ID format (should be rejected)
curl -H "X-Tenant-ID: ../../../etc/passwd" \
  http://localhost:8000/api/v1/resources
# Expected: 400 Bad Request - Invalid tenant ID
```

### Automated Verification Script

Run the integration tests to verify all components:

```bash
cd src/core

# Run tenant rate limit integration tests
pytest tests/integration/test_tenant_rate_limit.py -v

# Run cross-tenant isolation tests
pytest tests/integration/test_tenant_isolation.py -v

# Run Kubernetes quota tests (requires K8s cluster)
pytest tests/integration/test_k8s_quotas.py -v

# Run all integration tests
pytest tests/integration/ -v --tb=short
```

---

## API Reference

### Tenant Context Middleware

All API requests must include the `X-Tenant-ID` header:

```http
GET /api/v1/resources HTTP/1.1
Host: api.acgs.example.com
X-Tenant-ID: my-tenant-id
```

#### Header Requirements

| Header | Required | Format | Description |
|--------|----------|--------|-------------|
| `X-Tenant-ID` | Yes | `^[a-zA-Z0-9][a-zA-Z0-9\-_]{0,62}[a-zA-Z0-9]$` | Tenant identifier |

#### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 400 | `MISSING_TENANT_ID` | X-Tenant-ID header not provided |
| 400 | `INVALID_TENANT_ID` | Tenant ID format invalid |
| 403 | `CROSS_TENANT_ACCESS_DENIED` | Attempted to access another tenant's resource |
| 429 | `RATE_LIMIT_EXCEEDED` | Tenant rate limit exceeded |

### Rate Limit Headers

All responses include rate limit information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1704240000
X-RateLimit-Scope: tenant
X-Tenant-ID: my-tenant-id
```

### Programmatic Tenant Provisioning

```python
from shared.infrastructure.k8s_manager import K8sResourceManager

async def provision_new_tenant(tenant_id: str, tier: str = "standard"):
    """Provision a new tenant with appropriate quotas."""
    manager = K8sResourceManager()

    # Define quota based on tier
    quotas = {
        "basic": {"cpu": "1", "memory": "2Gi", "storage": "10Gi"},
        "standard": {"cpu": "2", "memory": "4Gi", "storage": "20Gi"},
        "premium": {"cpu": "8", "memory": "16Gi", "storage": "100Gi"},
    }

    tier_quota = quotas.get(tier, quotas["standard"])

    # Create namespace and all resources
    results = await manager.provision_tenant(
        tenant_id=tenant_id,
        cpu=tier_quota["cpu"],
        memory=tier_quota["memory"],
        storage=tier_quota["storage"],
        create_network_policy=True,
        create_limit_range=True,
    )

    return results
```

### Tenant Rate Limit Configuration

```python
from shared.security.rate_limiter import TenantRateLimitProvider

# Create provider with custom defaults
provider = TenantRateLimitProvider(
    default_requests=1000,
    default_window_seconds=60,
    default_burst_multiplier=1.2,
)

# Set custom quota for premium tenant
provider.set_tenant_quota(
    tenant_id="premium-tenant",
    requests=10000,
    window_seconds=60,
    burst_multiplier=1.5,
)

# Get quota for a tenant
quota = provider.get_tenant_quota("premium-tenant")
print(f"Limit: {quota.requests} requests/{quota.window_seconds}s")
```

### Tenant Audit Logging

```python
from shared.logging.audit_logger import TenantAuditLogger, AuditAction

# Create logger
logger = TenantAuditLogger()

# Log an action
await logger.log(
    tenant_id="my-tenant",
    action=AuditAction.CREATE,
    resource_type="policy",
    resource_id="policy-123",
    actor_id="user-456",
    details={"policy_name": "example"},
)

# Query logs (scoped to requesting tenant)
from shared.logging.audit_logger import AuditQueryParams

result = await logger.query(
    requesting_tenant_id="my-tenant",
    query=AuditQueryParams(
        action=AuditAction.CREATE,
        limit=100,
    ),
)

for entry in result.entries:
    print(f"{entry.timestamp}: {entry.action} - {entry.resource_type}")
```

---

## Monitoring

### Key Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `acgs2_tenant_rate_limit_exceeded_total` | Rate limit violations per tenant | > 10/minute |
| `acgs2_tenant_quota_usage_percent` | Resource quota utilization | > 80% |
| `acgs2_cross_tenant_access_blocked_total` | Cross-tenant access attempts | Any occurrence |
| `acgs2_tenant_namespace_count` | Total tenant namespaces | - |
| `acgs2_audit_entries_total` | Audit log entries per tenant | - |

### Prometheus Queries

```promql
# Rate limit violations by tenant
sum by (tenant_id) (
  rate(acgs2_tenant_rate_limit_exceeded_total[5m])
)

# Resource quota usage by tenant
acgs2_tenant_quota_usage_percent{resource="cpu"}

# Cross-tenant access attempts (security alert)
increase(acgs2_cross_tenant_access_blocked_total[1h]) > 0
```

### Grafana Dashboard

Import the multi-tenant dashboard from `deploy/grafana/dashboards/multi-tenant.json`.

---

## Troubleshooting

### Common Issues

#### 1. Missing X-Tenant-ID Header

**Error:**
```json
{
  "error": "Bad Request",
  "message": "Missing required header: X-Tenant-ID",
  "code": "MISSING_TENANT_ID"
}
```

**Solution:** Ensure all API requests include the `X-Tenant-ID` header.

#### 2. Rate Limit Exceeded

**Error:**
```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded for tenant 'my-tenant'. Try again in 45 seconds.",
  "retry_after": 45,
  "scope": "tenant"
}
```

**Solution:** Wait for the specified retry_after period or increase tenant quota.

#### 3. Kubernetes Namespace Creation Failed

**Error:**
```
K8sOperationResult(status=ERROR, message="Failed to create namespace: Forbidden")
```

**Solution:** Verify the service account has the required RBAC permissions:
```bash
kubectl auth can-i create namespaces --as=system:serviceaccount:acgs2:acgs2-sa
```

#### 4. ResourceQuota Exceeded

**Error:**
```
pods "my-pod" is forbidden: exceeded quota: tenant-quota, requested: requests.cpu=2, used: requests.cpu=2, limited: requests.cpu=2
```

**Solution:** Either reduce resource requests or increase tenant quota:
```bash
kubectl patch resourcequota tenant-quota -n tenant-my-tenant \
  --type='json' -p='[{"op": "replace", "path": "/spec/hard/requests.cpu", "value": "4"}]'
```

#### 5. Cross-Tenant Access Denied

**Error:**
```json
{
  "error": "Forbidden",
  "message": "Access denied: resource belongs to a different tenant",
  "code": "CROSS_TENANT_ACCESS_DENIED"
}
```

**Solution:** This is expected behavior. Ensure the request uses the correct tenant ID.

### Debug Commands

```bash
# Check tenant middleware configuration
kubectl exec -n acgs2 deployment/acgs2-agent-bus -- \
  env | grep TENANT

# View rate limit keys in Redis
redis-cli keys "acgs2:ratelimit:tenant:*"

# Check audit log entries for a tenant
redis-cli zrange "acgs2:audit:tenant:my-tenant:index" 0 -1

# View Kubernetes quota usage
kubectl describe resourcequota -n tenant-my-tenant

# Check network policy
kubectl get networkpolicy -n tenant-my-tenant -o yaml
```

---

## Security Considerations

### Tenant ID Validation

The system performs comprehensive validation on tenant IDs:

- **Length**: 1-64 characters
- **Format**: Must start and end with alphanumeric characters
- **Allowed Characters**: Alphanumeric, hyphens, underscores only
- **Blocked Patterns**: Path traversal (`..`, `/`, `\`), injection characters (`<`, `>`, `'`, `"`, etc.)

### Network Isolation

Each tenant namespace includes a NetworkPolicy that:

- Allows traffic within the same tenant namespace
- Allows DNS queries to kube-system
- Blocks all cross-tenant network traffic
- Allows egress to shared services (Kafka, Redis, OPA)

### Audit Log Protection

Audit logs are protected by:

- Mandatory tenant scoping on all queries
- No cross-tenant query capability
- Sensitive field redaction (passwords, tokens, API keys)
- Configurable retention period

### Rate Limiting Security

- Per-tenant quotas prevent noisy neighbor problems
- Sliding window algorithm prevents burst attacks
- Fail-open mode can be disabled for strict security
- Rate limit headers help clients manage their quota

---

## Appendix: Configuration Reference

### TenantContextConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `header_name` | str | `X-Tenant-ID` | HTTP header for tenant ID |
| `enabled` | bool | `true` | Enable tenant context extraction |
| `required` | bool | `true` | Require tenant ID on all requests |
| `exempt_paths` | list | `/health,/metrics,...` | Paths exempt from tenant requirement |
| `fail_open` | bool | `false` | Allow requests without tenant ID |

### K8sConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `namespace_prefix` | str | `tenant-` | Prefix for tenant namespaces |
| `default_cpu_quota` | str | `2` | Default CPU quota |
| `default_memory_quota` | str | `4Gi` | Default memory quota |
| `default_storage_quota` | str | `20Gi` | Default storage quota |
| `default_max_pods` | int | `50` | Default max pods |
| `retry_attempts` | int | `3` | K8s API retry attempts |
| `fail_safe` | bool | `true` | Continue when K8s unavailable |

### AuditLogConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `audit_enabled` | bool | `true` | Enable audit logging |
| `use_redis` | bool | `false` | Use Redis backend |
| `retention_days` | int | `90` | Days to retain logs |
| `enable_redaction` | bool | `true` | Redact sensitive fields |
| `max_entries_per_tenant` | int | `100000` | Max entries per tenant |

---

**Constitutional Hash:** `cdd01ef066bc6cf2` - All multi-tenant deployments must validate against this hash.
