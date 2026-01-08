# Safety Bounds Checker: Design & Rationale

## Circuit Breaker Pattern for ML Safety

The circuit breaker pattern is critical for maintaining the integrity and safety of online learning systems in governance contexts.

### Rationale

1. **Prevents Cascading Degradation**: A bad model update could corrupt future training, leading to progressive degradation. The circuit breaker halts learning before this cascade occurs.
2. **Fail-Safe for Governance**: In access control systems, a degraded model could grant improper permissions. The circuit breaker ensures the model maintains minimum quality standards.
3. **Audit Trail**: State transitions create observable events for compliance auditing.

## State Machine

- **OK (CLOSED CIRCUIT)**: Healthy operation, accuracy above threshold.
- **WARNING (DEGRADED CIRCUIT)**: Accuracy below threshold but within tolerance or temporary.
- **PAUSED (OPEN CIRCUIT)**: Consecutive failures limit reached. Learning is halted.
- **CRITICAL**: Circuit breaker tripped, requires manual intervention.

## Failure Mode Detection Strategy (Defense-in-Depth)

The checker uses multiple layers of validation to ensure robustness:

### 1. Cold Start Safety Bypass

**Why skip checks during cold start (n < 100)?**

- **Statistical Unreliability**: At low sample sizes, accuracy estimates have high variance ($SE = \sqrt{p(1-p)/n}$). For $n=10$, $SE \approx 11.3\%$.
- **False Alarm Risk**: Noise could trigger 3 consecutive failures purely by chance.
- **Coordination**: Allows the model to reach the "WARMING" phase where statistics stabilize.

### 2. Absolute Accuracy Threshold ($FAILED\_ACCURACY$)

- **Default**: 0.85 (85% accuracy).
- **Rationale**: Minimal acceptable quality for governance. Provides a safety floor regardless of past performance.
- **Trade-off**: Higher precision (minimize False Positives/Security Breaches) at the cost of Recall (False Negatives/Operational Friction).

### 3. Relative Degradation Detection ($FAILED\_DEGRADATION$)

- **Default**: 0.05 (5% drop).
- **Rationale**: Catches sudden regressions even if the model is still above the absolute threshold (e.g., 94% $\to$ 88%).
- **Benefit**: Prevents gradual "model rot" and detects unstable training batches early.

## Threshold Selection Rationale

- **min_samples_for_check = 100**: Balances responsiveness with statistical significance ($SE \approx 3.6\%$).
- **accuracy_threshold = 0.85**: Chosen for high-stakes governance where the cost of a false positive (unauthorized access) is much higher than a false negative (denial of service).
- **consecutive_failures_limit = 3**: Filters out transient noise while responding quickly to systematic issues.

## References

- Michael Nygard, "Release It! Design and Deploy Production-Ready Software" (2007)
- Martin Fowler, "CircuitBreaker" (2014)
- Sculley et al., "Hidden Technical Debt in Machine Learning Systems" (2015)
