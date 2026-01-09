"""
Unit tests for the Adaptive Learning Engine Safety Bounds module.

Tests cover:
- SafetyBoundsChecker: Circuit breaker pattern for online learning safety

Constitutional Hash: cdd01ef066bc6cf2
"""

import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest
from src.safety.bounds_checker import (
    CheckResult,
    SafetyAlert,
    SafetyBoundsChecker,
    SafetyCheckResult,
    SafetyMetrics,
    SafetyStatus,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def safety_checker() -> SafetyBoundsChecker:
    """Fresh SafetyBoundsChecker with default settings."""
    return SafetyBoundsChecker(
        accuracy_threshold=0.85,
        consecutive_failures_limit=3,
        min_samples_for_check=100,
        enable_auto_pause=True,
        degradation_threshold=0.05,
    )


@pytest.fixture
def low_threshold_checker() -> SafetyBoundsChecker:
    """Checker with low threshold for easier testing."""
    return SafetyBoundsChecker(
        accuracy_threshold=0.5,
        consecutive_failures_limit=3,
        min_samples_for_check=5,
        enable_auto_pause=True,
        degradation_threshold=0.1,
    )


@pytest.fixture
def mock_model():
    """Mock model for testing."""
    model = MagicMock()
    model.get_sample_count.return_value = 1000
    model.get_accuracy.return_value = 0.92
    return model


@pytest.fixture
def mock_cold_start_model():
    """Mock model in cold start state (few samples)."""
    model = MagicMock()
    model.get_sample_count.return_value = 50
    model.get_accuracy.return_value = 0.0
    return model


@pytest.fixture
def validation_dataset() -> List[Tuple[Dict[str, Any], int]]:
    """Validation dataset for accuracy testing."""
    return [
        ({"x": 0.1, "y": 0.2}, 0),
        ({"x": 0.9, "y": 0.8}, 1),
        ({"x": 0.2, "y": 0.1}, 0),
        ({"x": 0.8, "y": 0.9}, 1),
        ({"x": 0.15, "y": 0.25}, 0),
        ({"x": 0.85, "y": 0.75}, 1),
        ({"x": 0.3, "y": 0.2}, 0),
        ({"x": 0.7, "y": 0.8}, 1),
        ({"x": 0.25, "y": 0.15}, 0),
        ({"x": 0.95, "y": 0.85}, 1),
    ]


# =============================================================================
# SafetyStatus Enum Tests
# =============================================================================


class TestSafetyStatus:
    """Tests for SafetyStatus enum."""

    def test_safety_status_values(self):
        """Test SafetyStatus enum values."""
        assert SafetyStatus.OK.value == "ok"
        assert SafetyStatus.WARNING.value == "warning"
        assert SafetyStatus.PAUSED.value == "paused"
        assert SafetyStatus.CRITICAL.value == "critical"


# =============================================================================
# CheckResult Enum Tests
# =============================================================================


class TestCheckResult:
    """Tests for CheckResult enum."""

    def test_check_result_values(self):
        """Test CheckResult enum values."""
        assert CheckResult.PASSED.value == "passed"
        assert CheckResult.FAILED_ACCURACY.value == "failed_accuracy"
        assert CheckResult.FAILED_DEGRADATION.value == "failed_degradation"
        assert CheckResult.FAILED_DRIFT.value == "failed_drift"
        assert CheckResult.SKIPPED_COLD_START.value == "skipped_cold_start"
        assert CheckResult.SKIPPED_INSUFFICIENT_DATA.value == "skipped_insufficient_data"


# =============================================================================
# SafetyCheckResult Tests
# =============================================================================


class TestSafetyCheckResult:
    """Tests for SafetyCheckResult dataclass."""

    def test_safety_check_result_creation(self):
        """Test creating SafetyCheckResult."""
        result = SafetyCheckResult(
            passed=True,
            result=CheckResult.PASSED,
            current_accuracy=0.92,
            threshold=0.85,
            message="Safety check passed",
            consecutive_failures=0,
            safety_status=SafetyStatus.OK,
        )

        assert result.passed is True
        assert result.result == CheckResult.PASSED
        assert result.current_accuracy == 0.92
        assert result.threshold == 0.85
        assert result.message == "Safety check passed"
        assert result.consecutive_failures == 0
        assert result.safety_status == SafetyStatus.OK
        assert result.timestamp > 0
        assert result.metadata == {}

    def test_safety_check_result_with_metadata(self):
        """Test SafetyCheckResult with metadata."""
        result = SafetyCheckResult(
            passed=False,
            result=CheckResult.FAILED_DEGRADATION,
            current_accuracy=0.80,
            threshold=0.85,
            message="Accuracy dropped",
            consecutive_failures=1,
            safety_status=SafetyStatus.WARNING,
            metadata={"previous_accuracy": 0.90, "accuracy_drop": 0.10},
        )

        assert result.metadata["previous_accuracy"] == 0.90
        assert result.metadata["accuracy_drop"] == 0.10

    def test_safety_check_result_to_dict(self):
        """Test SafetyCheckResult serialization."""
        result = SafetyCheckResult(
            passed=True,
            result=CheckResult.PASSED,
            current_accuracy=0.92,
            threshold=0.85,
            message="Safety check passed",
            consecutive_failures=0,
            safety_status=SafetyStatus.OK,
        )

        data = result.to_dict()

        assert data["passed"] is True
        assert data["result"] == "passed"
        assert data["current_accuracy"] == 0.92
        assert data["threshold"] == 0.85
        assert data["safety_status"] == "ok"
        assert "timestamp" in data


# =============================================================================
# SafetyAlert Tests
# =============================================================================


class TestSafetyAlert:
    """Tests for SafetyAlert dataclass."""

    def test_safety_alert_creation(self):
        """Test creating SafetyAlert."""
        alert = SafetyAlert(
            severity="warning",
            message="Safety check failed",
            consecutive_failures=2,
            current_accuracy=0.80,
            threshold=0.85,
            action_taken="none",
        )

        assert alert.severity == "warning"
        assert alert.message == "Safety check failed"
        assert alert.consecutive_failures == 2
        assert alert.current_accuracy == 0.80
        assert alert.threshold == 0.85
        assert alert.action_taken == "none"
        assert alert.timestamp > 0
        assert alert.context == {}

    def test_safety_alert_to_dict(self):
        """Test SafetyAlert serialization."""
        alert = SafetyAlert(
            severity="critical",
            message="Learning paused",
            consecutive_failures=3,
            current_accuracy=0.75,
            threshold=0.85,
            action_taken="paused_learning",
            context={"status": "critical"},
        )

        data = alert.to_dict()

        assert data["severity"] == "critical"
        assert data["message"] == "Learning paused"
        assert data["consecutive_failures"] == 3
        assert data["action_taken"] == "paused_learning"
        assert data["context"]["status"] == "critical"


# =============================================================================
# SafetyMetrics Tests
# =============================================================================


class TestSafetyMetrics:
    """Tests for SafetyMetrics dataclass."""

    def test_safety_metrics_creation(self):
        """Test creating SafetyMetrics."""
        metrics = SafetyMetrics(
            total_checks=100,
            passed_checks=95,
            failed_checks=5,
            consecutive_failures=0,
            max_consecutive_failures=2,
            times_paused=1,
            times_resumed=1,
            current_status=SafetyStatus.OK,
            last_check_time=time.time(),
            last_failure_time=None,
        )

        assert metrics.total_checks == 100
        assert metrics.passed_checks == 95
        assert metrics.failed_checks == 5
        assert metrics.consecutive_failures == 0
        assert metrics.max_consecutive_failures == 2
        assert metrics.times_paused == 1
        assert metrics.current_status == SafetyStatus.OK

    def test_safety_metrics_to_dict(self):
        """Test SafetyMetrics serialization."""
        metrics = SafetyMetrics(
            total_checks=100,
            passed_checks=95,
            failed_checks=5,
            consecutive_failures=0,
            max_consecutive_failures=2,
            times_paused=1,
            times_resumed=1,
            current_status=SafetyStatus.OK,
            last_check_time=time.time(),
            last_failure_time=None,
        )

        data = metrics.to_dict()

        assert data["total_checks"] == 100
        assert data["passed_checks"] == 95
        assert data["current_status"] == "ok"


# =============================================================================
# SafetyBoundsChecker Tests - Initialization
# =============================================================================


class TestSafetyBoundsCheckerInit:
    """Tests for SafetyBoundsChecker initialization."""

    def test_default_initialization(self):
        """Test default initialization creates valid checker."""
        checker = SafetyBoundsChecker()

        assert checker.accuracy_threshold == 0.85
        assert checker.consecutive_failures_limit == 3
        assert checker.min_samples_for_check == 100
        assert checker.enable_auto_pause is True
        assert checker.degradation_threshold == 0.05
        assert checker._status == SafetyStatus.OK

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        checker = SafetyBoundsChecker(
            accuracy_threshold=0.90,
            consecutive_failures_limit=5,
            min_samples_for_check=50,
            enable_auto_pause=False,
            degradation_threshold=0.10,
        )

        assert checker.accuracy_threshold == 0.90
        assert checker.consecutive_failures_limit == 5
        assert checker.min_samples_for_check == 50
        assert checker.enable_auto_pause is False
        assert checker.degradation_threshold == 0.10

    def test_invalid_accuracy_threshold(self):
        """Test that invalid accuracy threshold raises error."""
        with pytest.raises(ValueError) as exc_info:
            SafetyBoundsChecker(accuracy_threshold=1.5)

        assert "accuracy_threshold" in str(exc_info.value)

        with pytest.raises(ValueError):
            SafetyBoundsChecker(accuracy_threshold=-0.1)

    def test_invalid_consecutive_failures_limit(self):
        """Test that invalid consecutive failures limit raises error."""
        with pytest.raises(ValueError) as exc_info:
            SafetyBoundsChecker(consecutive_failures_limit=0)

        assert "consecutive_failures_limit" in str(exc_info.value)

    def test_invalid_min_samples(self):
        """Test that invalid min samples raises error."""
        with pytest.raises(ValueError) as exc_info:
            SafetyBoundsChecker(min_samples_for_check=-1)

        assert "min_samples_for_check" in str(exc_info.value)

    def test_invalid_degradation_threshold(self):
        """Test that invalid degradation threshold raises error."""
        with pytest.raises(ValueError):
            SafetyBoundsChecker(degradation_threshold=1.5)

        with pytest.raises(ValueError):
            SafetyBoundsChecker(degradation_threshold=-0.1)


# =============================================================================
# SafetyBoundsChecker Tests - Model Checking
# =============================================================================


class TestSafetyBoundsCheckerModelCheck:
    """Tests for checking model safety."""

    def test_check_model_passes_high_accuracy(self, safety_checker, mock_model):
        """Test check passes with high accuracy model."""
        result = safety_checker.check_model(mock_model)

        assert result.passed is True
        assert result.result == CheckResult.PASSED
        assert result.current_accuracy == 0.92
        assert result.safety_status == SafetyStatus.OK

    def test_check_model_fails_low_accuracy(self, safety_checker, mock_model):
        """Test check fails with low accuracy model."""
        mock_model.get_accuracy.return_value = 0.70

        result = safety_checker.check_model(mock_model)

        assert result.passed is False
        assert result.result == CheckResult.FAILED_ACCURACY
        assert result.current_accuracy == 0.70
        assert result.consecutive_failures == 1

    def test_check_model_skips_cold_start(self, safety_checker, mock_cold_start_model):
        """Test check skips during cold start."""
        result = safety_checker.check_model(mock_cold_start_model)

        assert result.passed is True
        assert result.result == CheckResult.SKIPPED_COLD_START
        assert "skipped" in result.message.lower()

    def test_check_model_with_validation_data(self, safety_checker, mock_model, validation_dataset):
        """Test check model using validation data."""
        # Mock predict_one to return correct predictions
        mock_model.predict_one.side_effect = lambda x: MagicMock(
            prediction=1 if x.get("x", 0) > 0.5 else 0
        )

        result = safety_checker.check_model(mock_model, validation_data=validation_dataset)

        assert isinstance(result, SafetyCheckResult)
        # Accuracy depends on mock predictions vs actual labels

    def test_check_model_increments_total_checks(self, safety_checker, mock_model):
        """Test that check increments total check counter."""
        assert safety_checker._total_checks == 0

        safety_checker.check_model(mock_model)
        assert safety_checker._total_checks == 1

        safety_checker.check_model(mock_model)
        assert safety_checker._total_checks == 2


# =============================================================================
# SafetyBoundsChecker Tests - Accuracy Checking
# =============================================================================


class TestSafetyBoundsCheckerAccuracyCheck:
    """Tests for direct accuracy checking."""

    def test_check_accuracy_passes(self, safety_checker):
        """Test accuracy check passes with good accuracy."""
        result = safety_checker.check_accuracy(0.92)

        assert result.passed is True
        assert result.result == CheckResult.PASSED
        assert result.current_accuracy == 0.92

    def test_check_accuracy_fails_below_threshold(self, safety_checker):
        """Test accuracy check fails below threshold."""
        result = safety_checker.check_accuracy(0.80)

        assert result.passed is False
        assert result.result == CheckResult.FAILED_ACCURACY
        assert "below threshold" in result.message.lower()

    def test_check_accuracy_exactly_at_threshold(self, safety_checker):
        """Test accuracy check at exactly the threshold."""
        result = safety_checker.check_accuracy(0.85)

        assert result.passed is True

    def test_check_accuracy_just_below_threshold(self, safety_checker):
        """Test accuracy check just below threshold."""
        result = safety_checker.check_accuracy(0.849)

        assert result.passed is False


# =============================================================================
# SafetyBoundsChecker Tests - Degradation Detection
# =============================================================================


class TestSafetyBoundsCheckerDegradation:
    """Tests for degradation detection."""

    def test_detects_degradation(self, safety_checker):
        """Test that degradation is detected."""
        # First check establishes baseline
        safety_checker.check_accuracy(0.95)

        # Second check with significant drop
        result = safety_checker.check_accuracy(0.88)  # Drop of 0.07 > threshold 0.05

        assert result.passed is False
        assert result.result == CheckResult.FAILED_DEGRADATION
        assert "dropped" in result.message.lower()

    def test_no_degradation_within_threshold(self, safety_checker):
        """Test no degradation detected within threshold."""
        safety_checker.check_accuracy(0.95)

        # Small drop within threshold
        result = safety_checker.check_accuracy(0.92)  # Drop of 0.03 < threshold 0.05

        assert result.passed is True

    def test_degradation_metadata(self, safety_checker):
        """Test degradation includes metadata."""
        safety_checker.check_accuracy(0.95)
        result = safety_checker.check_accuracy(0.85)  # Drop of 0.10

        assert result.passed is False
        assert "previous_accuracy" in result.metadata
        assert "accuracy_drop" in result.metadata
        assert result.metadata["previous_accuracy"] == 0.95


# =============================================================================
# SafetyBoundsChecker Tests - Consecutive Failures
# =============================================================================


class TestSafetyBoundsCheckerConsecutiveFailures:
    """Tests for consecutive failure tracking."""

    def test_consecutive_failures_increment(self, safety_checker):
        """Test consecutive failures increment correctly."""
        assert safety_checker._consecutive_failures == 0

        safety_checker.check_accuracy(0.70)
        assert safety_checker._consecutive_failures == 1

        safety_checker.check_accuracy(0.75)
        assert safety_checker._consecutive_failures == 2

    def test_consecutive_failures_reset_on_pass(self, safety_checker):
        """Test consecutive failures reset on passing check."""
        safety_checker.check_accuracy(0.70)
        safety_checker.check_accuracy(0.75)
        assert safety_checker._consecutive_failures == 2

        # Reset last accuracy to avoid degradation check
        safety_checker._last_accuracy = None
        safety_checker.check_accuracy(0.90)
        assert safety_checker._consecutive_failures == 0

    def test_status_warning_on_failure(self, safety_checker):
        """Test status changes to WARNING on failure."""
        safety_checker.check_accuracy(0.70)

        assert safety_checker._status == SafetyStatus.WARNING


# =============================================================================
# SafetyBoundsChecker Tests - Auto Pause
# =============================================================================


class TestSafetyBoundsCheckerAutoPause:
    """Tests for automatic pause functionality."""

    def test_auto_pause_on_consecutive_failures(self, safety_checker):
        """Test learning is paused after consecutive failures."""
        # Trigger 3 consecutive failures
        for _ in range(3):
            safety_checker.check_accuracy(0.70)

        assert safety_checker._status == SafetyStatus.PAUSED
        assert safety_checker.is_learning_allowed() is False

    def test_no_pause_when_disabled(self):
        """Test no auto-pause when disabled."""
        checker = SafetyBoundsChecker(
            accuracy_threshold=0.85,
            consecutive_failures_limit=3,
            min_samples_for_check=0,
            enable_auto_pause=False,
        )

        for _ in range(5):
            checker.check_accuracy(0.70)

        # Status should be CRITICAL but not PAUSED
        assert checker._status == SafetyStatus.CRITICAL
        # Note: is_learning_allowed checks for PAUSED status specifically

    def test_pause_callback_triggered(self, safety_checker):
        """Test pause callback is triggered."""
        callback_called = [False]

        def on_pause():
            callback_called[0] = True

        safety_checker.register_pause_callback(on_pause)

        for _ in range(3):
            safety_checker.check_accuracy(0.70)

        assert callback_called[0] is True


# =============================================================================
# SafetyBoundsChecker Tests - Resume
# =============================================================================


class TestSafetyBoundsCheckerResume:
    """Tests for resume functionality."""

    def test_resume_on_passing_check(self, safety_checker):
        """Test learning resumes on passing check after pause."""
        # Trigger pause
        for _ in range(3):
            safety_checker.check_accuracy(0.70)

        assert safety_checker._status == SafetyStatus.PAUSED

        # Reset last accuracy to avoid degradation check
        safety_checker._last_accuracy = None

        # Passing check should resume
        safety_checker.check_accuracy(0.92)

        assert safety_checker._status == SafetyStatus.OK
        assert safety_checker.is_learning_allowed() is True

    def test_resume_callback_triggered(self, safety_checker):
        """Test resume callback is triggered."""
        callback_called = [False]

        def on_resume():
            callback_called[0] = True

        safety_checker.register_resume_callback(on_resume)

        # Trigger pause
        for _ in range(3):
            safety_checker.check_accuracy(0.70)

        # Reset and resume
        safety_checker._last_accuracy = None
        safety_checker.check_accuracy(0.92)

        assert callback_called[0] is True

    def test_force_resume(self, safety_checker):
        """Test force resume after manual intervention."""
        # Trigger pause
        for _ in range(3):
            safety_checker.check_accuracy(0.70)

        safety_checker.force_resume()

        assert safety_checker._status == SafetyStatus.OK
        assert safety_checker._consecutive_failures == 0
        assert safety_checker._last_accuracy is None


# =============================================================================
# SafetyBoundsChecker Tests - Alerts
# =============================================================================


class TestSafetyBoundsCheckerAlerts:
    """Tests for alert generation and management."""

    def test_alert_generated_on_failure(self, safety_checker):
        """Test alert is generated on safety failure."""
        safety_checker.check_accuracy(0.70)

        alerts = safety_checker.get_alert_history()
        assert len(alerts) == 1
        assert alerts[0].severity == "warning"

    def test_critical_alert_on_pause(self, safety_checker):
        """Test critical alert generated when paused."""
        for _ in range(3):
            safety_checker.check_accuracy(0.70)

        alerts = safety_checker.get_alert_history()
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        assert len(critical_alerts) >= 1

    def test_alert_callback_triggered(self, safety_checker):
        """Test alert callback is triggered."""
        callback_results = []

        def on_alert(alert: SafetyAlert):
            callback_results.append(alert)

        safety_checker.register_alert_callback(on_alert)
        safety_checker.check_accuracy(0.70)

        assert len(callback_results) == 1
        assert callback_results[0].severity == "warning"

    def test_alert_history_limit(self, safety_checker):
        """Test alert history is limited."""
        safety_checker._max_alert_history = 5

        # Generate many alerts
        for _ in range(10):
            safety_checker.check_accuracy(0.70)

        alerts = safety_checker.get_alert_history(limit=100)
        assert len(alerts) <= 5


# =============================================================================
# SafetyBoundsChecker Tests - Callback Management
# =============================================================================


class TestSafetyBoundsCheckerCallbacks:
    """Tests for callback registration and management."""

    def test_register_alert_callback(self, safety_checker):
        """Test registering alert callback."""

        def callback(alert):
            pass

        safety_checker.register_alert_callback(callback)
        assert len(safety_checker._alert_callbacks) == 1

    def test_unregister_alert_callback(self, safety_checker):
        """Test unregistering alert callback."""

        def callback(alert):
            pass

        safety_checker.register_alert_callback(callback)
        result = safety_checker.unregister_alert_callback(callback)

        assert result is True
        assert len(safety_checker._alert_callbacks) == 0

    def test_unregister_nonexistent_callback(self, safety_checker):
        """Test unregistering non-existent callback."""

        def callback(alert):
            pass

        result = safety_checker.unregister_alert_callback(callback)
        assert result is False

    def test_register_pause_callback(self, safety_checker):
        """Test registering pause callback."""

        def callback():
            pass

        safety_checker.register_pause_callback(callback)
        assert len(safety_checker._pause_callbacks) == 1

    def test_unregister_pause_callback(self, safety_checker):
        """Test unregistering pause callback."""

        def callback():
            pass

        safety_checker.register_pause_callback(callback)
        result = safety_checker.unregister_pause_callback(callback)

        assert result is True
        assert len(safety_checker._pause_callbacks) == 0

    def test_register_resume_callback(self, safety_checker):
        """Test registering resume callback."""

        def callback():
            pass

        safety_checker.register_resume_callback(callback)
        assert len(safety_checker._resume_callbacks) == 1

    def test_unregister_resume_callback(self, safety_checker):
        """Test unregistering resume callback."""

        def callback():
            pass

        safety_checker.register_resume_callback(callback)
        result = safety_checker.unregister_resume_callback(callback)

        assert result is True
        assert len(safety_checker._resume_callbacks) == 0

    def test_callback_exception_handled(self, safety_checker):
        """Test callback exceptions are handled gracefully."""

        def bad_callback(alert):
            raise ValueError("Callback error")

        safety_checker.register_alert_callback(bad_callback)

        # Should not raise
        result = safety_checker.check_accuracy(0.70)
        assert result.passed is False


# =============================================================================
# SafetyBoundsChecker Tests - Metrics and Status
# =============================================================================


class TestSafetyBoundsCheckerMetrics:
    """Tests for metrics retrieval."""

    def test_get_metrics(self, safety_checker):
        """Test getting safety metrics."""
        safety_checker.check_accuracy(0.92)
        safety_checker.check_accuracy(0.70)

        metrics = safety_checker.get_metrics()

        assert isinstance(metrics, SafetyMetrics)
        assert metrics.total_checks == 2
        assert metrics.passed_checks == 1
        assert metrics.failed_checks == 1
        assert metrics.consecutive_failures == 1

    def test_get_status(self, safety_checker):
        """Test getting current status."""
        assert safety_checker.get_status() == SafetyStatus.OK

        safety_checker.check_accuracy(0.70)
        assert safety_checker.get_status() == SafetyStatus.WARNING

    def test_get_consecutive_failures(self, safety_checker):
        """Test getting consecutive failures count."""
        assert safety_checker.get_consecutive_failures() == 0

        safety_checker.check_accuracy(0.70)
        assert safety_checker.get_consecutive_failures() == 1

    def test_is_learning_allowed(self, safety_checker):
        """Test is_learning_allowed method."""
        assert safety_checker.is_learning_allowed() is True

        for _ in range(3):
            safety_checker.check_accuracy(0.70)

        assert safety_checker.is_learning_allowed() is False


# =============================================================================
# SafetyBoundsChecker Tests - Configuration
# =============================================================================


class TestSafetyBoundsCheckerConfig:
    """Tests for configuration management."""

    def test_get_config(self, safety_checker):
        """Test getting checker configuration."""
        config = safety_checker.get_config()

        assert config["accuracy_threshold"] == 0.85
        assert config["consecutive_failures_limit"] == 3
        assert config["min_samples_for_check"] == 100
        assert config["enable_auto_pause"] is True
        assert config["degradation_threshold"] == 0.05

    def test_update_threshold(self, safety_checker):
        """Test updating accuracy threshold."""
        safety_checker.update_threshold(0.90)

        assert safety_checker.accuracy_threshold == 0.90

    def test_update_threshold_invalid(self, safety_checker):
        """Test updating with invalid threshold raises error."""
        with pytest.raises(ValueError):
            safety_checker.update_threshold(1.5)

        with pytest.raises(ValueError):
            safety_checker.update_threshold(-0.1)


# =============================================================================
# SafetyBoundsChecker Tests - Reset
# =============================================================================


class TestSafetyBoundsCheckerReset:
    """Tests for reset functionality."""

    def test_reset_clears_state(self, safety_checker):
        """Test that reset clears all state."""
        safety_checker.check_accuracy(0.70)
        safety_checker.check_accuracy(0.75)
        safety_checker.check_accuracy(0.72)

        assert safety_checker._total_checks > 0
        assert safety_checker._consecutive_failures > 0

        safety_checker.reset()

        assert safety_checker._total_checks == 0
        assert safety_checker._passed_checks == 0
        assert safety_checker._failed_checks == 0
        assert safety_checker._consecutive_failures == 0
        assert safety_checker._status == SafetyStatus.OK
        assert safety_checker._last_accuracy is None
        assert len(safety_checker._alert_history) == 0

    def test_reset_failures(self, safety_checker):
        """Test reset_failures method."""
        safety_checker.check_accuracy(0.70)
        safety_checker.check_accuracy(0.75)

        safety_checker.reset_failures()

        assert safety_checker._consecutive_failures == 0
        assert safety_checker._status == SafetyStatus.OK


# =============================================================================
# SafetyBoundsChecker Tests - Thread Safety
# =============================================================================


class TestSafetyBoundsCheckerThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_checks(self, safety_checker):
        """Test concurrent safety checks don't cause race conditions."""
        results = []
        errors = []

        def check():
            try:
                for i in range(50):
                    accuracy = 0.90 if i % 2 == 0 else 0.70
                    result = safety_checker.check_accuracy(accuracy)
                    results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=check) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 250

    def test_concurrent_callback_registration(self, safety_checker):
        """Test concurrent callback registration is thread-safe."""
        errors = []

        def register_callbacks():
            try:
                for i in range(50):

                    def callback(alert, idx=i):
                        pass

                    safety_checker.register_alert_callback(callback)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_callbacks) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# =============================================================================
# SafetyBoundsChecker Tests - Repr
# =============================================================================


class TestSafetyBoundsCheckerRepr:
    """Tests for string representation."""

    def test_repr(self, safety_checker):
        """Test __repr__ returns informative string."""
        repr_str = repr(safety_checker)

        assert "SafetyBoundsChecker" in repr_str
        assert "threshold=" in repr_str
        assert "failures=" in repr_str
        assert "status=" in repr_str


# =============================================================================
# Integration Tests - Full Safety Check Flow
# =============================================================================


class TestSafetyBoundsCheckerIntegration:
    """Integration tests for full safety check workflow."""

    def test_full_safety_flow(self, safety_checker, mock_model):
        """Test complete safety check flow."""
        alerts_received = []
        paused = [False]
        resumed = [False]

        def on_alert(alert):
            alerts_received.append(alert)

        def on_pause():
            paused[0] = True

        def on_resume():
            resumed[0] = True

        safety_checker.register_alert_callback(on_alert)
        safety_checker.register_pause_callback(on_pause)
        safety_checker.register_resume_callback(on_resume)

        # Initial check passes
        mock_model.get_accuracy.return_value = 0.92
        result = safety_checker.check_model(mock_model)
        assert result.passed is True
        assert safety_checker.get_status() == SafetyStatus.OK

        # Accuracy drops - warning
        mock_model.get_accuracy.return_value = 0.80
        result = safety_checker.check_model(mock_model)
        assert result.passed is False
        assert safety_checker.get_status() == SafetyStatus.WARNING
        assert len(alerts_received) == 1

        # Continue failing - pause
        for _ in range(2):
            mock_model.get_accuracy.return_value = 0.80
            safety_checker.check_model(mock_model)

        assert safety_checker.get_status() == SafetyStatus.PAUSED
        assert paused[0] is True
        assert safety_checker.is_learning_allowed() is False

        # Recovery
        safety_checker._last_accuracy = None  # Reset degradation tracking
        mock_model.get_accuracy.return_value = 0.95
        result = safety_checker.check_model(mock_model)

        assert result.passed is True
        assert safety_checker.get_status() == SafetyStatus.OK
        assert resumed[0] is True
        assert safety_checker.is_learning_allowed() is True

    def test_metrics_tracking_throughout(self, safety_checker):
        """Test metrics are tracked correctly throughout operations."""
        # Perform various operations
        safety_checker.check_accuracy(0.92)  # Pass
        safety_checker.check_accuracy(0.70)  # Fail
        safety_checker._last_accuracy = None
        safety_checker.check_accuracy(0.91)  # Pass

        metrics = safety_checker.get_metrics()

        assert metrics.total_checks == 3
        assert metrics.passed_checks == 2
        assert metrics.failed_checks == 1
        assert metrics.max_consecutive_failures >= 1
