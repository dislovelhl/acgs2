"""
ACGS-2 CLI - HITL Approvals Commands
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import json
import sys
from typing import Any

import click
from acgs2_sdk import HITLApprovalsService, create_client


@click.group()
@click.pass_context
def hitl(ctx):
    """HITL Approvals management commands"""
    pass


@hitl.command()
@click.option("--type", "request_type", required=True, help="Request type")
@click.option("--payload", help="JSON payload string")
@click.option("--payload-file", type=click.Path(exists=True), help="JSON payload file")
@click.option("--risk-score", type=float, help="Risk score (0-100)")
@click.option("--required-approvers", type=int, help="Required number of approvers")
@click.pass_context
def create(
    ctx,
    request_type: str,
    payload: str | None,
    payload_file: str | None,
    risk_score: float | None,
    required_approvers: int | None,
):
    """Create a new approval request"""

    async def create_request():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                hitl_service = HITLApprovalsService(client)

                # Parse payload
                request_payload: dict[str, Any] = {}
                if payload:
                    request_payload = json.loads(payload)
                elif payload_file:
                    with open(payload_file) as f:
                        request_payload = json.load(f)
                else:
                    click.secho("❌ Must provide either --payload or --payload-file", fg="red")
                    return

                # Create request
                request_data = {
                    "request_type": request_type,
                    "payload": request_payload,
                }
                if risk_score is not None:
                    request_data["risk_score"] = risk_score
                if required_approvers is not None:
                    request_data["required_approvers"] = required_approvers

                approval = await hitl_service.create_approval_request(request_data)

                click.secho("✅ Approval request created successfully!", fg="green")
                click.echo(f"ID: {approval.id}")
                click.echo(f"Type: {approval.request_type}")
                click.echo(f"Status: {approval.status}")
                click.echo(f"Risk Score: {approval.risk_score}")
                click.echo(f"Required Approvers: {approval.required_approvers}")

        except Exception as e:
            click.secho(f"❌ Failed to create approval request: {e}", fg="red")
            sys.exit(1)

    asyncio.run(create_request())


@hitl.command()
@click.argument("request_id")
@click.pass_context
def show(ctx, request_id: str):
    """Show approval request details"""

    async def show_request():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                hitl_service = HITLApprovalsService(client)

                approval = await hitl_service.get_approval_request(request_id)

                click.secho(f"📋 Approval Request: {approval.id}", fg="blue", bold=True)
                click.echo(f"Type: {approval.request_type}")
                click.echo(f"Status: {approval.status}")
                click.echo(f"Requester: {approval.requester_id}")
                click.echo(f"Risk Score: {approval.risk_score}")
                click.echo(f"Approvals: {approval.current_approvals}/{approval.required_approvers}")
                click.echo(f"Created: {approval.created_at}")

                if approval.expires_at:
                    click.echo(f"Expires: {approval.expires_at}")

                if approval.decisions:
                    click.echo("\n📝 Decisions:")
                    for decision in approval.decisions:
                        click.echo(f"  • {decision.approver_id}: {decision.decision}")
                        if decision.reasoning:
                            click.echo(f"    {decision.reasoning}")

                click.echo(f"\n📦 Payload: {json.dumps(approval.payload, indent=2)}")

        except Exception as e:
            click.secho(f"❌ Failed to get approval request: {e}", fg="red")
            sys.exit(1)

    asyncio.run(show_request())


@hitl.command()
@click.option("--status", help="Filter by status")
@click.option("--requester", help="Filter by requester ID")
@click.option("--pending-for", help="Filter by user who can approve")
@click.option("--limit", type=int, default=20, help="Number of results to show")
@click.pass_context
def list(
    ctx, status: str | None, requester: str | None, pending_for: str | None, limit: int
):
    """List approval requests"""

    async def list_requests():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                hitl_service = HITLApprovalsService(client)

                requests = await hitl_service.list_approval_requests(
                    status=status, requester_id=requester, pending_for=pending_for, page_size=limit
                )

                click.secho(f"📋 Approval Requests ({requests.total})", fg="blue", bold=True)

                if not requests.data:
                    click.echo("No approval requests found.")
                    return

                for req in requests.data:
                    status_color = {
                        "pending": "yellow",
                        "approved": "green",
                        "rejected": "red",
                        "escalated": "magenta",
                        "expired": "grey",
                    }.get(req.status, "white")

                    click.secho(f"• {req.id}", fg=status_color, nl=False)
                    click.echo(
                        f" | {req.request_type} | {req.requester_id} | {req.risk_score} | {req.current_approvals}/{req.required_approvers}"
                    )

        except Exception as e:
            click.secho(f"❌ Failed to list approval requests: {e}", fg="red")
            sys.exit(1)

    asyncio.run(list_requests())


@hitl.command()
@click.argument("request_id")
@click.option("--decision", type=click.Choice(["approve", "reject"]), required=True)
@click.option("--reasoning", required=True, help="Reason for the decision")
@click.pass_context
def decide(ctx, request_id: str, decision: str, reasoning: str):
    """Submit an approval decision"""

    async def submit_decision():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                hitl_service = HITLApprovalsService(client)

                decision_data = {"decision": decision, "reasoning": reasoning}

                updated_request = await hitl_service.submit_decision(request_id, decision_data)

                click.secho("✅ Decision submitted successfully!", fg="green")
                click.echo(f"Request: {updated_request.id}")
                click.echo(f"Status: {updated_request.status}")
                click.echo(
                    f"Approvals: {updated_request.current_approvals}/{updated_request.required_approvers}"
                )

        except Exception as e:
            click.secho(f"❌ Failed to submit decision: {e}", fg="red")
            sys.exit(1)

    asyncio.run(submit_decision())


@hitl.command()
@click.argument("request_id")
@click.option("--reason", required=True, help="Reason for escalation")
@click.pass_context
def escalate(ctx, request_id: str, reason: str):
    """Escalate an approval request"""

    async def escalate_request():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                hitl_service = HITLApprovalsService(client)

                updated_request = await hitl_service.escalate(request_id, reason)

                click.secho("📢 Request escalated successfully!", fg="yellow")
                click.echo(f"Request: {updated_request.id}")
                click.echo(f"Status: {updated_request.status}")

        except Exception as e:
            click.secho(f"❌ Failed to escalate request: {e}", fg="red")
            sys.exit(1)

    asyncio.run(escalate_request())


@hitl.command()
@click.argument("request_id")
@click.option("--reason", help="Reason for cancellation")
@click.pass_context
def cancel(ctx, request_id: str, reason: str | None):
    """Cancel an approval request"""

    async def cancel_request():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                hitl_service = HITLApprovalsService(client)

                await hitl_service.cancel_approval_request(request_id, reason)

                click.secho("🗑️  Request cancelled successfully!", fg="red")

        except Exception as e:
            click.secho(f"❌ Failed to cancel request: {e}", fg="red")
            sys.exit(1)

    asyncio.run(cancel_request())


@hitl.command()
@click.argument("user_id")
@click.option("--limit", type=int, default=10, help="Number of results to show")
@click.pass_context
def pending(ctx, user_id: str, limit: int):
    """Show pending approvals for a user"""

    async def show_pending():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                hitl_service = HITLApprovalsService(client)

                pending_requests = await hitl_service.get_pending_approvals(
                    user_id, page_size=limit
                )

                click.secho(
                    f"👤 Pending Approvals for {user_id} ({pending_requests.total})",
                    fg="blue",
                    bold=True,
                )

                if not pending_requests.data:
                    click.echo("No pending approvals.")
                    return

                for req in pending_requests.data:
                    click.echo(f"• {req.id} | {req.request_type} | Risk: {req.risk_score}")
                    click.echo(f"  Created: {req.created_at}")

        except Exception as e:
            click.secho(f"❌ Failed to get pending approvals: {e}", fg="red")
            sys.exit(1)

    asyncio.run(show_pending())


@hitl.command()
@click.pass_context
def metrics(ctx):
    """Show HITL approval metrics"""

    async def show_metrics():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                hitl_service = HITLApprovalsService(client)

                # Get metrics for last 30 days
                metrics = await hitl_service.get_approval_metrics(
                    start_date="-30days", end_date="now"
                )

                click.secho("📊 HITL Approval Metrics", fg="blue", bold=True)

                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        click.echo(f"{key}: {value}")
                    else:
                        click.echo(f"{key}: {value}")

        except Exception as e:
            click.secho(f"❌ Failed to get metrics: {e}", fg="red")
            sys.exit(1)

    asyncio.run(show_metrics())
