"""
Adaptive Learning Engine - Safety Bounds Checker
Constitutional Hash: cdd01ef066bc6cf2

Safety bounds checking to prevent model degradation through
accuracy threshold validation and circuit breaker patterns.
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.safety.enums import CheckResult, SafetyStatus
from src.safety.models import SafetyAlert, SafetyCheckResult, SafetyMetrics

logger = logging.getLogger(__name__)


class SafetyBoundsChecker:
    """
    Safety bounds checker to prevent model degradation.
    Implements circuit breaker pattern for online learning.
    See SAFETY_DESIGN.md for detailed design rationale and state machine.
    """

    def __init__(
        self,
        accuracy_threshold: float = 0.85,
        consecutive_failures_limit: int = 3,
        min_samples_for_check: int = 100,
        enable_auto_pause: bool = True,
        degradation_threshold: float = 0.05,
    ) -> None:
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
            },
        )

    def check_model(
        self,
        model: Any,
        validation_data: Optional[List[Tuple[Dict[str, Any], int]]] = None,
    ) -> SafetyCheckResult:
        """Main entry point for safety checks."""
        with self._lock:
            self._total_checks += 1
            self._last_check_time = time.time()

            # 1. Cold Start Check
            sample_count = self._get_sample_count(model)
            if sample_count < self.min_samples_for_check:
                return self._skip_cold_start(sample_count)

            # 2. Accuracy Calculation
            accuracy = self._get_model_accuracy(model, validation_data)

            # 3. Absolute Threshold Check
            if accuracy < self.accuracy_threshold:
                return self._handle_failure(
                    CheckResult.FAILED_ACCURACY,
                    accuracy,
                    f"Accuracy {accuracy:.3f} below threshold {self.accuracy_threshold:.3f}",
                )

            # 4. Relative Degradation Check
            if self._last_accuracy is not None:
                drop = self._last_accuracy - accuracy
                if drop > self.degradation_threshold:
                    return self._handle_failure(
                        CheckResult.FAILED_DEGRADATION,
                        accuracy,
                        f"Significant degradation detected: Accuracy dropped {drop:.3f} from {self._last_accuracy:.3f}",
                        metadata={"previous_accuracy": self._last_accuracy, "accuracy_drop": drop},
                    )

            # 5. All Checks Passed
            return self._handle_success(accuracy)

    def check_accuracy(self, accuracy: float) -> SafetyCheckResult:
        """Simplified check for a direct accuracy value."""
        with self._lock:
            self._total_checks += 1
            self._last_check_time = time.time()

            if accuracy < self.accuracy_threshold:
                return self._handle_failure(
                    CheckResult.FAILED_ACCURACY,
                    accuracy,
                    f"Accuracy {accuracy:.3f} below threshold {self.accuracy_threshold:.3f}",
                )

            if self._last_accuracy is not None:
                drop = self._last_accuracy - accuracy
                if drop > self.degradation_threshold:
                    return self._handle_failure(
                        CheckResult.FAILED_DEGRADATION,
                        accuracy,
                        f"Significant degradation detected: Accuracy dropped {drop:.3f} from {self._last_accuracy:.3f}",
                        metadata={"previous_accuracy": self._last_accuracy, "accuracy_drop": drop},
                    )

            return self._handle_success(accuracy)

    def _get_sample_count(self, model: Any) -> int:
        try:
            return model.get_sample_count()
        except (AttributeError, TypeError):
            return 0

    def _skip_cold_start(self, sample_count: int) -> SafetyCheckResult:
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

    def _get_model_accuracy(
        self, model: Any, validation_data: Optional[List[Tuple[Dict[str, Any], int]]] = None
    ) -> float:
        if validation_data and len(validation_data) > 0:
            return self._calculate_validation_accuracy(model, validation_data)
        try:
            return model.get_accuracy()
        except (AttributeError, TypeError):
            return 0.0

    def _calculate_validation_accuracy(
        self, model: Any, validation_data: List[Tuple[Dict[str, Any], int]]
    ) -> float:
        correct = 0
        total = len(validation_data)
        for features, label in validation_data:
            try:
                # Compatibility with different model interfaces
                if hasattr(model, "predict_one"):
                    pred_result = model.predict_one(features)
                    prediction = getattr(pred_result, "prediction", pred_result)
                else:
                    prediction = model.predict(features)

                if prediction == label:
                    correct += 1
            except Exception as e:
                logger.error(f"Error during validation prediction: {e}")
        return correct / total if total > 0 else 0.0

    def _handle_success(self, accuracy: float) -> SafetyCheckResult:
        self._passed_checks += 1
        self._consecutive_failures = 0
        self._last_accuracy = accuracy

        if self._status == SafetyStatus.WARNING:
            self._status = SafetyStatus.OK
        elif self._status == SafetyStatus.PAUSED:
            # If we were paused but now pass, auto-resume
            self._resume_learning()
            logger.info("Safety check passed: Auto-resumed learning")

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
        self._failed_checks += 1
        self._consecutive_failures += 1
        self._max_consecutive_failures = max(
            self._max_consecutive_failures, self._consecutive_failures
        )
        self._last_failure_time = time.time()
        self._last_accuracy = accuracy

        if self._consecutive_failures >= self.consecutive_failures_limit:
            if self._status != SafetyStatus.PAUSED:
                action = "paused_learning" if self.enable_auto_pause else "none"
                severity = "critical"
                self._status = (
                    SafetyStatus.PAUSED if self.enable_auto_pause else SafetyStatus.CRITICAL
                )

                self._generate_alert(
                    severity, f"CIRCUIT BREAKER OPENED: {message}", accuracy, action
                )
                if self.enable_auto_pause:
                    self._pause_learning(already_paused=True)
            else:
                action = "none"
        else:
            self._status = SafetyStatus.WARNING
            action = "none"
            self._generate_alert("warning", f"Safety warning: {message}", accuracy, action)

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

    def _pause_learning(self, already_paused: bool = False) -> None:
        if not already_paused:
            self._status = SafetyStatus.PAUSED
        self._times_paused += 1
        logger.critical("Safety circuit breaker: Learning PAUSED")
        for callback in self._pause_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in pause callback: {e}")

    def _resume_learning(self) -> None:
        self._status = SafetyStatus.OK
        self._consecutive_failures = 0
        self._last_accuracy = None  # Reset baseline on manual resume
        self._times_resumed += 1
        logger.info("Safety circuit breaker: Learning RESUMED")
        for callback in self._resume_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in resume callback: {e}")

    def _generate_alert(self, severity: str, message: str, accuracy: float, action: str) -> None:
        alert = SafetyAlert(
            severity=severity,
            message=message,
            consecutive_failures=self._consecutive_failures,
            current_accuracy=accuracy,
            threshold=self.accuracy_threshold,
            action_taken=action,
        )
        self._alert_history.append(alert)
        if len(self._alert_history) > self._max_alert_history:
            self._alert_history.pop(0)

        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    # Methods for state management and metrics
    def force_resume(self) -> None:
        with self._lock:
            self._resume_learning()

    def reset_failures(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            if self._status != SafetyStatus.PAUSED:
                self._status = SafetyStatus.OK

    def is_learning_allowed(self) -> bool:
        return self._status != SafetyStatus.PAUSED

    def get_status(self) -> SafetyStatus:
        return self._status

    def get_consecutive_failures(self) -> int:
        return self._consecutive_failures

    def get_metrics(self) -> SafetyMetrics:
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
        with self._lock:
            return self._alert_history[-limit:] if limit > 0 else []

    def get_config(self) -> Dict[str, Any]:
        return {
            "accuracy_threshold": self.accuracy_threshold,
            "consecutive_failures_limit": self.consecutive_failures_limit,
            "min_samples_for_check": self.min_samples_for_check,
            "enable_auto_pause": self.enable_auto_pause,
            "degradation_threshold": self.degradation_threshold,
        }

    def update_threshold(self, new_threshold: float) -> None:
        if not 0.0 <= new_threshold <= 1.0:
            raise ValueError(f"accuracy_threshold must be between 0 and 1, got {new_threshold}")
        with self._lock:
            self.accuracy_threshold = new_threshold
            logger.info(f"SafetyBoundsChecker accuracy threshold updated to {new_threshold}")

    # Callback registration
    def register_alert_callback(self, callback: Callable[[SafetyAlert], None]) -> None:
        self._alert_callbacks.append(callback)

    def unregister_alert_callback(self, callback: Callable[[SafetyAlert], None]) -> bool:
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
            return True
        return False

    def register_pause_callback(self, callback: Callable[[], None]) -> None:
        self._pause_callbacks.append(callback)

    def unregister_pause_callback(self, callback: Callable[[], None]) -> bool:
        if callback in self._pause_callbacks:
            self._pause_callbacks.remove(callback)
            return True
        return False

    def register_resume_callback(self, callback: Callable[[], None]) -> None:
        self._resume_callbacks.append(callback)

    def unregister_resume_callback(self, callback: Callable[[], None]) -> bool:
        if callback in self._resume_callbacks:
            self._resume_callbacks.remove(callback)
            return True
        return False

    def reset(self) -> None:
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
            self._alert_history = []
            logger.info("SafetyBoundsChecker reset to initial state")

    def __repr__(self) -> str:
        return f"SafetyBoundsChecker(status={self._status.value}, failures={self._consecutive_failures}, threshold={self.accuracy_threshold})"
