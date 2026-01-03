"""
ACGS-2 CLI - Policy Management Commands
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click
from acgs2_sdk import ComplianceService, PolicyService, create_client


@click.group()
@click.pass_context
def policy(ctx):
    """Policy management commands"""
    pass


@policy.command("create")
@click.option("--name", required=True, help="Policy name")
@click.option(
    "--file",
    "rules_file",
    type=click.Path(exists=True),
    required=True,
    help="JSON file containing policy rules",
)
@click.option("--description", help="Policy description")
@click.option("--tags", help="Comma-separated list of tags")
@click.option("--compliance-tags", help="Comma-separated list of compliance tags")
@click.pass_context
def create_policy(
    ctx,
    name: str,
    rules_file: str,
    description: str | None,
    tags: str | None,
    compliance_tags: str | None,
):
    """Create a new policy"""

    async def create():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                policy_service = PolicyService(client)

                # Load rules from file
                with open(rules_file) as f:
                    rules = json.load(f)

                policy_data = {
                    "name": name,
                    "rules": rules,
                }
                if description:
                    policy_data["description"] = description
                if tags:
                    policy_data["tags"] = [tag.strip() for tag in tags.split(",")]
                if compliance_tags:
                    policy_data["compliance_tags"] = [
                        tag.strip() for tag in compliance_tags.split(",")
                    ]

                policy = await policy_service.create(policy_data)

                click.secho("📋 Policy created successfully!", fg="green")
                click.echo(f"ID: {policy.id}")
                click.echo(f"Name: {policy.name}")
                click.echo(f"Version: {policy.version}")
                click.echo(f"Status: {policy.status}")
                if policy.description:
                    click.echo(f"Description: {policy.description}")

        except Exception as e:
            click.secho(f"❌ Failed to create policy: {e}", fg="red")
            sys.exit(1)

    asyncio.run(create())


@policy.command("list")
@click.option("--status", help="Filter by status")
@click.option("--tags", help="Filter by tags (comma-separated)")
@click.option("--limit", type=int, default=20, help="Number of results to show")
@click.pass_context
def list_policies(ctx, status: str | None, tags: str | None, limit: int):
    """List policies"""

    async def list():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                policy_service = PolicyService(client)

                params: dict[str, Any] = {"page_size": limit}
                if status:
                    params["status"] = status
                if tags:
                    params["tags"] = [tag.strip() for tag in tags.split(",")]

                policies = await policy_service.list(**params)

                click.secho(f"📋 Policies ({policies.total})", fg="blue", bold=True)

                if not policies.data:
                    click.echo("No policies found.")
                    return

                for pol in policies.data:
                    status_color = {
                        "draft": "grey",
                        "pending_review": "yellow",
                        "approved": "blue",
                        "active": "green",
                        "deprecated": "red",
                        "archived": "grey",
                    }.get(pol.status, "white")

                    click.secho(f"• {pol.id}", fg=status_color, nl=False)
                    click.echo(f" | {pol.name} | v{pol.version} | {pol.status}")

        except Exception as e:
            click.secho(f"❌ Failed to list policies: {e}", fg="red")
            sys.exit(1)

    asyncio.run(list())


@policy.command("show")
@click.argument("policy_id")
@click.pass_context
def show_policy(ctx, policy_id: str):
    """Show policy details"""

    async def show():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                policy_service = PolicyService(client)

                policy = await policy_service.get(policy_id)

                click.secho(f"📋 Policy: {policy.name}", fg="blue", bold=True)
                click.echo(f"ID: {policy.id}")
                click.echo(f"Version: {policy.version}")
                click.echo(f"Status: {policy.status}")
                if policy.description:
                    click.echo(f"Description: {policy.description}")
                if policy.tags:
                    click.echo(f"Tags: {', '.join(policy.tags)}")
                if policy.compliance_tags:
                    click.echo(f"Compliance Tags: {', '.join(policy.compliance_tags)}")
                click.echo(f"Created: {policy.created_at}")
                click.echo(f"Updated: {policy.updated_at}")

                click.echo("\n📝 Rules:")
                click.echo(json.dumps(policy.rules, indent=2))

        except Exception as e:
            click.secho(f"❌ Failed to get policy: {e}", fg="red")
            sys.exit(1)

    asyncio.run(show())


@policy.command("update")
@click.argument("policy_id")
@click.option("--name", help="New policy name")
@click.option(
    "--file",
    "rules_file",
    type=click.Path(exists=True),
    help="JSON file containing updated policy rules",
)
@click.option("--description", help="New description")
@click.option("--status", help="New status")
@click.option("--tags", help="New tags (comma-separated)")
@click.option("--compliance-tags", help="New compliance tags (comma-separated)")
@click.pass_context
def update_policy(
    ctx,
    policy_id: str,
    name: str | None,
    rules_file: str | None,
    description: str | None,
    status: str | None,
    tags: str | None,
    compliance_tags: str | None,
):
    """Update a policy"""

    async def update():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                policy_service = PolicyService(client)

                update_data: dict[str, Any] = {}

                if name:
                    update_data["name"] = name
                if rules_file:
                    with open(rules_file) as f:
                        update_data["rules"] = json.load(f)
                if description:
                    update_data["description"] = description
                if status:
                    update_data["status"] = status
                if tags:
                    update_data["tags"] = [tag.strip() for tag in tags.split(",")]
                if compliance_tags:
                    update_data["compliance_tags"] = [
                        tag.strip() for tag in compliance_tags.split(",")
                    ]

                if not update_data:
                    click.secho("❌ No update parameters provided", fg="red")
                    return

                policy = await policy_service.update(policy_id, update_data)

                click.secho("✅ Policy updated successfully!", fg="green")
                click.echo(f"Name: {policy.name}")
                click.echo(f"Status: {policy.status}")

        except Exception as e:
            click.secho(f"❌ Failed to update policy: {e}", fg="red")
            sys.exit(1)

    asyncio.run(update())


@policy.command("delete")
@click.argument("policy_id")
@click.option("--force", is_flag=True, help="Force deletion without confirmation")
@click.pass_context
def delete_policy(ctx, policy_id: str, force: bool):
    """Delete a policy"""

    if not force:
        if not click.confirm(f"Are you sure you want to delete policy {policy_id}?"):
            return

    async def delete():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                policy_service = PolicyService(client)

                await policy_service.delete(policy_id)

                click.secho("🗑️  Policy deleted successfully!", fg="red")

        except Exception as e:
            click.secho(f"❌ Failed to delete policy: {e}", fg="red")
            sys.exit(1)

    asyncio.run(delete())


@policy.command("validate")
@click.argument("policy_id")
@click.option("--context", required=True, help="JSON context for validation")
@click.pass_context
def validate_policy(ctx, policy_id: str, context: str):
    """Validate compliance against a policy"""

    async def validate():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                compliance_service = ComplianceService(client)

                context_data = json.loads(context)

                result = await compliance_service.validate(
                    policy_id, {"policy_id": policy_id, "context": context_data}
                )

                click.secho("✅ Compliance Validation Result", fg="green", bold=True)
                click.echo(f"Policy: {policy_id}")
                click.echo(f"Status: {result.status}")
                click.echo(f"Score: {result.score}/100")

                if result.violations:
                    click.secho("\n⚠️  Violations:", fg="yellow")
                    for violation in result.violations:
                        click.echo(f"  • {violation.rule_id}: {violation.message}")
                        click.echo(f"    Severity: {violation.severity}")
                else:
                    click.secho("✅ No violations found!", fg="green")

        except Exception as e:
            click.secho(f"❌ Failed to validate policy: {e}", fg="red")
            sys.exit(1)

    asyncio.run(validate())


@policy.command("deploy")
@click.argument("policy_id")
@click.pass_context
def deploy_policy(ctx, policy_id: str):
    """Deploy a policy to active status"""

    async def deploy():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                policy_service = PolicyService(client)

                policy = await policy_service.update(policy_id, {"status": "active"})

                click.secho("🚀 Policy deployed successfully!", fg="green")
                click.echo(f"Policy: {policy.name}")
                click.echo(f"Status: {policy.status}")

        except Exception as e:
            click.secho(f"❌ Failed to deploy policy: {e}", fg="red")
            sys.exit(1)

    asyncio.run(deploy())


@policy.command("test")
@click.argument("policy_file", type=click.Path(exists=True))
@click.option("--context", help="JSON test context")
@click.option("--context-file", type=click.Path(exists=True), help="JSON file with test context")
@click.pass_context
def test_policy(ctx, policy_file: str, context: str | None, context_file: str | None):
    """Test a policy against sample context"""

    async def test():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                policy_service = PolicyService(client)

                # Load policy from file
                with open(policy_file) as f:
                    policy_data = json.load(f)

                # Create temporary policy
                temp_policy = await policy_service.create(
                    {
                        "name": f"test-{Path(policy_file).stem}",
                        "rules": policy_data,
                        "description": "Temporary test policy",
                    }
                )

                try:
                    # Load test context
                    test_context: dict[str, Any] = {}
                    if context:
                        test_context = json.loads(context)
                    elif context_file:
                        with open(context_file) as f:
                            test_context = json.load(f)
                    else:
                        click.secho("❌ Must provide either --context or --context-file", fg="red")
                        return

                    compliance_service = ComplianceService(client)
                    result = await compliance_service.validate(
                        temp_policy.id, {"policy_id": temp_policy.id, "context": test_context}
                    )

                    click.secho("🧪 Policy Test Result", fg="blue", bold=True)
                    click.echo(f"Policy: {temp_policy.name}")
                    click.echo(f"Status: {result.status}")
                    click.echo(f"Score: {result.score}/100")

                    if result.violations:
                        click.secho("\n❌ Violations Found:", fg="red")
                        for violation in result.violations:
                            click.echo(f"  • {violation.rule_id}: {violation.message}")
                    else:
                        click.secho("\n✅ Policy test passed!", fg="green")

                finally:
                    # Clean up temporary policy
                    try:
                        await policy_service.delete(temp_policy.id)
                    except Exception:
                        pass  # Ignore cleanup errors

        except Exception as e:
            click.secho(f"❌ Failed to test policy: {e}", fg="red")
            sys.exit(1)

    asyncio.run(test())
