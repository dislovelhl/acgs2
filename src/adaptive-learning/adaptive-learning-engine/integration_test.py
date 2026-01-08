#!/usr/bin/env python3
"""
Integration Test Script for Adaptive Learning Engine
Constitutional Hash: cdd01ef066bc6cf2

This script performs comprehensive integration testing of all service components:
1. Configuration loading from environment
2. MLflow tracking database initialization
3. Redis connection verification (optional)
4. API endpoint initialization
5. Prometheus metrics setup
6. Drift detector initialization
7. Model manager initialization
8. Service lifecycle management
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": [],
    "skipped": [],
}


def log_test_result(test_name: str, status: str, message: str = "") -> None:
    """Log test result and track for final report."""
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")

    if status == "PASS":
        test_results["passed"].append((test_name, message))
        logger.info(f"[{timestamp}] ✅ {test_name}: PASSED {message}")
    elif status == "FAIL":
        test_results["failed"].append((test_name, message))
        logger.error(f"[{timestamp}] ❌ {test_name}: FAILED - {message}")
    elif status == "WARN":
        test_results["warnings"].append((test_name, message))
        logger.warning(f"[{timestamp}] ⚠️  {test_name}: WARNING - {message}")
    elif status == "SKIP":
        test_results["skipped"].append((test_name, message))
        logger.info(f"[{timestamp}] ⏭️  {test_name}: SKIPPED - {message}")


def test_1_environment_configuration() -> bool:
    """Test 1: Validate configuration loading from environment."""
    try:
        from src.config import AdaptiveLearningConfig

        # Load configuration
        config = AdaptiveLearningConfig.from_environment()

        # Validate key settings
        assert config.constitutional_hash == "cdd01ef066bc6cf2", "Constitutional hash mismatch"
        assert config.port > 0, "Invalid port"
        assert 0.0 <= config.safety_accuracy_threshold <= 1.0, "Invalid safety threshold"
        assert 0.0 <= config.drift_threshold <= 1.0, "Invalid drift threshold"

        log_test_result(
            "Environment Configuration",
            "PASS",
            f"(port={config.port}, hash={config.constitutional_hash[:8]}...)",
        )

        # Log configuration summary
        logger.info(f"  • Port: {config.port}")
        logger.info(f"  • Min training samples: {config.min_training_samples}")
        logger.info(f"  • Safety threshold: {config.safety_accuracy_threshold}")
        logger.info(f"  • Drift threshold: {config.drift_threshold}")
        logger.info(f"  • Prometheus enabled: {config.enable_prometheus}")
        logger.info(f"  • Redis cache enabled: {config.enable_redis_cache}")
        logger.info(f"  • Drift detection enabled: {config.enable_drift_detection}")

        return True

    except Exception as e:
        log_test_result("Environment Configuration", "FAIL", str(e))
        return False


def test_2_mlflow_configuration() -> bool:
    """Test 2: Check MLflow configuration and tracking database."""
    try:
        from src.config import AdaptiveLearningConfig

        config = AdaptiveLearningConfig.from_environment()

        # Validate MLflow settings
        assert config.mlflow_tracking_uri, "MLflow tracking URI not set"
        assert config.mlflow_model_name, "MLflow model name not set"

        # Check if SQLite database path is accessible
        if config.mlflow_tracking_uri.startswith("sqlite:///"):
            db_path = config.mlflow_tracking_uri.replace("sqlite:///", "")
            db_dir = Path(db_path).parent

            # Create directory if it doesn't exist
            db_dir.mkdir(parents=True, exist_ok=True)

            if db_dir.exists():
                log_test_result(
                    "MLflow Configuration",
                    "PASS",
                    f"(URI={config.mlflow_tracking_uri}, model={config.mlflow_model_name})",
                )
            else:
                log_test_result(
                    "MLflow Configuration",
                    "WARN",
                    f"Database directory not accessible: {db_dir}",
                )
        else:
            log_test_result(
                "MLflow Configuration",
                "PASS",
                f"(URI={config.mlflow_tracking_uri})",
            )

        logger.info(f"  • Tracking URI: {config.mlflow_tracking_uri}")
        logger.info(f"  • Model name: {config.mlflow_model_name}")
        logger.info(f"  • Champion alias: {config.mlflow_champion_alias}")

        return True

    except Exception as e:
        log_test_result("MLflow Configuration", "FAIL", str(e))
        return False


def test_3_redis_connection() -> bool:
    """Test 3: Verify Redis connection (optional - may not be running)."""
    try:
        from src.config import AdaptiveLearningConfig

        config = AdaptiveLearningConfig.from_environment()

        if not config.enable_redis_cache:
            log_test_result(
                "Redis Connection",
                "SKIP",
                "Redis cache disabled in configuration",
            )
            return True

        try:
            import redis

            # Parse Redis URL
            redis_client = redis.from_url(config.redis_url, decode_responses=True)

            # Test connection
            redis_client.ping()

            log_test_result(
                "Redis Connection",
                "PASS",
                f"(URL={config.redis_url})",
            )
            logger.info(f"  • Redis server info: {redis_client.info('server')['redis_version']}")

            redis_client.close()
            return True

        except redis.ConnectionError:
            log_test_result(
                "Redis Connection",
                "WARN",
                f"Redis not available at {config.redis_url} (optional)",
            )
            return True  # Still pass since Redis is optional

    except Exception as e:
        log_test_result("Redis Connection", "FAIL", str(e))
        return False


def test_4_model_manager_initialization() -> bool:
    """Test 4: Verify model manager initialization."""
    try:
        from src.models.model_manager import ModelManager
        from src.models.online_learner import OnlineLearner

        # Create online learner
        online_learner = OnlineLearner(min_samples_for_active=100)

        # Initialize model manager
        model_manager = ModelManager(initial_model=online_learner)

        # Verify initialization
        assert model_manager.current_model is not None, "Current model not set"
        assert model_manager.get_model_version() >= 0, "Invalid model version"

        log_test_result(
            "Model Manager Initialization",
            "PASS",
            f"(version={model_manager.get_model_version()})",
        )
        logger.info(f"  • Initial model version: {model_manager.get_model_version()}")
        logger.info(f"  • Model type: {type(online_learner).__name__}")

        return True

    except Exception as e:
        log_test_result("Model Manager Initialization", "FAIL", str(e))
        return False


def test_5_drift_detector_initialization() -> bool:
    """Test 5: Verify drift detector initialization."""
    try:
        from src.config import AdaptiveLearningConfig
        from src.monitoring.drift_detector import DriftDetector

        config = AdaptiveLearningConfig.from_environment()

        # Initialize drift detector
        drift_detector = DriftDetector(
            drift_threshold=config.drift_threshold,
            min_samples_for_drift=config.min_predictions_for_drift,
            reference_window_size=config.drift_window_size,
            current_window_size=config.drift_window_size,
        )

        # Verify initialization
        assert drift_detector.is_enabled(), "Drift detector not enabled"

        log_test_result(
            "Drift Detector Initialization",
            "PASS",
            f"(threshold={config.drift_threshold}, window={config.drift_window_size})",
        )
        logger.info(f"  • Drift threshold: {config.drift_threshold}")
        logger.info(f"  • Window size: {config.drift_window_size}")
        logger.info(f"  • Min predictions: {config.min_predictions_for_drift}")

        return True

    except Exception as e:
        log_test_result("Drift Detector Initialization", "FAIL", str(e))
        return False


def test_6_prometheus_metrics_setup() -> bool:
    """Test 6: Check Prometheus metrics setup."""
    try:
        from src.config import AdaptiveLearningConfig
        from src.monitoring.metrics import get_metrics_registry

        config = AdaptiveLearningConfig.from_environment()

        if not config.enable_prometheus:
            log_test_result(
                "Prometheus Metrics Setup",
                "SKIP",
                "Prometheus disabled in configuration",
            )
            return True

        # Get metrics registry
        metrics_registry = get_metrics_registry()

        # Set service info
        metrics_registry.set_service_info(
            service_name="adaptive-learning-engine",
            version="1.0.0",
            constitutional_hash=config.constitutional_hash,
        )

        # Get snapshot to verify metrics are working
        snapshot = metrics_registry.get_snapshot()

        log_test_result(
            "Prometheus Metrics Setup",
            "PASS",
            f"(service=adaptive-learning-engine, hash={config.constitutional_hash[:8]}...)",
        )
        logger.info(f"  • Predictions total: {snapshot.predictions_total}")
        logger.info(f"  • Training samples total: {snapshot.training_samples_total}")
        logger.info(f"  • Errors total: {snapshot.errors_total}")

        return True

    except Exception as e:
        log_test_result("Prometheus Metrics Setup", "FAIL", str(e))
        return False


def test_7_safety_bounds_checker() -> bool:
    """Test 7: Verify safety bounds checker initialization."""
    try:
        from src.config import AdaptiveLearningConfig
        from src.safety.bounds_checker import SafetyBoundsChecker

        config = AdaptiveLearningConfig.from_environment()

        # Initialize safety bounds checker
        safety_checker = SafetyBoundsChecker(
            accuracy_threshold=config.safety_accuracy_threshold,
            consecutive_failures_limit=config.safety_consecutive_failures_limit,
        )

        # Verify initialization
        assert safety_checker.accuracy_threshold > 0, "Invalid accuracy threshold"

        log_test_result(
            "Safety Bounds Checker",
            "PASS",
            f"(threshold={config.safety_accuracy_threshold}, limit={config.safety_consecutive_failures_limit})",
        )
        logger.info(f"  • Accuracy threshold: {config.safety_accuracy_threshold}")
        logger.info(f"  • Consecutive failures limit: {config.safety_consecutive_failures_limit}")

        return True

    except Exception as e:
        log_test_result("Safety Bounds Checker", "FAIL", str(e))
        return False


async def test_8_api_endpoints() -> bool:
    """Test 8: Verify API endpoint initialization."""
    try:
        from src.api.endpoints import router

        # Get all routes
        routes = [route for route in router.routes]

        # Verify key endpoints exist
        endpoint_paths = [route.path for route in routes]

        required_endpoints = ["/health", "/predict", "/train", "/metrics"]
        missing_endpoints = [ep for ep in required_endpoints if ep not in endpoint_paths]

        if missing_endpoints:
            log_test_result(
                "API Endpoints",
                "FAIL",
                f"Missing endpoints: {missing_endpoints}",
            )
            return False

        log_test_result(
            "API Endpoints",
            "PASS",
            f"({len(routes)} routes registered)",
        )
        logger.info(f"  • Total routes: {len(routes)}")
        logger.info(f"  • Endpoints: {', '.join(endpoint_paths)}")

        return True

    except Exception as e:
        log_test_result("API Endpoints", "FAIL", str(e))
        return False


def print_final_report() -> int:
    """Print final test report and return exit code."""
    logger.info("\n" + "=" * 80)
    logger.info("INTEGRATION TEST REPORT")
    logger.info("=" * 80)

    total_tests = (
        len(test_results["passed"])
        + len(test_results["failed"])
        + len(test_results["warnings"])
        + len(test_results["skipped"])
    )

    logger.info(f"\nTotal Tests: {total_tests}")
    logger.info(f"✅ Passed: {len(test_results['passed'])}")
    logger.info(f"❌ Failed: {len(test_results['failed'])}")
    logger.info(f"⚠️  Warnings: {len(test_results['warnings'])}")
    logger.info(f"⏭️  Skipped: {len(test_results['skipped'])}")

    if test_results["failed"]:
        logger.info("\n❌ FAILED TESTS:")
        for test_name, message in test_results["failed"]:
            logger.info(f"  • {test_name}: {message}")

    if test_results["warnings"]:
        logger.info("\n⚠️  WARNINGS:")
        for test_name, message in test_results["warnings"]:
            logger.info(f"  • {test_name}: {message}")

    if test_results["skipped"]:
        logger.info("\n⏭️  SKIPPED TESTS:")
        for test_name, message in test_results["skipped"]:
            logger.info(f"  • {test_name}: {message}")

    logger.info("\n" + "=" * 80)

    if test_results["failed"]:
        logger.error("INTEGRATION TESTS FAILED ❌")
        return 1
    elif test_results["warnings"]:
        logger.warning("INTEGRATION TESTS PASSED WITH WARNINGS ⚠️")
        return 0
    else:
        logger.info("ALL INTEGRATION TESTS PASSED ✅")
        return 0


async def run_all_tests() -> int:
    """Run all integration tests."""
    logger.info("=" * 80)
    logger.info("ADAPTIVE LEARNING ENGINE - INTEGRATION TEST SUITE")
    logger.info("Constitutional Hash: cdd01ef066bc6cf2")
    logger.info("=" * 80 + "\n")

    # Run synchronous tests
    test_1_environment_configuration()
    test_2_mlflow_configuration()
    test_3_redis_connection()
    test_4_model_manager_initialization()
    test_5_drift_detector_initialization()
    test_6_prometheus_metrics_setup()
    test_7_safety_bounds_checker()

    # Run async tests
    await test_8_api_endpoints()

    # Print final report
    return print_final_report()


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
