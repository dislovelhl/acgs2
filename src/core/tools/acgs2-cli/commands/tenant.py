"""
ACGS-2 CLI - Tenant Management Commands
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import sys

import click
from acgs2_sdk import create_client


@click.group()
@click.pass_context
def tenant(ctx):
    """Tenant management commands"""
    pass


@tenant.command("create")
@click.option("--name", required=True, help="Tenant name (unique identifier)")
@click.option("--display-name", required=True, help="Human-readable display name")
@click.option("--contact-email", required=True, help="Contact email address")
@click.option("--contact-name", help="Contact person name")
@click.option("--contact-phone", help="Contact phone number")
@click.option("--organization", help="Organization name")
@click.option("--org-size", help="Organization size (1-10, 11-50, 51-200, 201-1000, 1000+)")
@click.option("--industry", help="Industry sector")
@click.option(
    "--tier",
    type=click.Choice(["free", "professional", "enterprise", "enterprise_plus"]),
    default="free",
    help="Service tier",
)
@click.option("--data-residency", help="Data residency region")
@click.option("--compliance", help="Comma-separated compliance requirements (SOC2,GDPR,HIPAA)")
@click.option("--created-by", required=True, help="User ID creating the tenant")
@click.option("--owned-by", help="Organization/user that owns the tenant")
@click.pass_context
def create_tenant(
    ctx,
    name: str,
    display_name: str,
    contact_email: str,
    contact_name: str | None,
    contact_phone: str | None,
    organization: str | None,
    org_size: str | None,
    industry: str | None,
    tier: str,
    data_residency: str | None,
    compliance: str | None,
    created_by: str,
    owned_by: str | None,
):
    """Create a new tenant"""

    async def create():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                tenant_data = {
                    "name": name,
                    "display_name": display_name,
                    "contact_email": contact_email,
                    "tier": tier,
                    "created_by": created_by,
                }

                # Add optional fields
                if contact_name:
                    tenant_data["contact_name"] = contact_name
                if contact_phone:
                    tenant_data["contact_phone"] = contact_phone
                if organization:
                    tenant_data["organization_name"] = organization
                if org_size:
                    tenant_data["organization_size"] = org_size
                if industry:
                    tenant_data["industry"] = industry
                if data_residency:
                    tenant_data["data_residency"] = data_residency
                if compliance:
                    tenant_data["compliance_requirements"] = [
                        req.strip() for req in compliance.split(",")
                    ]
                if owned_by:
                    tenant_data["owned_by"] = owned_by

                # Call tenant management API
                response = await client.post("/api/v1/tenants/", json=tenant_data)
                tenant = response.data

                click.secho("🏢 Tenant created successfully!", fg="green")
                click.echo(f"ID: {tenant['id']}")
                click.echo(f"Name: {tenant['name']}")
                click.echo(f"Display Name: {tenant['displayName']}")
                click.echo(f"Status: {tenant['status']}")
                click.echo(f"Tier: {tenant['tier']}")
                click.echo(f"Created: {tenant['createdAt']}")

        except Exception as e:
            click.secho(f"❌ Failed to create tenant: {e}", fg="red")
            sys.exit(1)

    asyncio.run(create())


@tenant.command("list")
@click.option("--status", help="Filter by status")
@click.option("--tier", help="Filter by tier")
@click.option("--limit", type=int, default=20, help="Number of results to show")
@click.pass_context
def list_tenants(ctx, status: str | None, tier: str | None, limit: int):
    """List tenants"""

    async def list():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                params = {"page_size": limit}
                if status:
                    params["status"] = status
                if tier:
                    params["tier"] = tier

                response = await client.get("/api/v1/tenants/", params=params)
                data = response.data

                click.secho(f"🏢 Tenants ({data['total']})", fg="blue", bold=True)

                if not data["tenants"]:
                    click.echo("No tenants found.")
                    return

                for tenant in data["tenants"]:
                    status_color = {
                        "active": "green",
                        "suspended": "yellow",
                        "pending": "blue",
                        "deactivated": "red",
                    }.get(tenant["status"], "white")

                    click.secho(f"• {tenant['id']}", fg=status_color, nl=False)
                    click.echo(
                        f" | {tenant['name']} | {tenant['displayName']} | {tenant['tier']} | {tenant['status']}"
                    )

        except Exception as e:
            click.secho(f"❌ Failed to list tenants: {e}", fg="red")
            sys.exit(1)

    asyncio.run(list())


@tenant.command("show")
@click.argument("tenant_id")
@click.pass_context
def show_tenant(ctx, tenant_id: str):
    """Show tenant details"""

    async def show():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                response = await client.get(f"/api/v1/tenants/{tenant_id}")
                tenant = response.data

                click.secho(f"🏢 Tenant: {tenant['displayName']}", fg="blue", bold=True)
                click.echo(f"ID: {tenant['id']}")
                click.echo(f"Name: {tenant['name']}")
                click.echo(f"Status: {tenant['status']}")
                click.echo(f"Tier: {tenant['tier']}")
                click.echo(
                    f"Contact: {tenant.get('contactName', 'N/A')} <{tenant['contactEmail']}>"
                )

                if tenant.get("organizationName"):
                    click.echo(f"Organization: {tenant['organizationName']}")
                if tenant.get("industry"):
                    click.echo(f"Industry: {tenant['industry']}")

                click.echo(f"Created: {tenant['createdAt']}")
                if tenant.get("activatedAt"):
                    click.echo(f"Activated: {tenant['activatedAt']}")

                # Show quotas
                click.echo("\n📊 Resource Quotas:")
                click.echo(f"  Users: {tenant['currentUsers']}/{tenant['maxUsers']}")
                click.echo(f"  Policies: {tenant['currentPolicies']}/{tenant['maxPolicies']}")
                click.echo(f"  Models: {tenant['currentModels']}/{tenant['maxModels']}")
                click.echo(
                    f"  Approvals/Month: {tenant['approvalsThisMonth']}/{tenant['maxApprovalsPerMonth']}"
                )
                click.echo(
                    f"  Storage: {tenant['storageUsedGb']:.2f}/{tenant['storageLimitGb']} GB"
                )

        except Exception as e:
            click.secho(f"❌ Failed to get tenant: {e}", fg="red")
            sys.exit(1)

    asyncio.run(show())


@tenant.command("activate")
@click.argument("tenant_id")
@click.option("--activated-by", required=True, help="User ID activating the tenant")
@click.pass_context
def activate_tenant(ctx, tenant_id: str, activated_by: str):
    """Activate a pending tenant"""

    async def activate():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                response = await client.post(
                    f"/api/v1/tenants/{tenant_id}/activate", params={"activatedBy": activated_by}
                )
                tenant = response.data

                click.secho("✅ Tenant activated successfully!", fg="green")
                click.echo(f"Tenant: {tenant['displayName']}")
                click.echo(f"Status: {tenant['status']}")
                click.echo(f"Activated: {tenant['activatedAt']}")

        except Exception as e:
            click.secho(f"❌ Failed to activate tenant: {e}", fg="red")
            sys.exit(1)

    asyncio.run(activate())


@tenant.command("suspend")
@click.argument("tenant_id")
@click.option("--reason", required=True, help="Reason for suspension")
@click.option("--suspended-by", required=True, help="User ID suspending the tenant")
@click.pass_context
def suspend_tenant(ctx, tenant_id: str, reason: str, suspended_by: str):
    """Suspend a tenant"""

    async def suspend():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                response = await client.post(
                    f"/api/v1/tenants/{tenant_id}/suspend",
                    params={"reason": reason, "suspendedBy": suspended_by},
                )
                tenant = response.data

                click.secho("⚠️  Tenant suspended successfully!", fg="yellow")
                click.echo(f"Tenant: {tenant['displayName']}")
                click.echo(f"Status: {tenant['status']}")

        except Exception as e:
            click.secho(f"❌ Failed to suspend tenant: {e}", fg="red")
            sys.exit(1)

    asyncio.run(suspend())


@tenant.command("delete")
@click.argument("tenant_id")
@click.option("--deleted-by", required=True, help="User ID deleting the tenant")
@click.option("--force", is_flag=True, help="Force deletion without confirmation")
@click.pass_context
def delete_tenant(ctx, tenant_id: str, deleted_by: str, force: bool):
    """Delete/deactivate a tenant"""

    if not force and not click.confirm(f"Are you sure you want to delete tenant {tenant_id}?"):
        return

    async def delete():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                await client.delete(
                    f"/api/v1/tenants/{tenant_id}", params={"deletedBy": deleted_by}
                )

                click.secho("🗑️  Tenant deleted successfully!", fg="red")

        except Exception as e:
            click.secho(f"❌ Failed to delete tenant: {e}", fg="red")
            sys.exit(1)

    asyncio.run(delete())


@tenant.command("usage")
@click.argument("tenant_id")
@click.pass_context
def tenant_usage(ctx, tenant_id: str):
    """Show tenant usage metrics"""

    async def show_usage():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                response = await client.get(f"/api/v1/tenants/{tenant_id}/usage")
                usage = response.data

                click.secho(f"📊 Tenant Usage: {tenant_id}", fg="blue", bold=True)

                click.echo("\n📈 Resource Usage:")
                click.echo(f"  Total Users: {usage['totalUsers']}")
                click.echo(f"  Total Policies: {usage['totalPolicies']}")
                click.echo(f"  Total Models: {usage['totalModels']}")
                click.echo(f"  Total Approvals: {usage['totalApprovals']}")

                click.echo("\n📊 Utilization Percentages:")
                click.echo(f"  Users: {usage['userUtilization']:.1f}%")
                click.echo(f"  Policies: {usage['policyUtilization']:.1f}%")
                click.echo(f"  Models: {usage['modelUtilization']:.1f}%")
                click.echo(f"  Approvals: {usage['approvalUtilization']:.1f}%")
                click.echo(f"  Storage: {usage['storageUtilization']:.1f}%")

                click.echo("\n⏱️  Performance:")
                click.echo(f"  Avg Response Time: {usage['avgResponseTime']:.2f}ms")
                click.echo(f"  Error Rate: {usage['errorRate']:.2f}%")
                click.echo(f"  Uptime: {usage['uptimePercentage']:.1f}%")

        except Exception as e:
            click.secho(f"❌ Failed to get tenant usage: {e}", fg="red")
            sys.exit(1)

    asyncio.run(show_usage())


@tenant.command("quota-check")
@click.argument("tenant_id")
@click.option("--resource", required=True, help="Resource type (users, policies, models, etc.)")
@click.option("--amount", type=int, default=1, help="Amount requested")
@click.pass_context
def check_quota(ctx, tenant_id: str, resource: str, amount: int):
    """Check if tenant has quota for requested resource"""

    async def check():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                response = await client.get(
                    f"/api/v1/tenants/{tenant_id}/quotas/check",
                    params={"resource_type": resource, "amount": amount},
                )
                quota = response.data

                status_icon = "✅" if quota["allowed"] else "❌"
                status_color = "green" if quota["allowed"] else "red"

                click.secho(f"{status_icon} Quota Check: {resource}", fg=status_color, bold=True)
                click.echo(f"Requested: {amount}")
                click.echo(f"Current Usage: {quota['current_usage']}")
                click.echo(f"Limit: {quota['limit']}")
                click.echo(f"Available: {quota['limit'] - quota['current_usage']}")

        except Exception as e:
            click.secho(f"❌ Failed to check quota: {e}", fg="red")
            sys.exit(1)

    asyncio.run(check())


@tenant.command("access-check")
@click.argument("tenant_id")
@click.option("--user", required=True, help="User ID to check")
@click.option("--resource-type", required=True, help="Resource type")
@click.option("--resource-id", help="Specific resource ID")
@click.option("--permission", required=True, help="Required permission")
@click.pass_context
def check_access(
    ctx, tenant_id: str, user: str, resource_type: str, resource_id: str | None, permission: str
):
    """Check if user has access to specific resource"""

    async def check():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                params = {"userId": user, "resource_type": resource_type, "permission": permission}
                if resource_id:
                    params["resource_id"] = resource_id

                response = await client.get(
                    f"/api/v1/tenants/{tenant_id}/access/check", params=params
                )
                access = response.data

                status_icon = "✅" if access["allowed"] else "❌"
                status_color = "green" if access["allowed"] else "red"

                click.secho(f"{status_icon} Access Check", fg=status_color, bold=True)
                click.echo(f"User: {user}")
                click.echo(f"Resource: {resource_type}")
                if resource_id:
                    click.echo(f"Resource ID: {resource_id}")
                click.echo(f"Permission: {permission}")
                if access["role"]:
                    click.echo(f"Role: {access['role']}")
                if access["permissions"]:
                    click.echo(f"Permissions: {', '.join(access['permissions'])}")

        except Exception as e:
            click.secho(f"❌ Failed to check access: {e}", fg="red")
            sys.exit(1)

    asyncio.run(check())


@tenant.command("grant-access")
@click.argument("tenant_id")
@click.option("--user", required=True, help="User ID to grant access to")
@click.option("--resource-type", required=True, help="Resource type")
@click.option("--resource-id", help="Specific resource ID (leave empty for all)")
@click.option("--role", required=True, help="Access role")
@click.option("--permissions", required=True, help="Comma-separated permissions")
@click.option("--granted-by", required=True, help="User ID granting access")
@click.pass_context
def grant_access(
    ctx,
    tenant_id: str,
    user: str,
    resource_type: str,
    resource_id: str | None,
    role: str,
    permissions: str,
    granted_by: str,
):
    """Grant access to a resource"""

    async def grant():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                params = {
                    "userId": user,
                    "resource_type": resource_type,
                    "role": role,
                    "permissions": [p.strip() for p in permissions.split(",")],
                    "grantedBy": granted_by,
                }
                if resource_id:
                    params["resource_id"] = resource_id

                response = await client.post(
                    f"/api/v1/tenants/{tenant_id}/access/grant", params=params
                )
                policy = response.data

                click.secho("🔐 Access granted successfully!", fg="green")
                click.echo(f"User: {policy['userId']}")
                click.echo(f"Resource: {policy['resourceType']}")
                if policy.get("resourceId"):
                    click.echo(f"Resource ID: {policy['resourceId']}")
                click.echo(f"Role: {policy['role']}")
                click.echo(f"Permissions: {', '.join(policy['permissions'])}")

        except Exception as e:
            click.secho(f"❌ Failed to grant access: {e}", fg="red")
            sys.exit(1)

    asyncio.run(grant())
