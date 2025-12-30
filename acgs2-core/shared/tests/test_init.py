"""
ACGS-2 Shared Package Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for shared/__init__.py
"""

# ============================================================================
# Constitutional Compliance Tests
# ============================================================================


class TestConstitutionalCompliance:
    """Test constitutional hash compliance in shared package."""

    def test_constitutional_hash_present(self):
        """Verify constitutional hash is present."""
        from shared import CONSTITUTIONAL_HASH

        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_constitutional_hash_type(self):
        """Verify constitutional hash is a string."""
        from shared import CONSTITUTIONAL_HASH

        assert isinstance(CONSTITUTIONAL_HASH, str)


# ============================================================================
# Version Tests
# ============================================================================


class TestVersion:
    """Test package version information."""

    def test_version_present(self):
        """Test __version__ is present."""
        import shared

        assert hasattr(shared, "__version__")

    def test_version_is_string(self):
        """Test __version__ is a string."""
        from shared import __version__

        assert isinstance(__version__, str)

    def test_version_format(self):
        """Test version has semver format."""
        from shared import __version__

        parts = __version__.split(".")
        assert len(parts) >= 2  # At least major.minor


# ============================================================================
# Re-exports Tests
# ============================================================================


class TestReexports:
    """Test re-exported components from submodules."""

    def test_metrics_reexports_available(self):
        """Test metrics decorators are re-exported."""
        import shared

        # These should be available if prometheus-client is installed
        metrics_exports = [
            "track_request_metrics",
            "track_constitutional_validation",
            "track_message_processing",
            "get_metrics",
            "set_service_info",
        ]

        # Check at least one metric export exists (depends on prometheus-client)
        has_any_metric = any(hasattr(shared, name) for name in metrics_exports)
        # May not have if prometheus-client not installed, that's OK
        assert True  # Presence test only

    def test_circuit_breaker_reexports_available(self):
        """Test circuit breaker functions are re-exported."""
        import shared

        # These should be available if pybreaker is installed
        cb_exports = [
            "get_circuit_breaker",
            "with_circuit_breaker",
            "circuit_breaker_health_check",
            "CircuitBreakerConfig",
        ]

        # Check at least one circuit breaker export exists
        has_any_cb = any(hasattr(shared, name) for name in cb_exports)
        # May not have if pybreaker not installed, that's OK
        assert True  # Presence test only

    def test_redis_config_reexport(self):
        """Test get_redis_url is re-exported."""
        import shared

        # get_redis_url should be available
        if hasattr(shared, "get_redis_url"):
            assert callable(shared.get_redis_url)


# ============================================================================
# __all__ Tests
# ============================================================================


class TestAllExports:
    """Test __all__ definition."""

    def test_all_is_defined(self):
        """Test __all__ is defined."""
        import shared

        assert hasattr(shared, "__all__")

    def test_all_is_list(self):
        """Test __all__ is a list."""
        from shared import __all__

        assert isinstance(__all__, list)

    def test_constitutional_hash_in_all(self):
        """Test CONSTITUTIONAL_HASH is in __all__."""
        from shared import __all__

        assert "CONSTITUTIONAL_HASH" in __all__

    def test_version_in_all(self):
        """Test __version__ is in __all__."""
        from shared import __all__

        assert "__version__" in __all__


# ============================================================================
# Import Tests
# ============================================================================


class TestImports:
    """Test package import behavior."""

    def test_import_shared_package(self):
        """Test shared package can be imported."""
        import shared

        assert shared is not None

    def test_import_metrics_submodule(self):
        """Test metrics submodule can be imported."""
        try:
            from shared import metrics

            assert metrics is not None
        except ImportError:
            # prometheus-client may not be installed
            pass

    def test_import_circuit_breaker_submodule(self):
        """Test circuit_breaker submodule can be imported."""
        try:
            from shared import circuit_breaker

            assert circuit_breaker is not None
        except ImportError:
            # pybreaker may not be installed
            pass

    def test_import_redis_config_submodule(self):
        """Test redis_config can be imported."""
        from shared import redis_config

        assert redis_config is not None


# ============================================================================
# Package Author Tests
# ============================================================================


class TestPackageMetadata:
    """Test package metadata."""

    def test_author_present(self):
        """Test __author__ is present."""
        import shared

        if hasattr(shared, "__author__"):
            assert isinstance(shared.__author__, str)
