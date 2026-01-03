# ACGS-2 Tenant Management Service

**Constitutional Hash:** `cdd01ef066bc6cf2`

A dedicated service for multi-tenant isolation, resource management, and access control in the ACGS-2 AI Constitutional Governance Platform.

## Overview

The Tenant Management Service provides comprehensive multi-tenant capabilities:

- **Tenant Lifecycle Management**: Create, activate, suspend, and delete tenants
- **Resource Quotas**: Per-tenant resource limits and usage tracking
- **Access Control**: Granular permissions and role-based access
- **Audit Trails**: Tenant-specific audit logging and compliance
- **Service Isolation**: Complete data and operational separation

## Architecture

```
ACGS-2 Multi-Tenant Architecture
├── Tenant Management Service (Port 8500)
│   ├── Tenant CRUD Operations
│   ├── Resource Quota Management
│   ├── Access Control Policies
│   └── Audit Logging
├── Tenant Isolation Middleware
│   ├── Request Routing
│   ├── Quota Enforcement
│   └── Access Validation
└── Service Integration
    ├── API Gateway (Tenant Header Injection)
    ├── All Services (Tenant Context)
    └── CLI Tools (Tenant Commands)
```

## API Endpoints

### Tenant Management

```http
POST   /api/v1/tenants/                    # Create tenant
GET    /api/v1/tenants/                    # List tenants
GET    /api/v1/tenants/{tenant_id}         # Get tenant details
PUT    /api/v1/tenants/{tenant_id}         # Update tenant
POST   /api/v1/tenants/{tenant_id}/activate  # Activate tenant
POST   /api/v1/tenants/{tenant_id}/suspend   # Suspend tenant
DELETE /api/v1/tenants/{tenant_id}         # Delete tenant
```

### Resource Quotas

```http
GET    /api/v1/tenants/{tenant_id}/quotas/check     # Check quota
POST   /api/v1/tenants/{tenant_id}/quotas/consume   # Consume quota
GET    /api/v1/tenants/{tenant_id}/usage            # Get usage metrics
```

### Access Control

```http
GET    /api/v1/tenants/{tenant_id}/access/check     # Check access
POST   /api/v1/tenants/{tenant_id}/access/grant     # Grant access
```

## Service Tiers

| Tier | Users | Policies | Models | Approvals/Month | API Calls/Hour | Storage |
|------|-------|----------|--------|-----------------|----------------|---------|
| Free | 5 | 10 | 3 | 100 | 1,000 | 1GB |
| Professional | 50 | 100 | 20 | 1,000 | 10,000 | 10GB |
| Enterprise | 500 | 1,000 | 100 | 10,000 | 100,000 | 100GB |
| Enterprise+ | 5,000 | 10,000 | 1,000 | 100,000 | 1,000,000 | 1TB |

## Usage Examples

### Creating a Tenant

```python
from acgs2_sdk import create_client, ACGS2Config

config = ACGS2Config(base_url="http://localhost:8500")
async with create_client(config) as client:
    tenant = await client.post("/api/v1/tenants/", json={
        "name": "acme-corp",
        "displayName": "ACME Corporation",
        "contactEmail": "admin@acme.com",
        "tier": "enterprise",
        "createdBy": "platform-admin-001"
    })
    print(f"Created tenant: {tenant['id']}")
```

### CLI Usage

```bash
# Create tenant
acgs2-cli tenant create \
  --name acme-corp \
  --display-name "ACME Corporation" \
  --contact-email admin@acme.com \
  --tier enterprise \
  --created-by platform-admin-001

# List tenants
acgs2-cli tenant list --status active

# Show tenant details
acgs2-cli tenant show tenant-123

# Check resource quota
acgs2-cli tenant quota-check tenant-123 --resource policies --amount 5

# Activate tenant
acgs2-cli tenant activate tenant-123 --activated-by platform-admin-001
```

## Integration with Other Services

### API Gateway Integration

The API Gateway automatically injects tenant context:

```yaml
# Request Flow
Client Request → API Gateway (adds X-Tenant-ID) → Service → Tenant Middleware → Business Logic
```

### Service Integration

Services integrate tenant isolation:

```python
from tenant_middleware import TenantIsolationMiddleware, get_tenant_context

app = FastAPI()
app.add_middleware(TenantIsolationMiddleware)

@app.post("/api/v1/policies/")
async def create_policy(
    request: CreatePolicyRequest,
    tenant_ctx: dict = Depends(get_tenant_context)
):
    tenant_id = tenant_ctx["tenant_id"]
    # Policy automatically scoped to tenant
```

### Required Headers

All API requests must include:

```
X-Tenant-ID: tenant-uuid          # Required: Tenant identifier
X-User-ID: user-uuid             # Optional: User identifier for access control
Authorization: Bearer <token>    # Optional: Authentication token
```

## Security Model

### Tenant Isolation
- Complete data separation between tenants
- Shared-nothing architecture
- Cryptographic tenant identification

### Access Control
- Role-based permissions (admin, editor, viewer)
- Resource-specific access policies
- Platform admin override capabilities

### Audit Compliance
- All tenant operations logged
- GDPR and SOX compliance support
- Tamper-proof audit trails

## Deployment

### Docker

```bash
# Build service
docker build -t acgs2/tenant-management .

# Run service
docker run -p 8500:8500 acgs2/tenant-management
```

### Docker Compose

```yaml
services:
  tenant-management:
    build: ./services/tenant_management
    ports:
      - "8500:8500"
    environment:
      - ENVIRONMENT=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8500/health"]
```

## Configuration

### Environment Variables

```bash
# Service Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database Configuration (for production)
DATABASE_URL=postgresql://user:pass@localhost/tenant_db

# Redis Configuration (for caching)
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
PLATFORM_ADMIN_PREFIX=platform-admin-
```

## Monitoring

### Health Checks

```bash
curl http://localhost:8500/health
```

### Metrics Endpoints

```bash
# Prometheus metrics
curl http://localhost:8500/metrics
```

### Logging

All tenant operations are logged with structured JSON:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "tenant_id": "tenant-123",
  "user_id": "user-456",
  "action": "create_policy",
  "resource_type": "policy",
  "resource_id": "policy-789",
  "details": {"policy_name": "data-privacy"}
}
```

## Compliance

### GDPR Compliance
- Data residency controls
- Right to erasure implementation
- Audit trail retention policies

### SOX Compliance
- Immutable audit trails
- Access control logging
- Change management tracking

### SOC 2 Compliance
- Security monitoring
- Access control validation
- Incident response procedures

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run service locally
python src/main.py

# Run with auto-reload
uvicorn src.main:app --reload
```

## Constitutional Compliance

All tenant operations are constitutionally compliant with hash `cdd01ef066bc6cf2`. The service includes:

- **Immutable Audit Trails**: All tenant operations are cryptographically signed
- **Access Control Validation**: Constitutional principles enforced on all access decisions
- **Resource Quota Governance**: Fair resource allocation per constitutional guidelines
- **Data Sovereignty**: Tenant data isolation and residency controls

## Support

- **API Documentation**: http://localhost:8500/docs
- **Health Endpoint**: http://localhost:8500/health
- **Logs**: Structured JSON logging to stdout
- **Metrics**: Prometheus-compatible metrics endpoint

**Constitutional Hash:** `cdd01ef066bc6cf2`
