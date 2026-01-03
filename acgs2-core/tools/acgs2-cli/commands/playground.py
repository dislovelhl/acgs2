"""
ACGS-2 CLI - Interactive Policy Playground
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click
from acgs2_sdk import ComplianceService, PolicyService, create_client


@click.command()
@click.option("--policy", help="Policy ID or file path to load")
@click.option("--context", help="JSON context for testing")
@click.option("--interactive", "-i", is_flag=True, help="Start interactive mode")
@click.pass_context
def playground(ctx, policy: str | None, context: str | None, interactive: bool):
    """Interactive policy playground for testing governance rules"""

    if not interactive and not policy:
        click.secho("❌ Must specify --policy or use --interactive mode", fg="red")
        sys.exit(1)

    async def run_playground():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                policy_service = PolicyService(client)
                compliance_service = ComplianceService(client)

                # Load initial policy if specified
                current_policy = None
                if policy:
                    if Path(policy).exists():
                        # Load from file
                        with open(policy) as f:
                            policy_data = json.load(f)
                        current_policy = await policy_service.create(
                            {
                                "name": f"playground-{Path(policy).stem}",
                                "rules": policy_data,
                                "description": "Policy playground session",
                            }
                        )
                        click.secho(f"📋 Loaded policy from file: {current_policy.name}", fg="blue")
                    else:
                        # Load by ID
                        current_policy = await policy_service.get(policy)
                        click.secho(f"📋 Loaded policy: {current_policy.name}", fg="blue")

                # Load initial context if specified
                current_context: dict[str, Any] = {}
                if context:
                    current_context = json.loads(context)
                    click.secho("📝 Loaded test context", fg="blue")

                if interactive:
                    await run_interactive_mode(
                        client, policy_service, compliance_service, current_policy, current_context
                    )
                else:
                    # Single validation run
                    if not current_policy or not current_context:
                        click.secho("❌ Need both policy and context for single run", fg="red")
                        return

                    result = await compliance_service.validate(
                        current_policy.id,
                        {"policy_id": current_policy.id, "context": current_context},
                    )

                    display_validation_result(result)

                    # Clean up temporary policy
                    if policy and Path(policy).exists():
                        try:
                            await policy_service.delete(current_policy.id)
                        except Exception:
                            pass

        except Exception as e:
            click.secho(f"❌ Playground error: {e}", fg="red")
            sys.exit(1)

    asyncio.run(run_playground())


async def run_interactive_mode(
    client, policy_service, compliance_service, initial_policy, initial_context
):
    """Run interactive policy playground"""

    click.secho("🎮 ACGS-2 Policy Playground", fg="cyan", bold=True)
    click.echo("Constitutional Hash: cdd01ef066bc6cf2")
    click.echo("Type 'help' for commands, 'quit' to exit\n")

    current_policy = initial_policy
    current_context = initial_context
    temp_policies = []  # Track temporary policies for cleanup

    while True:
        try:
            # Show current state
            if current_policy:
                click.secho(
                    f"Current Policy: {current_policy.name} ({current_policy.id})", fg="blue"
                )
            else:
                click.secho("No policy loaded", fg="yellow")

            if current_context:
                click.secho(f"Context loaded: {len(current_context)} keys", fg="blue")
            else:
                click.secho("No context loaded", fg="yellow")

            # Get user input
            prompt = click.style("playground> ", fg="green", bold=True)
            command = click.prompt(prompt, type=str).strip()

            if not command:
                continue

            if command in ["quit", "exit", "q"]:
                break
            elif command == "help":
                show_help()
            elif command.startswith("load "):
                parts = command.split(" ", 1)
                if len(parts) > 1:
                    await handle_load_policy(policy_service, temp_policies, parts[1])
                else:
                    click.secho("❌ Usage: load <policy_file>", fg="red")
            elif command.startswith("context "):
                parts = command.split(" ", 1)
                if len(parts) > 1:
                    current_context = json.loads(parts[1])
                    click.secho("✅ Context updated", fg="green")
                else:
                    click.secho("❌ Usage: context <json>", fg="red")
            elif command.startswith("load-context "):
                parts = command.split(" ", 1)
                if len(parts) > 1:
                    with open(parts[1]) as f:
                        current_context = json.load(f)
                    click.secho("✅ Context loaded from file", fg="green")
                else:
                    click.secho("❌ Usage: load-context <file>", fg="red")
            elif command == "validate":
                if not current_policy or not current_context:
                    click.secho("❌ Need both policy and context to validate", fg="red")
                else:
                    result = await compliance_service.validate(
                        current_policy.id,
                        {"policy_id": current_policy.id, "context": current_context},
                    )
                    display_validation_result(result)
            elif command == "show-policy":
                if current_policy:
                    click.echo(
                        json.dumps(
                            {
                                "id": current_policy.id,
                                "name": current_policy.name,
                                "rules": current_policy.rules,
                            },
                            indent=2,
                        )
                    )
                else:
                    click.secho("❌ No policy loaded", fg="red")
            elif command == "show-context":
                if current_context:
                    click.echo(json.dumps(current_context, indent=2))
                else:
                    click.secho("❌ No context loaded", fg="red")
            elif command == "clear":
                current_policy = None
                current_context = {}
                click.secho("✅ Cleared policy and context", fg="green")
            elif command.startswith("edit-context"):
                await handle_edit_context(current_context)
            else:
                click.secho(f"❌ Unknown command: {command}", fg="red")
                click.echo("Type 'help' for available commands")

        except KeyboardInterrupt:
            break
        except click.Abort:
            break
        except Exception as e:
            click.secho(f"❌ Error: {e}", fg="red")

    # Cleanup temporary policies
    for policy_id in temp_policies:
        try:
            await policy_service.delete(policy_id)
        except Exception:
            pass

    click.secho("\n👋 Goodbye!", fg="cyan")


def show_help():
    """Display help information"""
    help_text = """
🎮 Policy Playground Commands:

📋 Policy Management:
  load <file>          Load policy from JSON file
  show-policy          Display current policy

📝 Context Management:
  context <json>       Set context as JSON string
  load-context <file>  Load context from JSON file
  show-context         Display current context
  edit-context         Edit context interactively

✅ Validation:
  validate             Run compliance validation

🧹 Utilities:
  clear                Clear current policy and context
  help                 Show this help
  quit                 Exit playground

📖 Examples:
  load my_policy.json
  context {"action": "deploy", "risk": "high"}
  validate
"""
    click.echo_via_pager(help_text)


async def handle_load_policy(policy_service, temp_policies, policy_file):
    """Handle loading a policy from file"""
    try:
        if not Path(policy_file).exists():
            click.secho(f"❌ File not found: {policy_file}", fg="red")
            return

        with open(policy_file) as f:
            policy_data = json.load(f)

        policy = await policy_service.create(
            {
                "name": f"playground-{Path(policy_file).stem}",
                "rules": policy_data,
                "description": "Policy playground session",
            }
        )

        temp_policies.append(policy.id)
        click.secho(f"✅ Policy loaded: {policy.name}", fg="green")
        return policy

    except Exception as e:
        click.secho(f"❌ Failed to load policy: {e}", fg="red")


async def handle_edit_context(current_context):
    """Handle interactive context editing"""
    click.secho("📝 Context Editor (enter empty line to finish)", fg="blue")

    while True:
        key = click.prompt("Key (or empty to finish)", type=str, default="").strip()
        if not key:
            break

        value_input = click.prompt(f"Value for '{key}' (JSON)", type=str)
        try:
            value = json.loads(value_input)
            current_context[key] = value
            click.secho(f"✅ Set {key} = {value}", fg="green")
        except json.JSONDecodeError:
            click.secho("❌ Invalid JSON value", fg="red")


def display_validation_result(result):
    """Display validation result in a nice format"""
    click.secho("\n📊 Validation Result", fg="blue", bold=True)

    status_color = "green" if result.status == "compliant" else "red"
    click.secho(f"Status: {result.status}", fg=status_color)
    click.echo(f"Score: {result.score}/100")

    if result.violations:
        click.secho("\n⚠️  Violations:", fg="yellow")
        for i, violation in enumerate(result.violations, 1):
            click.echo(f"  {i}. {violation.rule_id}: {violation.message}")
            click.echo(f"     Severity: {violation.severity}")
            if violation.details:
                click.echo(f"     Details: {violation.details}")
    else:
        click.secho("\n✅ No violations found!", fg="green")

    click.echo()
