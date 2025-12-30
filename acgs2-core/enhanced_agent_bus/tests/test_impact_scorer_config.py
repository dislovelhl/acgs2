"""
ACGS-2 Enhanced Agent Bus - Impact Scorer Configuration Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for the configurable ImpactScorer.
"""

import importlib.util
import os
import sys

# Add enhanced_agent_bus directory to path for standalone execution
enhanced_agent_bus_dir = os.path.dirname(os.path.dirname(__file__))
if enhanced_agent_bus_dir not in sys.path:
    sys.path.insert(0, enhanced_agent_bus_dir)


def _load_module(name, path):
    """Load a module directly from path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Load base modules first
_models = _load_module(
    "_test_models_scorer_config", os.path.join(enhanced_agent_bus_dir, "models.py")
)


# Create a mock parent package for relative imports
class MockPackage:
    pass


mock_parent = MockPackage()
mock_parent.models = _models
mock_parent.AgentMessage = _models.AgentMessage
mock_parent.MessageType = _models.MessageType

# Patch sys.modules for both direct and relative imports
sys.modules["models"] = _models
sys.modules["enhanced_agent_bus"] = mock_parent
sys.modules["enhanced_agent_bus.models"] = _models

# Import from loaded models
Priority = _models.Priority

# Load impact scorer directly (bypass __init__.py)
delib_dir = os.path.join(enhanced_agent_bus_dir, "deliberation_layer")

_impact_scorer = _load_module(
    "_test_impact_scorer_module", os.path.join(delib_dir, "impact_scorer.py")
)

ImpactScorer = _impact_scorer.ImpactScorer
ScoringConfig = _impact_scorer.ScoringConfig


class TestImpactScorerConfig:
    """Tests for ImpactScorer configuration."""

    def test_default_config(self):
        """Test initialization with default configuration."""
        scorer = ImpactScorer()
        assert scorer.config.semantic_weight == 0.30
        assert scorer.config.permission_weight == 0.20

    def test_custom_config(self):
        """Test initialization with custom configuration."""
        config = ScoringConfig(
            semantic_weight=0.5,
            priority_weight=0.5,
            permission_weight=0.0,
            volume_weight=0.0,
            context_weight=0.0,
            drift_weight=0.0,
            type_weight=0.0,
        )
        scorer = ImpactScorer(config=config)

        assert scorer.config.semantic_weight == 0.5
        assert scorer.config.priority_weight == 0.5

        # Test score calculation with custom weights
        # Only priority should contribute (semantic is 0 if no text/model)
        # Priority HIGH = 0.7
        # Expected = (0.7 * 0.5) / 1.0 = 0.35
        content = {"priority": Priority.HIGH}
        score = scorer.calculate_impact_score(content)

        # Note: If drift/volume/permission/context are 0, they return minimal scores like 0.1 usually
        # Let's check the implementation details in impact_scorer.py
        # permission returns 0.1 if no tools
        # volume returns 0.1 default
        # context returns 0.2 default
        # drift returns 0.0 default
        # So we have small values for those components even if weights are 0, they shouldn't matter.

        # Let's verify the calculation manually
        # semantic (0) * 0.5 + perms (0.1) * 0 + vol (0.1) * 0 + context (0.2) * 0 + drift * 0 + priority (0.7) * 0.5 + type (0.2) * 0
        # = 0 + 0 + 0 + 0 + 0 + 0.35 + 0 = 0.35

        np_score = 0.35
        assert abs(score - np_score) < 0.01

    def test_priority_boost(self):
        """Test critical priority boost configuration."""
        config = ScoringConfig(
            priority_weight=0.1, critical_priority_boost=0.95  # Low weight  # High boost
        )
        scorer = ImpactScorer(config=config)

        content = {"priority": Priority.CRITICAL}
        score = scorer.calculate_impact_score(content)

        # Should be boosted to at least 0.95
        assert score >= 0.95

    def test_semantic_boost(self):
        """Test high semantic relevance boost."""
        # This requires mocking _get_embeddings or forcing a high semantic score
        # We can subclass for testing to override semantic score generation

        class MockSemanticScorer(ImpactScorer):
            def _get_embeddings(self, text):
                # Return same as keyword embedding to get 1.0 similarity
                return self._get_keyword_embeddings()

            def _get_keyword_embeddings(self):
                import numpy as np

                return np.array([[1.0] * 768])

        config = ScoringConfig(semantic_weight=0.1, high_semantic_boost=0.85)  # Low weight
        scorer = MockSemanticScorer(config=config)
        # Mock BERT enabled
        scorer._bert_enabled = True
        scorer.model_name = "mock"

        content = {"content": "critical keyword match"}
        score = scorer.calculate_impact_score(content)

        assert score >= 0.85
