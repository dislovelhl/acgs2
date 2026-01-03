"""
ACGS-2 Tenant Management Service
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import (
    CreateTenantRequest,
    Tenant,
    TenantAccessPolicy,
    TenantAuditEvent,
    TenantResourceQuota,
    TenantStatus,
    TenantTier,
    TenantUsageMetrics,
    UpdateTenantRequest,
)

logger = logging.getLogger(__name__)


class TenantManagementService:
    """Core service for tenant management and multi-tenant isolation"""

    def __init__(self, storage_backend=None, audit_backend=None):
        """
        Initialize tenant management service

        Args:
            storage_backend: Storage backend for tenant data persistence
            audit_backend: Audit backend for tenant-specific audit logging
        """
        self.storage = storage_backend or InMemoryTenantStorage()
        self.audit = audit_backend or InMemoryAuditBackend()
        self._quotas_enabled = True
        self._access_control_enabled = True

    async def create_tenant(self, request: CreateTenantRequest, created_by_user: str) -> Tenant:
        """Create a new tenant with default quotas and settings"""

        # Set default quotas based on tier
        quotas = self._get_default_quotas(request.tier)

        tenant = Tenant(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            contact_email=request.contact_email,
            contact_name=request.contact_name,
            contact_phone=request.contact_phone,
            organization_name=request.organization_name,
            organization_size=request.organization_size,
            industry=request.industry,
            tier=request.tier,
            status=TenantStatus.PENDING,  # Requires admin activation
            data_residency=request.data_residency,
            compliance_requirements=request.compliance_requirements,
            created_by=created_by_user,
            owned_by=request.owned_by,
            admin_users=[created_by_user],  # Creator is initial admin
            **quotas,
        )

        # Validate tenant data
        await self._validate_tenant_creation(tenant)

        # Store tenant
        await self.storage.save_tenant(tenant)

        # Initialize default quotas
        await self._initialize_tenant_quotas(tenant.id, quotas)

        # Initialize default access policies
        await self._initialize_tenant_access_policies(tenant.id, created_by_user)

        # Audit the creation
        await self.audit.log_event(
            TenantAuditEvent(
                tenant_id=tenant.id,
                event_type="tenant_management",
                action="create",
                resource_type="tenant",
                resource_id=tenant.id,
                user_id=created_by_user,
                details={"tier": request.tier, "status": TenantStatus.PENDING},
            )
        )

        logger.info(f"Tenant created: {tenant.id} ({tenant.name}) by user {created_by_user}")
        return tenant

    async def get_tenant(self, tenant_id: str, requesting_user: Optional[str] = None) -> Tenant:
        """Get tenant by ID with access control"""

        tenant = await self.storage.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        # Check access control if enabled
        if self._access_control_enabled and requesting_user:
            await self._check_tenant_access(tenant_id, requesting_user, "read")

        return tenant

    async def update_tenant(
        self, tenant_id: str, request: UpdateTenantRequest, updated_by_user: str
    ) -> Tenant:
        """Update tenant information"""

        tenant = await self.get_tenant(tenant_id, updated_by_user)

        # Check admin permissions
        await self._check_tenant_admin_access(tenant_id, updated_by_user)

        # Update fields
        update_data = request.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in update_data.items():
            if hasattr(tenant, field):
                setattr(tenant, field, value)

        tenant.updated_at = datetime.utcnow()

        # Validate updated tenant
        await self._validate_tenant_update(tenant)

        # Store updated tenant
        await self.storage.save_tenant(tenant)

        # Audit the update
        await self.audit.log_event(
            TenantAuditEvent(
                tenant_id=tenant_id,
                event_type="tenant_management",
                action="update",
                resource_type="tenant",
                resource_id=tenant_id,
                user_id=updated_by_user,
                details=update_data,
            )
        )

        logger.info(f"Tenant updated: {tenant_id} by user {updated_by_user}")
        return tenant

    async def activate_tenant(self, tenant_id: str, activated_by_user: str) -> Tenant:
        """Activate a pending tenant"""

        tenant = await self.get_tenant(tenant_id, activated_by_user)

        # Only platform admins can activate tenants
        await self._check_platform_admin_access(activated_by_user)

        if tenant.status != TenantStatus.PENDING:
            raise InvalidTenantOperationError(f"Cannot activate tenant with status {tenant.status}")

        tenant.status = TenantStatus.ACTIVE
        tenant.activated_at = datetime.utcnow()
        tenant.updated_at = datetime.utcnow()

        await self.storage.save_tenant(tenant)

        # Audit activation
        await self.audit.log_event(
            TenantAuditEvent(
                tenant_id=tenant_id,
                event_type="tenant_management",
                action="activate",
                resource_type="tenant",
                resource_id=tenant_id,
                user_id=activated_by_user,
                details={
                    "previous_status": TenantStatus.PENDING,
                    "new_status": TenantStatus.ACTIVE,
                },
            )
        )

        logger.info(f"Tenant activated: {tenant_id} by user {activated_by_user}")
        return tenant

    async def suspend_tenant(self, tenant_id: str, reason: str, suspended_by_user: str) -> Tenant:
        """Suspend a tenant"""

        tenant = await self.get_tenant(tenant_id, suspended_by_user)

        # Only platform admins can suspend tenants
        await self._check_platform_admin_access(suspended_by_user)

        if tenant.status != TenantStatus.ACTIVE:
            raise InvalidTenantOperationError(f"Cannot suspend tenant with status {tenant.status}")

        tenant.status = TenantStatus.SUSPENDED
        tenant.suspended_at = datetime.utcnow()
        tenant.updated_at = datetime.utcnow()

        await self.storage.save_tenant(tenant)

        # Audit suspension
        await self.audit.log_event(
            TenantAuditEvent(
                tenant_id=tenant_id,
                event_type="tenant_management",
                action="suspend",
                resource_type="tenant",
                resource_id=tenant_id,
                user_id=suspended_by_user,
                details={"reason": reason, "previous_status": TenantStatus.ACTIVE},
            )
        )

        logger.info(f"Tenant suspended: {tenant_id} by user {suspended_by_user}")
        return tenant

    async def list_tenants(
        self, filters: Optional[Dict[str, Any]] = None, requesting_user: Optional[str] = None
    ) -> List[Tenant]:
        """List tenants with optional filtering"""

        # Platform admins can see all tenants, others see only their own
        if not await self._is_platform_admin(requesting_user):
            if requesting_user:
                # Get user's tenant and return only that
                user_tenant = await self.storage.get_tenant_by_user(requesting_user)
                return [user_tenant] if user_tenant else []
            else:
                return []

        tenants = await self.storage.list_tenants(filters or {})
        return tenants

    async def delete_tenant(self, tenant_id: str, deleted_by_user: str) -> None:
        """Delete a tenant (soft delete by deactivating)"""

        tenant = await self.get_tenant(tenant_id, deleted_by_user)

        # Only platform admins can delete tenants
        await self._check_platform_admin_access(deleted_by_user)

        # Mark as deactivated instead of hard delete
        tenant.status = TenantStatus.DEACTIVATED
        tenant.updated_at = datetime.utcnow()

        await self.storage.save_tenant(tenant)

        # Audit deletion
        await self.audit.log_event(
            TenantAuditEvent(
                tenant_id=tenant_id,
                event_type="tenant_management",
                action="delete",
                resource_type="tenant",
                resource_id=tenant_id,
                user_id=deleted_by_user,
                details={"previous_status": tenant.status},
            )
        )

        logger.info(f"Tenant deactivated: {tenant_id} by user {deleted_by_user}")

    # Resource Quota Management
    async def check_resource_quota(
        self, tenant_id: str, resource_type: str, requested_amount: int = 1
    ) -> bool:
        """Check if tenant has quota for requested resource"""

        if not self._quotas_enabled:
            return True

        quota = await self.storage.get_tenant_quota(tenant_id, resource_type)
        if not quota:
            return True  # No quota set, allow

        return (quota.current_usage + requested_amount) <= quota.limit

    async def consume_resource_quota(
        self, tenant_id: str, resource_type: str, amount: int = 1
    ) -> None:
        """Consume resource quota"""

        if not self._quotas_enabled:
            return

        quota = await self.storage.get_tenant_quota(tenant_id, resource_type)
        if quota:
            quota.current_usage += amount
            await self.storage.save_tenant_quota(quota)

            # Check if quota exceeded (log warning)
            if quota.current_usage > quota.limit:
                logger.warning(
                    f"Tenant {tenant_id} exceeded {resource_type} quota: "
                    f"{quota.current_usage}/{quota.limit}"
                )

    async def get_tenant_usage(self, tenant_id: str) -> TenantUsageMetrics:
        """Get tenant usage metrics"""

        tenant = await self.get_tenant(tenant_id)
        quotas = await self.storage.get_tenant_quotas(tenant_id)

        # Calculate utilization percentages
        user_utilization = (
            (tenant.current_users / tenant.max_users) * 100 if tenant.max_users > 0 else 0
        )
        policy_utilization = (
            (tenant.current_policies / tenant.max_policies) * 100 if tenant.max_policies > 0 else 0
        )
        model_utilization = (
            (tenant.current_models / tenant.max_models) * 100 if tenant.max_models > 0 else 0
        )
        approval_utilization = (tenant.approvals_this_month / tenant.max_approvals_per_month) * 100
        storage_utilization = (tenant.storage_used_gb / tenant.storage_limit_gb) * 100

        return TenantUsageMetrics(
            tenant_id=tenant_id,
            period_start=datetime.utcnow() - timedelta(days=30),
            period_end=datetime.utcnow(),
            total_users=tenant.current_users,
            total_policies=tenant.current_policies,
            total_models=tenant.current_models,
            total_approvals=tenant.approvals_this_month,
            user_utilization=user_utilization,
            policy_utilization=policy_utilization,
            model_utilization=model_utilization,
            approval_utilization=approval_utilization,
            storage_utilization=storage_utilization,
        )

    # Access Control
    async def check_resource_access(
        self,
        tenant_id: str,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str],
        required_permission: str,
    ) -> bool:
        """Check if user has access to specific resource"""

        if not self._access_control_enabled:
            return True

        # Check tenant membership
        tenant = await self.get_tenant(tenant_id)
        if user_id not in tenant.admin_users:
            # Check specific resource permissions
            policy = await self.storage.get_access_policy(
                tenant_id, user_id, resource_type, resource_id
            )
            if not policy:
                return False

            return required_permission in policy.permissions

        return True  # Admins have all permissions

    async def grant_resource_access(
        self,
        tenant_id: str,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str],
        role: str,
        permissions: List[str],
        granted_by: str,
    ) -> TenantAccessPolicy:
        """Grant access to a resource"""

        # Check if granter has permission to grant access
        await self._check_tenant_admin_access(tenant_id, granted_by)

        policy = TenantAccessPolicy(
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            role=role,
            permissions=permissions,
            granted_by=granted_by,
        )

        await self.storage.save_access_policy(policy)

        # Audit access grant
        await self.audit.log_event(
            TenantAuditEvent(
                tenant_id=tenant_id,
                event_type="access_control",
                action="grant",
                resource_type=resource_type,
                resource_id=resource_id or "all",
                user_id=granted_by,
                details={"target_user": user_id, "role": role, "permissions": permissions},
            )
        )

        return policy

    # Private helper methods
    def _get_default_quotas(self, tier: TenantTier) -> Dict[str, Any]:
        """Get default quotas based on tenant tier"""

        quota_configs = {
            TenantTier.FREE: {
                "max_users": 5,
                "max_policies": 10,
                "max_models": 3,
                "max_approvals_per_month": 100,
                "max_api_calls_per_hour": 1000,
                "storage_limit_gb": 1.0,
            },
            TenantTier.PROFESSIONAL: {
                "max_users": 50,
                "max_policies": 100,
                "max_models": 20,
                "max_approvals_per_month": 1000,
                "max_api_calls_per_hour": 10000,
                "storage_limit_gb": 10.0,
            },
            TenantTier.ENTERPRISE: {
                "max_users": 500,
                "max_policies": 1000,
                "max_models": 100,
                "max_approvals_per_month": 10000,
                "max_api_calls_per_hour": 100000,
                "storage_limit_gb": 100.0,
            },
            TenantTier.ENTERPRISE_PLUS: {
                "max_users": 5000,
                "max_policies": 10000,
                "max_models": 1000,
                "max_approvals_per_month": 100000,
                "max_api_calls_per_hour": 1000000,
                "storage_limit_gb": 1000.0,
            },
        }

        return quota_configs.get(tier, quota_configs[TenantTier.FREE])

    async def _validate_tenant_creation(self, tenant: Tenant) -> None:
        """Validate tenant creation data"""

        # Check for duplicate names
        existing = await self.storage.get_tenant_by_name(tenant.name)
        if existing:
            raise DuplicateTenantError(f"Tenant name '{tenant.name}' already exists")

        # Validate compliance requirements
        valid_compliance = ["SOC2", "GDPR", "HIPAA", "ISO27001", "PCI-DSS"]
        for req in tenant.compliance_requirements:
            if req not in valid_compliance:
                raise InvalidComplianceRequirementError(f"Invalid compliance requirement: {req}")

    async def _validate_tenant_update(self, tenant: Tenant) -> None:
        """Validate tenant update data"""

        # Prevent status changes that violate business rules
        if tenant.status == TenantStatus.DEACTIVATED and tenant.activated_at:
            raise InvalidTenantOperationError("Cannot reactivate a deactivated tenant")

    async def _initialize_tenant_quotas(self, tenant_id: str, quotas: Dict[str, Any]) -> None:
        """Initialize default quotas for new tenant"""

        quota_mappings = {
            "max_users": "users",
            "max_policies": "policies",
            "max_models": "models",
            "max_approvals_per_month": "approvals",
            "max_api_calls_per_hour": "api_calls",
            "storage_limit_gb": "storage",
        }

        for quota_field, resource_type in quota_mappings.items():
            if quota_field in quotas:
                quota = TenantResourceQuota(
                    tenant_id=tenant_id,
                    resource_type=resource_type,
                    limit=quotas[quota_field],
                    current_usage=0,
                )
                await self.storage.save_tenant_quota(quota)

    async def _initialize_tenant_access_policies(self, tenant_id: str, admin_user: str) -> None:
        """Initialize default access policies for new tenant"""

        # Admin has access to all resources
        admin_policy = TenantAccessPolicy(
            tenant_id=tenant_id,
            resource_type="*",  # All resources
            user_id=admin_user,
            role="admin",
            permissions=["read", "write", "delete", "execute", "admin"],
            granted_by=admin_user,
        )
        await self.storage.save_access_policy(admin_policy)

    async def _check_tenant_access(self, tenant_id: str, user_id: str, permission: str) -> None:
        """Check if user has access to tenant"""

        tenant = await self.storage.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        if user_id not in tenant.admin_users:
            raise AccessDeniedError(f"User {user_id} does not have access to tenant {tenant_id}")

    async def _check_tenant_admin_access(self, tenant_id: str, user_id: str) -> None:
        """Check if user has admin access to tenant"""

        tenant = await self.storage.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        if user_id not in tenant.admin_users:
            raise AccessDeniedError(
                f"User {user_id} does not have admin access to tenant {tenant_id}"
            )

    async def _check_platform_admin_access(self, user_id: str) -> None:
        """Check if user has platform admin access"""

        # This would typically check against a platform admin role/user list
        # For now, we'll assume platform admins have special user IDs or roles
        if not user_id or not user_id.startswith("platform-admin-"):
            raise AccessDeniedError(f"User {user_id} does not have platform admin access")

    async def _is_platform_admin(self, user_id: Optional[str]) -> bool:
        """Check if user is a platform admin"""

        return user_id is not None and user_id.startswith("platform-admin-")


# Storage backends (simplified in-memory implementations)
class InMemoryTenantStorage:
    """Simple in-memory storage for tenant data"""

    def __init__(self):
        self.tenants: Dict[str, Tenant] = {}
        self.quotas: Dict[str, List[TenantResourceQuota]] = {}
        self.access_policies: Dict[str, List[TenantAccessPolicy]] = {}
        self.user_tenant_map: Dict[str, str] = {}

    async def save_tenant(self, tenant: Tenant) -> None:
        self.tenants[tenant.id] = tenant
        # Update user-tenant mapping for admin users
        for admin_user in tenant.admin_users:
            self.user_tenant_map[admin_user] = tenant.id

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self.tenants.get(tenant_id)

    async def get_tenant_by_name(self, name: str) -> Optional[Tenant]:
        for tenant in self.tenants.values():
            if tenant.name == name:
                return tenant
        return None

    async def get_tenant_by_user(self, user_id: str) -> Optional[Tenant]:
        tenant_id = self.user_tenant_map.get(user_id)
        return self.tenants.get(tenant_id) if tenant_id else None

    async def list_tenants(self, filters: Dict[str, Any]) -> List[Tenant]:
        tenants = list(self.tenants.values())

        # Apply filters
        if "status" in filters:
            tenants = [t for t in tenants if t.status == filters["status"]]
        if "tier" in filters:
            tenants = [t for t in tenants if t.tier == filters["tier"]]

        return tenants

    async def save_tenant_quota(self, quota: TenantResourceQuota) -> None:
        if quota.tenant_id not in self.quotas:
            self.quotas[quota.tenant_id] = []
        self.quotas[quota.tenant_id].append(quota)

    async def get_tenant_quota(
        self, tenant_id: str, resource_type: str
    ) -> Optional[TenantResourceQuota]:
        tenant_quotas = self.quotas.get(tenant_id, [])
        for quota in tenant_quotas:
            if quota.resource_type == resource_type:
                return quota
        return None

    async def get_tenant_quotas(self, tenant_id: str) -> List[TenantResourceQuota]:
        return self.quotas.get(tenant_id, [])

    async def save_access_policy(self, policy: TenantAccessPolicy) -> None:
        if policy.tenant_id not in self.access_policies:
            self.access_policies[policy.tenant_id] = []
        self.access_policies[policy.tenant_id].append(policy)

    async def get_access_policy(
        self, tenant_id: str, user_id: str, resource_type: str, resource_id: Optional[str]
    ) -> Optional[TenantAccessPolicy]:
        tenant_policies = self.access_policies.get(tenant_id, [])
        for policy in tenant_policies:
            if (
                policy.user_id == user_id
                and policy.resource_type in [resource_type, "*"]
                and (policy.resource_id == resource_id or policy.resource_id is None)
            ):
                return policy
        return None


class InMemoryAuditBackend:
    """Simple in-memory audit logging"""

    def __init__(self):
        self.events: List[TenantAuditEvent] = []

    async def log_event(self, event: TenantAuditEvent) -> None:
        self.events.append(event)
        logger.info(
            f"Audit: {event.tenant_id} {event.action} {event.resource_type}:{event.resource_id} by {event.user_id}"
        )


# Custom exceptions
class TenantNotFoundError(Exception):
    pass


class DuplicateTenantError(Exception):
    pass


class InvalidTenantOperationError(Exception):
    pass


class AccessDeniedError(Exception):
    pass


class InvalidComplianceRequirementError(Exception):
    pass
