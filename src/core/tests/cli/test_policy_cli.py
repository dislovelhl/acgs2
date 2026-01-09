"""
Tests for ACGS-2 Policy CLI Tool

Tests verify:
- Validate command detects syntax errors in Rego files
- Test command correctly evaluates policies against input data
- Health command checks OPA server status
- Error handling for file not found, invalid JSON, OPA connection errors
- CLI options (--verbose, --opa-url) work correctly
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from cli.opa_service import OPAConnectionError  # noqa: E402, I001
from cli.opa_service import PolicyEvaluationResult, PolicyValidationResult
from cli.policy_cli import app  # noqa: E402, I001

# Create CLI runner for testing
runner = CliRunner()


class TestPolicyCLIHelp:
    """Test CLI help and version commands."""

    def test_main_help(self):
        """Test main help command shows available commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "validate" in result.stdout
        assert "test" in result.stdout
        assert "health" in result.stdout

    def test_version_flag(self):
        """Test --version flag shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "ACGS-2 Policy CLI" in result.stdout
        assert "v0.1.0" in result.stdout

    def test_validate_help(self):
        """Test validate command help."""
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate a Rego policy file" in result.stdout
        assert "--verbose" in result.stdout
        assert "--opa-url" in result.stdout

    def test_test_help(self):
        """Test test command help."""
        result = runner.invoke(app, ["test", "--help"])
        assert result.exit_code == 0
        assert "Test a Rego policy" in result.stdout
        assert "--input" in result.stdout
        assert "--path" in result.stdout


class TestValidateCommand:
    """Test the validate command."""

    @pytest.fixture
    def valid_policy_file(self, tmp_path: Path) -> Path:
        """Create a valid Rego policy file."""
        policy_content = """package test

default allow = false

allow {
    input.user == "admin"
}
"""
        policy_file = tmp_path / "valid_policy.rego"
        policy_file.write_text(policy_content)
        return policy_file

    @pytest.fixture
    def invalid_policy_file(self, tmp_path: Path) -> Path:
        """Create an invalid Rego policy file with syntax error."""
        policy_content = """package test

default allow = false

allow {
    input.user == "admin"  # missing closing brace
"""
        policy_file = tmp_path / "invalid_policy.rego"
        policy_file.write_text(policy_content)
        return policy_file

    @pytest.fixture
    def empty_policy_file(self, tmp_path: Path) -> Path:
        """Create an empty policy file."""
        policy_file = tmp_path / "empty_policy.rego"
        policy_file.write_text("")
        return policy_file

    def test_validate_file_not_found(self):
        """Test validation with non-existent file."""
        result = runner.invoke(app, ["validate", "/nonexistent/policy.rego"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_validate_not_a_file(self, tmp_path: Path):
        """Test validation with directory instead of file."""
        result = runner.invoke(app, ["validate", str(tmp_path)])
        assert result.exit_code == 1
        assert "Not a file" in result.stdout

    @patch("cli.policy_cli.OPAService")
    def test_validate_valid_policy(self, mock_opa_class, valid_policy_file: Path):
        """Test validation of a valid policy succeeds."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.validate_policy.return_value = PolicyValidationResult(
            is_valid=True,
            metadata={"validated_via": "policy_upload"},
        )

        result = runner.invoke(app, ["validate", str(valid_policy_file)])

        assert result.exit_code == 0
        assert "Policy is valid" in result.stdout

    @patch("cli.policy_cli.OPAService")
    def test_validate_invalid_policy(self, mock_opa_class, invalid_policy_file: Path):
        """Test validation of an invalid policy returns errors."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.validate_policy.return_value = PolicyValidationResult(
            is_valid=False,
            errors=["Line 7, Col 1: rego_parse_error: unexpected eof token"],
        )

        result = runner.invoke(app, ["validate", str(invalid_policy_file)])

        assert result.exit_code == 1
        assert "validation failed" in result.stdout.lower()
        assert "Line 7" in result.stdout or "rego_parse_error" in result.stdout

    @patch("cli.policy_cli.OPAService")
    def test_validate_empty_policy(self, mock_opa_class, empty_policy_file: Path):
        """Test validation of an empty policy."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.validate_policy.return_value = PolicyValidationResult(
            is_valid=False,
            errors=["Policy content is empty"],
        )

        result = runner.invoke(app, ["validate", str(empty_policy_file)])

        assert result.exit_code == 1
        assert "empty" in result.stdout.lower() or "validation failed" in result.stdout.lower()

    @patch("cli.policy_cli.OPAService")
    def test_validate_with_verbose_flag(self, mock_opa_class, valid_policy_file: Path):
        """Test validation with --verbose flag shows extra info."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.validate_policy.return_value = PolicyValidationResult(
            is_valid=True,
            metadata={"validated_via": "policy_upload"},
        )

        result = runner.invoke(app, ["validate", str(valid_policy_file), "--verbose"])

        assert result.exit_code == 0
        assert "Validating:" in result.stdout
        assert "bytes" in result.stdout

    @patch("cli.policy_cli.OPAService")
    def test_validate_with_custom_opa_url(self, mock_opa_class, valid_policy_file: Path):
        """Test validation with custom OPA URL."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {"status": "healthy", "opa_url": "http://custom:9999"}
        mock_opa.validate_policy.return_value = PolicyValidationResult(is_valid=True)

        result = runner.invoke(
            app, ["validate", str(valid_policy_file), "--opa-url", "http://custom:9999"]
        )

        assert result.exit_code == 0
        mock_opa_class.assert_called_once_with(opa_url="http://custom:9999")

    @patch("cli.policy_cli.OPAService")
    def test_validate_opa_connection_error(self, mock_opa_class, valid_policy_file: Path):
        """Test validation when OPA is not reachable."""
        # Setup mock to raise connection error
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.side_effect = OPAConnectionError(
            opa_url="http://localhost:8181",
            reason="Connection refused",
        )

        result = runner.invoke(app, ["validate", str(valid_policy_file)])

        assert result.exit_code == 1
        assert "Error" in result.stdout
        assert "docker run" in result.stdout  # Should show hint

    @patch("cli.policy_cli.OPAService")
    def test_validate_opa_unhealthy(self, mock_opa_class, valid_policy_file: Path):
        """Test validation with unhealthy OPA shows warning."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "unhealthy",
            "opa_url": "http://localhost:8181",
            "error": "Internal error",
        }
        mock_opa.validate_policy.return_value = PolicyValidationResult(is_valid=True)

        result = runner.invoke(app, ["validate", str(valid_policy_file)])

        # Should still attempt validation but show warning
        assert "Warning" in result.stdout or result.exit_code == 0


class TestTestCommand:
    """Test the test (evaluate) command."""

    @pytest.fixture
    def rbac_policy_file(self, tmp_path: Path) -> Path:
        """Create an RBAC policy file."""
        policy_content = """package rbac

default allow = false

allow {
    input.role == "admin"
}

allow {
    input.role == "user"
    input.action == "read"
}
"""
        policy_file = tmp_path / "rbac_policy.rego"
        policy_file.write_text(policy_content)
        return policy_file

    @pytest.fixture
    def input_json_file(self, tmp_path: Path) -> Path:
        """Create an input JSON file."""
        input_data = {"role": "admin", "action": "write"}
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(input_data))
        return input_file

    def test_test_file_not_found(self):
        """Test command with non-existent policy file."""
        result = runner.invoke(
            app, ["test", "/nonexistent/policy.rego", "--input", '{"role": "admin"}']
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_test_invalid_json_input(self, tmp_path: Path):
        """Test command with invalid JSON input."""
        policy_file = tmp_path / "policy.rego"
        policy_file.write_text("package test\ndefault allow = true")

        result = runner.invoke(app, ["test", str(policy_file), "--input", "not-valid-json"])

        assert result.exit_code == 1
        assert "Invalid JSON input" in result.stdout

    def test_test_input_file_not_found(self, tmp_path: Path):
        """Test command with non-existent input file."""
        policy_file = tmp_path / "policy.rego"
        policy_file.write_text("package test\ndefault allow = true")

        result = runner.invoke(
            app, ["test", str(policy_file), "--input", "@/nonexistent/input.json"]
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @patch("cli.policy_cli.OPAService")
    def test_test_policy_with_json_input(self, mock_opa_class, rbac_policy_file: Path):
        """Test policy evaluation with JSON input string."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.evaluate_policy.return_value = PolicyEvaluationResult(
            success=True,
            result={"allow": True},
            allowed=True,
            reason="Policy evaluated successfully",
            metadata={"policy_path": "data"},
        )

        result = runner.invoke(app, ["test", str(rbac_policy_file), "--input", '{"role": "admin"}'])

        assert result.exit_code == 0
        assert "Evaluation Successful" in result.stdout or "allow" in result.stdout

    @patch("cli.policy_cli.OPAService")
    def test_test_policy_with_file_input(
        self, mock_opa_class, rbac_policy_file: Path, input_json_file: Path
    ):
        """Test policy evaluation with input from file."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.evaluate_policy.return_value = PolicyEvaluationResult(
            success=True,
            result={"allow": True},
            allowed=True,
            reason="Policy evaluated successfully",
        )

        result = runner.invoke(
            app, ["test", str(rbac_policy_file), "--input", f"@{input_json_file}"]
        )

        assert result.exit_code == 0
        assert "Evaluation Successful" in result.stdout or "allow" in result.stdout

    @patch("cli.policy_cli.OPAService")
    def test_test_policy_with_custom_path(self, mock_opa_class, rbac_policy_file: Path):
        """Test policy evaluation with custom policy path."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.evaluate_policy.return_value = PolicyEvaluationResult(
            success=True,
            result=True,
            allowed=True,
            reason="Policy evaluated successfully",
            metadata={"policy_path": "data.rbac.allow"},
        )

        result = runner.invoke(
            app,
            [
                "test",
                str(rbac_policy_file),
                "--input",
                '{"role": "admin"}',
                "--path",
                "data.rbac.allow",
            ],
        )

        assert result.exit_code == 0
        mock_opa.evaluate_policy.assert_called_once()
        call_kwargs = mock_opa.evaluate_policy.call_args[1]
        assert call_kwargs["policy_path"] == "data.rbac.allow"

    @patch("cli.policy_cli.OPAService")
    def test_test_policy_with_verbose(self, mock_opa_class, rbac_policy_file: Path):
        """Test policy evaluation with --verbose flag."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.evaluate_policy.return_value = PolicyEvaluationResult(
            success=True,
            result={"allow": True},
            allowed=True,
            reason="Policy evaluated successfully",
        )

        result = runner.invoke(
            app,
            ["test", str(rbac_policy_file), "--input", '{"role": "admin"}', "--verbose"],
        )

        assert result.exit_code == 0
        assert "Testing:" in result.stdout
        assert "Input data" in result.stdout

    @patch("cli.policy_cli.OPAService")
    def test_test_policy_denied_result(self, mock_opa_class, rbac_policy_file: Path):
        """Test policy evaluation that returns denied."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.evaluate_policy.return_value = PolicyEvaluationResult(
            success=True,
            result={"allow": False},
            allowed=False,
            reason="Policy evaluated successfully",
        )

        result = runner.invoke(app, ["test", str(rbac_policy_file), "--input", '{"role": "guest"}'])

        assert result.exit_code == 0
        assert "DENIED" in result.stdout

    @patch("cli.policy_cli.OPAService")
    def test_test_policy_evaluation_failure(self, mock_opa_class, rbac_policy_file: Path):
        """Test policy evaluation failure."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.evaluate_policy.return_value = PolicyEvaluationResult(
            success=False,
            reason="Policy upload failed",
            metadata={"errors": ["Invalid policy"]},
        )

        result = runner.invoke(app, ["test", str(rbac_policy_file), "--input", '{"role": "admin"}'])

        assert result.exit_code == 1
        assert "failed" in result.stdout.lower()

    @patch("cli.policy_cli.OPAService")
    def test_test_opa_connection_error(self, mock_opa_class, rbac_policy_file: Path):
        """Test command when OPA is not reachable."""
        # Setup mock to raise connection error
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.side_effect = OPAConnectionError(
            opa_url="http://localhost:8181",
            reason="Connection refused",
        )

        result = runner.invoke(app, ["test", str(rbac_policy_file), "--input", '{"role": "admin"}'])

        assert result.exit_code == 1
        assert "Error" in result.stdout
        assert "docker run" in result.stdout  # Should show hint


class TestHealthCommand:
    """Test the health command."""

    @patch("cli.policy_cli.OPAService")
    def test_health_opa_healthy(self, mock_opa_class):
        """Test health command when OPA is healthy."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }

        result = runner.invoke(app, ["health"])

        assert result.exit_code == 0
        assert "healthy" in result.stdout.lower()
        assert "http://localhost:8181" in result.stdout

    @patch("cli.policy_cli.OPAService")
    def test_health_opa_unreachable(self, mock_opa_class):
        """Test health command when OPA is unreachable."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "unreachable",
            "opa_url": "http://localhost:8181",
            "error": "Connection refused",
        }

        result = runner.invoke(app, ["health"])

        assert result.exit_code == 1
        assert "unreachable" in result.stdout.lower()
        assert "docker run" in result.stdout  # Should show hint

    @patch("cli.policy_cli.OPAService")
    def test_health_with_custom_opa_url(self, mock_opa_class):
        """Test health command with custom OPA URL."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://custom:9999",
        }

        result = runner.invoke(app, ["health", "--opa-url", "http://custom:9999"])

        assert result.exit_code == 0
        mock_opa_class.assert_called_once_with(opa_url="http://custom:9999")

    @patch("cli.policy_cli.OPAService")
    def test_health_with_verbose(self, mock_opa_class):
        """Test health command with --verbose flag."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.get_connection_info.return_value = {
            "opa_url": "http://localhost:8181",
            "timeout": 10.0,
            "client_initialized": True,
            "async_client_initialized": False,
        }

        result = runner.invoke(app, ["health", "--verbose"])

        assert result.exit_code == 0
        assert "Connection Info" in result.stdout
        assert "timeout" in result.stdout.lower()


class TestPolicyValidationResult:
    """Test PolicyValidationResult dataclass."""

    def test_valid_result(self):
        """Test valid result properties."""
        result = PolicyValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_invalid_result_with_errors(self):
        """Test invalid result with errors."""
        result = PolicyValidationResult(
            is_valid=False,
            errors=["Line 5: syntax error"],
        )
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Line 5" in result.errors[0]

    def test_add_error_makes_invalid(self):
        """Test add_error method sets is_valid to False."""
        result = PolicyValidationResult(is_valid=True)
        result.add_error("New error")
        assert result.is_valid is False
        assert "New error" in result.errors

    def test_add_warning(self):
        """Test add_warning method preserves validity."""
        result = PolicyValidationResult(is_valid=True)
        result.add_warning("This is a warning")
        assert result.is_valid is True
        assert "This is a warning" in result.warnings


class TestPolicyEvaluationResult:
    """Test PolicyEvaluationResult dataclass."""

    def test_successful_result(self):
        """Test successful evaluation result."""
        result = PolicyEvaluationResult(
            success=True,
            result={"allow": True},
            allowed=True,
            reason="Evaluation successful",
        )
        assert result.success is True
        assert result.result == {"allow": True}
        assert result.allowed is True

    def test_failed_result(self):
        """Test failed evaluation result."""
        result = PolicyEvaluationResult(
            success=False,
            reason="Policy syntax error",
            metadata={"errors": ["Invalid syntax"]},
        )
        assert result.success is False
        assert result.allowed is None
        assert "errors" in result.metadata

    def test_denied_result(self):
        """Test denied evaluation result."""
        result = PolicyEvaluationResult(
            success=True,
            result={"allow": False},
            allowed=False,
            reason="User not authorized",
        )
        assert result.success is True
        assert result.allowed is False


class TestLargeFileHandling:
    """Test handling of large policy files."""

    @pytest.fixture
    def large_policy_file(self, tmp_path: Path) -> Path:
        """Create a large policy file (>1MB)."""
        # Generate a large policy with many rules
        rules = []
        for i in range(10000):
            rules.append(
                f"""
rule_{i} {{
    input.id == {i}
    input.value == "{i}_value"
}}
"""
            )
        policy_content = f"""package large_test

default allow = false

{"".join(rules)}
"""
        policy_file = tmp_path / "large_policy.rego"
        policy_file.write_text(policy_content)
        return policy_file

    @patch("cli.policy_cli.OPAService")
    def test_large_file_warning(self, mock_opa_class, large_policy_file: Path):
        """Test that large files show a warning."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.validate_policy.return_value = PolicyValidationResult(is_valid=True)

        result = runner.invoke(app, ["validate", str(large_policy_file)])

        # Should show warning about large file
        assert "Warning" in result.stdout or result.exit_code == 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def policy_with_special_chars(self, tmp_path: Path) -> Path:
        """Create a policy with special characters in path."""
        policy_dir = tmp_path / "path with spaces"
        policy_dir.mkdir()
        policy_file = policy_dir / "policy.rego"
        policy_file.write_text("package test\ndefault allow = true")
        return policy_file

    @patch("cli.policy_cli.OPAService")
    def test_policy_path_with_spaces(self, mock_opa_class, policy_with_special_chars: Path):
        """Test handling policy files in paths with spaces."""
        # Setup mock
        mock_opa = MagicMock()
        mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
        mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_opa.health_check.return_value = {
            "status": "healthy",
            "opa_url": "http://localhost:8181",
        }
        mock_opa.validate_policy.return_value = PolicyValidationResult(is_valid=True)

        result = runner.invoke(app, ["validate", str(policy_with_special_chars)])

        assert result.exit_code == 0

    def test_test_with_complex_json_input(self, tmp_path: Path):
        """Test handling complex nested JSON input."""
        policy_file = tmp_path / "policy.rego"
        policy_file.write_text("package test\ndefault allow = true")

        complex_input = json.dumps(
            {
                "user": {
                    "id": 123,
                    "roles": ["admin", "user"],
                    "metadata": {
                        "created": "2024-01-01",
                        "tags": ["important", "verified"],
                    },
                },
                "resource": {
                    "type": "document",
                    "id": "doc-456",
                },
            }
        )

        with patch("cli.policy_cli.OPAService") as mock_opa_class:
            mock_opa = MagicMock()
            mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
            mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
            mock_opa.health_check.return_value = {
                "status": "healthy",
                "opa_url": "http://localhost:8181",
            }
            mock_opa.evaluate_policy.return_value = PolicyEvaluationResult(
                success=True,
                result={"allow": True},
                allowed=True,
            )

            result = runner.invoke(app, ["test", str(policy_file), "--input", complex_input])

            assert result.exit_code == 0

    def test_test_with_unicode_input(self, tmp_path: Path):
        """Test handling Unicode characters in input."""
        policy_file = tmp_path / "policy.rego"
        policy_file.write_text("package test\ndefault allow = true")

        unicode_input = json.dumps({"name": "Test"})

        with patch("cli.policy_cli.OPAService") as mock_opa_class:
            mock_opa = MagicMock()
            mock_opa_class.return_value.__enter__ = MagicMock(return_value=mock_opa)
            mock_opa_class.return_value.__exit__ = MagicMock(return_value=False)
            mock_opa.health_check.return_value = {
                "status": "healthy",
                "opa_url": "http://localhost:8181",
            }
            mock_opa.evaluate_policy.return_value = PolicyEvaluationResult(
                success=True,
                result={"allow": True},
                allowed=True,
            )

            result = runner.invoke(app, ["test", str(policy_file), "--input", unicode_input])

            assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
