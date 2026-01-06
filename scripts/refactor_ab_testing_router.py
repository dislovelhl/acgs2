#!/usr/bin/env python3
"""
Refactor ABTestRouter Script

Breaks down the monolithic ABTestRouter class (656 lines) into focused components:
- ABTestMetricsManager: Metrics collection and analysis
- ABTestModelManager: Model loading and management
- ABTestRouter: Core routing logic (simplified)
"""

import re


def extract_class_section(file_path: str, class_name: str) -> str:
    """Extract the full ABTestRouter class definition."""
    with open(file_path, "r") as f:
        content = f.read()

    # Find class definition
    class_pattern = rf"(class {class_name}:.*?(?=\nclass|\n@|\n[a-zA-Z_#]|\Z))"
    match = re.search(class_pattern, content, re.DOTALL)

    if not match:
        raise ValueError(f"Could not find class {class_name}")

    return match.group(1).rstrip()


def create_metrics_manager() -> str:
    """Create the ABTestMetricsManager class."""

    return '''
class ABTestMetricsManager:
    """
    Manages A/B testing metrics collection, analysis, and reporting.

    Handles all metrics-related operations including outcome recording,
    statistical comparison, and traffic distribution analysis.
    """

    def __init__(self, split_ratio: float, min_samples: int, confidence_level: float):
        """Initialize metrics manager."""
        self.split_ratio = split_ratio
        self.min_samples = min_samples
        self.confidence_level = confidence_level

        # Metrics storage
        self.champion_metrics = CohortMetrics(
            cohort_type=CohortType.CHAMPION,
            total_requests=0,
            successful_predictions=0,
            total_latency_ms=0.0,
            outcomes=[]
        )

        self.candidate_metrics = CohortMetrics(
            cohort_type=CohortType.CANDIDATE,
            total_requests=0,
            successful_predictions=0,
            total_latency_ms=0.0,
            outcomes=[]
        )

    def record_outcome(self, cohort: CohortType, predicted: Any, actual: Any, latency_ms: float) -> None:
        """Record prediction outcome for metrics tracking."""
        metrics = self.champion_metrics if cohort == CohortType.CHAMPION else self.candidate_metrics

        metrics.total_requests += 1
        metrics.total_latency_ms += latency_ms

        is_correct = predicted == actual
        if is_correct:
            metrics.successful_predictions += 1

        metrics.outcomes.append({
            'predicted': predicted,
            'actual': actual,
            'correct': is_correct,
            'latency_ms': latency_ms,
            'timestamp': datetime.now(timezone.utc)
        })

        # Keep only recent outcomes for memory efficiency
        if len(metrics.outcomes) > 10000:
            metrics.outcomes = metrics.outcomes[-5000:]

    def compare_metrics(self) -> MetricsComparison:
        """Compare champion and candidate metrics."""
        champion_accuracy = (
            self.champion_metrics.successful_predictions / self.champion_metrics.total_requests
            if self.champion_metrics.total_requests > 0 else 0.0
        )

        candidate_accuracy = (
            self.candidate_metrics.successful_predictions / self.candidate_metrics.total_requests
            if self.candidate_metrics.total_requests > 0 else 0.0
        )

        improvement = candidate_accuracy - champion_accuracy

        # Check if we have enough samples
        total_samples = self.champion_metrics.total_requests + self.candidate_metrics.total_requests
        has_min_samples = total_samples >= self.min_samples

        # Check significance (simplified statistical test)
        is_significant = self._check_significance(champion_accuracy, candidate_accuracy)

        candidate_better = improvement > 0 and is_significant and has_min_samples

        return MetricsComparison(
            champion_accuracy=champion_accuracy,
            candidate_accuracy=candidate_accuracy,
            improvement=improvement,
            champion_samples=self.champion_metrics.total_requests,
            candidate_samples=self.candidate_metrics.total_requests,
            is_significant=is_significant,
            has_min_samples=has_min_samples,
            candidate_is_better=candidate_better
        )

    def _check_significance(self, champion_acc: float, candidate_acc: float) -> bool:
        """Check if the difference between accuracies is statistically significant."""
        # Simplified significance test - in production, use proper statistical tests
        if self.champion_metrics.total_requests < 30 or self.candidate_metrics.total_requests < 30:
            return False

        # Simple z-test approximation
        p1, p2 = champion_acc, candidate_acc
        n1, n2 = self.champion_metrics.total_requests, self.candidate_metrics.total_requests

        if n1 == 0 or n2 == 0:
            return False

        p_combined = (p1 * n1 + p2 * n2) / (n1 + n2)
        se = ((p_combined * (1 - p_combined)) * (1/n1 + 1/n2)) ** 0.5

        if se == 0:
            return abs(p1 - p2) > 0.01  # Fallback for edge cases

        z_score = abs(p1 - p2) / se
        return z_score > 1.96  # 95% confidence level

    def get_champion_metrics(self) -> CohortMetrics:
        """Get champion cohort metrics."""
        return self.champion_metrics

    def get_candidate_metrics(self) -> CohortMetrics:
        """Get candidate cohort metrics."""
        return self.candidate_metrics

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        comparison = self.compare_metrics()

        return {
            'champion': {
                'accuracy': comparison.champion_accuracy,
                'samples': comparison.champion_samples,
                'avg_latency': (
                    self.champion_metrics.total_latency_ms / self.champion_metrics.total_requests
                    if self.champion_metrics.total_requests > 0 else 0
                )
            },
            'candidate': {
                'accuracy': comparison.candidate_accuracy,
                'samples': comparison.candidate_samples,
                'avg_latency': (
                    self.candidate_metrics.total_latency_ms / self.candidate_metrics.total_requests
                    if self.candidate_metrics.total_requests > 0 else 0
                )
            },
            'comparison': {
                'improvement': comparison.improvement,
                'is_significant': comparison.is_significant,
                'has_min_samples': comparison.has_min_samples,
                'candidate_better': comparison.candidate_is_better
            },
            'traffic_distribution': self.get_traffic_distribution()
        }

    def get_traffic_distribution(self, n_requests: int = 1000) -> Dict[str, Any]:
        """Calculate expected traffic distribution."""
        champion_count = 0
        candidate_count = 0

        # Simulate traffic distribution
        for i in range(n_requests):
            # Simple hash-based routing simulation
            hash_value = hash(f"request-{i}") % 100
            if hash_value < (self.split_ratio * 100):
                candidate_count += 1
            else:
                champion_count += 1

        return {
            'champion_requests': champion_count,
            'candidate_requests': candidate_count,
            'champion_percentage': (champion_count / n_requests) * 100,
            'candidate_percentage': (candidate_count / n_requests) * 100,
            'expected_split': self.split_ratio
        }

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.champion_metrics = CohortMetrics(
            cohort_type=CohortType.CHAMPION,
            total_requests=0,
            successful_predictions=0,
            total_latency_ms=0.0,
            outcomes=[]
        )

        self.candidate_metrics = CohortMetrics(
            cohort_type=CohortType.CANDIDATE,
            total_requests=0,
            successful_predictions=0,
            total_latency_ms=0.0,
            outcomes=[]
        )
'''


def create_model_manager() -> str:
    """Create the ABTestModelManager class."""

    return '''
class ABTestModelManager:
    """
    Manages model loading and versioning for A/B testing.

    Handles loading champion and candidate models from MLflow registry,
    tracks versions, and provides model access to the router.
    """

    def __init__(self, champion_alias: str, candidate_alias: str, model_registry_name: str):
        """Initialize model manager."""
        self.champion_alias = champion_alias
        self.candidate_alias = candidate_alias
        self.model_registry_name = model_registry_name

        self.champion_model = None
        self.candidate_model = None
        self.champion_version = None
        self.candidate_version = None
        self.models_loaded = False

    def load_models(self) -> bool:
        """Load champion and candidate models from registry."""
        try:
            import mlflow.sklearn
            from mlflow.tracking import MlflowClient

            client = MlflowClient()

            # Load champion model
            champion_mv = client.get_model_version_by_alias(self.model_registry_name, self.champion_alias)
            self.champion_model = mlflow.sklearn.load_model(f"models:/{self.model_registry_name}@{self.champion_alias}")
            self.champion_version = champion_mv.version

            # Load candidate model
            candidate_mv = client.get_model_version_by_alias(self.model_registry_name, self.candidate_alias)
            self.candidate_model = mlflow.sklearn.load_model(f"models:/{self.model_registry_name}@{self.candidate_alias}")
            self.candidate_version = candidate_mv.version

            self.models_loaded = True
            logger.info(f"Loaded champion v{self.champion_version} and candidate v{self.candidate_version}")
            return True

        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            self.models_loaded = False
            return False

    def set_champion_model(self, model: Any, version: Optional[int] = None) -> None:
        """Manually set champion model."""
        self.champion_model = model
        self.champion_version = version
        self.models_loaded = self.models_loaded or (self.candidate_model is not None)

    def set_candidate_model(self, model: Any, version: Optional[int] = None) -> None:
        """Manually set candidate model."""
        self.candidate_model = model
        self.candidate_version = version
        self.models_loaded = self.models_loaded or (self.champion_model is not None)

    def get_champion_model(self) -> Any:
        """Get champion model."""
        return self.champion_model

    def get_candidate_model(self) -> Any:
        """Get candidate model."""
        return self.candidate_model

    def is_ready(self) -> bool:
        """Check if both models are loaded."""
        return self.models_loaded and self.champion_model is not None and self.candidate_model is not None
'''


def create_refactored_router() -> str:
    """Create the refactored ABTestRouter class."""

    return '''
class ABTestRouter:
    """
    A/B testing router for comparing champion vs candidate models.

    Routes traffic between champion and candidate models using deterministic
    hashing of request_id for consistent user experience. Now uses composition
    with specialized managers for metrics and model handling.
    """

    def __init__(
        self,
        split_ratio: float = AB_TEST_SPLIT,
        champion_alias: str = CHAMPION_ALIAS,
        candidate_alias: str = CANDIDATE_ALIAS,
        min_samples: int = AB_TEST_MIN_SAMPLES,
        confidence_level: float = AB_TEST_CONFIDENCE_LEVEL,
        model_registry_name: str = MODEL_REGISTRY_NAME,
    ):
        """Initialize A/B test router."""
        self.split_ratio = split_ratio
        self.ab_test_active = True

        # Initialize managers
        self.metrics_manager = ABTestMetricsManager(split_ratio, min_samples, confidence_level)
        self.model_manager = ABTestModelManager(champion_alias, candidate_alias, model_registry_name)

        # Load models on initialization
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Ensure models are loaded and router is ready."""
        if not self.model_manager.is_ready():
            success = self.model_manager.load_models()
            if not success:
                logger.warning("Failed to load models from registry, A/B testing disabled")
                self.ab_test_active = False

    def route(self, request_id: str) -> RoutingResult:
        """Route request to champion or candidate based on hash."""
        if not self.ab_test_active or not self.model_manager.is_ready():
            return RoutingResult(
                cohort=CohortType.CHAMPION,
                request_id=request_id,
                routing_reason="ab_test_inactive_or_models_not_ready"
            )

        hash_value = self._compute_hash_value(request_id)
        cohort = CohortType.CANDIDATE if hash_value < self.split_ratio else CohortType.CHAMPION

        return RoutingResult(
            cohort=cohort,
            request_id=request_id,
            routing_reason="hash_based_routing"
        )

    def _compute_hash_value(self, request_id: str) -> float:
        """Compute hash value for deterministic routing."""
        hash_obj = hashlib.sha256(request_id.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        return (hash_int % 10000) / 10000.0  # Value between 0 and 1

    def predict(self, cohort: CohortType, features: Any) -> PredictionResult:
        """Make prediction using specified cohort's model."""
        start_time = time.time()

        try:
            if cohort == CohortType.CHAMPION:
                model = self.model_manager.get_champion_model()
            else:
                model = self.model_manager.get_candidate_model()

            if model is None:
                raise ValueError(f"Model for {cohort.value} not available")

            # Make prediction
            if hasattr(model, 'predict'):
                prediction = model.predict(features)
            else:
                # Assume it's a function
                prediction = model(features)

            latency_ms = (time.time() - start_time) * 1000

            return PredictionResult(
                prediction=prediction,
                cohort=cohort,
                latency_ms=latency_ms,
                success=True
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Prediction failed for {cohort.value}: {e}")

            return PredictionResult(
                prediction=None,
                cohort=cohort,
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )

    def route_and_predict(self, request_id: str, features: Any) -> PredictionResult:
        """Route request and make prediction in one call."""
        routing = self.route(request_id)
        return self.predict(routing.cohort, features)

    def record_outcome(self, request_id: str, predicted: Any, actual: Any, latency_ms: Optional[float] = None) -> None:
        """Record prediction outcome for metrics."""
        routing = self.route(request_id)
        if latency_ms is None:
            latency_ms = 0.0  # Could be improved to track actual latency
        self.metrics_manager.record_outcome(routing.cohort, predicted, actual, latency_ms)

    def compare_metrics(self) -> MetricsComparison:
        """Compare champion and candidate performance."""
        return self.metrics_manager.compare_metrics()

    def promote_candidate(self, force: bool = False) -> PromotionResult:
        """Promote candidate model to champion."""
        comparison = self.compare_metrics()

        if not force and not comparison.candidate_is_better:
            return PromotionResult(
                success=False,
                status=PromotionStatus.BLOCKED,
                message="Candidate not ready for promotion",
                comparison=comparison
            )

        try:
            # In a real implementation, this would update the registry aliases
            # For now, just swap the models in memory
            champion_model = self.model_manager.get_champion_model()
            champion_version = self.model_manager.champion_version

            self.model_manager.set_champion_model(
                self.model_manager.get_candidate_model(),
                self.model_manager.candidate_version
            )
            self.model_manager.set_candidate_model(champion_model, champion_version)

            # Reset metrics for new candidate
            self.metrics_manager.reset_metrics()

            return PromotionResult(
                success=True,
                status=PromotionStatus.PROMOTED,
                message="Candidate promoted to champion",
                comparison=comparison
            )

        except Exception as e:
            return PromotionResult(
                success=False,
                status=PromotionStatus.ERROR,
                message=f"Promotion failed: {e}",
                comparison=comparison
            )

    # Delegate other methods to managers
    def set_champion_model(self, model: Any, version: Optional[int] = None) -> None:
        """Set champion model."""
        self.model_manager.set_champion_model(model, version)

    def set_candidate_model(self, model: Any, version: Optional[int] = None) -> None:
        """Set candidate model."""
        self.model_manager.set_candidate_model(model, version)

    def set_ab_test_active(self, active: bool) -> None:
        """Enable or disable A/B testing."""
        self.ab_test_active = active

    def get_champion_metrics(self) -> CohortMetrics:
        """Get champion metrics."""
        return self.metrics_manager.get_champion_metrics()

    def get_candidate_metrics(self) -> CohortMetrics:
        """Get candidate metrics."""
        return self.metrics_manager.get_candidate_metrics()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return self.metrics_manager.get_metrics_summary()

    def get_traffic_distribution(self, n_requests: int = 1000) -> Dict[str, Any]:
        """Get traffic distribution."""
        return self.metrics_manager.get_traffic_distribution(n_requests)
'''


def create_refactored_file(original_content: str) -> str:
    """Create the refactored ab_testing.py file."""

    # Find where to insert the new classes (after the existing data classes)
    insert_point = original_content.find("class ABTestRouter:")

    if insert_point == -1:
        raise ValueError("Could not find ABTestRouter class")

    # Extract the prefix (imports, enums, data classes)
    prefix = original_content[:insert_point]

    # Create the new file content
    new_content = prefix
    new_content += create_metrics_manager()
    new_content += "\n\n"
    new_content += create_model_manager()
    new_content += "\n\n"
    new_content += create_refactored_router()

    # Add the utility functions at the end
    # Find the utility functions after the class
    class_end = original_content.find("\n\n# Export key classes", insert_point)
    if class_end == -1:
        class_end = len(original_content)

    suffix = original_content[class_end:]
    new_content += suffix

    return new_content


def main():
    """Main refactoring function."""

    source_file = "src/core/enhanced_agent_bus/ab_testing.py"

    print("🔄 Refactoring ABTestRouter class...")
    print(f"Source: {source_file} (ABTestRouter class: 656 lines)")

    # Read original file
    with open(source_file, "r") as f:
        original_content = f.read()

    # Create refactored content
    refactored_content = create_refactored_file(original_content)

    # Backup original
    backup_file = source_file + ".backup"
    with open(backup_file, "w") as f:
        f.write(original_content)

    # Write refactored version
    with open(source_file, "w") as f:
        f.write(refactored_content)

    print("✅ ABTestRouter refactored successfully!")
    print("📁 Created components:")
    print("   - ABTestMetricsManager (metrics handling)")
    print("   - ABTestModelManager (model management)")
    print("   - ABTestRouter (simplified routing logic)")
    print(f"📋 Backup saved to: {backup_file}")
    print("\nNext steps:")
    print("1. Run tests to ensure functionality preserved")
    print("2. Check complexity metrics improved")
    print("3. Archive backup after validation")


if __name__ == "__main__":
    main()
