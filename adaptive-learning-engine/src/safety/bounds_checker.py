"""
Adaptive Learning Engine - Safety Bounds Checker
Constitutional Hash: cdd01ef066bc6cf2

Safety bounds checking to prevent model degradation through
accuracy threshold validation and circuit breaker patterns.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SafetyStatus(Enum):
    """Current safety status of the learning system."""

    OK = "ok"  # All checks passing
    WARNING = "warning"  # Below threshold but still learning
    PAUSED = "paused"  # Learning paused due to consecutive failures
    CRITICAL = "critical"  # Requires manual intervention


class CheckResult(Enum):
    """Result of a single safety check."""

    PASSED = "passed"
    FAILED_ACCURACY = "failed_accuracy"
    FAILED_DEGRADATION = "failed_degradation"
    FAILED_DRIFT = "failed_drift"
    SKIPPED_COLD_START = "skipped_cold_start"
    SKIPPED_INSUFFICIENT_DATA = "skipped_insufficient_data"


@dataclass
class SafetyCheckResult:
    """Result of a safety bounds check."""

    passed: bool
    result: CheckResult
    current_accuracy: float
    threshold: float
    message: str
    consecutive_failures: int
    safety_status: SafetyStatus
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "passed": self.passed,
            "result": self.result.value,
            "current_accuracy": self.current_accuracy,
            "threshold": self.threshold,
            "message": self.message,
            "consecutive_failures": self.consecutive_failures,
            "safety_status": self.safety_status.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class SafetyAlert:
    """Alert generated when safety bounds are violated."""

    severity: str  # "warning", "critical"
    message: str
    consecutive_failures: int
    current_accuracy: float
    threshold: float
    action_taken: str  # "none", "paused_learning", "alert_sent"
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "severity": self.severity,
            "message": self.message,
            "consecutive_failures": self.consecutive_failures,
            "current_accuracy": self.current_accuracy,
            "threshold": self.threshold,
            "action_taken": self.action_taken,
            "timestamp": self.timestamp,
            "context": self.context,
        }


@dataclass
class SafetyMetrics:
    """Metrics for safety bounds checking."""

    total_checks: int
    passed_checks: int
    failed_checks: int
    consecutive_failures: int
    max_consecutive_failures: int
    times_paused: int
    times_resumed: int
    current_status: SafetyStatus
    last_check_time: Optional[float]
    last_failure_time: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "consecutive_failures": self.consecutive_failures,
            "max_consecutive_failures": self.max_consecutive_failures,
            "times_paused": self.times_paused,
            "times_resumed": self.times_resumed,
            "current_status": self.current_status.value,
            "last_check_time": self.last_check_time,
            "last_failure_time": self.last_failure_time,
        }


class SafetyBoundsChecker:
    """Safety bounds checker to prevent model degradation.

    Implements circuit breaker pattern for online learning:
    - Checks model accuracy against configurable threshold
    - Tracks consecutive failures
    - Pauses learning after too many consecutive failures
    - Provides alert callbacks for monitoring integration

    The safety bounds prevent model degradation by:
    1. Rejecting updates when accuracy drops below threshold
    2. Pausing learning when consecutive failures exceed limit
    3. Alerting operators for manual intervention

    Example usage:
        # Initialize checker with thresholds
        checker = SafetyBoundsChecker(
            accuracy_threshold=0.85,
            consecutive_failures_limit=3,
        )

        # Check model before update
        result = checker.check_model(model)
        if result.passed:
            # Proceed with model update
            model_manager.swap_model(new_model)
        else:
            # Handle rejection
            logger.warning(f"Safety check failed: {result.message}")

        # Register alert callback
        checker.register_alert_callback(lambda alert: notify_ops(alert))

    Integration with ModelManager:
        async def safe_model_update(
            manager: ModelManager,
            checker: SafetyBoundsChecker,
            new_model: OnlineLearner,
        ) -> SwapResult:
            result = checker.check_model(new_model)
            if not result.passed:
                if result.safety_status == SafetyStatus.PAUSED:
                    manager.pause_learning()
                return SwapResult(
                    status=SwapStatus.REJECTED_SAFETY,
                    message=result.message,
                )
            return await manager.swap_model(new_model)
    """

    def __init__(
        self,
        accuracy_threshold: float = 0.85,
        consecutive_failures_limit: int = 3,
        min_samples_for_check: int = 100,
        enable_auto_pause: bool = True,
        degradation_threshold: float = 0.05,
    ) -> None:
        """Initialize the safety bounds checker.

        Args:
            accuracy_threshold: Minimum accuracy required (0.0-1.0).
            consecutive_failures_limit: Number of consecutive failures before pause.
            min_samples_for_check: Minimum samples before safety check is active.
            enable_auto_pause: If True, automatically pause learning on limit breach.
            degradation_threshold: Maximum allowed accuracy drop per update.
        """
        # Validate thresholds
        if not 0.0 <= accuracy_threshold <= 1.0:
            raise ValueError(
                f"accuracy_threshold must be between 0 and 1, got {accuracy_threshold}"
            )
        if consecutive_failures_limit < 1:
            raise ValueError(
                f"consecutive_failures_limit must be >= 1, got {consecutive_failures_limit}"
            )
        if min_samples_for_check < 0:
            raise ValueError(f"min_samples_for_check must be >= 0, got {min_samples_for_check}")
        if not 0.0 <= degradation_threshold <= 1.0:
            raise ValueError(
                f"degradation_threshold must be between 0 and 1, got {degradation_threshold}"
            )

        self.accuracy_threshold = accuracy_threshold
        self.consecutive_failures_limit = consecutive_failures_limit
        self.min_samples_for_check = min_samples_for_check
        self.enable_auto_pause = enable_auto_pause
        self.degradation_threshold = degradation_threshold

        # Thread safety
        self._lock = threading.RLock()

        # State tracking
        self._consecutive_failures = 0
        self._status = SafetyStatus.OK
        self._last_accuracy: Optional[float] = None

        # Metrics
        self._total_checks = 0
        self._passed_checks = 0
        self._failed_checks = 0
        self._max_consecutive_failures = 0
        self._times_paused = 0
        self._times_resumed = 0
        self._last_check_time: Optional[float] = None
        self._last_failure_time: Optional[float] = None

        # Alert history
        self._alert_history: List[SafetyAlert] = []
        self._max_alert_history = 100

        # Callbacks
        self._alert_callbacks: List[Callable[[SafetyAlert], None]] = []
        self._pause_callbacks: List[Callable[[], None]] = []
        self._resume_callbacks: List[Callable[[], None]] = []

        logger.info(
            "SafetyBoundsChecker initialized",
            extra={
                "accuracy_threshold": accuracy_threshold,
                "consecutive_failures_limit": consecutive_failures_limit,
                "min_samples_for_check": min_samples_for_check,
                "enable_auto_pause": enable_auto_pause,
            },
        )

    def check_model(
        self,
        model: Any,
        validation_data: Optional[List[Tuple[Dict[str, Any], int]]] = None,
    ) -> SafetyCheckResult:
        """Check if a model passes safety bounds.

        Validates model accuracy against threshold and checks for degradation.
        If validation_data is provided, uses it to calculate accuracy.
        Otherwise, uses the model's internal accuracy metric.

        Args:
            model: The OnlineLearner model to check.
            validation_data: Optional list of (features, label) tuples for validation.

        Returns:
            SafetyCheckResult with pass/fail status and details.
        """
        with self._lock:
            self._total_checks += 1
            self._last_check_time = time.time()

            # Get sample count from model
            try:
                sample_count = model.get_sample_count()
            except (AttributeError, TypeError):
                sample_count = 0

            # Skip check during cold start
            if sample_count < self.min_samples_for_check:
                return SafetyCheckResult(
                    passed=True,
                    result=CheckResult.SKIPPED_COLD_START,
                    current_accuracy=0.0,
                    threshold=self.accuracy_threshold,
                    message=f"Safety check skipped: only {sample_count} samples (need {self.min_samples_for_check})",
                    consecutive_failures=self._consecutive_failures,
                    safety_status=self._status,
                    metadata={"sample_count": sample_count},
                )

            # Calculate accuracy
            if validation_data is not None and len(validation_data) > 0:
                current_accuracy = self._calculate_validation_accuracy(model, validation_data)
            else:
                try:
                    current_accuracy = model.get_accuracy()
                except (AttributeError, TypeError):
                    current_accuracy = 0.0

            # Check accuracy threshold
            if current_accuracy < self.accuracy_threshold:
                return self._handle_failure(
                    CheckResult.FAILED_ACCURACY,
                    current_accuracy,
                    f"Accuracy {current_accuracy:.3f} below threshold {self.accuracy_threshold:.3f}",
                )

            # Check for significant degradation
            if self._last_accuracy is not None:
                accuracy_drop = self._last_accuracy - current_accuracy
                if accuracy_drop > self.degradation_threshold:
                    return self._handle_failure(
                        CheckResult.FAILED_DEGRADATION,
                        current_accuracy,
                        f"Accuracy dropped by {accuracy_drop:.3f} (threshold: {self.degradation_threshold:.3f})",
                        metadata={
                            "previous_accuracy": self._last_accuracy,
                            "accuracy_drop": accuracy_drop,
                        },
                    )

            # Passed all checks
            return self._handle_success(current_accuracy)

    def check_accuracy(self, accuracy: float) -> SafetyCheckResult:
        """Check if an accuracy value passes safety bounds.

        Simplified check when you have the accuracy value directly.

        Args:
            accuracy: Accuracy value to check (0.0-1.0).

        Returns:
            SafetyCheckResult with pass/fail status and details.
        """
        with self._lock:
            self._total_checks += 1
            self._last_check_time = time.time()

            # Check accuracy threshold
            if accuracy < self.accuracy_threshold:
                return self._handle_failure(
                    CheckResult.FAILED_ACCURACY,
                    accuracy,
                    f"Accuracy {accuracy:.3f} below threshold {self.accuracy_threshold:.3f}",
                )

            # Check for significant degradation
            if self._last_accuracy is not None:
                accuracy_drop = self._last_accuracy - accuracy
                if accuracy_drop > self.degradation_threshold:
                    return self._handle_failure(
                        CheckResult.FAILED_DEGRADATION,
                        accuracy,
                        f"Accuracy dropped by {accuracy_drop:.3f} (threshold: {self.degradation_threshold:.3f})",
                        metadata={
                            "previous_accuracy": self._last_accuracy,
                            "accuracy_drop": accuracy_drop,
                        },
                    )

            # Passed
            return self._handle_success(accuracy)

    def _handle_success(self, accuracy: float) -> SafetyCheckResult:
        """Handle a successful safety check.

        Args:
            accuracy: The accuracy value that passed.

        Returns:
            SafetyCheckResult indicating success.
        """
        self._passed_checks += 1
        self._consecutive_failures = 0
        self._last_accuracy = accuracy

        # Resume from paused state if applicable
        if self._status == SafetyStatus.PAUSED:
            self._resume_learning()

        self._status = SafetyStatus.OK

        return SafetyCheckResult(
            passed=True,
            result=CheckResult.PASSED,
            current_accuracy=accuracy,
            threshold=self.accuracy_threshold,
            message="Safety check passed",
            consecutive_failures=0,
            safety_status=self._status,
        )

    def _handle_failure(
        self,
        result: CheckResult,
        accuracy: float,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SafetyCheckResult:
        """Handle a failed safety check.

        Increments failure counter and potentially pauses learning.

        Args:
            result: The type of failure.
            accuracy: The accuracy value that failed.
            message: Human-readable failure message.
            metadata: Additional context for the failure.

        Returns:
            SafetyCheckResult indicating failure.
        """
        self._failed_checks += 1
        self._consecutive_failures += 1
        self._max_consecutive_failures = max(
            self._max_consecutive_failures, self._consecutive_failures
        )
        self._last_failure_time = time.time()

        # Determine severity and action
        if self._consecutive_failures >= self.consecutive_failures_limit:
            # Critical - pause learning
            if self._status != SafetyStatus.PAUSED:
                self._status = SafetyStatus.CRITICAL
                if self.enable_auto_pause:
                    self._pause_learning()
                self._generate_alert(
                    severity="critical",
                    message=f"Learning paused after {self._consecutive_failures} consecutive failures",
                    accuracy=accuracy,
                    action="paused_learning",
                )
        else:
            # Warning - not yet at limit
            self._status = SafetyStatus.WARNING
            self._generate_alert(
                severity="warning",
                message=f"Safety check failed ({self._consecutive_failures}/{self.consecutive_failures_limit}): {message}",
                accuracy=accuracy,
                action="none",
            )

        logger.warning(
            "Safety check failed",
            extra={
                "result": result.value,
                "accuracy": accuracy,
                "consecutive_failures": self._consecutive_failures,
                "status": self._status.value,
            },
        )

        return SafetyCheckResult(
            passed=False,
            result=result,
            current_accuracy=accuracy,
            threshold=self.accuracy_threshold,
            message=message,
            consecutive_failures=self._consecutive_failures,
            safety_status=self._status,
            metadata=metadata or {},
        )

    def _calculate_validation_accuracy(
        self,
        model: Any,
        validation_data: List[Tuple[Dict[str, Any], int]],
    ) -> float:
        """Calculate accuracy on a validation dataset.

        Args:
            model: The model to validate.
            validation_data: List of (features, label) tuples.

        Returns:
            Accuracy on the validation set (0.0-1.0).
        """
        if not validation_data:
            return 0.0

        correct = 0
        total = len(validation_data)

        for features, label in validation_data:
            try:
                result = model.predict_one(features)
                prediction = result.prediction if hasattr(result, "prediction") else result
                if prediction == label:
                    correct += 1
            except Exception as e:
                logger.debug(f"Validation prediction error: {e}")
                # Count as incorrect

        return correct / total if total > 0 else 0.0

    def _pause_learning(self) -> None:
        """Pause learning due to safety bounds violation."""
        self._status = SafetyStatus.PAUSED
        self._times_paused += 1

        logger.warning(
            "Learning paused by safety bounds",
            extra={
                "consecutive_failures": self._consecutive_failures,
                "times_paused": self._times_paused,
            },
        )

        # Notify pause callbacks
        for callback in self._pause_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Pause callback error: {e}")

    def _resume_learning(self) -> None:
        """Resume learning after safety bounds are satisfied."""
        self._times_resumed += 1

        logger.info(
            "Learning resumed after safety bounds satisfied",
            extra={
                "times_resumed": self._times_resumed,
            },
        )

        # Notify resume callbacks
        for callback in self._resume_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Resume callback error: {e}")

    def _generate_alert(
        self,
        severity: str,
        message: str,
        accuracy: float,
        action: str,
    ) -> None:
        """Generate and dispatch a safety alert.

        Args:
            severity: Alert severity ("warning" or "critical").
            message: Alert message.
            accuracy: Current accuracy value.
            action: Action taken ("none", "paused_learning").
        """
        alert = SafetyAlert(
            severity=severity,
            message=message,
            consecutive_failures=self._consecutive_failures,
            current_accuracy=accuracy,
            threshold=self.accuracy_threshold,
            action_taken=action,
            context={
                "status": self._status.value,
                "total_checks": self._total_checks,
                "failed_checks": self._failed_checks,
            },
        )

        # Add to history
        self._alert_history.append(alert)
        if len(self._alert_history) > self._max_alert_history:
            self._alert_history = self._alert_history[-self._max_alert_history :]

        # Dispatch to callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    def reset_failures(self) -> None:
        """Reset the consecutive failure counter.

        Use with caution - this bypasses the safety circuit breaker.
        Should only be called after manual review and intervention.
        """
        with self._lock:
            old_failures = self._consecutive_failures
            self._consecutive_failures = 0
            self._status = SafetyStatus.OK

            logger.info(
                "Safety failures reset manually",
                extra={"old_failures": old_failures},
            )

            # Resume if was paused
            if old_failures >= self.consecutive_failures_limit:
                self._resume_learning()

    def force_resume(self) -> None:
        """Force resume learning after manual intervention.

        Should only be called after manual review.
        """
        with self._lock:
            self.reset_failures()
            self._last_accuracy = None  # Reset degradation tracking

            logger.info("Learning force-resumed after manual intervention")

    def is_learning_allowed(self) -> bool:
        """Check if learning is currently allowed.

        Returns:
            True if learning is allowed, False if paused.
        """
        with self._lock:
            return self._status != SafetyStatus.PAUSED

    def get_status(self) -> SafetyStatus:
        """Get the current safety status.

        Returns:
            Current SafetyStatus enum value.
        """
        with self._lock:
            return self._status

    def get_consecutive_failures(self) -> int:
        """Get the current consecutive failure count.

        Returns:
            Number of consecutive failures.
        """
        with self._lock:
            return self._consecutive_failures

    def get_metrics(self) -> SafetyMetrics:
        """Get current safety metrics.

        Returns:
            SafetyMetrics dataclass with all current metrics.
        """
        with self._lock:
            return SafetyMetrics(
                total_checks=self._total_checks,
                passed_checks=self._passed_checks,
                failed_checks=self._failed_checks,
                consecutive_failures=self._consecutive_failures,
                max_consecutive_failures=self._max_consecutive_failures,
                times_paused=self._times_paused,
                times_resumed=self._times_resumed,
                current_status=self._status,
                last_check_time=self._last_check_time,
                last_failure_time=self._last_failure_time,
            )

    def get_alert_history(self, limit: int = 10) -> List[SafetyAlert]:
        """Get recent safety alerts.

        Args:
            limit: Maximum number of alerts to return.

        Returns:
            List of recent SafetyAlert objects.
        """
        with self._lock:
            return list(self._alert_history[-limit:])

    def get_config(self) -> Dict[str, Any]:
        """Get the checker configuration.

        Returns:
            Dictionary with current configuration.
        """
        return {
            "accuracy_threshold": self.accuracy_threshold,
            "consecutive_failures_limit": self.consecutive_failures_limit,
            "min_samples_for_check": self.min_samples_for_check,
            "enable_auto_pause": self.enable_auto_pause,
            "degradation_threshold": self.degradation_threshold,
        }

    def update_threshold(self, new_threshold: float) -> None:
        """Update the accuracy threshold.

        Args:
            new_threshold: New accuracy threshold (0.0-1.0).
        """
        if not 0.0 <= new_threshold <= 1.0:
            raise ValueError(f"accuracy_threshold must be between 0 and 1, got {new_threshold}")

        with self._lock:
            old_threshold = self.accuracy_threshold
            self.accuracy_threshold = new_threshold

            logger.info(
                "Safety threshold updated",
                extra={
                    "old_threshold": old_threshold,
                    "new_threshold": new_threshold,
                },
            )

    def register_alert_callback(self, callback: Callable[[SafetyAlert], None]) -> None:
        """Register a callback for safety alerts.

        Callbacks are invoked when safety violations occur.

        Args:
            callback: Function to call with SafetyAlert object.
        """
        with self._lock:
            self._alert_callbacks.append(callback)

    def unregister_alert_callback(self, callback: Callable[[SafetyAlert], None]) -> bool:
        """Unregister an alert callback.

        Args:
            callback: The callback to remove.

        Returns:
            True if callback was found and removed.
        """
        with self._lock:
            try:
                self._alert_callbacks.remove(callback)
                return True
            except ValueError:
                return False

    def register_pause_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback for when learning is paused.

        Args:
            callback: Function to call when learning is paused.
        """
        with self._lock:
            self._pause_callbacks.append(callback)

    def unregister_pause_callback(self, callback: Callable[[], None]) -> bool:
        """Unregister a pause callback.

        Args:
            callback: The callback to remove.

        Returns:
            True if callback was found and removed.
        """
        with self._lock:
            try:
                self._pause_callbacks.remove(callback)
                return True
            except ValueError:
                return False

    def register_resume_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback for when learning is resumed.

        Args:
            callback: Function to call when learning is resumed.
        """
        with self._lock:
            self._resume_callbacks.append(callback)

    def unregister_resume_callback(self, callback: Callable[[], None]) -> bool:
        """Unregister a resume callback.

        Args:
            callback: The callback to remove.

        Returns:
            True if callback was found and removed.
        """
        with self._lock:
            try:
                self._resume_callbacks.remove(callback)
                return True
            except ValueError:
                return False

    def reset(self) -> None:
        """Reset the checker to initial state.

        Warning: This clears all state and metrics.
        """
        with self._lock:
            self._consecutive_failures = 0
            self._status = SafetyStatus.OK
            self._last_accuracy = None
            self._total_checks = 0
            self._passed_checks = 0
            self._failed_checks = 0
            self._max_consecutive_failures = 0
            self._times_paused = 0
            self._times_resumed = 0
            self._last_check_time = None
            self._last_failure_time = None
            self._alert_history.clear()

            logger.info("SafetyBoundsChecker reset to initial state")

    def __repr__(self) -> str:
        """String representation of the checker."""
        return (
            f"SafetyBoundsChecker("
            f"threshold={self.accuracy_threshold:.2f}, "
            f"failures={self._consecutive_failures}/{self.consecutive_failures_limit}, "
            f"status={self._status.value})"
        )
