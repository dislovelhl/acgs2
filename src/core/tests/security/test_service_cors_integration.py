"""
Integration Tests for Service CORS Configuration
Constitutional Hash: cdd01ef066bc6cf2

Verifies that all ACGS-2 services properly reject wildcard CORS in production
and implement secure CORS configuration across different environments.

Test Coverage:
- Services using shared CORS config module
- Services with inline CORS implementation
- Production wildcard blocking
- Development localhost defaults
- Environment variable configuration
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest


class TestServiceCORSIntegration:
    """Integration tests for service CORS configuration."""

    # Services that should use shared CORS config module
    SHARED_MODULE_SERVICES = [
        "src/core/services/compliance_docs/src/main.py",
        "src/core/services/ml_governance/src/main.py",
        "src/core/services/hitl_approvals/src/main.py",
        "src/core/services/analytics-api/src/main.py",
        "src/integration-service/integration-service/src/main.py",
    ]

    # Services with inline CORS implementation
    INLINE_CORS_SERVICES = [
        "src/adaptive-learning/adaptive-learning-engine/src/main.py",
        "examples/02-ai-model-approval/app.py",
    ]

    @staticmethod
    def _get_repo_root() -> Path:
        """Get repository root directory."""
        current = Path(__file__).resolve()
        # Navigate up from src/core/tests/security/test_service_cors_integration.py
        return current.parent.parent.parent.parent.parent

    @staticmethod
    def _read_service_file(relative_path: str) -> Optional[str]:
        """Read service file content."""
        repo_root = TestServiceCORSIntegration._get_repo_root()
        file_path = repo_root / relative_path

        if not file_path.exists():
            return None

        return file_path.read_text()

    @staticmethod
    def _check_wildcard_in_source(content: str) -> List[Tuple[int, str]]:
        """
        Check for wildcard CORS patterns in source code.

        Returns:
            List of (line_number, line_content) tuples with wildcard patterns
        """
        wildcard_patterns = [
            r"allow_origins\s*=\s*\[.*['\"]?\*['\"]?.*\]",
            r"CORS_ORIGINS.*=.*['\"]?\*['\"]?",
            r"\.getenv\(['\"]CORS_ORIGINS['\"],\s*['\"]?\*['\"]?\)",
        ]

        violations = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith("#"):
                continue

            for pattern in wildcard_patterns:
                if re.search(pattern, line):
                    violations.append((line_num, line.strip()))

        return violations

    @staticmethod
    def _check_uses_shared_cors_config(content: str) -> bool:
        """Check if service uses shared CORS config module."""
        import_patterns = [
            r"from\s+(src\.core\.)?shared\.security\.cors_config\s+import\s+get_cors_config",
            r"import\s+(src\.core\.)?shared\.security\.cors_config",
            r"from\s+(src\.core\.)?shared\.security\s+import[\s\S]*?get_cors_config",
        ]

        for pattern in import_patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True

        return False

    @staticmethod
    def _check_uses_cors_middleware(content: str) -> bool:
        """Check if service uses get_cors_config() with middleware."""
        middleware_pattern = r"add_middleware\s*\(\s*CORSMiddleware\s*,\s*\*\*get_cors_config\(\)"
        return bool(re.search(middleware_pattern, content))

    @staticmethod
    def _check_inline_cors_validation(content: str) -> Dict[str, bool]:
        """
        Check if service has inline CORS validation for production.

        Returns:
            Dict with validation checks
        """
        checks = {
            "has_environment_check": False,
            "blocks_wildcard_in_production": False,
            "requires_explicit_origins_in_production": False,
            "has_https_validation": False,
        }

        # Check for environment detection
        env_patterns = [
            r"ENVIRONMENT\s*=\s*os\.getenv",
            r"if\s+ENVIRONMENT\.lower\(\)\s+in",
        ]
        for pattern in env_patterns:
            if re.search(pattern, content):
                checks["has_environment_check"] = True
                break

        # Check for wildcard blocking in production
        wildcard_block_patterns = [
            r"if\s+['\"]?\*['\"]?\s+in\s+origins",
            r"SECURITY\s+ERROR.*Wildcard.*not\s+allowed",
            r"ValueError.*Wildcard.*production",
        ]
        for pattern in wildcard_block_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                checks["blocks_wildcard_in_production"] = True
                break

        # Check for explicit origins requirement in production
        explicit_patterns = [
            r"CORS_ORIGINS.*must\s+be.*explicitly\s+set",
            r"if\s+not\s+cors_env_var",
        ]
        for pattern in explicit_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                checks["requires_explicit_origins_in_production"] = True
                break

        # Check for HTTPS validation
        https_patterns = [
            r"startswith\(['\"]https://['\"]",
            r"HTTPS.*production",
        ]
        for pattern in https_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                checks["has_https_validation"] = True
                break

        return checks

    def test_no_hardcoded_wildcard_cors(self):
        """Verify no service has hardcoded wildcard CORS."""
        all_services = self.SHARED_MODULE_SERVICES + self.INLINE_CORS_SERVICES
        violations = {}

        for service_path in all_services:
            content = self._read_service_file(service_path)
            if content is None:
                pytest.skip(f"Service file not found: {service_path}")

            wildcard_violations = self._check_wildcard_in_source(content)
            if wildcard_violations:
                violations[service_path] = wildcard_violations

        if violations:
            error_msg = "Found hardcoded wildcard CORS in services:\n"
            for service, lines in violations.items():
                error_msg += f"\n{service}:\n"
                for line_num, line in lines:
                    error_msg += f"  Line {line_num}: {line}\n"

            pytest.fail(error_msg)

    def test_shared_module_services_use_get_cors_config(self):
        """Verify services in the core package use shared CORS config module."""
        for service_path in self.SHARED_MODULE_SERVICES:
            content = self._read_service_file(service_path)
            if content is None:
                pytest.skip(f"Service file not found: {service_path}")

            # Check imports shared CORS config
            assert self._check_uses_shared_cors_config(content), (
                f"{service_path} should import get_cors_config from shared.security.cors_config"
            )

            # Check uses get_cors_config() with middleware
            assert self._check_uses_cors_middleware(content), (
                f"{service_path} should use app.add_middleware(CORSMiddleware, **get_cors_config())"
            )

    def test_inline_services_have_production_validation(self):
        """Verify services with inline CORS have proper production validation."""
        for service_path in self.INLINE_CORS_SERVICES:
            content = self._read_service_file(service_path)
            if content is None:
                pytest.skip(f"Service file not found: {service_path}")

            checks = self._check_inline_cors_validation(content)

            # All inline services must have environment checking
            assert checks["has_environment_check"], (
                f"{service_path} must detect environment (e.g., ENVIRONMENT = os.getenv(...))"
            )

            # Must block wildcards in production
            assert checks["blocks_wildcard_in_production"], (
                f"{service_path} must validate and block wildcard origins in production environment"
            )

            # Should require explicit origins in production
            assert checks["requires_explicit_origins_in_production"], (
                f"{service_path} should require explicit CORS_ORIGINS in production environment"
            )

    def test_shared_cors_module_blocks_wildcard_in_production(self, monkeypatch):
        """Test that shared CORS module blocks wildcards in production."""
        import sys

        # Add repo root to path for src.core imports
        repo_root = self._get_repo_root()
        sys.path.insert(0, str(repo_root))

        try:
            from src.core.shared.security.cors_config import CORSConfig, CORSEnvironment

            # Test wildcard blocking in production
            monkeypatch.setenv("ENVIRONMENT", "production")

            with pytest.raises(ValueError) as exc_info:
                CORSConfig(
                    allow_origins=["*"],
                    allow_credentials=True,
                    environment=CORSEnvironment.PRODUCTION,
                )

            assert "SECURITY ERROR" in str(exc_info.value)

            # Test wildcard without credentials also blocked
            with pytest.raises(ValueError) as exc_info:
                CORSConfig(
                    allow_origins=["*"],
                    allow_credentials=False,
                    environment=CORSEnvironment.PRODUCTION,
                )

            assert "Wildcard origins not allowed in production" in str(exc_info.value)
        finally:
            sys.path.remove(str(repo_root))

    def test_shared_cors_module_allows_localhost_in_development(self, monkeypatch):
        """Test that shared CORS module allows localhost in development."""
        import sys

        repo_root = self._get_repo_root()
        sys.path.insert(0, str(repo_root))

        try:
            from src.core.shared.security.cors_config import get_cors_config

            monkeypatch.setenv("ENVIRONMENT", "development")
            monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

            config = get_cors_config()

            # Should include localhost origins
            assert "http://localhost:3000" in config["allow_origins"]
            assert "http://localhost:8080" in config["allow_origins"]
            assert "http://localhost:5173" in config["allow_origins"]

            # Should not include wildcard
            assert "*" not in config["allow_origins"]
        finally:
            sys.path.remove(str(repo_root))

    def test_shared_cors_module_respects_env_override(self, monkeypatch):
        """Test that CORS_ALLOWED_ORIGINS env var overrides defaults."""
        import sys

        repo_root = self._get_repo_root()
        sys.path.insert(0, str(repo_root))

        try:
            from src.core.shared.security.cors_config import get_cors_config

            monkeypatch.setenv("ENVIRONMENT", "development")
            custom_origins = "https://custom1.example.com,https://custom2.example.com"
            monkeypatch.setenv("CORS_ALLOWED_ORIGINS", custom_origins)

            config = get_cors_config()

            # Should use custom origins from env
            assert "https://custom1.example.com" in config["allow_origins"]
            assert "https://custom2.example.com" in config["allow_origins"]
        finally:
            sys.path.remove(str(repo_root))

    def test_environment_files_have_no_wildcard(self):
        """Verify .env.dev and docker-compose have no wildcard CORS."""
        repo_root = self._get_repo_root()

        # Check .env.dev
        env_dev_path = repo_root / ".env.dev"
        if env_dev_path.exists():
            env_content = env_dev_path.read_text()

            # Find CORS_ORIGINS lines
            for line in env_content.split("\n"):
                if line.strip().startswith("CORS_ORIGINS="):
                    assert "*" not in line, f".env.dev contains wildcard CORS: {line}"

        # Check docker-compose.dev.yml
        docker_compose_path = repo_root / "docker-compose.dev.yml"
        if docker_compose_path.exists():
            compose_content = docker_compose_path.read_text()

            # Check CORS_ORIGINS environment variables
            in_env_section = False
            for line_num, line in enumerate(compose_content.split("\n"), 1):
                if "environment:" in line:
                    in_env_section = True
                elif in_env_section:
                    # Check if we've exited the environment section
                    if line and not line.startswith(" ") and not line.startswith("\t"):
                        in_env_section = False
                    elif "CORS_ORIGINS" in line:
                        assert "*" not in line, (
                            f"docker-compose.dev.yml line {line_num} contains "
                            f"wildcard CORS: {line.strip()}"
                        )

    def test_production_env_example_has_secure_cors(self):
        """Verify .env.production has secure CORS configuration."""
        repo_root = self._get_repo_root()
        env_prod_path = repo_root / ".env.production"

        if not env_prod_path.exists():
            pytest.skip(".env.production not found")

        env_content = env_prod_path.read_text()

        # Check CORS_ORIGINS configuration
        cors_found = False
        for line in env_content.split("\n"):
            if line.strip().startswith("CORS_ORIGINS="):
                cors_found = True

                # Should not contain wildcard
                assert "*" not in line, ".env.production should not contain wildcard CORS"

                # Should use HTTPS in production
                if not line.startswith("#"):  # Not a comment
                    origins = line.split("=", 1)[1]
                    for origin in origins.split(","):
                        origin = origin.strip()
                        if origin and not origin.startswith("#"):
                            assert origin.startswith("https://"), (
                                f".env.production should use HTTPS origins: {origin}"
                            )

        assert cors_found, ".env.production should define CORS_ORIGINS"


class TestInlineServiceCORSBehavior:
    """Test runtime behavior of services with inline CORS implementation."""

    @pytest.fixture
    def mock_environment(self, monkeypatch):
        """Mock environment variables for testing."""
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("APP_ENV", raising=False)
        return monkeypatch

    pass
    # Note: integration-service has been migrated to use shared CORS module
    # so runtime behavior tests for its previous inline implementation are removed.


class TestConstitutionalCompliance:
    """Test constitutional hash compliance."""

    def test_constitutional_hash_in_shared_module(self):
        """Verify constitutional hash in shared CORS module."""
        import sys

        repo_root = TestServiceCORSIntegration._get_repo_root()
        sys.path.insert(0, str(repo_root))

        try:
            from src.core.shared.security.cors_config import CONSTITUTIONAL_HASH

            assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"
        finally:
            sys.path.remove(str(repo_root))

    def test_constitutional_hash_in_test_file(self):
        """Verify this test file has constitutional hash."""
        test_file_path = Path(__file__)
        content = test_file_path.read_text()

        assert "cdd01ef066bc6cf2" in content, "Test file should include constitutional hash"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
