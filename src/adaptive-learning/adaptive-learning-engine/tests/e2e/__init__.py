# ACGS-2 Adaptive Learning Engine - End-to-End Tests
"""
End-to-End tests for complete Adaptive Learning Engine workflows.

Test Workflows Covered:
- Cold start scenario (no trained model)
- Online training with progressive validation
- Drift detection triggering
- Safety bounds enforcement
- Model rollback mechanism
- High load scenarios
- Complete ML lifecycle

Run with: poetry run pytest tests/e2e/ -v --tb=short

Constitutional Hash: cdd01ef066bc6cf2
"""
