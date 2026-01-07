# Cache Drift Detection Report Results

## Overview

The DriftDetector.check_drift() method creates a new Evidently Report object and runs full statistical analysis on every call. The _to_dataframe method also performs DataFrame conversion repeatedly from the same deque data without caching.

## Rationale

Drift detection is called periodically (every 5 minutes by default) and involves expensive operations: DataFrame creation from deques, statistical test execution (K-S, PSI tests). In high-traffic scenarios targeting 10,000+ RPS, these computations add unnecessary CPU overhead when reference/current windows haven't changed significantly.

---
*This spec was created from ideation and is pending detailed specification.*
