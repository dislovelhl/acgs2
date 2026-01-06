"""
Neural Pattern Training (NPT) Component

The NPT implements the learning feedback loop (Flow D) for continuous improvement:
- Aggregates training events from all system components
- Applies PII redaction and policy compliance filtering
- Curates datasets with provenance tracking
- Runs evaluation pipelines and regression tests
- Publishes updated patterns for system improvement

Key features:
- Training event aggregation and redaction
- Dataset curation with policy compliance
- Evaluation pipeline with reproducible results
- Pattern versioning and deployment
- Learning feedback loop integration
"""

import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core.interfaces import NeuralPatternTrainingInterface
from ..core.schemas import TrainingEvent

logger = logging.getLogger(__name__)


class NeuralPatternTraining(NeuralPatternTrainingInterface):
    """Neural Pattern Training - Learning feedback loop for continuous improvement."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._running = True

        # Training data storage
        self.training_events: List[TrainingEvent] = []
        self.redacted_datasets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Evaluation results
        self.evaluation_history: List[Dict[str, Any]] = []

        # Pattern versions
        self.pattern_versions: Dict[str, Dict[str, Any]] = {}

        # Statistics
        self.stats = {
            "total_events_received": 0,
            "events_redacted": 0,
            "datasets_curated": 0,
            "evaluations_run": 0,
            "patterns_published": 0,
        }

        logger.info("NPT initialized for learning feedback loop")

    @property
    def component_name(self) -> str:
        return "NPT"

    async def health_check(self) -> Dict[str, Any]:
        """Health check for NPT."""
        return {
            "component": self.component_name,
            "status": "healthy" if self._running else "unhealthy",
            "training_events": len(self.training_events),
            "datasets": len(self.redacted_datasets),
            "evaluations": len(self.evaluation_history),
            "pattern_versions": len(self.pattern_versions),
            "stats": self.stats,
        }

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("NPT shutting down")
        self._running = False

    async def receive_training_event(self, event: TrainingEvent) -> None:
        """
        Receive and process training event from system components.

        Applies PII redaction and policy compliance checks before storage.
        """
        if not self._running:
            return

        self.stats["total_events_received"] += 1

        # Apply PII redaction
        redacted_event = await self._redact_pii(event)

        # Check policy compliance
        if await self._check_policy_compliance(redacted_event):
            self.training_events.append(redacted_event)
            self.stats["events_redacted"] += 1

            # Auto-curate into datasets based on event type
            await self._auto_curate_event(redacted_event)

        else:
            logger.warning(f"Training event rejected due to policy violation: {event.event_type}")

    async def export_dataset(
        self, filters: Dict[str, Any], limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Export curated, redacted training dataset.

        Args:
            filters: Filters for dataset selection (component, event_type, time_range, etc.)
            limit: Maximum number of samples to return

        Returns:
            List of training samples with provenance
        """
        candidates = []

        # Apply filters
        for event in self.training_events:
            if self._matches_filters(event, filters):
                candidates.append(
                    {
                        "event_type": event.event_type,
                        "component": event.component,
                        "data": event.data,
                        "timestamp": event.timestamp,
                        "provenance": {
                            "redacted": event.redacted,
                            "policy_version": "v1.0.0",  # Would be dynamic
                            "retention_days": 90,
                        },
                    }
                )

        # Sort by timestamp (newest first) and apply limit
        candidates.sort(key=lambda x: x["timestamp"], reverse=True)
        return candidates[:limit]

    async def run_evaluation(
        self, dataset_filters: Dict[str, Any], evaluation_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run evaluation pipeline on curated dataset.

        Args:
            dataset_filters: Filters for selecting evaluation dataset
            evaluation_config: Evaluation configuration (metrics, baselines, etc.)

        Returns:
            Evaluation results with reproducibility info
        """
        if not self._running:
            return {"error": "NPT not running"}

        # Get evaluation dataset
        dataset = await self.export_dataset(
            dataset_filters, limit=evaluation_config.get("max_samples", 1000)
        )

        if not dataset:
            return {"error": "No data available for evaluation"}

        # Run evaluation (simplified - would integrate with actual ML evaluation)
        evaluation_result = await self._run_evaluation_pipeline(dataset, evaluation_config)

        # Store evaluation result
        eval_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset_filters": dataset_filters,
            "evaluation_config": evaluation_config,
            "results": evaluation_result,
            "dataset_size": len(dataset),
            "reproducibility_hash": self._compute_evaluation_hash(dataset, evaluation_config),
        }

        self.evaluation_history.append(eval_record)
        self.stats["evaluations_run"] += 1

        logger.info(f"Completed evaluation with {len(dataset)} samples")
        return evaluation_result

    async def publish_pattern_update(
        self, evaluation_results: Dict[str, Any], pattern_metadata: Dict[str, Any]
    ) -> str:
        """
        Publish updated patterns based on evaluation results.

        Args:
            evaluation_results: Results from evaluation pipeline
            pattern_metadata: Metadata about the pattern update

        Returns:
            Version ID of published patterns
        """
        if not self._running:
            return ""

        # Generate version ID
        version_id = f"pattern_v{len(self.pattern_versions) + 1}_{int(datetime.now(timezone.utc).timestamp())}"

        pattern_version = {
            "version_id": version_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "evaluation_results": evaluation_results,
            "metadata": pattern_metadata,
            "stats": {
                "training_events_used": self.stats["events_redacted"],
                "evaluations_completed": self.stats["evaluations_run"],
                "datasets_curated": self.stats["datasets_curated"],
            },
            "reproducibility_hash": self._compute_pattern_hash(
                evaluation_results, pattern_metadata
            ),
        }

        self.pattern_versions[version_id] = pattern_version
        self.stats["patterns_published"] += 1

        logger.info(f"Published pattern version: {version_id}")
        return version_id

    async def get_pattern_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve pattern version information.

        Args:
            version_id: Pattern version identifier

        Returns:
            Pattern version details or None if not found
        """
        return self.pattern_versions.get(version_id)

    async def list_pattern_versions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent pattern versions.

        Args:
            limit: Maximum number of versions to return

        Returns:
            List of pattern versions (newest first)
        """
        versions = list(self.pattern_versions.values())
        versions.sort(key=lambda x: x["timestamp"], reverse=True)
        return versions[:limit]

    async def _redact_pii(self, event: TrainingEvent) -> TrainingEvent:
        """
        Apply PII redaction to training event.

        Removes or anonymizes personally identifiable information.
        """
        redacted_data = event.data.copy()

        # PII patterns to redact
        pii_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{16}\b",  # Credit card
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{10}\b",  # Phone number
        ]

        # Simple redaction - replace with placeholders
        for pattern in pii_patterns:
            redacted_data = self._redact_pattern(redacted_data, pattern)

        return TrainingEvent(
            timestamp=event.timestamp,
            request_id=self._anonymize_id(event.request_id),
            component=event.component,
            event_type=event.event_type,
            data=redacted_data,
            redacted=True,
        )

    async def _check_policy_compliance(self, event: TrainingEvent) -> bool:
        """
        Check if training event complies with data usage policies.

        Ensures data is suitable for training and doesn't violate retention policies.
        """
        # Check event age (don't use very old data)
        event_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
        max_age_days = self.config.get("max_training_data_age_days", 90)
        age_days = (datetime.now(timezone.utc) - event_time).days

        if age_days > max_age_days:
            return False

        # Check for prohibited content
        prohibited_patterns = self.config.get("prohibited_training_patterns", [])
        data_str = json.dumps(event.data)

        for pattern in prohibited_patterns:
            import re

            if re.search(pattern, data_str, re.IGNORECASE):
                return False

        return True

    async def _auto_curate_event(self, event: TrainingEvent) -> None:
        """
        Automatically curate training event into appropriate datasets.
        """
        # Create dataset key based on event type and component
        dataset_key = f"{event.component}_{event.event_type}"

        curated_sample = {
            "timestamp": event.timestamp,
            "data": event.data,
            "provenance": {
                "component": event.component,
                "event_type": event.event_type,
                "redacted": event.redacted,
            },
        }

        self.redacted_datasets[dataset_key].append(curated_sample)

        # Maintain dataset size limits
        max_size = self.config.get("max_dataset_size", 10000)
        if len(self.redacted_datasets[dataset_key]) > max_size:
            # Keep most recent samples
            self.redacted_datasets[dataset_key] = self.redacted_datasets[dataset_key][-max_size:]

        self.stats["datasets_curated"] = len(self.redacted_datasets)

    async def _run_evaluation_pipeline(
        self, dataset: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run evaluation pipeline (simplified implementation).
        """
        # This would integrate with actual ML evaluation frameworks
        # For now, return mock results

        total_samples = len(dataset)
        event_types = set(sample["event_type"] for sample in dataset)

        # Mock evaluation metrics
        results = {
            "dataset_size": total_samples,
            "event_types_covered": list(event_types),
            "quality_score": 0.85,  # Mock quality metric
            "diversity_score": min(1.0, len(event_types) / 10),  # Mock diversity
            "contamination_rate": 0.02,  # Mock contamination check
            "recommendations": [
                "Increase dataset size for better generalization",
                "Add more diverse event types",
                "Verify PII redaction effectiveness",
            ]
            if total_samples < 1000
            else ["Dataset quality acceptable"],
        }

        return results

    def _matches_filters(self, event: TrainingEvent, filters: Dict[str, Any]) -> bool:
        """Check if event matches the given filters."""
        if "component" in filters and event.component != filters["component"]:
            return False

        if "event_type" in filters and event.event_type != filters["event_type"]:
            return False

        if "time_range" in filters:
            time_range = filters["time_range"]
            event_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))

            if "start" in time_range:
                start_time = datetime.fromisoformat(time_range["start"].replace("Z", "+00:00"))
                if event_time < start_time:
                    return False

            if "end" in time_range:
                end_time = datetime.fromisoformat(time_range["end"].replace("Z", "+00:00"))
                if event_time > end_time:
                    return False

        return True

    def _redact_pattern(self, data: Any, pattern: str) -> Any:
        """Recursively redact patterns in data structure."""
        import re

        if isinstance(data, str):
            return re.sub(pattern, "[REDACTED]", data)
        elif isinstance(data, dict):
            return {k: self._redact_pattern(v, pattern) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._redact_pattern(item, pattern) for item in data]
        else:
            return data

    def _anonymize_id(self, original_id: str) -> str:
        """Anonymize IDs for training data."""
        # Use hash of original ID for consistent anonymization
        return hashlib.sha256(original_id.encode()).hexdigest()[:16]

    def _compute_evaluation_hash(
        self, dataset: List[Dict[str, Any]], config: Dict[str, Any]
    ) -> str:
        """Compute hash for evaluation reproducibility."""
        combined = {
            "dataset_sample": dataset[:10],  # Sample first 10 items
            "config": config,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return hashlib.sha256(json.dumps(combined, sort_keys=True).encode()).hexdigest()

    def _compute_pattern_hash(
        self, evaluation_results: Dict[str, Any], metadata: Dict[str, Any]
    ) -> str:
        """Compute hash for pattern version reproducibility."""
        combined = {
            "evaluation_results": evaluation_results,
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return hashlib.sha256(json.dumps(combined, sort_keys=True).encode()).hexdigest()
