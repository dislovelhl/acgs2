"""
Adaptive Learning Engine - Safety Bounds Checker
Constitutional Hash: cdd01ef066bc6cf2

Safety bounds checking to prevent model degradation through
accuracy threshold validation and circuit breaker patterns.

CIRCUIT BREAKER PATTERN FOR ML SAFETY
======================================

This module implements a circuit breaker pattern adapted from reliability engineering
for machine learning safety. Circuit breakers prevent cascading failures by detecting
problematic conditions and temporarily halting operations before they cause wider damage.

Traditional Circuit Breaker (Electrical/Software):
- Monitors for failures (errors, timeouts, resource exhaustion)
- Opens circuit after threshold to prevent cascading failures
- Allows system recovery before resuming operations
- Three states: CLOSED (normal), OPEN (failing), HALF-OPEN (testing recovery)

ML Safety Circuit Breaker (This Implementation):
- Monitors model accuracy and degradation
- Pauses learning after consecutive accuracy failures
- Prevents bad model updates from reaching production
- Four states: OK, WARNING, CRITICAL, PAUSED (see SafetyStatus enum)

Why Circuit Breakers Are Critical for ML Safety:
1. **Prevents Cascading Degradation**: A bad model update could corrupt future training,
   leading to progressive degradation. Circuit breaker halts learning before this cascade.

2. **Fail-Safe for Governance**: In access control/governance, a degraded model could
   grant improper permissions or deny legitimate access. The circuit breaker ensures
   the model maintains minimum quality standards.

3. **Observable Failure States**: Instead of silent degradation, the circuit breaker
   provides clear state transitions (OK → WARNING → CRITICAL → PAUSED) that can be
   monitored and alerted on.

4. **Human-in-the-Loop**: By pausing on critical failures, the circuit breaker creates
   an opportunity for manual review before resuming operations. This is essential for
   safety-critical applications where automated recovery is risky.

FAILURE MODES AND DETECTION
============================

This checker detects multiple failure modes to provide defense-in-depth:

1. **FAILED_ACCURACY**: Model accuracy below absolute threshold
   - Indicates overall model performance is unacceptable
   - Threshold: accuracy_threshold (default 0.85 = 85%)
   - Example: Model drops to 80% accuracy after bad training batch

2. **FAILED_DEGRADATION**: Significant accuracy drop from previous check
   - Detects sudden performance regression even if still above threshold
   - Threshold: degradation_threshold (default 0.05 = 5% drop)
   - Example: Model goes from 90% → 84% accuracy (6% drop)

3. **FAILED_DRIFT**: Model failing due to distribution drift (reserved for integration)
   - Reserved for future integration with DriftDetector
   - Would indicate data distribution has shifted beyond model's capability

4. **SKIPPED_COLD_START**: Safety check bypassed during model initialization
   - Model has insufficient samples for meaningful accuracy estimation
   - Threshold: min_samples_for_check (default 100 samples)

5. **SKIPPED_INSUFFICIENT_DATA**: Safety check bypassed due to lack of validation data
   - No validation data provided and model has no internal accuracy metric

STATE MACHINE AND TRANSITIONS
==============================

The circuit breaker implements a state machine that escalates based on consecutive failures:

State: OK (CLOSED CIRCUIT)
- All safety checks passing
- Learning proceeds normally
- Consecutive failures: 0

    ↓ (First accuracy failure)

State: WARNING (DEGRADED)
- Some safety checks failing but below consecutive limit
- Learning continues but system is on alert
- Consecutive failures: 1 to (limit - 1)
- Example: 1/3 or 2/3 failures

    ↓ (Consecutive failures reach limit)

State: CRITICAL → PAUSED (OPEN CIRCUIT)
- Too many consecutive failures detected
- Learning automatically paused to prevent further degradation
- Consecutive failures: ≥ limit (default 3)
- Requires manual intervention (force_resume) to restart

    ↓ (Manual intervention + passing check)

State: OK (CIRCUIT RESET)
- Manual reset or passing check after pause
- Consecutive failures counter reset to 0
- Learning resumes

Why Consecutive Failures Matter:
- Single failure could be transient (bad batch, outlier data)
- Consecutive failures indicate systematic problem
- Default limit of 3 balances noise tolerance vs. safety
- Similar to TCP retransmit (3 strikes before circuit opens)

GOVERNANCE-SPECIFIC CONSIDERATIONS
===================================

For access control and governance applications:

1. **Conservative Thresholds**: Default 85% accuracy may seem low for some ML tasks,
   but governance systems often deal with:
   - Imbalanced data (rare access patterns)
   - High cost of false positives (denied legitimate access)
   - High cost of false negatives (granted improper access)

2. **Safety-Critical Operation**: Unlike recommendation systems where wrong predictions
   are annoying, governance errors can:
   - Violate compliance regulations (GDPR, SOC2, etc.)
   - Expose sensitive data to unauthorized users
   - Block critical business operations

3. **Audit Trail**: Circuit breaker state transitions create observable events for
   compliance auditing and incident investigation.

References:
- Michael Nygard, "Release It! Design and Deploy Production-Ready Software" (2007)
  Chapter on Circuit Breaker pattern for fault tolerance
- Martin Fowler, "CircuitBreaker" (2014)
  https://martinfowler.com/bliki/CircuitBreaker.html
- Netflix Hystrix (implementation reference)
  https://github.com/Netflix/Hystrix/wiki/How-it-Works#CircuitBreaker
- Sculley et al., "Hidden Technical Debt in Machine Learning Systems" (2015)
  NIPS paper on ML system failure modes and safety

Usage Example with Circuit Breaker Pattern:
    # Initialize with circuit breaker thresholds
    checker = SafetyBoundsChecker(
        accuracy_threshold=0.85,           # Minimum acceptable accuracy
        consecutive_failures_limit=3,      # Open circuit after 3 failures
        enable_auto_pause=True,            # Auto-pause on critical failure
    )

    # Register callbacks for circuit breaker events
    checker.register_alert_callback(lambda alert:
        notify_ops(f"Circuit breaker alert: {alert.severity}"))
    checker.register_pause_callback(lambda:
        notify_ops("CRITICAL: Learning circuit OPENED (paused)"))
    checker.register_resume_callback(lambda:
        notify_ops("Learning circuit CLOSED (resumed)"))

    # Check model before each update (circuit breaker check)
    result = checker.check_model(new_model)

    # State transitions based on check result:
    # OK → WARNING (first failure)
    # WARNING → WARNING (second failure)
    # WARNING → CRITICAL/PAUSED (third failure - circuit opens)

    if result.safety_status == SafetyStatus.PAUSED:
        # Circuit is open - learning halted
        logger.critical("Circuit breaker opened - manual intervention required")
        # Investigate root cause, fix data/model issues
        # Manually reset: checker.force_resume()
    elif result.safety_status == SafetyStatus.WARNING:
        # Circuit degraded but still closed
        logger.warning(f"Circuit breaker warning: {result.consecutive_failures}/3 failures")
    elif result.passed:
        # Circuit closed and healthy
        manager.swap_model(new_model)
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SafetyStatus(Enum):
    """Current safety status of the learning system.

    These states represent the circuit breaker state machine:

    OK (CLOSED CIRCUIT):
        - All safety checks are passing
        - Model accuracy is above threshold
        - No recent degradation detected
        - Consecutive failures: 0
        - Learning: ENABLED
        - Analogy: Electrical circuit is closed, current flows normally

    WARNING (DEGRADED CIRCUIT):
        - Some safety checks are failing
        - Below consecutive failure limit
        - System is on alert but still operational
        - Consecutive failures: 1 to (limit - 1)
        - Learning: ENABLED but monitored
        - Analogy: Circuit is experiencing intermittent issues but not yet tripped
        - Example: Model failed 1 or 2 checks but not yet at limit of 3

    CRITICAL (CIRCUIT TRIPPING):
        - Consecutive failure limit reached
        - Circuit breaker is opening to prevent cascading failures
        - Transitional state before PAUSED
        - Consecutive failures: ≥ limit
        - Learning: BEING DISABLED
        - Analogy: Circuit breaker is actively tripping

    PAUSED (OPEN CIRCUIT):
        - Learning has been halted by circuit breaker
        - Too many consecutive failures detected
        - Requires manual intervention to resume
        - Consecutive failures: ≥ limit
        - Learning: DISABLED
        - Analogy: Circuit breaker is open, no current flows
        - Recovery: Requires force_resume() or manual reset

    State Transition Flow:
        OK → WARNING → CRITICAL → PAUSED → (manual reset) → OK

    The circuit breaker prevents cascading ML failures by halting learning
    when model quality degrades below acceptable levels. This is critical for
    governance systems where bad model updates could grant improper permissions
    or deny legitimate access.
    """

    OK = "ok"  # All checks passing (CLOSED CIRCUIT)
    WARNING = "warning"  # Below threshold but still learning (DEGRADED CIRCUIT)
    PAUSED = "paused"  # Learning paused due to consecutive failures (OPEN CIRCUIT)
    CRITICAL = "critical"  # Circuit breaker tripping, requires manual intervention


class CheckResult(Enum):
    """Result of a single safety check.

    These represent different failure modes the circuit breaker monitors:

    PASSED:
        - All safety checks passed
        - Model accuracy ≥ threshold
        - No significant degradation detected
        - Resets consecutive failure counter to 0
        - Circuit breaker closes (or stays closed)

    FAILED_ACCURACY:
        - Model accuracy below absolute threshold
        - Check: current_accuracy < accuracy_threshold
        - Default threshold: 0.85 (85% accuracy)
        - Indicates overall model performance is unacceptable
        - Example: Model accuracy drops to 80% after bad training batch
        - Increments consecutive failure counter
        - May trigger circuit breaker if consecutive failures ≥ limit

    FAILED_DEGRADATION:
        - Significant accuracy drop from previous check
        - Check: (previous_accuracy - current_accuracy) > degradation_threshold
        - Default threshold: 0.05 (5% drop)
        - Detects sudden performance regression even if above absolute threshold
        - Example: Model goes from 90% → 84% accuracy (6% drop)
        - Prevents gradual model rot from going unnoticed
        - Increments consecutive failure counter
        - More sensitive than FAILED_ACCURACY for detecting regressions

    FAILED_DRIFT:
        - Model failing due to distribution drift (reserved for future integration)
        - Would integrate with DriftDetector to detect when data distribution
          has shifted beyond the model's capability to adapt
        - Example: Governance policies fundamentally changed, requiring retraining
        - Currently not implemented but reserved for future use

    SKIPPED_COLD_START:
        - Safety check bypassed during model initialization
        - Model has insufficient samples for meaningful accuracy estimation
        - Check: sample_count < min_samples_for_check (default 100)
        - Accuracy metrics are unreliable with few samples (high variance)
        - Does NOT count as pass or fail (neutral result)
        - Does NOT reset consecutive failure counter
        - Example: Model trained on only 50 samples cannot provide reliable accuracy

    SKIPPED_INSUFFICIENT_DATA:
        - Safety check bypassed due to lack of validation data
        - No validation_data provided and model has no internal accuracy metric
        - Does NOT count as pass or fail (neutral result)
        - Does NOT reset consecutive failure counter
        - Indicates configuration issue that should be addressed

    Failure Mode Detection Strategy (Defense-in-Depth):

    The checker uses multiple failure modes to provide robust safety:
    1. FAILED_ACCURACY catches absolute performance issues
    2. FAILED_DEGRADATION catches relative regressions
    3. Both contribute to consecutive failure counter
    4. Circuit breaker trips on ANY consecutive failures (regardless of type)

    This multi-layered approach ensures the circuit breaker catches both:
    - Sudden crashes in model quality (FAILED_DEGRADATION)
    - Gradual decay below acceptable levels (FAILED_ACCURACY)
    """

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

        This is the main entry point for circuit breaker safety checks. It implements
        defense-in-depth by checking multiple failure modes:
        1. Cold start bypass (insufficient data for meaningful check)
        2. Absolute accuracy threshold (FAILED_ACCURACY)
        3. Relative degradation threshold (FAILED_DEGRADATION)

        Args:
            model: The OnlineLearner model to check.
            validation_data: Optional list of (features, label) tuples for validation.

        Returns:
            SafetyCheckResult with pass/fail status and details.
        """
        with self._lock:
            self._total_checks += 1
            self._last_check_time = time.time()

            # FAILURE MODE: SKIPPED_COLD_START
            #
            # Get sample count to determine if model has enough data for safety check
            # During cold start (few samples), accuracy is unreliable due to high variance
            try:
                sample_count = model.get_sample_count()
            except (AttributeError, TypeError):
                sample_count = 0

            # Skip check during cold start (insufficient samples)
            # Why min_samples_for_check=100?
            # - Statistical significance: Accuracy estimate has SE ≈ sqrt(p(1-p)/n)
            #   With n=100, SE ≈ 0.05 (5% margin of error at 95% CI)
            # - Prevents false alarms during model initialization
            # - Coordinated with OnlineLearner's min_training_samples for consistency
            if sample_count < self.min_samples_for_check:
                # Return neutral result (not pass/fail, just skipped)
                # Does NOT affect consecutive failure counter
                return SafetyCheckResult(
                    passed=True,  # Allow model swap during cold start
                    result=CheckResult.SKIPPED_COLD_START,
                    current_accuracy=0.0,
                    threshold=self.accuracy_threshold,
                    message=f"Safety check skipped: only {sample_count} samples (need {self.min_samples_for_check})",
                    consecutive_failures=self._consecutive_failures,
                    safety_status=self._status,
                    metadata={"sample_count": sample_count},
                )

            # ACCURACY CALCULATION
            #
            # Use validation data if provided (more reliable, held-out test set)
            # Otherwise fall back to model's internal accuracy (progressive validation)
            if validation_data is not None and len(validation_data) > 0:
                current_accuracy = self._calculate_validation_accuracy(model, validation_data)
            else:
                try:
                    current_accuracy = model.get_accuracy()
                except (AttributeError, TypeError):
                    current_accuracy = 0.0

            # FAILURE MODE 1: FAILED_ACCURACY
            #
            # Check if accuracy is below absolute threshold
            # This catches overall model performance degradation
            #
            # Why accuracy_threshold=0.85 for governance?
            # - Governance systems require high accuracy (access control is safety-critical)
            # - 85% balances precision/recall for typical imbalanced governance data
            # - Lower than 85% means too many false positives (denied access) or
            #   false negatives (improper access granted)
            # - Conservative threshold appropriate for compliance requirements
            if current_accuracy < self.accuracy_threshold:
                # CIRCUIT BREAKER: Increment failure counter
                # May transition OK → WARNING or WARNING → CRITICAL/PAUSED
                return self._handle_failure(
                    CheckResult.FAILED_ACCURACY,
                    current_accuracy,
                    f"Accuracy {current_accuracy:.3f} below threshold {self.accuracy_threshold:.3f}",
                )

            # FAILURE MODE 2: FAILED_DEGRADATION
            #
            # Check for significant accuracy drop from previous check
            # This catches sudden performance regression even if still above threshold
            #
            # Why degradation_threshold=0.05 (5% drop)?
            # - Detects sudden model degradation that could indicate:
            #   * Bad training batch (corrupted data)
            #   * Distribution shift (concept drift)
            #   * Model corruption (numerical instability)
            # - 5% is statistically significant for n=100+ samples (SE ≈ 5%)
            # - Prevents slow model rot by catching relative degradation
            # - More sensitive than absolute threshold for detecting regressions
            #
            # Example: Model at 90% accuracy drops to 84%
            # - Still above threshold (84% > 85% is false, so FAILED_ACCURACY too)
            # - But 6% drop exceeds degradation_threshold (6% > 5%)
            # - FAILED_DEGRADATION catches this regression
            if self._last_accuracy is not None:
                accuracy_drop = self._last_accuracy - current_accuracy
                if accuracy_drop > self.degradation_threshold:
                    # CIRCUIT BREAKER: Increment failure counter
                    # Provides metadata about previous accuracy and drop magnitude
                    return self._handle_failure(
                        CheckResult.FAILED_DEGRADATION,
                        current_accuracy,
                        f"Accuracy dropped by {accuracy_drop:.3f} (threshold: {self.degradation_threshold:.3f})",
                        metadata={
                            "previous_accuracy": self._last_accuracy,
                            "accuracy_drop": accuracy_drop,
                        },
                    )

            # PASSED: All safety checks passed
            #
            # Model accuracy is above threshold AND no significant degradation
            # CIRCUIT BREAKER: Reset failure counter to 0
            # May transition WARNING → OK or PAUSED → OK (circuit closes)
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

        CIRCUIT BREAKER CLOSES/RESETS
        ==============================

        This method handles the circuit breaker closing/resetting when a safety check passes.
        It represents the recovery path from failure states (WARNING, CRITICAL, PAUSED) back
        to normal operation (OK).

        Circuit Breaker Reset Behavior:
        1. Reset consecutive failure counter to 0
        2. Update last_accuracy for degradation tracking
        3. If circuit was PAUSED, automatically resume learning (circuit closes)
        4. Transition to OK state (normal operation)

        Why Automatic Resume is Safe:
        - Circuit only closes if a safety check PASSES (evidence of recovery)
        - Model accuracy is above threshold (quality verified)
        - No significant degradation detected (stability verified)
        - Unlike traditional circuit breakers (timeout-based), ML circuit breakers
          require proof of recovery before closing

        State Transitions on Success:
        - OK → OK: Circuit already closed, counter stays at 0
        - WARNING → OK: Circuit closes, consecutive failures reset
        - PAUSED → OK: Circuit closes, learning resumes (calls _resume_learning)

        Args:
            accuracy: The accuracy value that passed.

        Returns:
            SafetyCheckResult indicating success.
        """
        # Track success metrics
        self._passed_checks += 1

        # CIRCUIT BREAKER RESET: Reset consecutive failure counter
        # This is the key to circuit breaker recovery - a single success
        # resets the failure count, requiring failures to be truly consecutive
        # to trigger circuit open
        self._consecutive_failures = 0

        # Update accuracy for future degradation checks
        self._last_accuracy = accuracy

        # CIRCUIT BREAKER CLOSES: Resume from paused state if applicable
        # If circuit was OPEN (PAUSED), this successful check provides evidence
        # that the underlying issue has been resolved. Automatically close the
        # circuit and resume normal learning operations.
        if self._status == SafetyStatus.PAUSED:
            self._resume_learning()  # Triggers resume callbacks, logs recovery

        # Transition to OK state (circuit fully closed and healthy)
        self._status = SafetyStatus.OK

        return SafetyCheckResult(
            passed=True,
            result=CheckResult.PASSED,
            current_accuracy=accuracy,
            threshold=self.accuracy_threshold,
            message="Safety check passed",
            consecutive_failures=0,  # Reset to 0 on success
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

        This method implements the core circuit breaker escalation logic:
        1. Track consecutive failures (counter increments)
        2. Escalate from OK → WARNING → CRITICAL → PAUSED based on count
        3. Generate alerts at appropriate severity levels
        4. Trigger auto-pause when threshold is reached (circuit opens)

        Args:
            result: The type of failure.
            accuracy: The accuracy value that failed.
            message: Human-readable failure message.
            metadata: Additional context for the failure.

        Returns:
            SafetyCheckResult indicating failure.
        """
        # CIRCUIT BREAKER: Track failure metrics
        # These metrics are critical for circuit breaker state decisions
        self._failed_checks += 1  # Total failures (all-time)
        self._consecutive_failures += 1  # Consecutive failures (resets on success)
        self._max_consecutive_failures = max(
            self._max_consecutive_failures, self._consecutive_failures
        )
        self._last_failure_time = time.time()

        # CIRCUIT BREAKER STATE TRANSITION LOGIC
        #
        # The circuit breaker uses consecutive failures to determine when to open:
        # - Transient failures (single occurrence) don't trigger circuit open
        # - Persistent failures (consecutive occurrences) indicate systematic issue
        #
        # State Transitions:
        # OK (0 failures) → WARNING (1+ failures) → CRITICAL/PAUSED (3+ failures)
        #
        # Why 3 consecutive failures?
        # - 1 failure: Could be noise, outlier batch, temporary data issue
        # - 2 failures: Concerning, but still possibly transient
        # - 3 failures: Highly unlikely to be coincidence, indicates systematic problem
        #   (Probability of 3 false alarms in a row ≈ 0.1^3 = 0.001 if p(false alarm) = 0.1)
        #
        # This is similar to:
        # - TCP retransmit threshold (3 duplicate ACKs trigger fast retransmit)
        # - Traditional circuit breakers (often use 3-5 failure threshold)
        # - Statistical significance (3 standard deviations for 99.7% confidence)

        if self._consecutive_failures >= self.consecutive_failures_limit:
            # CIRCUIT BREAKER OPENS (CRITICAL → PAUSED)
            #
            # Consecutive failure limit reached - circuit breaker trips to prevent
            # cascading degradation. Learning is halted to prevent bad model updates
            # from corrupting future training data or reaching production.
            #
            # This is the "open circuit" state where no learning operations flow through.
            # Manual intervention (force_resume) is required to close the circuit again.

            if self._status != SafetyStatus.PAUSED:
                # Transition to CRITICAL (tripping) then PAUSED (open)
                self._status = SafetyStatus.CRITICAL

                if self.enable_auto_pause:
                    # AUTO-PAUSE MECHANISM
                    # If enable_auto_pause=True, automatically halt learning
                    # This is the circuit breaker "opening" to prevent further damage
                    self._pause_learning()  # Sets status to PAUSED

                # Generate CRITICAL alert for operator intervention
                # In production, this should trigger:
                # - PagerDuty/OpsGenie alert for on-call engineer
                # - Dashboard alert showing circuit breaker state
                # - Audit log entry for compliance tracking
                self._generate_alert(
                    severity="critical",
                    message=f"Learning paused after {self._consecutive_failures} consecutive failures",
                    accuracy=accuracy,
                    action="paused_learning",
                )
        else:
            # CIRCUIT BREAKER WARNING (DEGRADED BUT STILL CLOSED)
            #
            # Failures detected but below consecutive limit - circuit is still closed
            # but in a degraded/warning state. Learning continues but system is on alert.
            #
            # Example states:
            # - 1/3 failures: First failure, could be transient
            # - 2/3 failures: Second consecutive failure, concerning but not critical yet
            #
            # This warning state allows for:
            # - Early detection of emerging issues
            # - Operator awareness before circuit opens
            # - Graceful handling of transient failures without circuit trip

            self._status = SafetyStatus.WARNING

            # Generate WARNING alert for monitoring
            # Not critical yet, but operators should be aware of degradation
            self._generate_alert(
                severity="warning",
                message=f"Safety check failed ({self._consecutive_failures}/{self.consecutive_failures_limit}): {message}",
                accuracy=accuracy,
                action="none",  # No action taken yet, still learning
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
        """Pause learning due to safety bounds violation.

        CIRCUIT BREAKER OPENS (PAUSED STATE)
        =====================================

        This method opens the circuit breaker, halting all learning operations.
        It represents the final safety action when consecutive failures indicate
        a systematic problem that requires human intervention.

        Circuit Breaker Open State:
        - All learning operations are blocked (is_learning_allowed() returns False)
        - Model updates are rejected to prevent further degradation
        - System maintains current model until manual recovery
        - Consecutive failure counter remains elevated until reset

        Why Open the Circuit?
        1. **Prevent Cascading Failures**: A degraded model learning from its own
           bad predictions creates a feedback loop. Opening the circuit breaks this loop.

        2. **Preserve System Stability**: Better to maintain a slightly degraded model
           than risk further corruption through continued learning.

        3. **Force Human Review**: Systematic failures (3+ consecutive) indicate issues
           that automated systems cannot resolve:
           - Data quality problems (garbage in, garbage out)
           - Distribution shift requiring retraining from scratch
           - Configuration errors (wrong thresholds, bad hyperparameters)
           - Infrastructure issues (corrupted data pipeline)

        4. **Governance Safety**: In access control, continued learning with a failing
           model could grant improper permissions or deny legitimate access at scale.

        Integration with ModelManager:
        When the circuit opens, the ModelManager should:
        - Reject new model updates (return SwapStatus.REJECTED_SAFETY)
        - Continue serving the current (paused) model for predictions
        - Alert operators for manual investigation
        - Wait for force_resume() before accepting updates again

        Recovery Process:
        1. Operator investigates root cause (check logs, data quality, drift metrics)
        2. Fix underlying issue (repair data pipeline, retrain model, adjust thresholds)
        3. Manually call force_resume() to close circuit
        4. Monitor for successful checks before resuming normal operations

        Callbacks:
        Pause callbacks are invoked to notify integrated systems:
        - ModelManager: Stop processing new model updates
        - Monitoring: Trigger critical alerts (PagerDuty, Slack, etc.)
        - Audit Log: Record circuit breaker state change for compliance
        - Dashboard: Update UI to show PAUSED state
        """
        # Set circuit breaker to OPEN (PAUSED) state
        self._status = SafetyStatus.PAUSED
        self._times_paused += 1

        logger.warning(
            "Learning paused by safety bounds",
            extra={
                "consecutive_failures": self._consecutive_failures,
                "times_paused": self._times_paused,
            },
        )

        # CIRCUIT BREAKER EVENT: Notify registered callbacks
        # These callbacks should trigger operational response:
        # - Alert on-call engineer (critical system state)
        # - Update monitoring dashboards (circuit is now OPEN)
        # - Log to audit trail (compliance requirement)
        # - Block new model updates in ModelManager
        for callback in self._pause_callbacks:
            try:
                callback()
            except Exception as e:
                # Don't let callback errors prevent circuit from opening
                # Circuit breaker state change is more critical than callback success
                logger.error(f"Pause callback error: {e}")

    def _resume_learning(self) -> None:
        """Resume learning after safety bounds are satisfied.

        CIRCUIT BREAKER CLOSES (OK STATE)
        ==================================

        This method closes the circuit breaker, resuming normal learning operations.
        It is called when a safety check passes after the circuit was previously open,
        or when an operator manually forces resume via force_resume().

        Circuit Breaker Closed State:
        - Learning operations are enabled (is_learning_allowed() returns True)
        - Model updates are accepted if they pass safety checks
        - Consecutive failure counter is reset to 0
        - System transitions to OK state (normal operation)

        When Does the Circuit Close?
        1. **Automatic Recovery**: A safety check passes after the circuit was PAUSED
           - This happens in _handle_success() when status == PAUSED
           - Indicates the underlying issue has been resolved
           - System automatically resumes normal operation

        2. **Manual Recovery**: Operator calls force_resume() after investigation
           - Used when operator has fixed root cause manually
           - Resets failure counters and degradation tracking
           - Allows system to return to normal operation under supervision

        Why Automatic Closure is Safe:
        - Circuit only closes if a safety check PASSES (accuracy above threshold)
        - This means the model has recovered to acceptable performance
        - Unlike traditional circuit breakers (which use timeout), ML circuit
          breakers require evidence of recovery (passing check) before closing

        Why Manual Intervention is Sometimes Required:
        - If model cannot recover automatically (e.g., fundamental distribution shift)
        - If data pipeline needs repair (no new valid data arriving)
        - If thresholds need adjustment (overly conservative settings)
        - If model needs complete retraining (not just continued learning)

        Integration with ModelManager:
        When the circuit closes, the ModelManager should:
        - Resume accepting new model updates (if they pass safety checks)
        - Continue monitoring for future failures
        - Log the recovery event for audit trail
        - Update dashboards to show OK state

        Callbacks:
        Resume callbacks are invoked to notify integrated systems:
        - ModelManager: Resume processing model updates
        - Monitoring: Clear critical alerts, send recovery notification
        - Audit Log: Record circuit breaker recovery for compliance
        - Dashboard: Update UI to show OK state
        """
        # Increment resume counter for metrics tracking
        self._times_resumed += 1

        logger.info(
            "Learning resumed after safety bounds satisfied",
            extra={
                "times_resumed": self._times_resumed,
            },
        )

        # CIRCUIT BREAKER EVENT: Notify registered callbacks
        # These callbacks should handle operational recovery:
        # - Clear critical alerts (system has recovered)
        # - Update monitoring dashboards (circuit is now CLOSED)
        # - Log recovery to audit trail (compliance requirement)
        # - Resume accepting model updates in ModelManager
        for callback in self._resume_callbacks:
            try:
                callback()
            except Exception as e:
                # Don't let callback errors prevent circuit from closing
                # Circuit breaker state change is more critical than callback success
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
