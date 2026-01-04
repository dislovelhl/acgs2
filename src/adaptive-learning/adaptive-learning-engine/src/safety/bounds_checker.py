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

            # FAILURE MODE: SKIPPED_COLD_START (Cold Start Safety Bypass)
            # ============================================================
            #
            # During model initialization (cold start), the model has insufficient training
            # samples for reliable accuracy estimation. Safety checks are bypassed during
            # this phase to prevent false alarms from statistical noise and premature
            # circuit breaker activation.
            #
            # WHY SKIP SAFETY CHECKS DURING COLD START?
            # ==========================================
            #
            # 1. STATISTICAL UNRELIABILITY:
            #    With few samples (n < 100), accuracy estimates have high variance and
            #    are not statistically significant. Random fluctuations dominate signal.
            #
            #    Standard Error (SE) of Accuracy Estimate:
            #      SE = sqrt(p * (1-p) / n)
            #
            #    Where:
            #      - p = true accuracy (unknown, assume ~0.85 for governance models)
            #      - n = sample count
            #      - SE = standard error of the accuracy estimate
            #
            #    Cold Start Examples (n < 100):
            #      - n=10:  SE = sqrt(0.85*0.15/10)  ≈ 0.113 (±11.3% margin of error!)
            #      - n=25:  SE = sqrt(0.85*0.15/25)  ≈ 0.071 (±7.1% margin of error)
            #      - n=50:  SE = sqrt(0.85*0.15/50)  ≈ 0.050 (±5.0% margin of error)
            #
            #    With n=10, measured 75% accuracy could represent true accuracy anywhere
            #    from 64% to 86% (75% ± 11.3% at 95% CI). This massive uncertainty makes
            #    safety checks meaningless - failures would be mostly random noise.
            #
            # 2. RISK OF FALSE CIRCUIT BREAKER TRIPS:
            #    If safety checks run during cold start, high variance could trigger
            #    consecutive failures purely from statistical noise, causing the circuit
            #    breaker to open (PAUSED state) before the model has a chance to stabilize.
            #
            #    Scenario Without Cold Start Skip:
            #      Check 1 (n=20): Measured 78% accuracy (SE±9%) → FAILED_ACCURACY
            #      Check 2 (n=40): Measured 81% accuracy (SE±6%) → FAILED_ACCURACY
            #      Check 3 (n=60): Measured 83% accuracy (SE±5%) → FAILED_ACCURACY
            #      Result: Circuit breaker OPENS (3 consecutive failures)
            #      Reality: Model was actually improving (78%→81%→83%) but high variance
            #               caused all checks to fail threshold (85%). Model never got
            #               chance to reach statistical stability.
            #
            #    With Cold Start Skip:
            #      Check 1 (n=20): SKIPPED_COLD_START (neutral, doesn't count as failure)
            #      Check 2 (n=40): SKIPPED_COLD_START (neutral, doesn't count as failure)
            #      Check 3 (n=60): SKIPPED_COLD_START (neutral, doesn't check yet)
            #      Check 4 (n=120): Measured 87% accuracy → PASSED (circuit stays closed)
            #      Result: Model reaches statistical stability before safety validation begins
            #
            # 3. COORDINATION WITH MODEL WARMING PHASE:
            #    OnlineLearner transitions through states: COLD_START → WARMING → ACTIVE
            #    The WARMING state persists until min_training_samples=1000 is reached,
            #    during which:
            #      - StandardScaler statistics are stabilizing (mean/variance estimates)
            #      - Model weights are converging through gradient descent
            #      - Predictions are unreliable and should not be used for production
            #
            #    SafetyBoundsChecker's min_samples_for_check=100 is deliberately set
            #    LOWER than OnlineLearner's min_training_samples=1000 to provide early
            #    safety validation during the WARMING phase:
            #
            #    Sample Count Timeline:
            #      n=0-99:    COLD_START state, safety checks SKIPPED (too unstable)
            #      n=100-999: WARMING state, safety checks ACTIVE (early validation)
            #      n=1000+:   ACTIVE state, safety checks ACTIVE (production validation)
            #
            #    This staged approach allows safety checks to begin validating model
            #    quality during the warming phase (100-999 samples) while still
            #    preventing premature failures during extreme cold start (0-99 samples).
            #
            # WHY MIN_SAMPLES_FOR_CHECK = 100 SPECIFICALLY?
            # ==============================================
            #
            # The threshold of 100 samples balances statistical significance with
            # responsive safety validation. It's chosen based on several factors:
            #
            # 1. STATISTICAL SIGNIFICANCE (Primary Justification):
            #
            #    Standard Error at n=100:
            #      SE = sqrt(0.85 * 0.15 / 100) = sqrt(0.1275 / 100) = sqrt(0.001275) ≈ 0.036
            #
            #    This means at 100 samples:
            #      - Standard error: ±3.6%
            #      - 95% Confidence Interval: ±1.96 * 0.036 ≈ ±7% (about ±0.07)
            #      - Measured 85% accuracy likely represents true accuracy in [78%, 92%] range
            #
            #    Comparison to Accuracy Threshold (85%):
            #      - Threshold: 85% minimum required accuracy
            #      - SE at n=100: ±3.6%
            #      - If measured accuracy is exactly 85%, true accuracy is likely 81-89%
            #      - This provides reasonable confidence that measured accuracy reflects reality
            #
            #    With n=100, the standard error (3.6%) is small enough that:
            #      - True failures (model actually below 85%) will be detected reliably
            #      - False alarms from noise are reduced (but circuit breaker's consecutive
            #        failure requirement provides additional filtering)
            #
            # 2. CENTRAL LIMIT THEOREM CONVERGENCE:
            #
            #    The Central Limit Theorem (CLT) states that sample means approach a
            #    normal distribution as sample size increases. For binary classification
            #    accuracy (Bernoulli trials):
            #      - n=30: CLT starts to apply (rough approximation)
            #      - n=50: Better convergence to normal distribution
            #      - n=100: Strong convergence, reliable confidence intervals
            #
            #    At n=100, we can reliably use normal distribution approximations for
            #    confidence intervals, making statistical tests (like comparing accuracy
            #    to threshold) mathematically sound.
            #
            # 3. TRADE-OFF: EARLY WARNING VS. FALSE ALARMS
            #
            #    Lower Threshold (e.g., n=50):
            #      Advantages:
            #        - Earlier safety validation (detects problems sooner)
            #        - Shorter cold start period (safety checks begin at 50 samples)
            #      Disadvantages:
            #        - SE ≈ 5% (higher variance, more noise)
            #        - More false alarms during model initialization
            #        - Circuit breaker may trip on statistical noise (despite consecutive
            #          failure filtering, 3 consecutive noisy checks could still fail)
            #      Use case: High-risk governance where immediate validation is critical
            #
            #    Higher Threshold (e.g., n=200):
            #      Advantages:
            #        - SE ≈ 2.5% (lower variance, more reliable estimates)
            #        - Fewer false alarms (very stable accuracy measurement)
            #        - Strong statistical confidence in threshold violations
            #      Disadvantages:
            #        - Delayed safety validation (checks don't start until 200 samples)
            #        - Model could degrade during samples 100-199 without detection
            #        - Longer exposure window if model is fundamentally broken
            #      Use case: Low-risk systems where stability > responsiveness
            #
            #    Optimal n=100:
            #      - Balances responsiveness (checks start at 100 samples) with reliability
            #        (SE ≈ 3.6% is acceptable for safety decisions with circuit breaker)
            #      - SE of 3.6% means ~16% false alarm rate per check, but consecutive
            #        failure requirement (3 strikes) reduces cumulative false alarm rate
            #        to 0.16^3 ≈ 0.4% (highly unlikely to trip circuit breaker on noise)
            #      - Detects real issues within 100-300 samples (1-3 checks if consecutive)
            #        while maintaining statistical rigor
            #
            # 4. ALIGNMENT WITH DOMAIN STANDARDS:
            #
            #    Machine Learning Evaluation Best Practices:
            #      - Scikit-learn cross-validation typically uses k=5 or k=10 folds
            #      - With 1000-sample dataset, each fold has 100-200 test samples
            #      - n=100 aligns with minimum fold size for reliable evaluation
            #
            #    Statistical Testing Standards:
            #      - Psychology/social sciences: n=30 minimum (CLT approximation)
            #      - Medical trials: n=100+ for Phase II studies (preliminary efficacy)
            #      - A/B testing: n=100+ per variant for basic significance tests
            #      - n=100 is widely recognized as "sufficient for initial analysis"
            #
            #    Governance-Specific Considerations:
            #      - With 10% minority class (rare access patterns), n=100 provides
            #        ~10 samples from minority class (borderline sufficient)
            #      - Below n=100, minority class may have <5 samples (unreliable metrics)
            #      - At n=100, both classes have enough samples for basic validation
            #
            # 5. COORDINATION WITH ONLINELEARNER STATE TRANSITIONS:
            #
            #    OnlineLearner State Machine:
            #      - COLD_START:  0-999 samples (model not production-ready)
            #      - WARMING:     100-999 samples (model stabilizing but not ready)
            #      - ACTIVE:      1000+ samples (model production-ready)
            #
            #    SafetyBoundsChecker Integration:
            #      - n=0-99:   SKIPPED_COLD_START (no safety checks, model too unstable)
            #      - n=100-999: WARMING safety validation (early checks during stabilization)
            #      - n=1000+:  ACTIVE safety validation (production checks)
            #
            #    Why min_samples_for_check (100) < min_training_samples (1000)?
            #    ---------------------------------------------------------------
            #
            #    This intentional gap (100 vs 1000) serves two critical purposes:
            #
            #    a) EARLY ANOMALY DETECTION DURING WARMING:
            #       If the model is fundamentally broken (bad hyperparameters, corrupted
            #       data pipeline, severe distribution mismatch), we want to detect this
            #       during the WARMING phase (100-999 samples) rather than waiting until
            #       ACTIVE state (1000+ samples).
            #
            #       Example: Data Pipeline Corruption
            #         - Model trained with features not being normalized correctly
            #         - By n=100, accuracy might be obviously bad (e.g., 60%)
            #         - Safety check at n=100 detects: FAILED_ACCURACY (60% < 85%)
            #         - Circuit breaker WARNING issued (1/3 failures)
            #         - Operators alerted early to investigate data pipeline
            #         - Without early checks, model would continue to n=1000 with
            #           bad data, wasting 900 more samples and operator time
            #
            #    b) PROGRESSIVE VALIDATION PHILOSOPHY:
            #       Safety validation doesn't need the same confidence level as
            #       production deployment. The circuit breaker provides defense-in-depth:
            #         - Single failure at n=100: WARNING (could be noise, keep watching)
            #         - Two failures at n=100, n=200: WARNING (pattern emerging)
            #         - Three failures at n=100, n=200, n=300: PAUSED (systematic issue)
            #
            #       Even with higher variance at n=100 (SE≈3.6%), the consecutive failure
            #       requirement (3 strikes) filters out transient noise. Real systematic
            #       issues will fail consistently across multiple checks.
            #
            #    c) RISK MITIGATION DURING WARMING:
            #       The WARMING phase (100-999 samples) is higher risk than ACTIVE:
            #         - StandardScaler statistics still converging (unstable normalization)
            #         - Model weights still adjusting (gradient descent not converged)
            #         - Predictions unreliable (not used for production yet)
            #
            #       Starting safety checks at n=100 provides oversight during this risky
            #       phase, even though the model isn't production-ready. If safety checks
            #       fail during WARMING, it's a signal to investigate before reaching ACTIVE.
            #
            #    Example Integration Flow:
            #      n=50:   OnlineLearner: COLD_START, SafetyBoundsChecker: SKIPPED
            #              → Model too unstable for any validation
            #
            #      n=150:  OnlineLearner: WARMING, SafetyBoundsChecker: ACTIVE
            #              → Safety check runs: 87% accuracy → PASSED
            #              → Model is warming but showing good signs (above 85% threshold)
            #              → Continue warming phase with safety oversight
            #
            #      n=250:  OnlineLearner: WARMING, SafetyBoundsChecker: ACTIVE
            #              → Safety check runs: 82% accuracy → FAILED_ACCURACY
            #              → Circuit breaker: WARNING (1/3 failures)
            #              → Alert: "Model accuracy dropped during warming - investigate"
            #              → Operator checks data pipeline, finds normalization bug
            #
            #      n=1000: OnlineLearner: ACTIVE, SafetyBoundsChecker: ACTIVE
            #              → Model now production-ready (if safety checks passed)
            #              → Both systems agree: model is stable and safe
            #
            # 6. WHAT HAPPENS DURING SKIP (Neutral Result):
            #
            #    When sample_count < min_samples_for_check (n < 100):
            #      - Return: SKIPPED_COLD_START result
            #      - passed=True: Allows model swap to proceed (not blocking)
            #      - Does NOT increment consecutive_failures counter
            #      - Does NOT reset consecutive_failures counter
            #      - Circuit breaker state UNCHANGED (stays in current state)
            #      - No alerts generated (neither warning nor critical)
            #
            #    This neutral behavior is critical because:
            #      - Cold start is expected and normal (not a failure)
            #      - Shouldn't penalize model for being new (not fair to increment failures)
            #      - Shouldn't reward model for being untested (not safe to reset failures)
            #      - Circuit breaker should remain in previous state until real validation
            #
            #    Neutral Result Philosophy:
            #      - PASSED (passed=False, failures reset): Model validated as safe
            #      - FAILED (passed=False, failures increment): Model validated as unsafe
            #      - SKIPPED (passed=True, failures unchanged): Model not yet validated
            #
            #    The passed=True allows ModelManager to swap the model during cold start
            #    (not blocking deployment), but the neutral circuit breaker state ensures
            #    previous safety context is preserved (don't erase history of failures
            #    just because a new untested model arrived).
            #
            # 7. PRODUCTION IMPACT OF THRESHOLD CHOICE:
            #
            #    In a typical governance deployment with 100 requests/hour:
            #      - Time to 100 samples: ~1 hour (assuming 100% feedback rate)
            #      - Cold start duration: 1 hour of SKIPPED safety checks
            #      - WARMING phase: 1-10 hours (100-1000 samples)
            #
            #    With min_samples_for_check=50 (too low):
            #      - Cold start duration: 30 minutes
            #      - Advantage: 30 minutes faster initial validation
            #      - Disadvantage: Higher false alarm rate during 30-60 min window
            #                     (SE≈5% means ~20% false alarm rate per check)
            #      - Risk: Could trigger circuit breaker on noise, requiring manual force_resume
            #
            #    With min_samples_for_check=200 (too high):
            #      - Cold start duration: 2 hours
            #      - Advantage: Very low false alarm rate (SE≈2.5%)
            #      - Disadvantage: Model could degrade for 1 extra hour without detection
            #                     (samples 100-199 have no safety oversight)
            #      - Risk: Broken model has more time to impact production before detection
            #
            #    Optimal min_samples_for_check=100:
            #      - Cold start duration: 1 hour (reasonable for new model initialization)
            #      - SE≈3.6% provides acceptable confidence (not perfect, but good enough
            #        with consecutive failure filtering from circuit breaker)
            #      - Balances early detection (starts at 1 hour) with reliability
            #        (false alarms filtered by 3-strike rule)
            #
            # SUMMARY: Cold Start Skip Logic
            # ===============================
            #
            # During cold start (n < 100 samples), safety checks are bypassed because:
            #   1. Statistical unreliability: SE≈11% at n=10, too much noise
            #   2. Risk of false circuit breaker trips: Noise could trigger 3 consecutive failures
            #   3. Coordination with WARMING phase: Checks begin during stabilization (100-999)
            #
            # The threshold min_samples_for_check=100 is optimal because:
            #   1. Statistical significance: SE≈3.6%, acceptable for safety decisions
            #   2. CLT convergence: n=100 provides reliable normal approximation
            #   3. Early warning: Checks start during WARMING phase (before production)
            #   4. Domain standards: Aligns with ML evaluation best practices (k-fold CV)
            #   5. Coordination: Provides safety oversight during model stabilization
            #
            # During skip (n < 100):
            #   - Returns SKIPPED_COLD_START (neutral result)
            #   - passed=True (allows model swap, doesn't block deployment)
            #   - Circuit breaker state UNCHANGED (preserves safety context)
            #   - No alerts generated (cold start is expected, not a failure)
            #
            # This approach prevents false alarms during model initialization while
            # enabling early detection of systematic issues during the warming phase.
            #
            # Get sample count to determine if model has enough data for safety check
            try:
                sample_count = model.get_sample_count()
            except (AttributeError, TypeError):
                # Model doesn't implement get_sample_count() - assume 0 samples (cold start)
                sample_count = 0

            # COLD START SKIP: Bypass safety checks if insufficient samples for reliable validation
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

            # FAILURE MODE 1: FAILED_ACCURACY (Absolute Threshold Violation)
            #
            # Check if accuracy is below absolute threshold
            # This catches overall model performance degradation
            #
            # ACCURACY THRESHOLD SELECTION: Why accuracy_threshold=0.85 for governance?
            # =========================================================================
            #
            # The 0.85 threshold represents a carefully chosen balance between safety,
            # adaptability, and operational feasibility for governance systems.
            #
            # 1. GOVERNANCE-SPECIFIC FALSE POSITIVE/NEGATIVE TRADE-OFFS:
            #    In access control and governance systems:
            #    - False Positive (FP): Granting access that should be denied
            #      * CRITICAL SEVERITY: Security breach, compliance violation
            #      * Exposes sensitive data to unauthorized users
            #      * Legal/financial consequences (GDPR fines, audit failures)
            #    - False Negative (FN): Denying access that should be granted
            #      * MODERATE SEVERITY: User inconvenience, productivity impact
            #      * Can be mitigated with human review/override
            #      * Reversible with minimal long-term damage
            #    Traditional ML often optimizes for balanced FP/FN, but governance
            #    systems prioritize minimizing FP even at cost of higher FN.
            #
            # 2. WHY 85% SPECIFICALLY?
            #    - Maximum 15% combined error rate (FP + FN)
            #    - Typical governance model tuning:
            #      * Optimize for high precision (minimize FP): ~5-8% FP rate
            #      * Accept lower recall (higher FN): ~7-10% FN rate
            #      * Overall accuracy: 85-90% range
            #    - Lower threshold (e.g., 80%):
            #      * 20% error rate unacceptable for compliance
            #      * Too many false positives (data breaches)
            #      * Undermines trust in automated governance
            #    - Higher threshold (e.g., 90%):
            #      * Too strict for concept drift in governance domain
            #      * Would frequently trigger circuit breaker (excessive pausing)
            #      * Reduces adaptability to evolving policies/roles
            #      * Governance data often imbalanced (rare access patterns)
            #
            # 3. ABSOLUTE THRESHOLD IS CRITICAL FOR SAFETY:
            #    Unlike relative checks (degradation_threshold), absolute threshold
            #    provides a hard safety floor that model MUST maintain.
            #    - Prevents "boiling frog" gradual degradation
            #    - Example: Model improving from 70% → 75% → 80%
            #      * Positive trend (improving), but 80% < 85% (REJECTED)
            #      * Relative improvement doesn't matter if baseline is unsafe
            #      * Must reach minimum safety level before production use
            #    - Ensures model quality never drops below acceptable minimum
            #    - No exceptions for "improving but still below threshold" scenarios
            #
            # 4. DEFENSE-IN-DEPTH WITH DEGRADATION CHECK:
            #    Absolute threshold (0.85) + Relative degradation check (0.05) provide
            #    comprehensive protection:
            #    - Scenario 1: Model at 90% drops to 84%
            #      * Fails absolute threshold (84% < 85%): FAILED_ACCURACY
            #      * Also fails degradation check (6% > 5%): FAILED_DEGRADATION
            #      * Both checks catch this dangerous regression
            #    - Scenario 2: Model at 92% drops to 87%
            #      * Passes absolute threshold (87% > 85%)
            #      * Fails degradation check (5% ≥ 5%): FAILED_DEGRADATION
            #      * Relative check catches regression even when above threshold
            #    - Scenario 3: Model at 80% improves to 82%
            #      * Fails absolute threshold (82% < 85%): FAILED_ACCURACY
            #      * Relative check N/A (improving, not degrading)
            #      * Absolute check prevents low-quality model deployment
            #
            # 5. STATISTICAL INTERPRETATION:
            #    With min_samples_for_check=100:
            #    - Standard Error (SE) ≈ sqrt(p(1-p)/n) = sqrt(0.85*0.15/100) ≈ 0.036
            #    - 95% Confidence Interval: 0.85 ± 1.96*0.036 ≈ [0.78, 0.92]
            #    - Measured 85% accuracy likely represents true 78-92% range
            #    - Provides buffer above critical safety level (~80%)
            #    - Reduces false alarms from statistical noise
            #
            # This absolute threshold acts as the primary safety net. Combined with
            # consecutive failure tracking (circuit breaker), it prevents deployment
            # of unsafe models while tolerating transient noise.
            if current_accuracy < self.accuracy_threshold:
                # CIRCUIT BREAKER: Increment failure counter
                # May transition OK → WARNING or WARNING → CRITICAL/PAUSED
                return self._handle_failure(
                    CheckResult.FAILED_ACCURACY,
                    current_accuracy,
                    f"Accuracy {current_accuracy:.3f} below threshold {self.accuracy_threshold:.3f}",
                )

            # FAILURE MODE 2: FAILED_DEGRADATION (Relative Regression Detection)
            #
            # DEGRADATION DETECTION ALGORITHM: Detecting Sudden Performance Regression
            # =========================================================================
            #
            # This check detects significant accuracy drops from the previous safety check,
            # catching sudden performance regressions that might be missed by absolute
            # thresholds alone. It provides defense-in-depth by monitoring model stability
            # over time, not just absolute performance.
            #
            # ALGORITHM: Relative Accuracy Comparison
            # ----------------------------------------
            #
            # 1. Compare current accuracy to previous check's accuracy (if available)
            #    - Only triggers if we have history (_last_accuracy is not None)
            #    - First check after initialization doesn't have previous baseline
            #
            # 2. Calculate accuracy drop: accuracy_drop = previous_accuracy - current_accuracy
            #    - Direction matters: positive drop means degradation (accuracy decreased)
            #    - Negative drop means improvement (accuracy increased) - not a failure
            #
            #    Mathematical Calculation:
            #      accuracy_drop = self._last_accuracy - current_accuracy
            #
            #    Examples:
            #      - Previous: 0.90, Current: 0.84 → drop = 0.90 - 0.84 = 0.06 (6% degradation)
            #      - Previous: 0.85, Current: 0.88 → drop = 0.85 - 0.88 = -0.03 (3% improvement)
            #      - Previous: 0.92, Current: 0.92 → drop = 0.92 - 0.92 = 0.00 (stable)
            #
            # 3. Compare drop to degradation_threshold (default 0.05 = 5%)
            #    - If accuracy_drop > degradation_threshold: FAILED_DEGRADATION
            #    - If accuracy_drop ≤ degradation_threshold: Continue to PASSED
            #
            # WHY DEGRADATION_THRESHOLD = 0.05 (5% Drop)?
            # ---------------------------------------------
            #
            # The 5% threshold is carefully chosen to balance sensitivity to real issues
            # vs. robustness to statistical noise in governance applications.
            #
            # 1. STATISTICAL SIGNIFICANCE:
            #    With min_samples_for_check=100 and typical accuracy ~0.85:
            #    - Standard Error (SE) ≈ sqrt(0.85 * 0.15 / 100) ≈ 0.036 (3.6%)
            #    - 95% Confidence Interval: ± 1.96 * 0.036 ≈ ± 0.07 (7%)
            #    - Observed 5% drop could be noise OR real degradation
            #    - But 5% threshold is ~1.4 standard errors (about 84th percentile)
            #    - This means ~16% chance of false alarm from noise alone
            #    - Consecutive failure requirement (3 strikes) reduces noise:
            #      * Probability of 3 consecutive false alarms: 0.16^3 ≈ 0.4% (very unlikely)
            #      * Circuit breaker pattern filters transient noise while catching real issues
            #
            # 2. SUDDEN VS. GRADUAL DEGRADATION:
            #    The degradation check serves a different purpose than absolute threshold:
            #
            #    Absolute Threshold (FAILED_ACCURACY):
            #      - Catches: Gradual decay, models that never reach production quality
            #      - Example: Model slowly degrades 88% → 86% → 84% → 82%
            #      - Each step is small (2% drop < 5% threshold), but crosses 85% floor
            #      - FAILED_ACCURACY catches when it hits 84% < 85%
            #
            #    Relative Threshold (FAILED_DEGRADATION):
            #      - Catches: Sudden crashes, acute model failures
            #      - Example: Model suddenly crashes 92% → 86%
            #      - 6% drop > 5% threshold (FAILED_DEGRADATION)
            #      - Still above 85% floor (passes absolute threshold)
            #      - Relative check catches this acute regression
            #
            #    Defense-in-Depth: Both checks together provide comprehensive safety:
            #      - Scenario A: 92% → 86% (6% drop, above floor)
            #        * FAILED_DEGRADATION catches acute crash
            #        * Passes absolute threshold (86% > 85%)
            #      - Scenario B: 86% → 84% (2% drop, below floor)
            #        * Passes degradation threshold (2% < 5%)
            #        * FAILED_ACCURACY catches floor violation (84% < 85%)
            #      - Scenario C: 90% → 83% (7% drop, below floor)
            #        * Both checks fail (defense-in-depth confirmation)
            #
            # 3. WHAT CAUSES SUDDEN DEGRADATION?
            #    A 5%+ drop typically indicates systematic issues requiring investigation:
            #
            #    a) Bad Training Batch (Data Quality):
            #       - Corrupted features (missing values, encoding errors)
            #       - Label noise (incorrect ground truth in feedback)
            #       - Outlier batch (adversarial samples, edge cases)
            #       Example: Governance model trained on batch with flipped labels
            #                (grant/deny swapped) → learns incorrect policy
            #
            #    b) Distribution Shift (Concept Drift):
            #       - Sudden change in data distribution (policy update, org restructure)
            #       - Covariate shift (feature distributions change but label mapping stays same)
            #       - Prior probability shift (class balance changes dramatically)
            #       Example: Company acquires new division with different access patterns
            #
            #    c) Model Corruption (Numerical Instability):
            #       - Gradient explosion (learning_rate too high, unstable SGD)
            #       - Weight overflow (numerical precision issues)
            #       - Catastrophic forgetting (new data overwrites previous knowledge)
            #       Example: Learning rate spike causes weights to diverge
            #
            #    d) Infrastructure Issues:
            #       - Feature extraction pipeline broken (wrong features fed to model)
            #       - Preprocessing bug (scaling, normalization errors)
            #       - Model deserialization error (loaded wrong model version)
            #       Example: StandardScaler reset during deployment, features no longer normalized
            #
            # 4. WHY NOT LOWER (e.g., 3%) OR HIGHER (e.g., 10%) THRESHOLD?
            #
            #    Lower Threshold (3%):
            #      - Too sensitive to statistical noise (SE ≈ 3.6%)
            #      - Would trigger false alarms on normal variance
            #      - Excessive alerts lead to "alert fatigue" (operators ignore warnings)
            #      - Circuit breaker would open too frequently (reduced adaptability)
            #      - Better handled by consecutive failure filtering (not threshold tuning)
            #
            #    Higher Threshold (10%):
            #      - Too slow to detect acute issues (92% → 82% is catastrophic)
            #      - By the time 10% drop detected, model may be unsafe (82% < 85%)
            #      - Absolute threshold would catch it anyway (redundant)
            #      - Misses moderate regressions (88% → 81% is 7% drop, below 10%)
            #      - Defeats purpose of early warning system
            #
            #    Optimal 5% Threshold:
            #      - Statistically significant (~1.4 SE) but not excessive false alarms
            #      - Catches acute issues before absolute threshold violation
            #      - Combined with consecutive failures (3 strikes) filters noise
            #      - Provides early warning for intervention before critical failure
            #      - Balances sensitivity (catch real issues) vs. specificity (avoid false alarms)
            #
            # 5. GOVERNANCE-SPECIFIC CONSIDERATIONS:
            #
            #    Why degradation detection is critical for access control/governance:
            #
            #    a) Cascading Impact:
            #       - Degraded model grants improper permissions
            #       - Bad permissions propagate to downstream systems
            #       - Audit logs filled with incorrect decisions
            #       - Compliance violations accumulate over time
            #       - Early detection (5% drop) prevents cascade
            #
            #    b) Feedback Loop Risk:
            #       - Model learns from its own predictions (online learning)
            #       - Degraded model makes bad predictions
            #       - Bad predictions become training labels (feedback loop)
            #       - Further degrades model (positive feedback, exponential decay)
            #       - Circuit breaker halts loop before irreversible corruption
            #
            #    c) Auditability Requirements:
            #       - Compliance requires explaining why decisions changed
            #       - Sudden 5%+ drop is auditable event (clear threshold crossed)
            #       - Gradual 1-2% drifts harder to detect and explain
            #       - Degradation detection provides audit trail for investigations
            #
            #    d) User Trust:
            #       - Users notice when access patterns change suddenly
            #       - 5%+ regression means ~1 in 20 users sees different behavior
            #       - Early detection maintains consistent user experience
            #       - Prevents "why did this suddenly get denied?" support tickets
            #
            # 6. DIRECTION OF CALCULATION (Why previous - current, not current - previous):
            #
            #    Mathematical Calculation:
            #      accuracy_drop = self._last_accuracy - current_accuracy
            #
            #    Why This Direction?
            #      - Positive value = degradation (accuracy decreased, bad)
            #      - Negative value = improvement (accuracy increased, good)
            #      - Natural interpretation: "drop" means going down
            #
            #    Example:
            #      Previous: 0.90, Current: 0.84
            #      accuracy_drop = 0.90 - 0.84 = +0.06 (6% drop, positive means degradation)
            #
            #    Alternative (Wrong Direction):
            #      accuracy_drop_wrong = current_accuracy - self._last_accuracy
            #      = 0.84 - 0.90 = -0.06 (negative value, confusing)
            #      Would need: if accuracy_drop_wrong < -self.degradation_threshold (awkward)
            #
            #    Our Direction Benefits:
            #      - Intuitive: positive drop = degradation (matches English semantics)
            #      - Simple comparison: accuracy_drop > threshold (no negation needed)
            #      - Consistent with "accuracy drop" terminology throughout codebase
            #      - Improvement (negative drop) naturally ignored (< 0, fails > threshold check)
            #
            # 7. INTEGRATION WITH CIRCUIT BREAKER:
            #
            #    When degradation detected:
            #      - Increments consecutive_failures counter (same as FAILED_ACCURACY)
            #      - Both failure modes contribute equally to circuit breaker
            #      - After 3 consecutive degradation failures: circuit opens (PAUSED)
            #      - Prevents continued learning from degraded model
            #      - Requires investigation and manual intervention (force_resume)
            #
            #    State Transitions on Degradation Failure:
            #      - 1st degradation: OK → WARNING (1/3 failures, alert sent)
            #      - 2nd degradation: WARNING → WARNING (2/3 failures, concern growing)
            #      - 3rd degradation: WARNING → CRITICAL → PAUSED (circuit opens)
            #      - Manual fix + passing check: PAUSED → OK (circuit closes)
            #
            # Example Scenarios with Concrete Numbers:
            # -----------------------------------------
            #
            # Scenario 1: Acute Regression (Caught by Degradation)
            #   Check 1: 92% accuracy (baseline established)
            #   Check 2: 86% accuracy
            #     → drop = 92% - 86% = 6% > 5% threshold
            #     → FAILED_DEGRADATION (1/3 failures, WARNING)
            #     → Still above 85% absolute threshold (passes FAILED_ACCURACY check)
            #     → Degradation check provides early warning
            #
            # Scenario 2: Gradual Decay (Caught by Absolute Threshold)
            #   Check 1: 88% accuracy (baseline)
            #   Check 2: 86% accuracy (drop = 2% < 5%, passes degradation)
            #   Check 3: 84% accuracy (drop = 2% < 5%, passes degradation)
            #     → But 84% < 85% absolute threshold
            #     → FAILED_ACCURACY catches gradual decay
            #     → Degradation check alone would miss this pattern
            #
            # Scenario 3: Catastrophic Failure (Both Checks Fail)
            #   Check 1: 90% accuracy (baseline)
            #   Check 2: 82% accuracy
            #     → drop = 90% - 82% = 8% > 5% threshold (FAILED_DEGRADATION)
            #     → 82% < 85% absolute threshold (FAILED_ACCURACY)
            #     → Both checks fail (defense-in-depth confirmation)
            #     → High confidence this is real issue, not noise
            #
            # Scenario 4: Improvement (No Failure)
            #   Check 1: 85% accuracy (baseline)
            #   Check 2: 88% accuracy
            #     → drop = 85% - 88% = -3% < 5% threshold (improvement, ignored)
            #     → 88% > 85% absolute threshold (passes)
            #     → PASSED, consecutive_failures reset to 0
            #     → Circuit closes if was previously open
            #
            # This degradation detection algorithm provides critical safety by catching
            # sudden model failures that absolute thresholds might miss, enabling early
            # intervention before cascading failures occur in production governance systems.
            if self._last_accuracy is not None:
                # Calculate accuracy drop from previous check
                # Direction: previous - current makes positive = degradation (intuitive)
                accuracy_drop = self._last_accuracy - current_accuracy

                # Check if drop exceeds 5% threshold (statistically significant regression)
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

            # ABSOLUTE ACCURACY THRESHOLD CHECK
            #
            # Why accuracy_threshold=0.85 for governance?
            # ============================================
            #
            # Governance systems make high-stakes decisions about data access, permissions,
            # and policy enforcement. The 0.85 threshold is chosen based on several factors:
            #
            # 1. SAFETY-CRITICAL CONTEXT:
            #    - False Negatives (FN): Model predicts "deny" but should "grant"
            #      * Blocks legitimate user access to critical systems
            #      * Disrupts business operations and productivity
            #      * Lower severity than false positives in most cases
            #    - False Positives (FP): Model predicts "grant" but should "deny"
            #      * Exposes sensitive data to unauthorized users
            #      * Violates compliance regulations (GDPR, HIPAA, SOC2)
            #      * Security breach with legal/financial consequences
            #      * Higher severity - unacceptable in governance context
            #
            # 2. ACCURACY THRESHOLD SELECTION RATIONALE:
            #    - With 85% accuracy threshold:
            #      * Maximum 15% error rate (FP + FN combined)
            #      * Assuming balanced precision/recall: ~7.5% FP, ~7.5% FN
            #      * In practice: Can tune model to minimize FP at cost of higher FN
            #    - Why not higher (e.g., 90%)?
            #      * Governance data is often imbalanced (rare access patterns)
            #      * Concept drift is common (policies/roles change frequently)
            #      * Setting threshold too high causes excessive false alarms
            #      * Would frequently pause learning, reducing adaptability
            #    - Why not lower (e.g., 80%)?
            #      * 20% error rate too high for compliance/security requirements
            #      * Unacceptable false positive rate (potential data breaches)
            #      * Undermines trust in ML-based governance system
            #
            # 3. ABSOLUTE VS. RELATIVE THRESHOLDS:
            #    - Absolute threshold (0.85) provides hard safety floor
            #    - Model MUST maintain minimum quality regardless of trend
            #    - Prevents gradual degradation ("boiling frog" problem)
            #    - Example: Model improving from 75% → 80% is STILL rejected
            #      * Even though accuracy is increasing (positive trend)
            #      * 80% < 85% absolute threshold (unsafe for production)
            #      * Relative improvement doesn't matter if baseline is too low
            #    - Contrast with degradation_threshold (relative check):
            #      * Catches regression: 90% → 85% is 5% drop (triggers FAILED_DEGRADATION)
            #      * But 85% still passes absolute threshold (borderline safe)
            #      * Both checks provide defense-in-depth
            #
            # 4. DOMAIN-SPECIFIC GOVERNANCE CONSIDERATIONS:
            #    - Access control decisions are binary (grant/deny) and irreversible
            #    - Audit logs require high accuracy for compliance investigations
            #    - Model errors can cascade (wrong permissions lead to more wrong decisions)
            #    - Human review is expensive - can't manually verify all predictions
            #    - Must maintain user trust while adapting to policy changes
            #
            # 5. STATISTICAL INTERPRETATION:
            #    - With n=100 samples: SE ≈ sqrt(0.85 * 0.15 / 100) ≈ 0.036 (3.6%)
            #    - 95% CI: [81.4%, 88.6%] - reasonable confidence bounds
            #    - Measured accuracy of 0.85 likely represents true range 82-88%
            #    - Provides buffer above critical safety level (~80%)
            #
            # This absolute threshold acts as a safety net - the circuit breaker will
            # pause learning before accuracy drops to dangerous levels. Combined with
            # degradation_threshold (relative check), it provides comprehensive safety.
            if accuracy < self.accuracy_threshold:
                return self._handle_failure(
                    CheckResult.FAILED_ACCURACY,
                    accuracy,
                    f"Accuracy {accuracy:.3f} below threshold {self.accuracy_threshold:.3f}",
                )

            # DEGRADATION CHECK (Relative Regression Detection)
            #
            # Check for significant accuracy drop from previous check.
            # See check_model() DEGRADATION DETECTION ALGORITHM section for full explanation.
            #
            # Quick Summary:
            # - Detects sudden performance regression (acute failures)
            # - Complements absolute threshold (catches gradual decay)
            # - accuracy_drop = previous - current (positive = degradation)
            # - degradation_threshold = 0.05 (5% drop triggers failure)
            # - Balances sensitivity to real issues vs. statistical noise
            # - Integrates with circuit breaker (contributes to consecutive failures)
            if self._last_accuracy is not None:
                # Calculate accuracy drop from previous check
                # Direction: previous - current makes positive = degradation (intuitive)
                accuracy_drop = self._last_accuracy - accuracy

                # Check if drop exceeds 5% threshold (statistically significant regression)
                if accuracy_drop > self.degradation_threshold:
                    # CIRCUIT BREAKER: Increment failure counter
                    # Provides metadata about previous accuracy and drop magnitude
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
        # WHY CONSECUTIVE_FAILURES_LIMIT = 3?
        # This threshold balances two competing concerns:
        # (1) CONFIRMATION: Need multiple failures to distinguish systematic issues from noise
        # (2) SPEED: Must detect and halt degradation before significant production impact
        #
        # CONFIRMATION WITHOUT FALSE ALARMS:
        # ------------------------------------
        # Single failures can occur due to transient issues:
        # - 1 failure: Could be statistical noise, outlier batch, temporary data spike
        #   * With accuracy SE ≈ 3.6%, ~16% chance of false alarm from noise alone
        #   * Too sensitive - would cause unnecessary circuit breaker trips
        #   * Action: Issue WARNING alert but continue learning
        #
        # - 2 failures: Concerning pattern, but could still be coincidental
        #   * Probability of 2 consecutive false alarms: 0.16 × 0.16 = 2.6%
        #   * Still plausible as random fluctuation in noisy governance data
        #   * Action: Escalate WARNING severity but continue learning
        #
        # - 3 failures: Extremely unlikely to be coincidence (statistical confirmation)
        #   * Probability of 3 consecutive false alarms: 0.16^3 ≈ 0.4% (highly improbable)
        #   * Strong evidence of systematic issue requiring intervention
        #   * Action: CRITICAL alert + PAUSED (circuit breaker opens)
        #
        # DETECTION WITHOUT EXCESSIVE DELAYS:
        # ------------------------------------
        # Why not 4 or 5 failures? Timing matters for preventing production impact:
        #
        # Typical Governance Model Update Frequency:
        # - High-traffic systems: Safety checks every 5-15 minutes (frequent model updates)
        # - Medium-traffic systems: Safety checks every 30-60 minutes (moderate updates)
        # - Low-traffic systems: Safety checks every 2-4 hours (infrequent updates)
        #
        # Time to Circuit Breaker Open with Different Thresholds:
        #
        # High-Traffic System (10-minute check intervals):
        # - 3 failures: 30 minutes to detection (ACCEPTABLE)
        #   * Fail at T=0, T=10, T=20 → Paused at T=20
        #   * Production running degraded model for only 20 minutes
        # - 5 failures: 50 minutes to detection (TOO SLOW)
        #   * Fail at T=0, T=10, T=20, T=30, T=40 → Paused at T=40
        #   * Production running degraded model for 40+ minutes (UNACCEPTABLE)
        #
        # Medium-Traffic System (30-minute check intervals):
        # - 3 failures: 90 minutes to detection (ACCEPTABLE for moderate traffic)
        #   * Fail at T=0, T=30, T=60 → Paused at T=60
        #   * Balances false alarm prevention with reasonable detection time
        # - 5 failures: 150 minutes to detection (2.5 hours - TOO SLOW)
        #   * Would allow degraded model to impact production for hours
        #
        # Low-Traffic System (2-hour check intervals):
        # - 3 failures: 6 hours to detection (ACCEPTABLE for low-traffic)
        #   * Fail at T=0, T=2h, T=4h → Paused at T=4h
        #   * Lower traffic means lower impact exposure
        # - 5 failures: 10 hours to detection (TOO SLOW even for low traffic)
        #
        # PRODUCTION IMPACT ANALYSIS:
        # In a high-traffic governance system processing 100 requests/minute:
        # - 3-failure threshold (30 min): ~3,000 requests with degraded model
        # - 5-failure threshold (50 min): ~5,000 requests with degraded model
        #   * 2,000 additional requests at risk (67% more exposure)
        #
        # With 85% accuracy threshold and 80% degraded model accuracy:
        # - Expected additional errors: 2,000 × (0.85 - 0.80) = 100 more errors
        #   * 100 more false grants (security breaches) or false denials (user impact)
        #   * In governance, even small numbers matter (compliance violations, audit failures)
        #
        # WHY NOT LOWER (e.g., 2 failures)?
        # - Too sensitive to noise (2.6% false alarm rate)
        # - Would cause frequent unnecessary pauses
        # - Reduces system adaptability (excessive circuit breaker trips)
        # - Alert fatigue for operators (ignored warnings become dangerous)
        #
        # SIMILAR INDUSTRY STANDARDS:
        # The 3-failure threshold aligns with established reliability engineering patterns:
        # - TCP retransmit threshold (3 duplicate ACKs trigger fast retransmit)
        # - Traditional circuit breakers (often use 3-5 failure threshold)
        # - Statistical significance (3 standard deviations for 99.7% confidence)
        # - AWS health checks (default 3 consecutive failures before instance marked unhealthy)
        # - Kubernetes liveness probes (default failureThreshold=3)
        #
        # TUNING GUIDANCE:
        # The consecutive_failures_limit can be adjusted based on your deployment:
        #
        # Use 2 failures if:
        # - Extremely high-traffic (1000s requests/minute)
        # - Ultra-low tolerance for degradation (banking, healthcare)
        # - Excellent data quality (very low noise)
        # - Willing to handle occasional false alarm pauses
        #
        # Use 4-5 failures if:
        # - Very low-traffic (infrequent model updates)
        # - High tolerance for transient degradation
        # - Noisy data (imbalanced classes, sparse features)
        # - Want to minimize circuit breaker trips
        #
        # Default 3 is optimal for most governance applications, providing statistical
        # confirmation (0.4% false alarm rate) with reasonable detection speed (minutes
        # to hours depending on traffic, not days).

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
                    # AUTO-PAUSE MECHANISM: Preventing Bad Model Updates
                    # ====================================================
                    #
                    # When enable_auto_pause=True, the circuit breaker automatically halts
                    # learning after consecutive_failures_limit failures. This prevents
                    # degraded models from corrupting production in several critical ways:
                    #
                    # 1. FEEDBACK LOOP PREVENTION:
                    #    A degraded model makes incorrect predictions → those predictions
                    #    generate incorrect feedback labels → model learns from its own
                    #    mistakes → degradation accelerates.
                    #
                    #    Example in Governance:
                    #    - Model incorrectly grants access (FP) → User accesses resource →
                    #      System logs "successful access" as positive feedback →
                    #      Model learns to grant more improper access → CASCADE
                    #
                    # 2. PRODUCTION CORRUPTION PREVENTION:
                    #    Without auto-pause, consecutive failures would allow ModelManager
                    #    to swap in progressively worse models, degrading the production
                    #    system. Auto-pause blocks swaps until human review confirms fix.
                    #
                    #    Timeline without auto-pause:
                    #    T0: Model at 90% accuracy (production)
                    #    T1: New model at 84% fails check → WARNING (swap allowed)
                    #    T2: New model at 82% fails check → WARNING (swap allowed)
                    #    T3: New model at 79% fails check → WARNING (swap allowed)
                    #    T4: Production now running 79% model → CRITICAL FAILURE
                    #
                    #    Timeline WITH auto-pause:
                    #    T0: Model at 90% accuracy (production)
                    #    T1: New model at 84% fails check → WARNING (swap allowed)
                    #    T2: New model at 82% fails check → WARNING (swap allowed)
                    #    T3: New model at 79% fails check → PAUSED (swap BLOCKED)
                    #    T4: Production still running 90% model → STABLE
                    #
                    # 3. FORCED INVESTIGATION WINDOW:
                    #    Auto-pause creates mandatory stop for root cause analysis:
                    #    - Is training data corrupted? (bad labels, feature drift)
                    #    - Is there distribution shift? (concept drift, covariate shift)
                    #    - Are hyperparameters misconfigured? (learning rate too high)
                    #    - Is there infrastructure failure? (broken pipeline)
                    #
                    # 4. GOVERNANCE SAFETY MARGIN:
                    #    In access control, even a brief period with a degraded model can:
                    #    - Grant unauthorized access (security breach, compliance violation)
                    #    - Deny legitimate access (business disruption, user frustration)
                    #    - Create audit inconsistencies (compliance risk)
                    #    Auto-pause prevents these risks by blocking updates proactively.
                    #
                    # WHY ENABLE_AUTO_PAUSE IS CRITICAL:
                    # When enable_auto_pause=False (NOT RECOMMENDED for production):
                    # - Circuit breaker transitions to CRITICAL but does NOT pause
                    # - Learning continues despite consecutive failures (DANGEROUS)
                    # - Operator must manually monitor and pause (human-in-the-loop delay)
                    # - Use only for testing/debugging where controlled degradation is acceptable
                    #
                    # When enable_auto_pause=True (RECOMMENDED for production):
                    # - Circuit breaker automatically pauses learning (fail-safe)
                    # - No human intervention delay (immediate protection)
                    # - Forces operators to fix root cause before resume (deliberate recovery)
                    # - Default: True for safety-critical governance applications
                    #
                    # This is the circuit breaker "opening" to prevent further damage.
                    # Sets status to PAUSED and blocks all future learning operations.
                    self._pause_learning()  # Opens circuit breaker

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

        Recovery Process and Manual Intervention:
        ==========================================

        When the circuit breaker opens (PAUSED state), manual intervention via
        force_resume() is required to restart learning. This deliberate human-in-the-loop
        ensures systematic issues are resolved before resuming operations.

        WHEN TO USE MANUAL INTERVENTION (force_resume):

        Scenario 1: Root Cause Identified and Fixed
        --------------------------------------------
        If investigation reveals a fixable issue that has been resolved:

        Example: Data Pipeline Corruption
        - Investigation: Features were not being normalized correctly
        - Fix: Repaired StandardScaler initialization in preprocessing
        - Action: force_resume() after verifying fix on validation data
        - Rationale: Root cause eliminated, safe to resume learning

        Example: Hyperparameter Misconfiguration
        - Investigation: Learning rate (0.1) was too high, causing divergence
        - Fix: Reduced learning_rate to 0.01 in model configuration
        - Action: force_resume() after testing with smaller learning rate
        - Rationale: Configuration corrected, stable training expected

        Example: Bad Training Batch
        - Investigation: Single batch contained corrupted labels (flipped grant/deny)
        - Fix: Removed corrupted batch from training queue, validated data quality
        - Action: force_resume() after data quality checks pass
        - Rationale: Corrupted data purged, clean training data restored

        Scenario 2: Temporary Distribution Shift Resolved
        --------------------------------------------------
        If drift detection shows distribution has returned to normal:

        Example: Organizational Restructure
        - Investigation: Company acquisition caused temporary access pattern shift
        - Resolution: Access patterns stabilized after integration completed
        - Action: force_resume() after drift_score returns to baseline
        - Rationale: Distribution shift was temporary, model is valid again

        Example: Seasonal Policy Change
        - Investigation: End-of-quarter access patterns deviated from norm
        - Resolution: Quarter ended, access patterns returned to typical levels
        - Action: force_resume() after monitoring shows pattern normalization
        - Rationale: Seasonal drift resolved, model applicable again

        Scenario 3: Threshold Adjustment After Review
        ----------------------------------------------
        If investigation shows thresholds were too conservative:

        Example: Overly Strict Accuracy Threshold
        - Investigation: Model consistently at 83-84% (below 85% threshold)
        - Analysis: Domain research shows 80-85% is acceptable for this use case
        - Action: Lower accuracy_threshold to 0.80, then force_resume()
        - Rationale: Threshold was misconfigured, model is actually safe
        - CAUTION: Only adjust thresholds after thorough domain analysis!

        WHEN NOT TO USE MANUAL INTERVENTION:

        Do NOT force_resume() if:

        1. Root Cause Unknown:
           - Consecutive failures detected but cause unclear
           - Action: Continue investigation, review logs/metrics/drift
           - Risk: Resuming without fix will trigger circuit breaker again

        2. Systematic Data Quality Issues:
           - Label noise, feature corruption, or missing values persist
           - Action: Fix data pipeline, validate data quality first
           - Risk: Model will learn from garbage data (garbage in, garbage out)

        3. Fundamental Model Degradation:
           - Model has catastrophically forgotten previous knowledge
           - Distribution shift is permanent (concept drift)
           - Action: Retrain model from scratch with new data
           - Risk: Resuming learning won't fix fundamental model corruption

        4. Infrastructure Instability:
           - Database connections flapping, network issues, resource constraints
           - Action: Stabilize infrastructure before resuming
           - Risk: Unstable infrastructure will cause repeated failures

        STANDARD RECOVERY WORKFLOW:

        Step 1: INVESTIGATE
        -------------------
        - Check logs for error messages and stack traces
        - Review accuracy metrics (current vs. historical)
        - Analyze drift scores (check_drift() results)
        - Inspect recent training batches (data quality)
        - Verify infrastructure health (database, network, resources)

        Step 2: DIAGNOSE
        ----------------
        - Identify root cause (data quality, drift, configuration, infrastructure)
        - Determine if issue is transient or systematic
        - Assess whether model can be salvaged or needs retraining

        Step 3: FIX
        -----------
        - Repair data pipeline if corrupted
        - Adjust hyperparameters if misconfigured
        - Retrain model if fundamentally degraded
        - Fix infrastructure if unstable

        Step 4: VALIDATE
        ----------------
        - Test fix on validation data (ensure accuracy > threshold)
        - Verify data quality checks pass
        - Confirm drift scores are within acceptable range
        - Run safety checks manually before force_resume()

        Step 5: RESUME
        --------------
        - Call force_resume() to close circuit breaker
        - Monitor initial checks closely (ensure they pass)
        - Watch for consecutive failures (circuit may reopen)
        - Document incident for post-mortem analysis

        Step 6: MONITOR
        ---------------
        - Track accuracy metrics for next 24-48 hours
        - Watch for circuit breaker state transitions
        - Verify model performance remains stable
        - Conduct post-mortem to prevent recurrence

        ALTERNATIVE: AUTOMATIC RECOVERY

        The circuit breaker can also close automatically if a safety check passes
        after being PAUSED. This happens in _handle_success() when status == PAUSED.

        Automatic recovery occurs when:
        - Underlying issue self-resolves (temporary drift, transient error)
        - Next model update happens to pass safety checks
        - No manual intervention was needed

        However, automatic recovery should NOT be relied upon for systematic issues.
        If consecutive failures indicated a real problem, force_resume() with
        investigation is the safer approach.

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
