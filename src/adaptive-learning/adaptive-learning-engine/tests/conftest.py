import pytest
from prometheus_client import CollectorRegistry
from src.monitoring.metrics import MetricsRegistry


@pytest.fixture
def metrics_registry():
    """Provide a fresh MetricsRegistry for tests."""
    registry = CollectorRegistry()
    return MetricsRegistry(registry=registry, prefix="test_adaptive")


@pytest.fixture
def reference_data():
    """Provide reference data for drift detection tests."""
    return [{"feature1": 0.5, "feature2": 1.0} for _ in range(100)]


@pytest.fixture
def similar_data():
    """Provide similar data for drift detection tests."""
    return [{"feature1": 0.51, "feature2": 1.01} for _ in range(50)]
