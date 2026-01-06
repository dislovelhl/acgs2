import json
import random
import time
from pathlib import Path
from typing import Any, Dict

from ..crypto.ledger_helper import ExperimentLedger
from .metrics import GovernanceEvaluator


class RedTeamSimulator:
    """
    Simulates a red team attack or experiment execution.
    Executes tasks against a (mock) governance layer.
    """

    def __init__(self, experiment_id: str, task_template_path: str):
        self.experiment_id = experiment_id
        self.ledger = ExperimentLedger(experiment_id)
        with open(task_template_path, "r") as f:
            self.tasks = json.load(f)

    def mock_governance_layer(self, task: Dict[str, Any]) -> str:
        """
        Mock implementation of a governance policy engine.
        In a real scenario, this would call OPA or the ACGS Deliberation Layer.
        """
        # Logic to match baseline Rego policy
        prompt = task.get("prompt", "").lower()
        task_type = task.get("type")

        if task_type == "non-compliant":
            return "block"

        if "ignore all previous instructions" in prompt:
            return "block"

        if task_type == "boundary":
            # 50/50 chance of passing without justification in this mock
            return "allow" if random.random() > 0.5 else "deny"

        return "allow"

    def run_experiment(self, iterations: int = 1):
        # print(f"Starting Experiment: {self.experiment_id}")  # DEBUG_CLEANUP
        for _i in range(iterations):
            for task in self.tasks:
                start_time = time.time()

                # Mock high-performance processing delay (0.1ms to 5ms)
                time.sleep(random.uniform(0.0001, 0.005))

                action = self.mock_governance_layer(task)
                latency_ms = (time.time() - start_time) * 1000

                self.ledger.record_event(
                    task_id=task["id"], task_type=task["type"], action=action, latency_ms=latency_ms
                )

        # print(f"Experiment {self.experiment_id} completed.")  # DEBUG_CLEANUP
        return self.ledger


if __name__ == "__main__":
    # Ensure relative imports work if run as script
    # For now, assuming it's run from the governance-experiments directory
    repo_root = Path(__file__).parent.parent.parent
    task_path = repo_root / "data/tasks/templates.json"

    simulator = RedTeamSimulator("exp-baseline-001", str(task_path))
    ledger = simulator.run_experiment(iterations=10)

    # Export results
    export_path = repo_root / "reports/baseline_results.json"
    export_path.parent.mkdir(exist_ok=True)
    ledger.export_logs(str(export_path))

    # Calculate initial metrics
    with open(export_path, "r") as f:
        logs = json.load(f)
    evaluator = GovernanceEvaluator(logs)
    # print(evaluator.generate_summary())  # DEBUG_CLEANUP
