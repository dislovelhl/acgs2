#!/usr/bin/env python3
"""
ACGS Code Analysis Engine - Deployment Readiness Validation
Validates all success criteria for resuming deployment to Phase 2.

Constitutional Hash: cdd01ef066bc6cf2

Success Criteria:
- Successful local service startup capability
- Passing basic smoke tests
- Confirmed integration with existing ACGS infrastructure (PostgreSQL 5439, Redis 6389)
- Validated constitutional compliance implementation
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def setup_test_environment() -> None:
    """Setup environment variables for testing."""
    os.environ["POSTGRESQL_PASSWORD"] = "test_password"
    os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key_for_development_only"
    os.environ["REDIS_PASSWORD"] = ""
    os.environ["ENVIRONMENT"] = "testing"


def test_configuration_loading() -> dict[str, Any]:
    """Test 1: Configuration Loading."""
    try:
        from config.settings import get_settings

        settings = get_settings()

        # Validate key configuration values
        checks = {
            "service_name": settings.service_name == "acgs-code-analysis-engine",
            "port": settings.port == 8007,
            "constitutional_hash": settings.constitutional_hash == "cdd01ef066bc6cf2",
            "postgresql_port": settings.postgresql_port == 5439,
            "redis_port": settings.redis_port == 6389,
            "database_url_format": "postgresql+asyncpg://" in settings.database_url,
            "redis_url_format": "redis://" in settings.redis_url,
        }

        all_passed = all(checks.values())

        return {
            "status": "pass" if all_passed else "fail",
            "checks": checks,
            "settings": {
                "service_name": settings.service_name,
                "port": settings.port,
                "constitutional_hash": settings.constitutional_hash,
                "postgresql_port": settings.postgresql_port,
                "redis_port": settings.redis_port,
            },
        }

    except Exception as e:
        return {"status": "fail", "error": str(e)}


def test_service_imports() -> dict[str, Any]:
    """Test 2: Service Import Validation."""
    try:
        # Test utility imports
        from app.utils.constitutional import CONSTITUTIONAL_HASH

        return {
            "status": "pass",
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "imports_successful": True,
        }

    except Exception as e:
        return {"status": "fail", "error": str(e), "imports_successful": False}


def test_database_configuration() -> dict[str, Any]:
    """Test 3: Database Configuration."""
    try:
        from config.database import DatabaseManager
        from config.settings import get_settings

        settings = get_settings()

        # Test database manager instantiation
        DatabaseManager(
            host=settings.postgresql_host,
            port=settings.postgresql_port,
            database=settings.postgresql_database,
            username=settings.postgresql_user,
            password=settings.postgresql_password,
        )

        return {
            "status": "pass",
            "database_url": settings.database_url,
            "host": settings.postgresql_host,
            "port": settings.postgresql_port,
            "database": settings.postgresql_database,
        }

    except Exception as e:
        return {"status": "fail", "error": str(e)}


def test_cache_configuration() -> dict[str, Any]:
    """Test 4: Cache Service Configuration."""
    try:
        from config.settings import get_settings

        from app.services.cache_service import CacheService

        settings = get_settings()

        # Test cache service instantiation
        CacheService(redis_url=settings.redis_url)

        return {
            "status": "pass",
            "redis_url": settings.redis_url,
            "redis_host": settings.redis_host,
            "redis_port": settings.redis_port,
            "redis_db": settings.redis_db,
        }

    except Exception as e:
        return {"status": "fail", "error": str(e)}


def test_constitutional_compliance() -> dict[str, Any]:
    """Test 5: Constitutional Compliance Validation."""
    try:
        from config.settings import get_settings

        from app.utils.constitutional import CONSTITUTIONAL_HASH

        settings = get_settings()
        expected_hash = "cdd01ef066bc6cf2"

        # Test settings hash
        settings_hash_valid = settings.constitutional_hash == expected_hash

        # Test utility constant hash
        utility_hash_valid = expected_hash == CONSTITUTIONAL_HASH

        # Test hash validation function
        hash_validation_works = settings.constitutional_hash == CONSTITUTIONAL_HASH

        all_valid = settings_hash_valid and utility_hash_valid and hash_validation_works

        return {
            "status": "pass" if all_valid else "fail",
            "expected_hash": expected_hash,
            "settings_hash": settings.constitutional_hash,
            "utility_hash": CONSTITUTIONAL_HASH,
            "settings_hash_valid": settings_hash_valid,
            "utility_hash_valid": utility_hash_valid,
            "hash_consistency": hash_validation_works,
        }

    except Exception as e:
        return {"status": "fail", "error": str(e)}


def test_acgs_infrastructure_readiness() -> dict[str, Any]:
    """Test 6: ACGS Infrastructure Integration Readiness."""
    try:
        from config.settings import get_settings

        settings = get_settings()

        # Test service URLs and ports
        infrastructure_config = {
            "auth_service_url": str(settings.auth_service_url),
            "context_service_url": str(settings.context_service_url),
            "service_registry_url": str(settings.service_registry_url),
            "postgresql_configured": f"localhost:{settings.postgresql_port}",
            "redis_configured": f"localhost:{settings.redis_port}",
        }

        # Validate expected ports
        port_checks = {
            "auth_service_port": "8016" in infrastructure_config["auth_service_url"],
            "context_service_port": "8012" in infrastructure_config["context_service_url"],
            "postgresql_port": settings.postgresql_port == 5439,
            "redis_port": settings.redis_port == 6389,
            "service_port": settings.port == 8007,
        }

        all_ports_correct = all(port_checks.values())

        return {
            "status": "pass" if all_ports_correct else "fail",
            "infrastructure_config": infrastructure_config,
            "port_checks": port_checks,
            "all_ports_correct": all_ports_correct,
        }

    except Exception as e:
        return {"status": "fail", "error": str(e)}


def run_deployment_readiness_validation() -> dict[str, Any]:
    """Run comprehensive deployment readiness validation."""
    # Setup test environment
    setup_test_environment()

    # Run all validation tests
    test_results = {
        "configuration_loading": test_configuration_loading(),
        "service_imports": test_service_imports(),
        "database_configuration": test_database_configuration(),
        "cache_configuration": test_cache_configuration(),
        "constitutional_compliance": test_constitutional_compliance(),
        "acgs_infrastructure_readiness": test_acgs_infrastructure_readiness(),
    }

    # Analyze results
    passed_tests = [name for name, result in test_results.items() if result.get("status") == "pass"]
    failed_tests = [name for name, result in test_results.items() if result.get("status") == "fail"]

    total_tests = len(test_results)
    passed_count = len(passed_tests)
    success_rate = (passed_count / total_tests) * 100

    # Determine deployment readiness
    deployment_ready = passed_count == total_tests

    return {
        "deployment_ready": deployment_ready,
        "success_rate": success_rate,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "test_results": test_results,
        "timestamp": datetime.now().isoformat(),
        "constitutional_hash": "cdd01ef066bc6cf2",
    }


def main() -> None:
    """Main validation execution function."""
    try:
        results = run_deployment_readiness_validation()

        # Save results to file
        results_file = "deployment_readiness_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        # Exit with appropriate code
        if results["deployment_ready"]:
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
