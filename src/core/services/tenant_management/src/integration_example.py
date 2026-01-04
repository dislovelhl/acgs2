"""
ACGS-2 Tenant Integration Example
Constitutional Hash: cdd01ef066bc6cf2

Example showing how to integrate tenant isolation into existing services.
"""

# Example: Integrating tenant isolation into Policy Service

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel


# Mock services and functions for example
class PolicyService:
    async def list(self, tenant_filter=None, skip=0, limit=100):
        return []

    async def create(self, policy_data):
        return {"id": "policy-123", **policy_data}

    async def get(self, policy_id):
        return {"id": policy_id}


def create_tenant_filter(tenant_id: str):
    return {"tenant_id": tenant_id}


async def get_current_tenant():
    return {"tenant_id": "tenant-123", "user_id": "user-456"}


async def validate_tenant_operation(tenant_id, user_id, resource, action):
    pass


def inject_tenant_id(data, tenant_id):
    data["tenant_id"] = tenant_id
    return data


class Policy(BaseModel):
    id: str
    tenant_id: str
    name: str
    content: str
    created_at: datetime
    updated_at: datetime


class CreatePolicyRequest(BaseModel):
    name: str
    content: str


"""
# 1. Update service main.py to include tenant middleware

from fastapi import FastAPI
from src.core.shared.tenant_integration import TenantMiddleware

app = FastAPI()
app.add_middleware(TenantMiddleware)

# 2. Update API endpoints to use tenant context

from src.core.shared.tenant_integration import get_current_tenant, validate_tenant_operation

@app.post("/api/v1/policies/")
async def create_policy(
    request: CreatePolicyRequest,
    tenant_ctx = Depends(get_current_tenant)
):
    tenant_id = tenant_ctx["tenant_id"]
    user_id = tenant_ctx["user_id"]

    # Validate tenant permissions and quotas
    await validate_tenant_operation(tenant_id, user_id, "policy", "create")

    # Create policy with tenant scope
    policy_data = inject_tenant_id(request.dict(), tenant_id)
    policy = await policy_service.create(policy_data)

    return policy

# 3. Update database queries to include tenant filtering

def get_policies_for_tenant(tenant_id: str):
    return Policy.find(create_tenant_filter(tenant_id))

# 4. Update CLI to include tenant context

@policy.command("create")
@click.option("--tenant-id", required=True, help="Tenant ID")
@click.option("--user-id", help="User ID for access control")
@click.pass_context
def create_policy(ctx, tenant_id, user_id, name, rules_file):
    # CLI automatically includes tenant context in requests
    headers = {"X-Tenant-ID": tenant_id}
    if user_id:
        headers["X-User-ID"] = user_id

    # Make request with tenant context
    response = requests.post(
        f"{ctx.obj['base_url']}/api/v1/policies/",
        json={"name": name, "rules": rules},
        headers=headers
    )

# 5. Update docker-compose to include tenant service dependency

services:
  policy-registry:
    depends_on:
      tenant-management:
        condition: service_healthy
    environment:
      - TENANT_SERVICE_URL=http://tenant-management:8500

# 6. Update health checks to validate tenant integration

@app.get("/health")
async def health_check():
    # Check tenant service connectivity
    try:
        tenant_client = get_tenant_client()
        await tenant_client.get_tenant("health-check")
        tenant_status = "healthy"
    except Exception:
        tenant_status = "unhealthy"

    return {
        "status": "healthy" if tenant_status == "healthy" else "degraded",
        "services": {
            "tenant_management": tenant_status
        },
        "constitutional_hash": "cdd01ef066bc6cf2"
    }
"""

# Example FastAPI router with tenant integration
from fastapi import HTTPException

from src.core.shared.tenant_integration import (
    get_current_tenant,
    inject_tenant_id,
    validate_tenant_operation,
)

router = APIRouter()

# Mock policy service instance
policy_service = PolicyService()


@router.get("/policies/")
async def list_policies(tenant_ctx=Depends(get_current_tenant), skip: int = 0, limit: int = 100):
    """List policies for tenant"""
    tenant_id = tenant_ctx["tenant_id"]

    # Get policies scoped to tenant
    policies = await policy_service.list(
        tenant_filter=create_tenant_filter(tenant_id), skip=skip, limit=limit
    )

    return {"policies": policies, "total": len(policies)}


@router.post("/policies/")
async def create_policy(request: CreatePolicyRequest, tenant_ctx=Depends(get_current_tenant)):
    """Create policy with tenant isolation"""
    tenant_id = tenant_ctx["tenant_id"]
    user_id = tenant_ctx["user_id"]

    # Validate permissions and quotas
    await validate_tenant_operation(tenant_id, user_id, "policy", "create")

    # Inject tenant context
    policy_data = inject_tenant_id(request.dict(), tenant_id)

    # Create policy
    policy = await policy_service.create(policy_data)

    return policy


@router.get("/policies/{policy_id}")
async def get_policy(policy_id: str, tenant_ctx=Depends(get_current_tenant)):
    """Get policy with tenant validation"""
    tenant_id = tenant_ctx["tenant_id"]

    # Get policy scoped to tenant
    policy = await policy_service.get(policy_id)

    # Validate tenant ownership
    if policy.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=404, detail="Policy not found")

    return policy


# Example database model with tenant field
from pydantic import BaseModel


class Policy(BaseModel):
    id: str
    tenant_id: str  # Tenant isolation field
    name: str
    rules: list
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Example database query with tenant filtering
def get_policies_by_tenant(tenant_id: str, status: str = None):
    query = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    return Policy.find(query)


def create_policy_with_tenant(data: dict, tenant_id: str):
    policy_data = data.copy()
    policy_data["tenant_id"] = tenant_id
    policy_data["created_at"] = datetime.utcnow()
    policy_data["updated_at"] = datetime.utcnow()

    policy = Policy(**policy_data)
    policy.save()
    return policy


# Example middleware integration for other frameworks
class TenantIsolationMiddleware:
    """Generic middleware for tenant isolation"""

    def __init__(self, tenant_service_url: str):
        self.tenant_service_url = tenant_service_url

    def process_request(self, request):
        """Process incoming request"""
        tenant_id = request.headers.get("X-Tenant-ID")
        user_id = request.headers.get("X-User-ID")

        if not tenant_id:
            raise ValueError("Missing X-Tenant-ID header")

        # Validate tenant
        tenant_info = self._validate_tenant(tenant_id)

        # Add to request context
        request.tenant_id = tenant_id
        request.tenant_info = tenant_info
        request.user_id = user_id

    def _validate_tenant(self, tenant_id: str) -> dict:
        """Validate tenant exists and is active"""
        # Implementation would call tenant service
        return {"id": tenant_id, "status": "active", "tier": "enterprise"}
