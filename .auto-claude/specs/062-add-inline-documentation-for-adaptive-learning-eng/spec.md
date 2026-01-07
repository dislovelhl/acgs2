# Add inline documentation for adaptive learning engine algorithms

## Overview

The adaptive-learning-engine contains sophisticated ML algorithms (River online learning, Evidently drift detection, MLflow model registry) but many core algorithm files lack inline explanations. Files like drift_detector.py, online_learner.py, and bounds_checker.py implement complex safety-critical logic without explaining the mathematical foundations or decision rationale.

## Rationale

The adaptive learning engine is a core differentiator for ACGS-2, enabling 'ML-based adaptive governance' as stated in the README. Contributors and auditors need to understand the safety bounds checking, drift detection thresholds, and online learning approaches to verify correctness and contribute improvements. Current docstrings focus on API usage rather than algorithmic explanation.

---
*This spec was created from ideation and is pending detailed specification.*
