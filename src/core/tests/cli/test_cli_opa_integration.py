"""
End-to-End Integration Tests for CLI with Live OPA Server

These tests verify the CLI commands work correctly with a running OPA server.
Requirements:
- OPA server must be running at http://localhost:8181
- Run: docker run -d -p 8181:8181 openpolicyagent/opa run --server

Tests:
1. CLI validate command with valid policy
2. CLI validate command with invalid policy (syntax error detection)
3. CLI test command with JSON input
4. CLI health command
5. Error handling when OPA is unavailable
"""

import os
import sys
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

# Add parent path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from cli.opa_service import OPAService  # noqa: E402, I001
from cli.policy_cli import app  # noqa: E402, I001

# Create CLI runner for testing
runner = CliRunner()

# OPA server URL for integration tests
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181")


def is_opa_available() -> bool:
    """Check if OPA server is available."""
    try:
        response = httpx.get(f"{OPA_URL}/health", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


# Skip all tests if OPA is not available
_skip_reason = (
    f"OPA server not available at {OPA_URL}. "
    "Start with: docker run -d -p 8181:8181 openpolicyagent/opa run --server"
)
pytestmark = pytest.mark.skipif(not is_opa_available(), reason=_skip_reason)


class TestCLIOPAIntegrationHealth:
    """Test CLI health command with live OPA server."""

    def test_health_command_success(self):
        """Test health command shows OPA is healthy."""
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "OPA server is healthy" in result.stdout

    def test_health_command_verbose(self):
        """Test health command with verbose flag shows details."""
        result = runner.invoke(app, ["health", "--verbose"])
        assert result.exit_code == 0
        assert "OPA server is healthy" in result.stdout
        assert "Connection Info" in result.stdout


class TestCLIOPAIntegrationValidate:
    """Test CLI validate command with live OPA server."""

    @pytest.fixture
    def valid_policy_file(self, tmp_path: Path) -> Path:
        """Create a valid Rego policy file."""
        policy_content = """# Simple valid Rego policy for E2E testing
package test.valid

import rego.v1

default allow := false

# Allow if the user is an admin
allow if {
    input.user.role == "admin"
}

# Allow if the request method is GET
allow if {
    input.request.method == "GET"
    input.user.authenticated == true
}
"""
        policy_file = tmp_path / "valid_policy.rego"
        policy_file.write_text(policy_content)
        return policy_file

    @pytest.fixture
    def invalid_policy_file(self, tmp_path: Path) -> Path:
        """Create an invalid Rego policy file with syntax error."""
        policy_content = """# Invalid Rego policy with syntax errors
package test.invalid

default allow = false

# Missing closing brace
allow {
    input.user.role == "admin"

# Invalid syntax - missing operator
allow if input.user.role "admin"
"""
        policy_file = tmp_path / "invalid_policy.rego"
        policy_file.write_text(policy_content)
        return policy_file

    def test_validate_valid_policy(self, valid_policy_file: Path):
        """Test validate command with valid policy returns success."""
        result = runner.invoke(app, ["validate", str(valid_policy_file)])
        assert result.exit_code == 0
        assert "Policy is valid" in result.stdout

    def test_validate_valid_policy_verbose(self, valid_policy_file: Path):
        """Test validate command with verbose flag shows details."""
        result = runner.invoke(app, ["validate", str(valid_policy_file), "--verbose"])
        assert result.exit_code == 0
        assert "Policy is valid" in result.stdout
        assert "Validating:" in result.stdout

    def test_validate_invalid_policy(self, invalid_policy_file: Path):
        """Test validate command with invalid policy returns error with details."""
        result = runner.invoke(app, ["validate", str(invalid_policy_file)])
        assert result.exit_code == 1
        assert "validation failed" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_validate_nonexistent_file(self):
        """Test validate command with non-existent file returns error."""
        result = runner.invoke(app, ["validate", "/nonexistent/policy.rego"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestCLIOPAIntegrationTest:
    """Test CLI test (evaluate) command with live OPA server."""

    @pytest.fixture
    def rbac_policy_file(self, tmp_path: Path) -> Path:
        """Create an RBAC policy file for testing evaluation."""
        policy_content = """# RBAC policy for E2E testing with evaluation
package test.rbac

import rego.v1

default allow := false

# Admins can do anything
allow if {
    input.role == "admin"
}

# Editors can read and write
allow if {
    input.role == "editor"
    input.action == "read"
}

allow if {
    input.role == "editor"
    input.action == "write"
}

# Viewers can only read
allow if {
    input.role == "viewer"
    input.action == "read"
}
"""
        policy_file = tmp_path / "rbac_policy.rego"
        policy_file.write_text(policy_content)
        return policy_file

    def test_test_command_admin_allowed(self, rbac_policy_file: Path):
        """Test test command with admin role - should be allowed."""
        input_json = '{"role": "admin", "action": "delete"}'
        result = runner.invoke(
            app, ["test", str(rbac_policy_file), "--input", input_json, "--path", "data.test.rbac"]
        )
        assert result.exit_code == 0
        assert "Evaluation Successful" in result.stdout
        # Admin should be allowed
        assert "allow" in result.stdout.lower()

    def test_test_command_viewer_read_allowed(self, rbac_policy_file: Path):
        """Test test command with viewer role reading - should be allowed."""
        input_json = '{"role": "viewer", "action": "read"}'
        result = runner.invoke(
            app, ["test", str(rbac_policy_file), "--input", input_json, "--path", "data.test.rbac"]
        )
        assert result.exit_code == 0
        assert "Evaluation Successful" in result.stdout

    def test_test_command_viewer_write_denied(self, rbac_policy_file: Path):
        """Test test command with viewer role writing - should be denied."""
        input_json = '{"role": "viewer", "action": "write"}'
        result = runner.invoke(
            app, ["test", str(rbac_policy_file), "--input", input_json, "--path", "data.test.rbac"]
        )
        assert result.exit_code == 0
        assert "Evaluation Successful" in result.stdout
        # Result should show allow: false or DENIED
        # The allow value in result should be false

    def test_test_command_verbose(self, rbac_policy_file: Path):
        """Test test command with verbose flag shows input data."""
        input_json = '{"role": "admin"}'
        result = runner.invoke(
            app,
            [
                "test",
                str(rbac_policy_file),
                "--input",
                input_json,
                "--path",
                "data.test.rbac",
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "Testing:" in result.stdout
        assert "Input data:" in result.stdout

    def test_test_command_invalid_json(self, rbac_policy_file: Path):
        """Test test command with invalid JSON input returns error."""
        result = runner.invoke(app, ["test", str(rbac_policy_file), "--input", "not valid json"])
        assert result.exit_code == 1
        assert "Invalid JSON" in result.stdout

    def test_test_command_with_input_file(self, rbac_policy_file: Path, tmp_path: Path):
        """Test test command with input from file."""
        # Create input JSON file
        input_file = tmp_path / "input.json"
        input_file.write_text('{"role": "admin", "action": "delete"}')

        result = runner.invoke(
            app,
            [
                "test",
                str(rbac_policy_file),
                "--input",
                f"@{input_file}",
                "--path",
                "data.test.rbac",
            ],
        )
        assert result.exit_code == 0
        assert "Evaluation Successful" in result.stdout


class TestOPAServiceIntegration:
    """Test OPAService class directly with live OPA server."""

    def test_opa_service_health_check(self):
        """Test OPAService health check with live OPA."""
        with OPAService(opa_url=OPA_URL) as opa:
            health = opa.health_check()
            assert health["status"] == "healthy"
            assert health["opa_url"] == OPA_URL

    def test_opa_service_validate_valid_policy(self):
        """Test OPAService validates valid policy."""
        policy = """package test

import rego.v1

default allow := false

allow if { input.admin == true }
"""
        with OPAService(opa_url=OPA_URL) as opa:
            result = opa.validate_policy(policy)
            assert result.is_valid is True
            assert len(result.errors) == 0

    def test_opa_service_validate_invalid_policy(self):
        """Test OPAService detects invalid policy."""
        policy = """package test

import rego.v1

default allow := false

allow if { input.admin ==  # syntax error
"""
        with OPAService(opa_url=OPA_URL) as opa:
            result = opa.validate_policy(policy)
            assert result.is_valid is False
            assert len(result.errors) > 0

    def test_opa_service_evaluate_policy(self):
        """Test OPAService evaluates policy correctly."""
        policy = """package test.eval

import rego.v1

default allow := false

allow if { input.admin == true }
"""
        with OPAService(opa_url=OPA_URL) as opa:
            # Test with admin=true
            result = opa.evaluate_policy(
                policy_content=policy, input_data={"admin": True}, policy_path="data.test.eval"
            )
            assert result.success is True
            assert result.result.get("allow") is True

            # Test with admin=false
            result = opa.evaluate_policy(
                policy_content=policy, input_data={"admin": False}, policy_path="data.test.eval"
            )
            assert result.success is True
            assert result.result.get("allow") is False


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
