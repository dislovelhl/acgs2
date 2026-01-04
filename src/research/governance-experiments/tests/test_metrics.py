from src.evaluators.metrics import GovernanceEvaluator


def test_metrics_calculation_basic():
    logs = [
        {"task_id": "c1", "task_type": "compliant", "action": "allow", "latency_ms": 10},
        {"task_id": "c2", "task_type": "compliant", "action": "block", "latency_ms": 10},  # FP
        {"task_id": "v1", "task_type": "non-compliant", "action": "block", "latency_ms": 20},
        {
            "task_id": "v2",
            "task_type": "non-compliant",
            "action": "allow",
            "latency_ms": 20,
        },  # Miss
    ]
    evaluator = GovernanceEvaluator(logs)
    metrics = evaluator.calculate_metrics()

    assert metrics["blocked_rate"] == 0.5  # 1 blocked out of 2 non-compliant
    assert metrics["fp_rate"] == 0.5  # 1 blocked out of 2 compliant
    assert metrics["audit_latency"]["p50"] == 15.0
    assert metrics["total_actions"] == 4


def test_metrics_empty_logs():
    evaluator = GovernanceEvaluator([])
    metrics = evaluator.calculate_metrics()

    assert metrics["blocked_rate"] == 0.0
    assert metrics["total_actions"] == 0


def test_metrics_all_compliant():
    logs = [
        {"task_id": "c1", "task_type": "compliant", "action": "allow", "latency_ms": 5},
        {"task_id": "c2", "task_type": "compliant", "action": "allow", "latency_ms": 5},
    ]
    evaluator = GovernanceEvaluator(logs)
    metrics = evaluator.calculate_metrics()

    assert metrics["blocked_rate"] == 0.0
    assert metrics["fp_rate"] == 0.0
    assert metrics["total_actions"] == 2


def test_metrics_all_violation_blocked():
    logs = [
        {"task_id": "v1", "task_type": "non-compliant", "action": "block", "latency_ms": 100},
        {"task_id": "v2", "task_type": "non-compliant", "action": "block", "latency_ms": 100},
    ]
    evaluator = GovernanceEvaluator(logs)
    metrics = evaluator.calculate_metrics()

    assert metrics["blocked_rate"] == 1.0
    assert metrics["fp_rate"] == 0.0
    assert metrics["total_actions"] == 2
