import logging

import pytest

from src.core.governance.metrics.dfc import DFCCalculator, DFCComponents


def test_dfc_calculation_perfect():
    calculator = DFCCalculator()
    components = DFCComponents(
        democratic_participation=1.0,
        stakeholder_engagement=1.0,
        constitutional_evolution=1.0,
        transparency_ratio=1.0,
    )
    score = calculator.calculate(components)
    assert score == 1.0


def test_dfc_calculation_degraded(caplog):
    caplog.set_level(logging.WARNING)
    calculator = DFCCalculator(threshold=0.70)
    components = DFCComponents(
        democratic_participation=0.5,
        stakeholder_engagement=0.6,
        constitutional_evolution=0.5,
        transparency_ratio=0.8,
    )
    # Average: (0.5 + 0.6 + 0.5 + 0.8) / 4 = 2.4 / 4 = 0.6
    score = calculator.calculate(components)
    assert score == pytest.approx(0.6)
    assert "Possible normative divergence detected" in caplog.text


def test_dfc_calculation_healthy(caplog):
    caplog.set_level(logging.INFO)
    calculator = DFCCalculator(threshold=0.70)
    components = DFCComponents(
        democratic_participation=0.8,
        stakeholder_engagement=0.8,
        constitutional_evolution=0.8,
        transparency_ratio=0.8,
    )
    score = calculator.calculate(components)
    assert score == 0.8
    assert "DFC Diagnostic Check: PASSED" in caplog.text


def test_dfc_weight_sum():
    calculator = DFCCalculator()
    assert sum(calculator.weights.values()) == 1.0
