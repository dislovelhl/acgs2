# Adaptive Learning Engine - Drift Detection Design

## Overview

Concept drift occurs when the statistical properties of the target variable, which the model is trying to predict, change over time in unforeseen ways. This causes predictions to become less accurate as time passes.

The ACGS-2 Drift Detector uses **Evidently AI** as its core engine for distribution comparison, augmented with custom thresholds and governance-specific heuristics.

## Statistical Foundations

### 1. Kolmogorov-Smirnov (K-S) Test

For numerical features, we use the K-S test to compare distributions.

- **Null Hypothesis ($H_0$):** Both samples come from the same distribution.
- **Alternative Hypothesis ($H_1$):** Samples come from different distributions.
- **Interpretation:**
  - $p$-value < 0.05: Reject $H_0$ (drift detected)
  - D-statistic ∈ [0, 1]: larger values indicate greater divergence

### 2. Population Stability Index (PSI)

Used for categorical or binned numerical features.
$$PSI = \sum (P_{curr} - P_{ref}) \times \ln(P_{curr} / P_{ref})$$

- **Interpretation:**
  - PSI < 0.1: No significant change
  - 0.1 ≤ PSI < 0.25: Moderate shift (warning)
  - PSI ≥ 0.25: Severe shift (critical)

### 3. Chi-Squared Test

Used for categorical features with low cardinality.
$$\chi^2 = \sum \frac{(O_i - E_i)^2}{E_i}$$
Where $O_i$ is observed counts and $E_i$ is expected counts.

## Architecture

### Component Breakdown

- **Reference Window:** A locked baseline distribution representing "normal" behavior.
- **Current Window:** A sliding window of recent observations to check for drift.
- **Drift Result:** Encapsulates the status (OK, WARNING, DRIFTED) and associated metrics.

### Detection Workflow

1. **Data Collection:** Accumulate feature-prediction pairs.
2. **Windowing:** Maintain current observations in a sliding window (default 500-1000 samples).
3. **Preset Evaluation:** Run Evidently `DataDriftPreset`.
4. **Goverance Thresholding:** Overlay PSI and p-value checks with custom sensitivity (default 0.2).
5. **Alerting:** Trigger callbacks if drift is detected.

## Configurable Sensitivity

| Sensitivity  | PSI Threshold | Reference Size | Current Size |
| ------------ | ------------- | -------------- | ------------ |
| High         | 0.10          | 1000           | 200          |
| Balanced     | 0.20          | 2000           | 500          |
| Conservative | 0.30          | 5000           | 1000         |

## Cache Management

Drift checks are computationally expensive. We cache results based on a hash of the current data window to avoid redundant evaluations if no new data has arrived.
