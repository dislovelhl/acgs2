"""
ACGS-2 Enhanced Agent Bus - Import Utilities Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for the import utility functions in imports.py.
"""

# Import the utilities we're testing
from src.core.enhanced_agent_bus.imports import (
    get_import_status,
    import_with_fallback,
    optional_import,
    try_import,
    try_relative_import,
)


class TestTryImport:
    """Tests for try_import utility."""

    def test_successful_relative_import(self) -> None:
        """Test that try_import works with valid relative path."""
        success, imports = try_import(".models", "models", ["AgentMessage"])
        assert success is True
        assert "AgentMessage" in imports
        assert imports["AgentMessage"] is not None

    def test_successful_absolute_import_fallback(self) -> None:
        """Test that try_import falls back to absolute import."""
        # Use a module that exists in Python stdlib
        success, imports = try_import(".nonexistent", "os", ["path"])
        assert success is True
        assert "path" in imports

    def test_failed_import_returns_false(self) -> None:
        """Test that try_import returns False when both imports fail."""
        success, imports = try_import(".nonexistent", "also_nonexistent", ["Foo"])
        assert success is False
        assert imports == {}

    def test_multiple_names_imported(self) -> None:
        """Test importing multiple names at once."""
        success, imports = try_import(
            ".models", "models", ["AgentMessage", "MessageType", "Priority"]
        )
        assert success is True
        assert len(imports) == 3
        assert all(name in imports for name in ["AgentMessage", "MessageType", "Priority"])


class TestImportWithFallback:
    """Tests for import_with_fallback utility."""

    def test_first_module_success(self) -> None:
        """Test that first available module is used."""
        imports = import_with_fallback(
            ["enhanced_agent_bus.models", "os"],
            ["AgentMessage"],
        )
        assert "AgentMessage" in imports
        assert imports["AgentMessage"] is not None

    def test_fallback_to_second_module(self) -> None:
        """Test fallback to second module when first fails."""
        imports = import_with_fallback(
            ["nonexistent_module", "os"],
            ["path"],
        )
        assert "path" in imports
        assert imports["path"] is not None

    def test_default_values_used_on_failure(self) -> None:
        """Test that default values are returned when all imports fail."""
        imports = import_with_fallback(
            ["nonexistent1", "nonexistent2"],
            ["Foo", "Bar"],
            {"Foo": "default_foo", "Bar": "default_bar"},
        )
        assert imports["Foo"] == "default_foo"
        assert imports["Bar"] == "default_bar"

    def test_none_defaults_on_failure(self) -> None:
        """Test that None is returned for each name when no defaults provided."""
        imports = import_with_fallback(
            ["nonexistent"],
            ["Foo", "Bar"],
        )
        assert imports["Foo"] is None
        assert imports["Bar"] is None

    def test_constitutional_hash_fallback(self) -> None:
        """Test typical use case: CONSTITUTIONAL_HASH with fallback."""
        imports = import_with_fallback(
            ["shared.constants", "enhanced_agent_bus.models"],
            ["CONSTITUTIONAL_HASH"],
            {"CONSTITUTIONAL_HASH": "cdd01ef066bc6cf2"},
        )
        assert imports["CONSTITUTIONAL_HASH"] == "cdd01ef066bc6cf2"


class TestOptionalImport:
    """Tests for optional_import utility."""

    def test_successful_import(self) -> None:
        """Test successful optional import."""
        path = optional_import("os", "path")
        assert path is not None

    def test_failed_import_returns_default(self) -> None:
        """Test that default is returned on failed import."""
        result = optional_import("nonexistent_module", "Foo", default="fallback")
        assert result == "fallback"

    def test_none_default(self) -> None:
        """Test that None is returned by default."""
        result = optional_import("nonexistent_module", "Foo")
        assert result is None

    def test_missing_attribute_returns_default(self) -> None:
        """Test that default is returned when attribute doesn't exist."""
        result = optional_import("os", "nonexistent_attribute", default="fallback")
        assert result == "fallback"


class TestTryRelativeImport:
    """Tests for try_relative_import utility."""

    def test_relative_import_success(self) -> None:
        """Test successful relative import."""
        result = try_relative_import(".models", "models", "AgentMessage")
        assert result is not None

    def test_absolute_import_fallback(self) -> None:
        """Test fallback to absolute import."""
        result = try_relative_import(".nonexistent", "os", "path")
        assert result is not None

    def test_default_on_failure(self) -> None:
        """Test default value returned on failure."""
        result = try_relative_import(
            ".nonexistent", "also_nonexistent", "Foo", default="default_value"
        )
        assert result == "default_value"

    def test_none_default(self) -> None:
        """Test None returned by default on failure."""
        result = try_relative_import(".nonexistent", "also_nonexistent", "Foo")
        assert result is None


class TestGetImportStatus:
    """Tests for get_import_status utility."""

    def test_returns_dict(self) -> None:
        """Test that get_import_status returns a dictionary."""
        status = get_import_status()
        assert isinstance(status, dict)

    def test_contains_expected_keys(self) -> None:
        """Test that status contains expected keys."""
        status = get_import_status()
        expected_keys = [
            "metrics_enabled",
            "otel_enabled",
            "circuit_breaker_enabled",
            "policy_client_available",
            "deliberation_available",
            "crypto_available",
            "config_available",
            "audit_client_available",
            "opa_client_available",
            "use_rust",
            "metering_available",
            "default_redis_url",
        ]
        for key in expected_keys:
            assert key in status, f"Missing key: {key}"

    def test_values_are_booleans_or_strings(self) -> None:
        """Test that values are appropriate types."""
        status = get_import_status()
        for key, value in status.items():
            if key == "default_redis_url":
                assert isinstance(value, str)
            else:
                assert isinstance(value, bool), f"{key} should be bool, got {type(value)}"


class TestIntegration:
    """Integration tests for import utilities."""

    def test_import_utilities_work_together(self) -> None:
        """Test that utilities can be used in combination."""
        # First check if something is available
        status = get_import_status()

        # Then try importing based on availability
        if status.get("policy_client_available"):
            result = optional_import("enhanced_agent_bus.policy_client", "PolicyClient")
            # If status says available, import should succeed
            # (Note: may still be None if the module structure differs)

        # Use fallback pattern
        imports = import_with_fallback(
            ["shared.constants", "enhanced_agent_bus.models"],
            ["CONSTITUTIONAL_HASH"],
            {"CONSTITUTIONAL_HASH": "cdd01ef066bc6cf2"},
        )
        assert imports["CONSTITUTIONAL_HASH"] is not None

    def test_type_hints_work_correctly(self) -> None:
        """Test that type hints are correct for the utilities."""
        # try_import returns tuple[bool, dict[str, Any]]
        success, imports = try_import(".models", "models", ["AgentMessage"])
        assert isinstance(success, bool)
        assert isinstance(imports, dict)

        # import_with_fallback returns dict[str, Any]
        result = import_with_fallback(["os"], ["path"])
        assert isinstance(result, dict)

        # optional_import returns Any
        value = optional_import("os", "path")
        # Just verify it doesn't raise

        # try_relative_import returns Any
        value = try_relative_import(".models", "models", "AgentMessage")
        # Just verify it doesn't raise
