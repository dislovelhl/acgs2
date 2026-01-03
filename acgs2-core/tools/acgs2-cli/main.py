#!/usr/bin/env python3
"""
ACGS-2 Unified CLI Tool
Constitutional Hash: cdd01ef066bc6cf2

A comprehensive command-line interface for ACGS-2 AI Constitutional Governance Platform.
Provides unified access to all services: HITL Approvals, ML Governance, Policy Management,
and interactive Policy Playground.
"""

import asyncio
import logging
import sys
from pathlib import Path

import click

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from acgs2_sdk import ACGS2Config, create_client
from acgs2_cli.config import CLIConfig
from acgs2_cli.commands.hitl import hitl
from acgs2_cli.commands.ml import ml
from acgs2_cli.commands.policy import policy
from acgs2_cli.commands.playground import playground
from acgs2_cli.commands.tenant import tenant

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.group()
@click.option("--base-url", default="http://localhost:8080", help="ACGS-2 API Gateway URL")
@click.option("--api-key", envvar="ACGS2_API_KEY", help="API key for authentication")
@click.option("--tenant-id", default="acgs-dev", envvar="ACGS2_TENANT_ID", help="Tenant ID")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--config", type=click.Path(exists=True), help="Path to configuration file")
@click.pass_context
def cli(ctx, base_url, api_key, tenant_id, verbose, config):
    """ACGS-2 Unified CLI Tool

    A comprehensive command-line interface for the AI Constitutional Governance System.

    Constitutional Hash: cdd01ef066bc6cf2

    Examples:

        # Check system health
        acgs2-cli health

        # Create an approval request
        acgs2-cli hitl create --type model_deployment --payload-file deployment.json

        # List ML models
        acgs2-cli ml models list

        # Start policy playground
        acgs2-cli playground

        # Validate a policy
        acgs2-cli policy validate --file policy.json
    """

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    cli_config = CLIConfig.load(config)
    cli_config.base_url = base_url
    cli_config.api_key = api_key
    cli_config.tenant_id = tenant_id

    # Create SDK client
    sdk_config = ACGS2Config(
        base_url=cli_config.base_url,
        api_key=cli_config.api_key,
        tenant_id=cli_config.tenant_id,
        timeout=cli_config.timeout,
    )

    ctx.ensure_object(dict)
    ctx.obj["config"] = cli_config
    ctx.obj["sdk_config"] = sdk_config


@cli.command()
@click.pass_context
def health(ctx):
    """Check ACGS-2 system health"""

    async def check_health():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                health_data = await client.health_check()

                click.secho("🩺 ACGS-2 System Health", fg="blue", bold=True)
                click.echo(f"Healthy: {'✅' if health_data['healthy'] else '❌'}")
                click.echo(".2f")
                click.echo(f"Constitutional Hash: {health_data['constitutional_hash']}")
                if health_data.get("version"):
                    click.echo(f"Version: {health_data['version']}")

        except Exception as e:
            click.secho(f"❌ Health check failed: {e}", fg="red")
            sys.exit(1)

    asyncio.run(check_health())


@cli.command()
@click.pass_context
def version(ctx):
    """Show ACGS-2 CLI version and constitutional hash"""
    click.secho("ACGS-2 CLI Tool", fg="blue", bold=True)
    click.echo("Version: 2.0.0")
    click.echo("Constitutional Hash: cdd01ef066bc6cf2")
    click.echo("SDK Version: 2.0.0")


# Add subcommands
cli.add_command(hitl)
cli.add_command(ml)
cli.add_command(policy)
cli.add_command(playground)
cli.add_command(tenant)


if __name__ == "__main__":
    cli()
