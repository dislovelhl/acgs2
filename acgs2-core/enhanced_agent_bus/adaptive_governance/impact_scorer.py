"""
ACGS-2 Impact Scorer
Constitutional Hash: cdd01ef066bc6cf2

Implements ML-based impact assessment for messages and actions with
hybrid rule-based and model-based risk scoring.

This module contains:
- ImpactScorer: Hybrid impact assessment system combining rule-based heuristics
  with ML models (IsolationForest) for risk prediction.

Key Features:
- Asynchronous feature extraction from messages
- Hybrid scoring: ML-based + rule-based fallback
- Confidence estimation for predictions
- MLflow integration for model versioning
- Adaptive model retraining based on feedback
"""
