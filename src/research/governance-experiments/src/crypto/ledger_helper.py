import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class ExperimentAuditEntry:
    experiment_id: str
    task_id: str
    task_type: str
    action: str
    latency_ms: float
    timestamp: float
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        data = {
            "experiment_id": self.experiment_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "action": self.action,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


class ExperimentLedger:
    """
    Helper for recording experiment logs to the audit ledger.
    Supports local signing and verification logic.
    """

    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.entries: List[ExperimentAuditEntry] = []

    def record_event(self, task_id: str, task_type: str, action: str, latency_ms: float):
        entry = ExperimentAuditEntry(
            experiment_id=self.experiment_id,
            task_id=task_id,
            task_type=task_type,
            action=action,
            latency_ms=latency_ms,
            timestamp=time.time(),
        )
        self.entries.append(entry)
        return entry.hash

    def sign_ledger(self, private_key_mock: str = "mock_key") -> str:
        """
        Signs the entire entry list hash to create a checkpoint.
        In a real scenario, this would interface with the ACGS Identity Service.
        """
        ledger_hash = hashlib.sha256("".join([e.hash for e in self.entries]).encode()).hexdigest()
        signature = f"sig:{private_key_mock}:{ledger_hash}"
        return signature

    def export_logs(self, filepath: str):
        with open(filepath, "w") as f:
            json.dump([asdict(e) for e in self.entries], f, indent=2)

    @staticmethod
    def verify_integrity(logs: List[Dict[str, Any]], expected_signature: str) -> bool:
        """
        Verifies that logs haven't been tampered with since they were signed.
        """
        try:
            entries = [ExperimentAuditEntry(**log) for log in logs]
            ledger_hash = hashlib.sha256("".join([e.hash for e in entries]).encode()).hexdigest()
            # Simple mock signature check
            return expected_signature.endswith(ledger_hash)
        except Exception:
            return False


if __name__ == "__main__":
    ledger = ExperimentLedger("exp-001")
    ledger.record_event("t1", "compliant", "allow", 1.2)
    ledger.record_event("v1", "non-compliant", "block", 2.1)

    sig = ledger.sign_ledger()
    print(f"Ledger signed: {sig}")

    # Simulate export/import
    logs = [asdict(e) for e in ledger.entries]
    is_valid = ExperimentLedger.verify_integrity(logs, sig)
    print(f"Integrity check: {'PASSED' if is_valid else 'FAILED'}")
