"""Constitutional Hash: cdd01ef066bc6cf2
ACGS-2 Policy CLI Tool

Provides command-line interface for Rego policy validation and testing.
Uses Typer for CLI framework and integrates with OPA for policy evaluation.

Usage:
    python -m cli.policy_cli validate <policy_file>
    python -m cli.policy_cli test <policy_file> --input <json_input>
"""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from .opa_service import (
    OPAConnectionError,
    OPAService,
    PolicyEvaluationResult,
    PolicyValidationResult,
)

# Create Typer app
app = typer.Typer(
    name="policy_cli",
    help="ACGS-2 Policy CLI - Validate and test Rego policies",
    add_completion=False,
)

console = Console()


def _format_validation_result(result: PolicyValidationResult, verbose: bool = False) -> None:
    """Format and display validation result."""
    if result.is_valid:
        console.print("[green]✓ Policy is valid[/green]")
        if verbose and result.metadata:
            console.print(f"  Metadata: {result.metadata}")
    else:
        console.print("[red]✗ Policy validation failed[/red]")
        for error in result.errors:
            console.print(f"  [red]• {error}[/red]")
        if result.warnings:
            for warning in result.warnings:
                console.print(f"  [yellow]⚠ {warning}[/yellow]")


def _format_evaluation_result(result: PolicyEvaluationResult, verbose: bool = False) -> None:
    """Format and display evaluation result."""
    if result.success:
        # Create results panel
        title = "[green]Evaluation Successful[/green]"

        # Format the result as JSON
        result_json = json.dumps(result.result, indent=2)
        syntax = Syntax(result_json, "json", theme="monokai", line_numbers=False)

        console.print(Panel(syntax, title=title, border_style="green"))

        # Show allowed status if available
        if result.allowed is not None:
            allowed_text = "[green]ALLOWED[/green]" if result.allowed else "[red]DENIED[/red]"
            console.print(f"\nDecision: {allowed_text}")

        if verbose:
            if result.reason:
                console.print(f"Reason: {result.reason}")
            if result.metadata:
                console.print(f"Metadata: {result.metadata}")
    else:
        console.print("[red]✗ Policy evaluation failed[/red]")
        console.print(f"  Reason: {result.reason}")
        if "errors" in result.metadata:
            for error in result.metadata["errors"]:
                console.print(f"  [red]• {error}[/red]")


def _read_policy_file(policy_file: Path) -> str:
    """Read policy content from file."""
    if not policy_file.exists():
        console.print(f"[red]Error: Policy file not found: {policy_file}[/red]")
        raise typer.Exit(code=1)

    if not policy_file.is_file():
        console.print(f"[red]Error: Not a file: {policy_file}[/red]")
        raise typer.Exit(code=1)

    # Check file size (warn if >1MB)
    file_size = policy_file.stat().st_size
    if file_size > 1024 * 1024:
        console.print(
            f"[yellow]Warning: Large policy file ({file_size / 1024 / 1024:.2f} MB)[/yellow]"
        )

    try:
        return policy_file.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/red]")
        raise typer.Exit(code=1) from None


def _parse_json_input(input_str: str) -> dict:
    """Parse JSON input string."""
    try:
        return json.loads(input_str)
    except json.JSONDecodeError as e:
        console.print("[red]Error: Invalid JSON input[/red]")
        console.print(f"  {e.msg} at line {e.lineno}, column {e.colno}")
        raise typer.Exit(code=1) from None


@app.command()
def validate(
    policy_file: Annotated[
        Path,
        typer.Argument(
            help="Path to Rego policy file to validate",
            exists=False,  # We handle existence check ourselves for better error messages
        ),
    ],
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed validation information"),
    ] = False,
    opa_url: Annotated[
        Optional[str],
        typer.Option(
            "--opa-url", help="OPA server URL (default: $OPA_URL or http://localhost:8181)"
        ),
    ] = None,
) -> None:
    """
    Validate a Rego policy file for syntax and semantic errors.

    Checks the policy against the OPA server without deploying it.
    Returns exit code 0 if valid, 1 if invalid or error.

    Examples:
        python -m cli.policy_cli validate policy.rego
        python -m cli.policy_cli validate policy.rego --verbose
        python -m cli.policy_cli validate policy.rego --opa-url http://localhost:8181
    """
    # Read policy content
    policy_content = _read_policy_file(policy_file)

    if verbose:
        console.print(f"Validating: {policy_file}")
        console.print(f"Policy size: {len(policy_content)} bytes")

    # Validate using OPA service
    try:
        with OPAService(opa_url=opa_url) as opa:
            # Check OPA health first
            health = opa.health_check()
            if health["status"] != "healthy":
                console.print(f"[yellow]Warning: OPA server status: {health['status']}[/yellow]")
                if verbose and "error" in health:
                    console.print(f"  {health['error']}")

            result = opa.validate_policy(policy_content)
            _format_validation_result(result, verbose)

            if not result.is_valid:
                raise typer.Exit(code=1)

    except OPAConnectionError as e:
        console.print(f"[red]Error: {e.message}[/red]")
        console.print("\n[yellow]Hint: Start OPA with:[/yellow]")
        console.print("  docker run -p 8181:8181 openpolicyagent/opa run --server")
        raise typer.Exit(code=1) from None
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(code=1) from None


@app.command()
def test(
    policy_file: Annotated[
        Path,
        typer.Argument(
            help="Path to Rego policy file to test",
            exists=False,  # We handle existence check ourselves for better error messages
        ),
    ],
    input_data: Annotated[
        str,
        typer.Option(
            "--input",
            "-i",
            help="JSON input data for policy evaluation (as string or @file path)",
        ),
    ],
    policy_path: Annotated[
        str,
        typer.Option(
            "--path",
            "-p",
            help="Policy data path to query (default: 'data' for full result)",
        ),
    ] = "data",
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed evaluation information"),
    ] = False,
    opa_url: Annotated[
        Optional[str],
        typer.Option(
            "--opa-url", help="OPA server URL (default: $OPA_URL or http://localhost:8181)"
        ),
    ] = None,
) -> None:
    """
    Test a Rego policy against sample input data.

    Evaluates the policy without affecting OPA server state (dry-run).
    Input can be provided as JSON string or file path prefixed with @.

    Examples:
        python -m cli.policy_cli test policy.rego --input '{"user": "admin", "role": "admin"}'
        python -m cli.policy_cli test policy.rego --input @input.json
        python -m cli.policy_cli test policy.rego -i '{"x": 10}' --path data.test.allow
    """
    # Read policy content
    policy_content = _read_policy_file(policy_file)

    # Parse input data
    if input_data.startswith("@"):
        # Read from file
        input_file = Path(input_data[1:])
        if not input_file.exists():
            console.print(f"[red]Error: Input file not found: {input_file}[/red]")
            raise typer.Exit(code=1)
        try:
            input_json = input_file.read_text(encoding="utf-8")
            parsed_input = _parse_json_input(input_json)
        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[red]Error reading input file: {e}[/red]")
            raise typer.Exit(code=1) from None
    else:
        parsed_input = _parse_json_input(input_data)

    if verbose:
        console.print(f"Testing: {policy_file}")
        console.print(f"Policy path: {policy_path}")
        console.print("Input data:")
        input_syntax = Syntax(json.dumps(parsed_input, indent=2), "json", theme="monokai")
        console.print(input_syntax)
        console.print()

    # Evaluate using OPA service
    try:
        with OPAService(opa_url=opa_url) as opa:
            # Check OPA health first
            health = opa.health_check()
            if health["status"] != "healthy":
                console.print(f"[yellow]Warning: OPA server status: {health['status']}[/yellow]")
                if verbose and "error" in health:
                    console.print(f"  {health['error']}")

            result = opa.evaluate_policy(
                policy_content=policy_content,
                input_data=parsed_input,
                policy_path=policy_path,
            )
            _format_evaluation_result(result, verbose)

            if not result.success:
                raise typer.Exit(code=1)

    except OPAConnectionError as e:
        console.print(f"[red]Error: {e.message}[/red]")
        console.print("\n[yellow]Hint: Start OPA with:[/yellow]")
        console.print("  docker run -p 8181:8181 openpolicyagent/opa run --server")
        raise typer.Exit(code=1) from None
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(code=1) from None


@app.command()
def health(
    opa_url: Annotated[
        Optional[str],
        typer.Option(
            "--opa-url", help="OPA server URL (default: $OPA_URL or http://localhost:8181)"
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed health information"),
    ] = False,
) -> None:
    """
    Check OPA server health status.

    Examples:
        python -m cli.policy_cli health
        python -m cli.policy_cli health --opa-url http://localhost:8181
    """
    try:
        with OPAService(opa_url=opa_url) as opa:
            health_result = opa.health_check()

            if health_result["status"] == "healthy":
                console.print("[green]✓ OPA server is healthy[/green]")
                console.print(f"  URL: {health_result['opa_url']}")
            elif health_result["status"] == "unreachable":
                console.print("[red]✗ OPA server is unreachable[/red]")
                console.print(f"  URL: {health_result['opa_url']}")
                if verbose and "error" in health_result:
                    console.print(f"  Error: {health_result['error']}")
                console.print("\n[yellow]Hint: Start OPA with:[/yellow]")
                console.print("  docker run -p 8181:8181 openpolicyagent/opa run --server")
                raise typer.Exit(code=1) from None
            else:
                console.print(f"[yellow]⚠ OPA server status: {health_result['status']}[/yellow]")
                console.print(f"  URL: {health_result['opa_url']}")
                if verbose and "error" in health_result:
                    console.print(f"  Error: {health_result['error']}")

            if verbose:
                conn_info = opa.get_connection_info()
                table = Table(title="Connection Info")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="green")
                for key, value in conn_info.items():
                    table.add_row(key, str(value))
                console.print(table)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(code=1) from None


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-V", help="Show version and exit"),
    ] = False,
) -> None:
    """
    ACGS-2 Policy CLI - Validate and test Rego policies.

    This tool provides commands for working with OPA (Open Policy Agent) policies:

    - validate: Check policy syntax and semantics
    - test: Evaluate policy against input data (dry-run)
    - health: Check OPA server status
    """
    if version:
        console.print("ACGS-2 Policy CLI v0.1.0")
        raise typer.Exit()


if __name__ == "__main__":
    app()
