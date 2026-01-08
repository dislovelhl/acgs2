# Online Learner Theoretical Background

## Progressive Validation (Online Learning)

Unlike traditional machine learning, online learning implements a "predict first, then learn" paradigm, also known as prequential evaluation.

### Key Advantages

- **No upfront split**: Each sample is used for both testing and training.
- **Production simulation**: Predicts on sample $i$, then learns from it.
- **Unbiased evaluation**: No information leakage or overfitting to a fixed test set.

## Rolling Window Configuration

The `rolling_window_size` balances statistical significance with drift detection responsiveness.

- **Statistical Significance**: With $N=100$, the standard error for $p=0.85$ is $\approx 3.6\%$.
- **Drift Responsiveness**: Detects significant drift within 100-200 samples.
- **Governance Rationale**: Aligns with policy drift patterns which are typically gradual.

## Online Learning Algorithms

### Logistic Regression with SGD

Updates weights incrementally using Stochastic Gradient Descent.

- **Learning Rate**: Step size for weight updates.
- **L2 Regularization**: Prevents overfitting.

### Perceptron

Mistake-driven learning that updates weights only when a prediction is incorrect.

- **Mistake-Driven**: Conservative updates when correct.

### Passive-Aggressive Classifier

Balances stability and adaptability using margin-based updates.

- **Passive**: No update if margin is sufficient.
- **Aggressive**: Update if margin is violated.

## Time-Weighted Learning

Exponential time decay ($0.99$ factor) handles non-stationary distributions.

- **Half-life**: $\approx 69$ samples.
- **Forgetfulness**: Samples older than 500 units have $<1\%$ weight.

## Model State Lifecycle

The online learner progresses through distinct states as it accumulates training samples.

### State Transitions

1. **COLD_START** (0 samples): No learned patterns. Returns fail-safe defaults (deny).
2. **WARMING** (1 to min_training_samples-1): Collecting samples, normalization statistics stabilizing.
3. **ACTIVE** (≥ min_training_samples): Statistically stable, ready for production decisions.
4. **PAUSED**: Safety circuit breaker triggered. Learning halted to prevent corruption.

### Threshold Rationale (min_training_samples = 1000)

- **Statistical Significance**: $n=1000$ ensures narrow confidence intervals ($\pm 3\%$).
- **StandardScaler Stability**: Welford's algorithm requires sufficient samples for stable mean/variance estimates.
- **Convergence**: Weights stabilize after the initial period of high gradient noise.
- **Class Balance**: High probability of observing both positive and negative cases.

## Time-Weighted Learning Strategies

Since River's `learn_one` does not natively support sample weights for all models, we use two approximation strategies.

### Strategy 1: Multiple Learning (Weights > 1.0)

For $w > 1.0$, we learn from the sample $\lfloor w \rfloor$ times.

- **Intuition**: Equivalent to encountering the sample multiple times in the stream.
- **Mathematical Bound**: Approximates $w \cdot \nabla L(x, y)$ in SGD.

### Strategy 2: Probabilistic Learning (Weights < 1.0)

For $w < 1.0$, we learn from the sample with probability $w$.

- **Intuition**: Old samples are occasionally "forgotten" to adapt to drift.
- **Expectation**: $E[\text{update}] = w \cdot \nabla L(x, y)$.
