# ML Safety Circuit Breaker: Design and Theory

## Overview

This document describes the circuit breaker pattern adapted from reliability engineering for machine learning safety. Circuit breakers prevent cascading failures by detecting problematic conditions and temporarily halting operations before they cause wider damage.

## Pattern Comparison

### Traditional Circuit Breaker (Software)

- Monitors for failures (errors, timeouts, resource exhaustion)
- Opens circuit after threshold to prevent cascading failures
- Allows system recovery before resuming operations
- Three states: CLOSED (normal), OPEN (failing), HALF-OPEN (testing recovery)

### ML Safety Circuit Breaker

- Monitors model accuracy and degradation
- Pauses learning after consecutive accuracy failures
- Prevents bad model updates from reaching production
- Four states: OK, WARNING, CRITICAL, PAUSED (see SafetyStatus enum)

## Why Circuit Breakers Are Critical for ML Safety

1. **Prevents Cascading Degradation**: A bad model update could corrupt future training, leading to progressive degradation. Circuit breaker halts learning before this cascade.
2. **Fail-Safe for Governance**: In access control/governance, a degraded model could grant improper permissions or deny legitimate access.
3. **Observable Failure States**: State transitions (OK → WARNING → CRITICAL → PAUSED) provide clear monitoring signals.
4. **Human-in-the-Loop**: Creating an opportunity for manual review before resuming operations.

## Failure Modes and Detection

The checker detects multiple failure modes to provide defense-in-depth:

1. **FAILED_ACCURACY**: Model accuracy below absolute threshold (default 85%).
2. **FAILED_DEGRADATION**: Significant accuracy drop from previous check (default 5%).
3. **FAILED_DRIFT**: Distribution drift beyond model capability (reserved for future integration).
4. **SKIPPED_COLD_START**: Safety check bypassed during model initialization (n < 100).

## State Machine and Transitions

The circuit breaker implements a state machine that escalates based on consecutive failures:

- **State: OK (CLOSED CIRCUIT)**

  - All safety checks passing.
  - Learning proceeds normally.
  - Consecutive failures: 0.

- **State: WARNING (DEGRADED)**

  - Some safety checks failing but below consecutive limit.
  - Learning continues but system is on alert.
  - Consecutive failures: 1 to (limit - 1).

- **State: CRITICAL → PAUSED (OPEN CIRCUIT)**
  - Too many consecutive failures detected.
  - Learning automatically paused.
  - Consecutive failures: ≥ limit (default 3).
  - Requires manual intervention (`force_resume`) to restart.

## Statistics and Thresholds

### Cold Start (n=100)

The threshold of 100 samples balances statistical significance with responsive safety validation.

- **SE (Standard Error)**: ±3.6% at n=100.
- **CLT (Central Limit Theorem)**: n=100 provides reliable normal approximation.

### Accuracy Threshold (85%)

- Represents a balance between security (FP) and productivity (FN).
- 85% ensures a maximum 15% combined error rate.

### Degradation Threshold (5%)

- Catches sudden crashes rather than gradual decay.
- Combined with the 3-strike rule, reduces false alarm probability to ~0.4%.
