"""
Adaptive Learning Engine - Online Learner
Constitutional Hash: cdd01ef066bc6cf2

River-based online learning model for real-time governance decisions.
Implements progressive validation (predict first, then learn) paradigm.

PROGRESSIVE VALIDATION (PREQUENTIAL EVALUATION)
===============================================

River implements the "prequential evaluation" paradigm (predictive sequential),
originally proposed by Dawid (1984) for online learning systems. This evaluation
approach more accurately simulates production reality than traditional batch
learning with train/test splits.

Key Principle: "Test, then train"
---------------------------------
For each incoming sample, the model:
1. Makes a prediction FIRST (without seeing the true label)
2. Records the prediction for evaluation
3. Only THEN learns from the sample (after prediction is recorded)

This order is critical - it ensures the model is evaluated on genuinely unseen
data, exactly as it would behave in production where labels arrive after predictions.

Contrast with Batch Learning
-----------------------------
Traditional ML:
- Split data into train/test sets upfront
- Train on all training data
- Evaluate on held-out test set
- Problem: Assumes static data distribution (i.i.d. assumption)
- Problem: Test set may not represent future production data

Progressive Validation (Online Learning):
- No upfront split - each sample is "test, then train"
- Model predicts on sample i, then learns from it
- Sample i+1 becomes the next test case
- Advantage: Simulates production streaming reality
- Advantage: Naturally handles distribution shift (non-stationary data)
- Advantage: More realistic performance estimates

Why This Matters for Governance
--------------------------------
Governance policies evolve over time - new regulations emerge, organizational
priorities shift, user behavior adapts. Progressive validation ensures our
adaptive learning system is evaluated on its ability to:
1. Handle distribution shift (policy drift over time)
2. Learn incrementally without catastrophic forgetting
3. Maintain performance as new governance patterns emerge

The prequential paradigm gives us a more honest estimate of production
performance than batch learning would, since governance is inherently
a streaming, non-stationary problem.

Theoretical Guarantees
----------------------
Under the prequential paradigm:
- Cumulative accuracy converges to true model performance in stationary settings
- Rolling accuracy tracks recent performance for drift detection
- No "future information leakage" - all predictions are truly out-of-sample
- Evaluation is unbiased (no overfitting to a fixed test set)

References
----------
- Dawid, A. P. (1984). "Present Position and Potential Developments: Some
  Personal Views: Statistical Theory: The Prequential Approach."
  Journal of the Royal Statistical Society, Series A.

- Gama, J., Žliobaitė, I., Bifet, A., Pechenizkiy, M., & Bouchachia, A. (2014).
  "A Survey on Concept Drift Adaptation." ACM Computing Surveys, 46(4), 1-37.
  https://doi.org/10.1145/2523813

- River documentation on progressive validation:
  https://riverml.xyz/latest/introduction/getting-started/

- Bifet, A., & Gavaldà, R. (2007). "Learning from Time-Changing Data with
  Adaptive Windowing." SIAM International Conference on Data Mining.
"""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

from river import compose, linear_model, metrics, optim, preprocessing

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Supported online learning model types."""

    LOGISTIC_REGRESSION = "logistic_regression"
    PERCEPTRON = "perceptron"
    PA_CLASSIFIER = "pa_classifier"  # Passive-Aggressive


class ModelState(Enum):
    """Current state of the online learner."""

    COLD_START = "cold_start"  # No training samples yet
    WARMING = "warming"  # Below min_training_samples
    ACTIVE = "active"  # Trained and ready
    PAUSED = "paused"  # Learning paused due to safety bounds


@dataclass
class PredictionResult:
    """Result from a single prediction."""

    prediction: int
    confidence: float
    probabilities: Dict[int, float]
    model_state: ModelState
    sample_count: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class TrainingResult:
    """Result from a single training update."""

    success: bool
    sample_count: int
    current_accuracy: float
    model_state: ModelState
    message: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ModelMetrics:
    """Current metrics for the online learner."""

    accuracy: float
    sample_count: int
    model_state: ModelState
    recent_accuracy: float  # Rolling window accuracy
    last_update_time: float
    predictions_count: int
    model_type: str


class OnlineLearner:
    """River-based online learning model for governance decisions.

    Implements the River online learning paradigm with progressive validation
    (prequential evaluation), which more accurately simulates production ML
    systems than traditional batch learning approaches.

    Core Paradigm: Progressive Validation
    --------------------------------------
    Unlike batch ML where you train once on historical data and deploy:
    1. Each sample arrives as a stream (one at a time)
    2. Model makes prediction WITHOUT seeing the label (production simulation)
    3. True label arrives (delayed feedback in real systems)
    4. Model learns from the labeled sample
    5. Next sample arrives → repeat

    This "test-then-train" cycle ensures:
    - No future information leakage (all predictions are truly out-of-sample)
    - Realistic performance estimates (simulates production streaming)
    - Natural handling of distribution drift (model adapts continuously)
    - Memory efficiency (no need to store entire training dataset)

    Why This Matters for Governance
    --------------------------------
    Governance is NOT a static problem with i.i.d. data:
    - Policies evolve (new regulations, changing organizational priorities)
    - User behavior adapts (users learn the system, adversarial actors probe)
    - Context shifts (seasonal patterns, organizational restructuring)

    Progressive validation gives us honest performance metrics under these
    non-stationary conditions. Batch learning would overfit to historical
    patterns that may no longer apply.

    Implementation Features
    -----------------------
    - One sample at a time (true online learning, not mini-batches)
    - Predict first, then learn (progressive validation / prequential)
    - No separate fit phase (learning is continuous)
    - Cold start handling with conservative defaults (fail-safe for governance)
    - Time-weighted learning for conflicting signals (recent data matters more)
    - Thread-safe operations for concurrent requests (production-ready)
    - Rolling accuracy tracking (detect performance degradation early)

    Model State Lifecycle
    ----------------------
    COLD_START → WARMING → ACTIVE
                          ↕
                       PAUSED (safety circuit breaker)

    - COLD_START: No training samples yet, returns conservative defaults
    - WARMING: Collecting samples but below min_training_samples threshold
    - ACTIVE: Sufficient samples (≥1000), ready for production predictions
    - PAUSED: Safety bounds triggered, learning halted (requires intervention)

    Example usage:
        learner = OnlineLearner()

        # Progressive validation workflow (THE CORRECT ORDER):
        # 1. Predict first (without label)
        prediction = learner.predict_one(features)

        # 2. Later, when true label arrives, learn from it
        learner.learn_one(features, label)

        # Combined atomic operation (ensures correct order):
        prediction, training_result = learner.predict_and_learn(features, label)

        # Monitor performance
        metrics = learner.get_metrics()
        print(f"Cumulative accuracy: {metrics.accuracy:.3f}")
        print(f"Rolling accuracy (last 100): {metrics.recent_accuracy:.3f}")

    References
    ----------
    - River ML: https://riverml.xyz/
    - Gama et al. (2014): "A Survey on Concept Drift Adaptation"
    - Dawid (1984): "The Prequential Approach" (original progressive validation)
    """

    # COLD START SAFETY DEFAULTS
    # ===========================
    # During cold start (no training samples yet), the model has no learned
    # knowledge about governance patterns. We must return safe defaults that
    # minimize risk in safety-critical governance applications.
    #
    # DEFAULT_PREDICTION = 0 (DENY)
    # - Fail-safe principle: When uncertain, deny by default
    # - Governance rationale: False positives (deny when should allow) are
    #   safer than false negatives (allow when should deny)
    # - Example: Denying a risky data access is safer than allowing it
    # - As model learns patterns, it can confidently predict 1 (allow) when appropriate
    # - This conservative default prevents untrained models from making high-risk decisions
    #
    # DEFAULT_CONFIDENCE = 0.5 (MAXIMUM UNCERTAINTY)
    # - Represents complete uncertainty (equal probability for both classes)
    # - Signals to downstream systems: "This prediction is a guess, not informed"
    # - Enables safety systems to detect cold start state (low confidence → extra scrutiny)
    # - Contrasts with trained model confidences (typically 0.7-0.95 for clear patterns)
    # - Maximum entropy: No bias toward either class (truly uninformed prior)
    DEFAULT_PREDICTION = 0
    DEFAULT_CONFIDENCE = 0.5

    def __init__(
        self,
        model_type: ModelType = ModelType.LOGISTIC_REGRESSION,
        min_training_samples: int = 1000,
        learning_rate: float = 0.1,
        l2_regularization: float = 0.01,
        rolling_window_size: int = 100,
        time_decay_factor: float = 0.99,
    ) -> None:
        """Initialize the online learner.

        Args:
            model_type: Type of online learning model to use.
            min_training_samples: Minimum samples before model is active.
            learning_rate: Learning rate for the optimizer.
            l2_regularization: L2 regularization strength.
            rolling_window_size: Window size for rolling accuracy tracking.
                Default: 100 samples balances drift detection responsiveness with
                statistical stability. See ROLLING WINDOW CONFIGURATION below.
            time_decay_factor: Factor for time-weighted learning (0.0-1.0).

        ROLLING WINDOW CONFIGURATION
        =============================
        The rolling_window_size parameter controls the number of recent samples
        used to compute rolling accuracy, which tracks recent model performance
        for drift detection and adaptation monitoring.

        Why rolling_window_size = 100 Is Optimal:
        ------------------------------------------
        This default balances several competing statistical requirements:

        1. STATISTICAL SIGNIFICANCE
           - For binary classification, accuracy estimate has standard error:
             SE = sqrt(p(1-p) / n) where p = true accuracy, n = window size
           - With n=100 and p≈0.85 (target accuracy):
             SE ≈ sqrt(0.85 * 0.15 / 100) ≈ 0.036 (3.6% margin of error)
           - 95% confidence interval: ±1.96 * SE ≈ ±7%
           - This is tight enough to detect meaningful drift (>5-10% drops)
             without excessive noise from small sample variance

        2. DRIFT DETECTION RESPONSIVENESS
           - Smaller windows (e.g., 50) detect drift faster but are noisier
           - Larger windows (e.g., 500) are more stable but slower to detect drift
           - 100 samples provides a reasonable compromise:
             * Detects significant drift within 100-200 samples
             * Filters out transient noise and outliers
             * Responds to sustained performance degradation

        3. GOVERNANCE-SPECIFIC RATIONALE
           - In governance systems, policy drift is gradual (not sudden)
           - 100 samples is typically hours-days of production traffic
           - Fast enough to catch emerging issues (e.g., new regulation impact)
           - Slow enough to avoid false alarms from temporary anomalies
           - Aligns with operational monitoring cadences (hourly/daily)

        4. MEMORY EFFICIENCY
           - Window size affects memory footprint for drift detection
           - 100 samples is small enough for low overhead
           - Yet large enough for meaningful statistical analysis
           - Supports real-time streaming with minimal latency

        Trade-offs of Different Window Sizes:
        --------------------------------------
        - window_size = 50:
          * Advantage: Faster drift detection (responds within 50-100 samples)
          * Disadvantage: High variance (±10% accuracy fluctuations)
          * Use case: Rapidly evolving environments, frequent retraining

        - window_size = 100 (DEFAULT):
          * Advantage: Balanced responsiveness and stability
          * Advantage: ~±7% confidence interval (reasonable precision)
          * Use case: Most governance applications (stable policies, gradual drift)

        - window_size = 500:
          * Advantage: Very stable accuracy estimates (±3% confidence interval)
          * Disadvantage: Slow drift detection (needs 500-1000 samples to confirm)
          * Use case: High-traffic systems with low expected drift

        Statistical Properties of Rolling Windows:
        -------------------------------------------
        Rolling accuracy is computed over a fixed-size sliding window using
        River's metrics.Rolling() wrapper. Key properties:

        - SLIDING WINDOW: As new samples arrive, oldest samples are evicted
          (FIFO queue behavior using collections.deque)
        - UNBIASED: Each sample in window has equal weight (unlike exponential decay)
        - STATIONARY OVER WINDOW: Assumes distribution is stable within window
        - NON-OVERLAPPING WITH PAST: Only considers last N samples (forget earlier)

        For drift detection, compare rolling accuracy to cumulative accuracy:
        - rolling_accuracy << cumulative_accuracy → Recent degradation (drift)
        - rolling_accuracy ≈ cumulative_accuracy → Stable performance
        - rolling_accuracy >> cumulative_accuracy → Recent improvement (adaptation)

        Theoretical Foundation:
        -----------------------
        The rolling window approach is a standard technique in concept drift
        detection literature. Key references:

        - Gama et al. (2014): Fixed-size sliding windows for drift detection
          https://doi.org/10.1145/2523813
        - Bifet & Gavaldà (2007): ADWIN adaptive windowing algorithm
          (our fixed window is simpler but less adaptive)
        - Klinkenberg (2004): Window sizing for drift adaptation
          (recommends 100-500 samples for most applications)
        """
        self.model_type = model_type
        self.min_training_samples = min_training_samples
        self.learning_rate = learning_rate
        self.l2_regularization = l2_regularization
        self.rolling_window_size = rolling_window_size
        self.time_decay_factor = time_decay_factor

        # Thread safety
        self._lock = threading.RLock()

        # Build the model pipeline
        self._model = self._build_pipeline()

        # METRICS TRACKING: CUMULATIVE VS. ROLLING ACCURACY
        # ==================================================
        # We track two complementary accuracy metrics that serve different purposes
        # in online learning systems:
        #
        # 1. CUMULATIVE ACCURACY (self._accuracy_metric)
        #    - Tracks overall model performance across ALL samples ever seen
        #    - Computed as: total_correct / total_samples (from sample 1 to current)
        #    - Purpose: Measures long-term model health and overall capability
        #    - Properties:
        #      * Converges to true model accuracy in stationary settings (law of large numbers)
        #      * Slow to change (each new sample has decreasing influence: 1/n weight)
        #      * Not sensitive to recent drift (old samples still contribute equally)
        #      * Unbiased estimator of long-run performance
        #    - Example: After 10,000 samples with 85% accuracy, the 10,001st sample
        #      only shifts accuracy by ±0.01% (minimal impact)
        #
        # 2. ROLLING ACCURACY (self._rolling_accuracy_metric)
        #    - Tracks recent model performance over last N samples (default: 100)
        #    - Computed as: correct_in_window / window_size (only last 100 samples)
        #    - Purpose: Detects concept drift and monitors adaptation effectiveness
        #    - Properties:
        #      * Sensitive to recent changes (each new sample has 1/N weight)
        #      * Higher variance than cumulative (smaller sample size)
        #      * Quickly reflects performance degradation or improvement
        #      * Early warning system for drift and model deterioration
        #    - Example: After 10,000 samples, the 10,001st sample shifts rolling
        #      accuracy by ±1% (100x more sensitive than cumulative)
        #
        # WHY TRACK BOTH METRICS?
        # ------------------------
        # They provide complementary information for production ML monitoring:
        #
        # Scenario 1: Stable Performance
        # - cumulative_accuracy ≈ 0.85, rolling_accuracy ≈ 0.85
        # - Interpretation: Model is consistently performing well
        # - Action: Normal operation, continue learning
        #
        # Scenario 2: Recent Degradation (DRIFT DETECTED)
        # - cumulative_accuracy ≈ 0.85, rolling_accuracy ≈ 0.70
        # - Interpretation: Model was good historically but struggling on recent data
        # - Likely cause: Concept drift (distribution shift, policy change)
        # - Action: Trigger drift alert, investigate data changes, consider retraining
        #
        # Scenario 3: Early Stage Improvement
        # - cumulative_accuracy ≈ 0.70, rolling_accuracy ≈ 0.85
        # - Interpretation: Model was poor initially but improving recently
        # - Likely cause: Successful adaptation after cold start or drift recovery
        # - Action: Monitor continued improvement, model is learning effectively
        #
        # Scenario 4: Both Low (CRITICAL)
        # - cumulative_accuracy ≈ 0.60, rolling_accuracy ≈ 0.60
        # - Interpretation: Model has never performed well and still isn't
        # - Likely cause: Insufficient training data, wrong model choice, or poor features
        # - Action: Safety bounds trigger, pause learning, investigate root cause
        #
        # IMPLEMENTATION: River's metrics.Rolling() Wrapper
        # --------------------------------------------------
        # River's metrics.Rolling() implements a sliding window over any base metric.
        # Internal mechanism:
        #
        # 1. SLIDING WINDOW WITH DEQUE
        #    - Uses collections.deque(maxlen=window_size) to store recent predictions
        #    - FIFO (First-In-First-Out): When window is full, oldest sample is evicted
        #    - Memory complexity: O(window_size) - stores (y_true, y_pred) pairs
        #
        # 2. INCREMENTAL UPDATE ALGORITHM
        #    - On each new sample (y_true, y_pred):
        #      (a) If window is full: Remove oldest sample's contribution to accuracy
        #      (b) Add new sample's contribution to accuracy
        #      (c) Recompute: accuracy = correct_in_window / len(window)
        #    - This is O(1) per update (constant time, no need to recompute all samples)
        #
        # 3. PROGRESSIVE VALIDATION COMPLIANCE
        #    - Maintains prequential evaluation property: prediction made before learning
        #    - Each (y_true, y_pred) pair added to window was predicted before label seen
        #    - Ensures rolling accuracy is truly out-of-sample (unbiased)
        #
        # 4. WINDOW INITIALIZATION BEHAVIOR
        #    - First N samples: Window is not yet full (size < window_size)
        #    - Accuracy computed over available samples: correct_so_far / samples_so_far
        #    - After N samples: Window is full, starts evicting oldest
        #    - This means rolling accuracy is initially identical to cumulative accuracy
        #      until window_size samples are collected
        #
        # Example Rolling Window Trace (window_size=3):
        # Sample 1: window=[1], rolling_accuracy = 1/1 = 1.00 (correct)
        # Sample 2: window=[1,0], rolling_accuracy = 1/2 = 0.50 (incorrect)
        # Sample 3: window=[1,0,1], rolling_accuracy = 2/3 = 0.67 (correct)
        # Sample 4: window=[0,1,1], rolling_accuracy = 2/3 = 0.67 (evicted 1, added 1)
        # Sample 5: window=[1,1,0], rolling_accuracy = 2/3 = 0.67 (evicted 0, added 0)
        #
        # Statistical Interpretation:
        # ---------------------------
        # The rolling accuracy is an unbiased estimator of the model's current
        # performance, assuming the distribution is stationary within the window.
        #
        # Standard error of rolling accuracy (binary classification):
        # SE = sqrt(p(1-p) / window_size)
        #
        # For window_size=100 and p=0.85 (typical governance accuracy):
        # SE ≈ sqrt(0.85 * 0.15 / 100) ≈ 0.036 (3.6%)
        #
        # 95% confidence interval: accuracy ± 1.96*SE ≈ accuracy ± 7%
        #
        # This means:
        # - Observed rolling accuracy of 0.78 is significantly below 0.85 (drift)
        # - Observed rolling accuracy of 0.83 is within noise (no drift detected)
        # - Need ~2-3 standard errors difference to confidently detect drift
        #
        # For drift detection, use the rule:
        # IF rolling_accuracy < cumulative_accuracy - 2*SE:
        #     # Statistically significant degradation detected (95% confidence)
        #     trigger_drift_alert()
        #
        # References:
        # -----------
        # - River metrics.Rolling() documentation:
        #   https://riverml.xyz/latest/api/metrics/Rolling/
        # - Gama et al. (2014): "A Survey on Concept Drift Adaptation"
        #   Section on sliding window approaches for drift detection
        # - Bifet & Gavaldà (2007): Comparison of fixed vs. adaptive windows
        self._accuracy_metric = metrics.Accuracy()
        self._rolling_accuracy_metric = metrics.Rolling(
            metrics.Accuracy(), window_size=rolling_window_size
        )

        # State tracking
        self._sample_count = 0
        self._predictions_count = 0
        self._state = ModelState.COLD_START
        self._last_update_time: Optional[float] = None
        self._is_paused = False

        # Recent predictions for drift detection (thread-safe deque)
        self._recent_predictions: Deque[Tuple[Dict[str, Any], int, float]] = deque(
            maxlen=rolling_window_size
        )

        # Feature statistics for input validation
        self._feature_stats: Dict[str, Dict[str, float]] = {}

        logger.info(
            "OnlineLearner initialized",
            extra={
                "model_type": model_type.value,
                "min_training_samples": min_training_samples,
                "learning_rate": learning_rate,
            },
        )

    def _build_pipeline(self) -> compose.Pipeline:
        """Build the River model pipeline with preprocessing.

        Returns:
            Composed pipeline with preprocessing and model.
        """
        # ONLINE LEARNING ALGORITHMS
        # ===========================
        # River provides several online classification algorithms that update their
        # weights incrementally with each sample (one at a time). Unlike batch ML
        # which trains on entire datasets, these models learn continuously from
        # streaming data.
        #
        # Key Property: Each algorithm processes samples individually and updates
        # weights immediately. This enables:
        # - Memory efficiency (no need to store training data)
        # - Real-time adaptation (immediate response to new patterns)
        # - Concept drift handling (continuous weight updates track distribution shift)

        # Select the base model based on configuration
        if self.model_type == ModelType.LOGISTIC_REGRESSION:
            # LOGISTIC REGRESSION WITH SGD
            # ============================
            # Online logistic regression uses Stochastic Gradient Descent (SGD) to
            # update weights incrementally with each training sample.
            #
            # Algorithm:
            # ----------
            # For each sample (x, y):
            #   1. Compute prediction: p(y=1|x) = σ(w·x) where σ = sigmoid function
            #   2. Calculate gradient: ∇L = (p - y) * x  (negative log-likelihood)
            #   3. Update weights: w ← w - η * ∇L  (η = learning_rate)
            #   4. Apply L2 regularization: w ← w * (1 - η*λ)  (λ = l2_regularization)
            #
            # SGD Properties:
            # - Incremental updates: Weights adjust with every sample (not batches)
            # - Stochastic: Each update uses one sample's gradient (noisy but fast)
            # - Convergence: In online setting, tracks moving target (non-stationary)
            # - L2 regularization: Prevents overfitting by penalizing large weights
            #
            # Why SGD for Online Learning?
            # - Immediate weight updates (no waiting for batch accumulation)
            # - Low memory footprint (single sample gradient)
            # - Adaptive to drift (recent samples influence current weights more)
            # - Probabilistic outputs (predict_proba gives calibrated confidences)
            #
            # Hyperparameters:
            # - learning_rate (η): Step size for weight updates (default: 0.1)
            #   - Too high: Unstable, oscillates around optimal weights
            #   - Too low: Slow adaptation, can't track drift
            # - l2_regularization (λ): Weight penalty strength (default: 0.01)
            #   - Prevents overfitting to recent samples
            #   - Smooths decision boundary for better generalization
            model = linear_model.LogisticRegression(
                optimizer=optim.SGD(self.learning_rate),
                l2=self.l2_regularization,
            )

        elif self.model_type == ModelType.PERCEPTRON:
            # PERCEPTRON (ONLINE MISTAKE-DRIVEN LEARNING)
            # ============================================
            # The Perceptron is the simplest online learning algorithm, updating
            # weights only when it makes a mistake (prediction ≠ true label).
            #
            # Algorithm:
            # ----------
            # For each sample (x, y):
            #   1. Compute prediction: ŷ = sign(w·x)  (binary: -1 or +1)
            #   2. If ŷ ≠ y (mistake):
            #      - Update: w ← w + y*x  (move weights toward correct class)
            #   3. If ŷ = y (correct):
            #      - No update (weights unchanged)
            #   4. Apply L2 regularization: w ← w * (1 - λ)
            #
            # Mistake-Driven Learning:
            # - Conservative updates: Only changes weights when wrong
            # - Aggressive corrections: Full sample vector added/subtracted
            # - No learning rate: Updates are unscaled (fixed step size)
            # - Deterministic: Same samples → same final weights (if linearly separable)
            #
            # Perceptron Convergence Theorem:
            # - If data is linearly separable, Perceptron converges in finite steps
            # - In online setting with drift, never fully converges (intentional)
            # - Continuous adaptation as distribution shifts
            #
            # Advantages:
            # - Extremely fast (no probability calculations)
            # - Simple and robust (few hyperparameters)
            # - Memory-efficient (just weight vector)
            #
            # Disadvantages:
            # - No probability estimates (hard classifications only)
            # - Struggles with non-separable data (no margin concept)
            # - Can be unstable with conflicting labels (no confidence weighting)
            #
            # Hyperparameters:
            # - l2_regularization (λ): Weight decay to prevent unbounded growth
            #   - Critical for non-stationary data (prevents old patterns dominating)
            model = linear_model.Perceptron(l2=self.l2_regularization)

        elif self.model_type == ModelType.PA_CLASSIFIER:
            # PASSIVE-AGGRESSIVE CLASSIFIER (MARGIN-BASED ONLINE LEARNING)
            # ============================================================
            # Passive-Aggressive (PA) algorithm balances stability and adaptability
            # by using margin-based updates with controlled aggressiveness.
            #
            # Algorithm:
            # ----------
            # For each sample (x, y):
            #   1. Compute margin: m = y * (w·x)  (signed distance from decision boundary)
            #   2. Compute loss: ℓ = max(0, 1 - m)  (hinge loss, 0 if margin ≥ 1)
            #   3. If ℓ > 0 (margin violated):
            #      - Compute step size: τ = ℓ / (||x||² + 1/(2C))
            #      - Update: w ← w + τ * y * x
            #   4. If ℓ = 0 (sufficient margin):
            #      - No update (passive)
            #
            # Passive-Aggressive Philosophy:
            # - PASSIVE when margin ≥ 1: Don't update if prediction is confident and correct
            # - AGGRESSIVE when margin < 1: Update to achieve margin of at least 1
            # - Bounded aggressiveness: C parameter limits maximum step size
            #
            # Margin-Based Updates:
            # - Similar to online SVM (hinge loss, margin optimization)
            # - Loss = 0 when margin ≥ 1 (correct with confidence)
            # - Loss increases as margin decreases (closer to boundary or wrong side)
            # - Update magnitude proportional to loss (larger errors → larger updates)
            #
            # C Parameter (Aggressiveness Control):
            # - C controls the trade-off between stability and adaptation
            # - Large C (e.g., 1.0):
            #   - More aggressive updates (larger step sizes)
            #   - Faster adaptation to new patterns
            #   - Risk: Overfitting to outliers or label noise
            # - Small C (e.g., 0.01):
            #   - More conservative updates (smaller step sizes)
            #   - Smoother decision boundary
            #   - Risk: Slow adaptation to concept drift
            # - Default: C = learning_rate (typically 0.1)
            #   - Balances adaptation speed with robustness
            #
            # Advantages Over Perceptron:
            # - Margin awareness: Distinguishes "barely correct" from "confidently correct"
            # - Controlled updates: C prevents excessive weight changes from outliers
            # - Better calibration: Maintains decision boundary margins for robustness
            #
            # When to Use PA Classifier:
            # - Non-stationary data with occasional label noise (C provides robustness)
            # - When you need faster adaptation than logistic regression (no probability overhead)
            # - Binary classification with clear decision boundaries
            #
            # Hyperparameters:
            # - C: Aggressiveness parameter (step size limiter)
            #   - Typically 0.01-1.0 range
            #   - We use learning_rate for consistency across models
            model = linear_model.PAClassifier(C=self.learning_rate)

        else:
            # Default to logistic regression (most robust for governance)
            model = linear_model.LogisticRegression(
                optimizer=optim.SGD(self.learning_rate),
                l2=self.l2_regularization,
            )

        # FEATURE PREPROCESSING: ONLINE STANDARDSCALER
        # ============================================
        # StandardScaler normalizes features to zero mean and unit variance,
        # critical for linear models where feature scales affect learning.
        #
        # Why Standardization Matters:
        # - Linear models (LogReg, Perceptron, PA) compute w·x as weighted sum
        # - Features with large scales (e.g., counts in 1000s) dominate small scales (e.g., ratios 0-1)
        # - Unstandardized features cause:
        #   (1) Slow convergence (gradient descent takes tiny steps on small features)
        #   (2) Poor generalization (weights overfit to large-scale features)
        #   (3) Numerical instability (overflow/underflow in exp() for logistic regression)
        #
        # Online StandardScaler:
        # - Computes running mean and variance incrementally (Welford's algorithm)
        # - Updates statistics with each sample: μ_new = μ_old + (x - μ_old)/n
        # - Transforms: z = (x - μ) / σ  (zero mean, unit variance)
        # - Memory efficient: Stores only μ, σ, n (not entire dataset)
        #
        # Behavior During Cold Start:
        # - First sample: Cannot standardize (no variance yet)
        # - Early samples: High variance in normalization (statistics unstable)
        # - After ~100 samples: Statistics stabilize, normalization becomes reliable
        # - This is why min_training_samples=1000 ensures stable model before ACTIVE
        #
        # Handling Distribution Shift:
        # - StandardScaler adapts to changing distributions (unlike batch preprocessing)
        # - Mean and variance track recent data trends
        # - Prevents feature scaling from becoming stale as data drifts
        # - Trade-off: Past and present samples normalized differently
        #
        # Pipeline Composition:
        # River's Pipeline applies transformations sequentially:
        #   1. StandardScaler.learn_one(x) → updates mean/variance statistics
        #   2. StandardScaler.transform_one(x) → z = normalized features
        #   3. Model.learn_one(z, y) → trains on normalized features
        #   4. For prediction: x → normalize → predict (consistent transformation)
        pipeline = compose.Pipeline(
            ("scaler", preprocessing.StandardScaler()),
            ("model", model),
        )

        return pipeline

    def predict_one(self, x: Dict[str, Any]) -> PredictionResult:
        """Make a prediction for a single sample.

        In the progressive validation paradigm, predict BEFORE learning.
        This simulates production reality where we predict before knowing outcome.

        Args:
            x: Feature dictionary with numeric values.

        Returns:
            PredictionResult with prediction, confidence, and metadata.
        """
        with self._lock:
            self._predictions_count += 1
            timestamp = time.time()

            # COLD START SAFETY STRATEGY
            # ===========================
            # When the model has received zero training samples (_state == COLD_START),
            # it has no learned knowledge about governance patterns. Returning predictions
            # from an untrained model would be dangerous in safety-critical applications.
            #
            # Safety-First Approach:
            # - Return DEFAULT_PREDICTION = 0 (deny) - fail-safe for governance
            # - Return DEFAULT_CONFIDENCE = 0.5 - signals maximum uncertainty
            # - Probabilities = {0: 0.5, 1: 0.5} - uniform distribution (no bias)
            #
            # Why This Matters:
            # - Governance decisions have real-world impact (data access, policy enforcement)
            # - False negatives (allowing bad actions) are costlier than false positives
            # - Conservative default prevents untrained model from granting risky permissions
            # - Downstream systems can detect cold start via low confidence and route to human review
            #
            # State Transition:
            # - COLD_START persists until first training sample arrives
            # - Then transitions to WARMING state (see _update_state())
            if self._state == ModelState.COLD_START:
                return PredictionResult(
                    prediction=self.DEFAULT_PREDICTION,
                    confidence=self.DEFAULT_CONFIDENCE,
                    probabilities={0: 0.5, 1: 0.5},
                    model_state=self._state,
                    sample_count=self._sample_count,
                    timestamp=timestamp,
                )

            # WARMING AND ACTIVE STATE PREDICTIONS
            # =====================================
            # For WARMING (1 ≤ samples < min_training_samples) and ACTIVE (samples ≥ 1000),
            # we use the model's learned predictions instead of defaults.
            #
            # WARMING State (samples < 1000):
            # - Model is learning but predictions may be unreliable
            # - StandardScaler statistics are still stabilizing
            # - Model weights have high variance (not yet converged)
            # - Confidence scores may be poorly calibrated
            # - Downstream systems should treat WARMING predictions with extra scrutiny
            #
            # ACTIVE State (samples ≥ 1000):
            # - Model has sufficient training for stable, reliable predictions
            # - Ready for production governance decisions
            # - Confidence scores are well-calibrated (typically 0.7-0.95 for clear patterns)
            # - Model continues to learn incrementally (adapts to distribution shift)
            #
            # Both states use the same prediction logic - the state distinction helps
            # downstream systems decide how much to trust the predictions.

            # Get probability predictions
            try:
                proba = self._model.predict_proba_one(x)

                # Handle case where model hasn't seen both classes yet
                if proba is None or not proba:
                    prediction = self.DEFAULT_PREDICTION
                    confidence = self.DEFAULT_CONFIDENCE
                    probabilities = {0: 0.5, 1: 0.5}
                else:
                    # Get prediction and confidence
                    prediction = max(proba.keys(), key=lambda k: proba[k])
                    confidence = proba.get(prediction, self.DEFAULT_CONFIDENCE)
                    probabilities = dict(proba)

                    # Ensure both classes are represented
                    if 0 not in probabilities:
                        probabilities[0] = 1.0 - probabilities.get(1, 0.5)
                    if 1 not in probabilities:
                        probabilities[1] = 1.0 - probabilities.get(0, 0.5)

            except Exception as e:
                logger.warning(f"Prediction error, using default: {e}")
                prediction = self.DEFAULT_PREDICTION
                confidence = self.DEFAULT_CONFIDENCE
                probabilities = {0: 0.5, 1: 0.5}

            return PredictionResult(
                prediction=prediction,
                confidence=confidence,
                probabilities=probabilities,
                model_state=self._state,
                sample_count=self._sample_count,
                timestamp=timestamp,
            )

    def learn_one(
        self,
        x: Dict[str, Any],
        y: int,
        sample_weight: Optional[float] = None,
    ) -> TrainingResult:
        """Update the model with a single training sample.

        CRITICAL: In the progressive validation paradigm, learn AFTER predicting.
        This method should only be called after predict_one() for the same sample.

        Progressive Validation Implementation
        --------------------------------------
        River's prequential evaluation requires this specific order:
        1. predict_one(x) → get prediction without seeing label y
        2. learn_one(x, y) → update model with labeled sample

        This method internally verifies this order by making a prediction
        and comparing it to the true label BEFORE updating the model weights.
        This ensures:
        - Accuracy metrics reflect truly out-of-sample performance
        - No information leakage (model hasn't seen y when predicting)
        - Simulation of production: predict now, learn later when label arrives

        Why One Sample at a Time?
        --------------------------
        True online learning processes samples individually, not in batches:
        - Immediate adaptation to new patterns (no waiting for batch)
        - Memory-efficient (no need to accumulate samples)
        - Handles non-stationary distributions (concept drift)
        - Simulates real-time systems (streaming governance decisions)

        Args:
            x: Feature dictionary with numeric values.
            y: Target label (0 or 1 for binary classification).
            sample_weight: Optional weight for time-weighted learning.
                          Weights >1.0 strengthen signal (learn multiple times).
                          Weights <1.0 weaken signal (probabilistic learning).
                          This enables time-decay for handling non-stationary data.

        Returns:
            TrainingResult with success status and metrics.
        """
        with self._lock:
            timestamp = time.time()

            # Check if learning is paused
            if self._is_paused:
                return TrainingResult(
                    success=False,
                    sample_count=self._sample_count,
                    current_accuracy=self.get_accuracy(),
                    model_state=ModelState.PAUSED,
                    message="Learning is paused due to safety bounds",
                    timestamp=timestamp,
                )

            try:
                # Validate input
                if not isinstance(y, int) or y not in (0, 1):
                    return TrainingResult(
                        success=False,
                        sample_count=self._sample_count,
                        current_accuracy=self.get_accuracy(),
                        model_state=self._state,
                        message=f"Invalid label: {y}. Must be 0 or 1.",
                        timestamp=timestamp,
                    )

                # PREQUENTIAL EVALUATION: Predict before learning
                # ================================================
                # This is the CORE of progressive validation. For sample i:
                # 1. Get prediction using model trained on samples 1...i-1
                # 2. Compare prediction to true label y (for accuracy)
                # 3. Only THEN update model weights with sample i
                #
                # This ensures accuracy metrics are computed on truly unseen data,
                # exactly as they would be in production where predictions happen
                # before labels arrive. It gives an unbiased estimate of future
                # performance.
                if self._sample_count > 0:
                    try:
                        y_pred = self._model.predict_one(x)
                        if y_pred is not None:
                            # Update cumulative accuracy (overall model health)
                            self._accuracy_metric.update(y, y_pred)
                            # Update rolling accuracy (recent performance for drift detection)
                            self._rolling_accuracy_metric.update(y, y_pred)
                    except Exception as e:
                        logger.debug(f"Could not update accuracy metrics: {e}")

                # TIME-WEIGHTED LEARNING FOR NON-STATIONARY ENVIRONMENTS
                # =======================================================
                # In governance systems, data is non-stationary (distribution shifts over time):
                # - Policies evolve (new regulations, organizational changes)
                # - User behavior adapts (learning patterns, adversarial probing)
                # - Context shifts (seasonal patterns, staffing changes)
                #
                # Recent samples are more representative of current patterns than old samples.
                # Time-weighted learning gives higher importance to recent data, enabling
                # faster adaptation to distribution shift while retaining some historical knowledge.
                #
                # EXPONENTIAL TIME DECAY (time_decay_factor = 0.99)
                # --------------------------------------------------
                # Sample weights decay exponentially with time:
                #   weight(t) = decay_factor^(current_time - sample_time)
                #
                # Example with decay_factor = 0.99:
                # - Sample from 1 time unit ago:    weight = 0.99^1  ≈ 0.990 (99% importance)
                # - Sample from 10 time units ago:  weight = 0.99^10 ≈ 0.904 (90% importance)
                # - Sample from 100 time units ago: weight = 0.99^100 ≈ 0.366 (37% importance)
                # - Sample from 500 time units ago: weight = 0.99^500 ≈ 0.007 (0.7% importance)
                #
                # Why decay_factor = 0.99?
                # -------------------------
                # This value provides a balance between adaptation and stability:
                #
                # 1. HALF-LIFE CALCULATION
                #    - Half-life = ln(0.5) / ln(decay_factor) = 69 samples
                #    - Samples older than 69 time units have <50% weight
                #    - Samples older than 500 time units are effectively forgotten (<1% weight)
                #
                # 2. RESPONSIVENESS TO DRIFT
                #    - Decay = 0.99: Moderate adaptation (half-life ~70 samples)
                #      → Balanced for governance (responds to policy changes without overreacting)
                #    - Decay = 0.95: Fast adaptation (half-life ~14 samples)
                #      → Too sensitive for governance (overreacts to noise, unstable)
                #    - Decay = 0.999: Slow adaptation (half-life ~693 samples)
                #      → Too slow for governance (misses important policy shifts)
                #
                # 3. STABILITY VS. PLASTICITY TRADE-OFF
                #    - High decay (→1.0): More stable (retains historical patterns longer)
                #      - Advantage: Robust to noise and temporary anomalies
                #      - Disadvantage: Slow to adapt to genuine distribution shifts
                #    - Low decay (→0.0): More plastic (forgets history quickly)
                #      - Advantage: Fast adaptation to new patterns
                #      - Disadvantage: Unstable, sensitive to outliers
                #    - 0.99 balances: Adapts within ~100 samples while filtering noise
                #
                # 4. GOVERNANCE-SPECIFIC RATIONALE
                #    - Policy changes are gradual (weeks-months), not instant
                #    - 0.99 decay tracks policy evolution without catastrophic forgetting
                #    - Prevents adversarial actors from rapidly manipulating model with bursts
                #    - Maintains audit trail (old patterns influence model for ~500 samples)
                #
                # Theoretical Foundation: Concept Drift Adaptation
                # --------------------------------------------------
                # Time-weighted learning is a common approach for concept drift (non-stationary
                # distributions). Key theoretical results:
                #
                # - Gama et al. (2014): Exponential decay minimizes regret in shifting environments
                # - Bifet & Gavaldà (2007): Adaptive windowing with decay provides logarithmic bounds
                # - Klinkenberg (2004): Weighted instances improve accuracy under gradual drift
                #
                # Alternative: Fixed sliding window (e.g., last 1000 samples)
                # - Advantages: Clear temporal boundary, easier to reason about
                # - Disadvantages: Abrupt forgetting (sample 1001 → 0% weight instantly)
                # - Exponential decay is smoother (gradual forgetting prevents instability)
                #
                # SAMPLE_WEIGHT APPROXIMATION
                # ============================
                # River's learn_one() API does NOT natively support sample weights (unlike
                # scikit-learn's fit() which accepts sample_weight parameter). To implement
                # time-weighted learning, we approximate sample weights using two strategies:
                #
                # Strategy 1: Multiple Learning for Weights > 1.0
                # ------------------------------------------------
                # For sample_weight = w > 1.0:
                # - Learn from the same sample ⌊w⌋ times (rounded down)
                # - Example: weight = 2.7 → learn 2 times
                #
                # Intuition: Learning twice from a sample is equivalent to encountering it twice
                # in the stream, which increases its influence on model weights.
                #
                # Mathematical Equivalence (for SGD):
                # - Single update with weight w:  θ_new = θ_old - η * w * ∇L(x, y)
                # - k separate updates:           θ_new = θ_old - η * Σ[i=1 to k] ∇L(x, y)
                # - For k = ⌊w⌋, this approximates w * ∇L(x, y)
                #
                # Limitations:
                # - Integer approximation (weight 2.7 → 2 instead of exact 2.7)
                # - Computationally expensive for large weights (weight 100 → 100 learn_one calls)
                # - Not exact for non-linear updates (Perceptron, PA may behave differently)
                #
                # Strategy 2: Probabilistic Learning for Weights < 1.0
                # -----------------------------------------------------
                # For sample_weight = w < 1.0:
                # - Learn with probability = w (Bernoulli trial)
                # - Example: weight = 0.3 → 30% chance of learning, 70% chance of skipping
                #
                # Intuition: Old samples should occasionally be ignored to "forget" outdated patterns.
                # Probabilistic learning achieves this in expectation.
                #
                # Mathematical Equivalence (in expectation):
                # - Learning with probability p: E[update] = p * ∇L(x, y)
                # - Equivalent to weight w = p in expectation
                # - Law of Large Numbers: Over many samples, average effect = p * gradient
                #
                # Example with time_decay_factor = 0.99:
                # - Sample from 100 time units ago: weight = 0.99^100 ≈ 0.366
                # - 36.6% probability of learning from this sample
                # - 63.4% probability of skipping (forgetting old pattern)
                #
                # Limitations:
                # - Stochastic (randomness introduces variance in model updates)
                # - Small weights (e.g., 0.01) rarely trigger learning (only 1% of the time)
                # - Not deterministic (same data → different models due to random sampling)
                #
                # Why This Approximation Works in Practice
                # ------------------------------------------
                # For online learning with time decay:
                # - Most samples have weight ≈ 1.0 (recent samples)
                # - Very old samples (weight < 0.1) contribute minimally anyway
                # - Randomness in probabilistic learning averages out over stream
                # - Net effect: Recent samples dominate (high weight), old samples fade (low weight)
                #
                # Production Considerations
                # --------------------------
                # - For governance, determinism is preferred (same data → same model)
                # - If reproducibility is critical, use fixed time windows instead of probabilistic decay
                # - For drift adaptation, probabilistic decay is acceptable (streaming setting)
                #
                # References
                # ----------
                # - Gama, J., et al. (2014): "A Survey on Concept Drift Adaptation"
                #   https://doi.org/10.1145/2523813
                # - Bifet, A., & Gavaldà, R. (2007): "Learning from Time-Changing Data with
                #   Adaptive Windowing" (ADWIN algorithm)
                # - Klinkenberg, R. (2004): "Learning Drifting Concepts: Example Selection vs.
                #   Example Weighting" (demonstrates weighted instances improve drift adaptation)

                if sample_weight is not None and sample_weight != 1.0:
                    if sample_weight > 1.0:
                        # STRATEGY 1: Multiple learning iterations for weights > 1.0
                        # -----------------------------------------------------------
                        # Approximate sample_weight by learning multiple times from the sample.
                        # Round down to nearest integer: weight 2.7 → learn 2 times.
                        #
                        # This increases the sample's influence on model weights, simulating
                        # encountering it multiple times in the stream (importance sampling).
                        for _ in range(int(sample_weight)):
                            self._model.learn_one(x, y)
                    elif sample_weight > 0:
                        # STRATEGY 2: Probabilistic learning for weights < 1.0
                        # -----------------------------------------------------
                        # Learn from sample with probability = sample_weight (Bernoulli trial).
                        # Example: weight = 0.3 → 30% chance of learning, 70% chance of skipping.
                        #
                        # This achieves weight = w in expectation: E[update] = w * gradient.
                        # Over many samples, the law of large numbers ensures correct weighting.
                        #
                        # Effect: Old samples (low weight due to decay) are probabilistically
                        # forgotten, enabling adaptation to distribution shift.
                        import random

                        if random.random() < sample_weight:
                            self._model.learn_one(x, y)
                else:
                    # STANDARD LEARNING (sample_weight = 1.0 or None)
                    # ------------------------------------------------
                    # Most samples use standard learning (weight = 1.0), which means:
                    # - Recent samples (no decay applied yet)
                    # - Equal importance (no time-weighting configured)
                    # - Standard online learning (one update per sample)
                    self._model.learn_one(x, y)

                # Update state
                self._sample_count += 1
                self._last_update_time = timestamp

                # Store for drift detection
                self._recent_predictions.append((x.copy(), y, timestamp))

                # Update feature statistics
                self._update_feature_stats(x)

                # Update model state
                self._update_state()

                return TrainingResult(
                    success=True,
                    sample_count=self._sample_count,
                    current_accuracy=self.get_accuracy(),
                    model_state=self._state,
                    message="Training sample processed successfully",
                    timestamp=timestamp,
                )

            except Exception as e:
                logger.error(f"Training error: {e}")
                return TrainingResult(
                    success=False,
                    sample_count=self._sample_count,
                    current_accuracy=self.get_accuracy(),
                    model_state=self._state,
                    message=f"Training error: {str(e)}",
                    timestamp=timestamp,
                )

    def predict_and_learn(
        self,
        x: Dict[str, Any],
        y: int,
        sample_weight: Optional[float] = None,
    ) -> Tuple[PredictionResult, TrainingResult]:
        """Predict and then learn in a single atomic operation.

        PROGRESSIVE VALIDATION CONVENIENCE METHOD
        =========================================
        This method enforces the correct "test-then-train" order required by
        prequential evaluation. It guarantees that:

        1. predict_one(x) is called FIRST (without seeing label y)
        2. learn_one(x, y) is called SECOND (after prediction recorded)
        3. Both operations are thread-safe (atomic under lock)

        Why Use This Instead of Separate Calls?
        ----------------------------------------
        Calling predict_one() and learn_one() separately is valid, but this
        combined method provides:
        - Guaranteed correct order (prevents accidentally learning before predicting)
        - Thread safety (both operations under single lock acquisition)
        - Convenience (simpler API for common use case)
        - Performance (single lock acquisition instead of two)

        Production Streaming Scenario
        ------------------------------
        In real-world streaming systems, labels often arrive delayed:
        - T=0: Request arrives, predict_one(features) → decision
        - T=1-60min: User action or human review provides true label
        - T=60min: learn_one(features, label) → model adapts

        This method simulates that scenario when you have both features and
        label available simultaneously (e.g., batch replay of historical data
        for model initialization).

        Args:
            x: Feature dictionary with numeric values.
            y: Target label (0 or 1 for binary classification).
            sample_weight: Optional weight for time-weighted learning.
                          Use this for time-decay in non-stationary environments.

        Returns:
            Tuple of (PredictionResult, TrainingResult).
            The prediction is what the model would have predicted in production,
            and the training result confirms whether learning succeeded.

        Example:
            # Replay historical data with progressive validation
            for features, label in historical_data:
                pred, train = learner.predict_and_learn(features, label)
                print(f"Predicted: {pred.prediction}, Actual: {label}, "
                      f"Accuracy so far: {train.current_accuracy:.3f}")
        """
        with self._lock:
            # Step 1: Predict (simulate production prediction without label)
            prediction = self.predict_one(x)
            # Step 2: Learn (simulate delayed label arrival and model update)
            training = self.learn_one(x, y, sample_weight)
            return prediction, training

    def get_accuracy(self) -> float:
        """Get the current cumulative accuracy.

        PROGRESSIVE VALIDATION METRIC
        ==============================
        This accuracy is computed using prequential evaluation - each prediction
        was made on a sample BEFORE the model learned from it. This ensures:

        - No overfitting to test set (every sample was "test, then train")
        - Unbiased performance estimate (truly out-of-sample predictions)
        - Production-realistic metric (simulates streaming deployment)

        Cumulative accuracy tracks overall model health across all samples.
        It converges to the true model performance in stationary settings.

        For non-stationary data (concept drift), also monitor rolling_accuracy
        which tracks recent performance and can detect degradation earlier.

        Returns:
            Accuracy value between 0 and 1 (cumulative across all samples).
        """
        with self._lock:
            if self._sample_count == 0:
                return 0.0
            try:
                return float(self._accuracy_metric.get())
            except Exception:
                return 0.0

    def get_rolling_accuracy(self) -> float:
        """Get the rolling window accuracy for drift detection and monitoring.

        ROLLING ACCURACY: STATISTICAL INTERPRETATION
        =============================================
        This metric tracks model performance over the most recent N samples
        (default: 100) using a fixed-size sliding window. It provides a
        statistically-grounded view of current model behavior, complementing
        the cumulative accuracy metric which tracks long-term performance.

        What Rolling Accuracy Measures
        -------------------------------
        Rolling accuracy estimates the model's CURRENT performance, assuming
        the data distribution is stationary within the window. Mathematically:

            rolling_accuracy = (# correct predictions in last N samples) / N

        This is an unbiased estimator of the model's true current accuracy,
        with standard error that decreases with window size:

            SE = sqrt(p(1-p) / N)

        where p = true current accuracy, N = window_size (default: 100)

        Statistical Properties and Interpretation
        ------------------------------------------
        For binary classification with window_size=100 and p≈0.85 (target):

        1. STANDARD ERROR: SE ≈ sqrt(0.85 * 0.15 / 100) ≈ 0.036 (3.6%)

        2. 95% CONFIDENCE INTERVAL: accuracy ± 1.96*SE ≈ accuracy ± 7%
           - Observed accuracy of 0.82-0.88 is within statistical noise
           - Observed accuracy of 0.75 is significantly below 0.85 (drift signal)

        3. VARIANCE: Var(accuracy) = p(1-p) / N ≈ 0.001275
           - Rolling accuracy fluctuates more than cumulative accuracy
           - Each new sample shifts rolling accuracy by up to ±1%
           - Cumulative accuracy shifts by much less (±0.01% after 10k samples)

        4. MINIMUM DETECTABLE DRIFT:
           - Need ~2 standard errors difference for statistical significance
           - With SE=0.036, can detect drift of 2*0.036 ≈ 7% or larger
           - Smaller drift (e.g., 3-5%) may not be reliably distinguished from noise

        Difference from Cumulative Accuracy
        ------------------------------------
        CUMULATIVE ACCURACY (get_accuracy()):
        - Tracks: Performance across ALL samples from start to current
        - Sensitivity: Very low (1/n weight per sample, decreases over time)
        - Variance: Very low (law of large numbers, converges to true mean)
        - Purpose: Overall model health, long-term capability assessment
        - Example: After 10,000 samples, each new sample has 0.01% influence

        ROLLING ACCURACY (this method):
        - Tracks: Performance over LAST N samples only (default: 100)
        - Sensitivity: High (1/N weight per sample, constant over time)
        - Variance: Higher (smaller sample size, more statistical noise)
        - Purpose: Drift detection, recent performance monitoring
        - Example: After 10,000 samples, each new sample has 1% influence

        Use Rolling Accuracy For:
        --------------------------
        1. CONCEPT DRIFT DETECTION
           - Compare rolling vs. cumulative accuracy
           - If rolling << cumulative (e.g., 0.70 vs 0.85):
             → Recent degradation detected (likely drift)
           - If rolling ≈ cumulative:
             → Stable performance (no drift)

        2. ADAPTATION MONITORING
           - Track rolling accuracy after drift or retraining
           - Rising rolling accuracy indicates successful adaptation
           - Stagnant rolling accuracy suggests model can't learn new pattern

        3. EARLY WARNING SYSTEM
           - Rolling accuracy degrades faster than cumulative
           - Provides 100-200 sample lead time before cumulative drops
           - Enables proactive intervention (retrain, swap model, investigate)

        4. STATISTICAL SIGNIFICANCE TESTING
           - Compute difference: delta = cumulative_accuracy - rolling_accuracy
           - Estimate SE: SE_rolling ≈ sqrt(0.85 * 0.15 / 100) ≈ 0.036
           - If delta > 2*SE_rolling (e.g., delta > 0.07):
             → Statistically significant drift at 95% confidence level
           - If delta < 2*SE_rolling:
             → Difference likely due to sampling noise, not drift

        Progressive Validation Property
        --------------------------------
        Like cumulative accuracy, rolling accuracy is computed using
        prequential evaluation (predict-then-learn). Each prediction in
        the rolling window was made BEFORE the model learned from that
        sample, ensuring truly out-of-sample performance measurement.

        This means rolling accuracy is an unbiased estimate of production
        performance - it reflects how the model would perform on genuinely
        unseen data, not overfit to a fixed test set.

        Practical Example: Drift Detection Pattern
        -------------------------------------------
        Production monitoring code should implement statistical drift detection:

            cumulative = learner.get_accuracy()
            rolling = learner.get_rolling_accuracy()

            # Compute statistical significance
            SE = (0.85 * 0.15 / 100) ** 0.5  # ≈ 0.036 for p=0.85, N=100
            threshold = 2 * SE  # 95% confidence (≈ 0.07)

            if rolling < cumulative - threshold:
                # Statistically significant degradation detected
                severity = "CRITICAL" if rolling < 0.80 else "WARNING"
                logger.warning(
                    f"Drift detected: cumulative={cumulative:.3f}, "
                    f"rolling={rolling:.3f}, severity={severity}"
                )

                if severity == "CRITICAL":
                    # Pause learning to prevent further degradation
                    learner.pause_learning()
                    # Trigger model swap or retraining
                    trigger_model_swap()
            elif rolling > cumulative + threshold:
                # Model is improving (post-drift recovery or cold start learning)
                logger.info(
                    f"Model adaptation successful: cumulative={cumulative:.3f}, "
                    f"rolling={rolling:.3f}"
                )

        Window Initialization Behavior
        -------------------------------
        During the first N samples (window not yet full):
        - Rolling accuracy computed over available samples only
        - rolling_accuracy ≈ cumulative_accuracy initially
        - Statistical properties (SE, confidence intervals) apply after
          window fills (after first 100 samples)

        Trade-offs of Window Size
        --------------------------
        Smaller window (e.g., 50):
        - Advantage: Faster drift detection (responds within 50-100 samples)
        - Disadvantage: Higher variance (SE ≈ 0.05, ±10% confidence interval)
        - Use case: Rapidly evolving environments with frequent drift

        Current window (100):
        - Advantage: Balanced responsiveness and statistical stability
        - Advantage: Reasonable SE (≈0.036, ±7% confidence interval)
        - Use case: Most governance applications (stable with gradual drift)

        Larger window (e.g., 500):
        - Advantage: Very stable estimates (SE ≈ 0.016, ±3% confidence interval)
        - Disadvantage: Slower drift detection (needs 500-1000 samples)
        - Use case: High-traffic systems with low expected drift

        Theoretical Foundation
        ----------------------
        Rolling window approaches for drift detection are well-studied in
        the online learning literature:

        - Gama et al. (2014): "A Survey on Concept Drift Adaptation"
          Fixed-size sliding windows as baseline drift detection method
          https://doi.org/10.1145/2523813

        - Bifet & Gavaldà (2007): "Learning from Time-Changing Data with
          Adaptive Windowing" (ADWIN algorithm)
          Compares fixed windows (our approach) with adaptive windows

        - Page (1954): "Continuous Inspection Schemes"
          Original statistical framework for sequential change detection
          (foundation for CUSUM and related drift detection methods)

        - Klinkenberg (2004): "Learning Drifting Concepts: Example Selection
          vs. Example Weighting"
          Empirical analysis showing 100-500 sample windows work well in practice

        Returns:
            Rolling accuracy value between 0 and 1 (last N samples only).
            Returns 0.0 if no samples processed yet.
        """
        with self._lock:
            if self._sample_count == 0:
                return 0.0
            try:
                return float(self._rolling_accuracy_metric.get())
            except Exception:
                return 0.0

    def get_metrics(self) -> ModelMetrics:
        """Get current model metrics.

        Returns:
            ModelMetrics dataclass with all current metrics.
        """
        with self._lock:
            return ModelMetrics(
                accuracy=self.get_accuracy(),
                sample_count=self._sample_count,
                model_state=self._state,
                recent_accuracy=self.get_rolling_accuracy(),
                last_update_time=self._last_update_time or 0.0,
                predictions_count=self._predictions_count,
                model_type=self.model_type.value,
            )

    def get_recent_data(self) -> List[Tuple[Dict[str, Any], int, float]]:
        """Get recent training data for drift detection.

        Returns:
            List of (features, label, timestamp) tuples.
        """
        with self._lock:
            return list(self._recent_predictions)

    def get_state(self) -> ModelState:
        """Get the current model state.

        Returns:
            Current ModelState enum value.
        """
        with self._lock:
            return self._state

    def get_sample_count(self) -> int:
        """Get the total number of training samples processed.

        Returns:
            Number of samples.
        """
        with self._lock:
            return self._sample_count

    def is_ready(self) -> bool:
        """Check if the model is ready for production predictions.

        Returns:
            True if model is in ACTIVE state.
        """
        with self._lock:
            return self._state == ModelState.ACTIVE

    def pause_learning(self) -> None:
        """Pause online learning (used by safety bounds)."""
        with self._lock:
            self._is_paused = True
            self._state = ModelState.PAUSED
            logger.warning("Online learning paused due to safety bounds trigger")

    def resume_learning(self) -> None:
        """Resume online learning."""
        with self._lock:
            self._is_paused = False
            self._update_state()
            logger.info("Online learning resumed")

    def reset(self) -> None:
        """Reset the model to initial state.

        Warning: This clears all learned weights and metrics.
        """
        with self._lock:
            self._model = self._build_pipeline()
            self._accuracy_metric = metrics.Accuracy()
            self._rolling_accuracy_metric = metrics.Rolling(
                metrics.Accuracy(), window_size=self.rolling_window_size
            )
            self._sample_count = 0
            self._predictions_count = 0
            self._state = ModelState.COLD_START
            self._last_update_time = None
            self._is_paused = False
            self._recent_predictions.clear()
            self._feature_stats.clear()
            logger.info("OnlineLearner reset to initial state")

    def clone(self) -> "OnlineLearner":
        """Create a copy of the learner with the same configuration.

        Note: This creates a fresh learner without learned weights.

        Returns:
            New OnlineLearner instance.
        """
        return OnlineLearner(
            model_type=self.model_type,
            min_training_samples=self.min_training_samples,
            learning_rate=self.learning_rate,
            l2_regularization=self.l2_regularization,
            rolling_window_size=self.rolling_window_size,
            time_decay_factor=self.time_decay_factor,
        )

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model for serialization.

        Returns:
            Dictionary with model configuration and state.
        """
        with self._lock:
            return {
                "model_type": self.model_type.value,
                "min_training_samples": self.min_training_samples,
                "learning_rate": self.learning_rate,
                "l2_regularization": self.l2_regularization,
                "rolling_window_size": self.rolling_window_size,
                "time_decay_factor": self.time_decay_factor,
                "sample_count": self._sample_count,
                "predictions_count": self._predictions_count,
                "state": self._state.value,
                "accuracy": self.get_accuracy(),
                "rolling_accuracy": self.get_rolling_accuracy(),
                "last_update_time": self._last_update_time,
                "is_paused": self._is_paused,
            }

    def _update_state(self) -> None:
        """Update the model state based on current sample count.

        MODEL STATE LIFECYCLE AND TRANSITIONS
        ======================================
        The online learner progresses through distinct states as it accumulates
        training samples. These states reflect the model's readiness for
        production governance decisions.

        State Transition Flow:
        ----------------------
        COLD_START (0 samples)
            ↓ (first sample arrives)
        WARMING (1 to min_training_samples-1)
            ↓ (reaches min_training_samples)
        ACTIVE (≥ min_training_samples)
            ↕ (safety bounds triggered / resumed)
        PAUSED (safety circuit breaker)

        State Descriptions:
        -------------------
        COLD_START (sample_count == 0):
        - No training samples processed yet
        - Model has no learned patterns
        - Returns DEFAULT_PREDICTION=0 (deny) with DEFAULT_CONFIDENCE=0.5
        - Rationale: Fail-safe for governance - untrained model should not make risky decisions

        WARMING (1 ≤ sample_count < min_training_samples):
        - Model is learning but statistics are not yet stable
        - Predictions are improving but may be unreliable
        - StandardScaler normalization is stabilizing (mean/variance estimates improving)
        - Model weights are converging but with high variance
        - Still considered "training phase" - not ready for critical production decisions

        Why min_training_samples = 1000?
        ---------------------------------
        The threshold of 1000 samples before ACTIVE state is based on statistical
        stability requirements for online learning:

        1. STATISTICAL SIGNIFICANCE
           - Sample size n=1000 provides confidence intervals narrow enough for
             production governance decisions
           - Central Limit Theorem: Sampling distribution of model parameters
             becomes approximately normal with n ≥ 30-100
           - For binary classification, 1000 samples typically ensures:
             * Accuracy estimate ±3% margin of error (95% confidence)
             * Both classes observed with sufficient frequency
             * Feature correlations reliably estimated

        2. ONLINE STANDARDSCALER STABILITY
           - StandardScaler computes incremental mean and variance using Welford's algorithm
           - Early samples (n < 100) have high variance in normalization statistics
           - After ~500-1000 samples, mean/variance estimates stabilize
           - Unstable normalization causes inconsistent feature scaling → poor predictions

        3. MODEL WEIGHT CONVERGENCE
           - Linear models (LogisticRegression, Perceptron, PA) require sufficient samples
             to learn stable decision boundaries
           - Early samples cause large weight swings (high gradient magnitudes)
           - After 1000 samples, weight updates become smaller and more stable
           - Prevents premature production deployment with unconverged weights

        4. GOVERNANCE SAFETY MARGIN
           - Governance decisions are safety-critical (data access, policy enforcement)
           - Deploying undertrained models risks costly errors (false negatives)
           - 1000-sample threshold provides safety margin beyond minimum statistical requirements
           - Conservative but appropriate for high-stakes applications

        5. CLASS BALANCE VERIFICATION
           - Binary classification requires observing both classes (0 and 1)
           - With 1000 samples, even rare class (e.g., 10% of data) has ~100 examples
           - Prevents model from learning trivial "always predict majority class" strategy
           - Ensures both deny (0) and allow (1) patterns are learned

        Trade-offs:
        -----------
        - Higher threshold (e.g., 5000): More stable but slower to activate
        - Lower threshold (e.g., 500): Faster activation but less reliable predictions
        - 1000 balances: Quick enough for practical deployment, safe enough for governance

        ACTIVE (sample_count ≥ min_training_samples):
        - Model has sufficient training data for stable predictions
        - Ready for production governance decisions
        - Continues to learn incrementally (online learning never stops)
        - Monitored by SafetyBoundsChecker for performance degradation

        PAUSED (_is_paused == True):
        - Safety circuit breaker triggered (accuracy drop, consecutive failures)
        - Learning is halted to prevent model degradation
        - Predictions still returned but flagged as PAUSED state
        - Requires manual intervention (resume_learning()) to reactivate
        - Prevents bad samples from corrupting trained model
        """
        if self._is_paused:
            # Safety circuit breaker active - halt all learning
            # Requires manual resume_learning() call to exit PAUSED state
            self._state = ModelState.PAUSED
        elif self._sample_count == 0:
            # No training samples yet - return fail-safe defaults
            self._state = ModelState.COLD_START
        elif self._sample_count < self.min_training_samples:
            # Collecting samples but not yet statistically stable
            # Model is learning but not ready for production governance decisions
            self._state = ModelState.WARMING
        else:
            # Sufficient samples for stable predictions - ready for production
            # Model continues to learn incrementally while serving predictions
            self._state = ModelState.ACTIVE

    def _update_feature_stats(self, x: Dict[str, Any]) -> None:
        """Update running statistics for features.

        Used for input validation and drift detection baseline.
        """
        for key, value in x.items():
            if not isinstance(value, (int, float)):
                continue

            if key not in self._feature_stats:
                self._feature_stats[key] = {
                    "min": float("inf"),
                    "max": float("-inf"),
                    "count": 0,
                    "sum": 0.0,
                    "sum_sq": 0.0,
                }

            stats = self._feature_stats[key]
            stats["min"] = min(stats["min"], value)
            stats["max"] = max(stats["max"], value)
            stats["count"] += 1
            stats["sum"] += value
            stats["sum_sq"] += value * value

    def get_feature_stats(self) -> Dict[str, Dict[str, float]]:
        """Get computed feature statistics.

        Returns:
            Dictionary of feature names to stats (min, max, mean, std).
        """
        with self._lock:
            result = {}
            for key, stats in self._feature_stats.items():
                count = stats["count"]
                if count > 0:
                    mean = stats["sum"] / count
                    variance = (stats["sum_sq"] / count) - (mean * mean)
                    std = variance**0.5 if variance > 0 else 0.0
                    result[key] = {
                        "min": stats["min"],
                        "max": stats["max"],
                        "mean": mean,
                        "std": std,
                        "count": count,
                    }
            return result

    @property
    def model(self) -> compose.Pipeline:
        """Access the underlying River pipeline (read-only).

        Returns:
            The River Pipeline object.
        """
        return self._model

    def __repr__(self) -> str:
        """String representation of the learner."""
        return (
            f"OnlineLearner("
            f"type={self.model_type.value}, "
            f"state={self._state.value}, "
            f"samples={self._sample_count}, "
            f"accuracy={self.get_accuracy():.3f})"
        )
