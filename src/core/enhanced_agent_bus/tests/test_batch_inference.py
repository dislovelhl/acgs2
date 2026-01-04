"""
ACGS-2 Enhanced Agent Bus - Batch Inference Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive tests for batch inference, tokenization caching, ONNX session
lazy loading, and optimized inference paths in the impact_scorer.py module.
"""

import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Add enhanced_agent_bus directory to path
enhanced_agent_bus_dir = os.path.dirname(os.path.dirname(__file__))
if enhanced_agent_bus_dir not in sys.path:
    sys.path.insert(0, enhanced_agent_bus_dir)


class TestONNXAvailableFlag:
    """Tests for ONNX_AVAILABLE flag proper definition."""

    def test_onnx_available_flag_exists(self):
        """Test that ONNX_AVAILABLE flag is defined as a boolean."""
        from deliberation_layer.impact_scorer import ONNX_AVAILABLE

        assert isinstance(ONNX_AVAILABLE, bool)

    def test_transformers_available_flag_exists(self):
        """Test that TRANSFORMERS_AVAILABLE flag is defined as a boolean."""
        from deliberation_layer.impact_scorer import TRANSFORMERS_AVAILABLE

        assert isinstance(TRANSFORMERS_AVAILABLE, bool)

    def test_onnx_available_matches_import_state(self):
        """Test that ONNX_AVAILABLE reflects actual onnxruntime availability."""
        from deliberation_layer.impact_scorer import ONNX_AVAILABLE

        try:
            import onnxruntime
            assert ONNX_AVAILABLE is True, "ONNX_AVAILABLE should be True when onnxruntime is installed"
        except ImportError:
            assert ONNX_AVAILABLE is False, "ONNX_AVAILABLE should be False when onnxruntime is not installed"


class TestTokenizationCaching:
    """Tests for tokenization caching functionality."""

    @pytest.fixture
    def mock_tokenizer(self):
        """Create a mock tokenizer that tracks calls."""
        mock = MagicMock()
        mock.return_value = {
            "input_ids": MagicMock(),
            "attention_mask": MagicMock(),
        }
        return mock

    @pytest.fixture
    def mock_lru_cache(self):
        """Create a mock LRU cache for testing."""

        class MockLRUCache:
            def __init__(self, maxsize=100):
                self.maxsize = maxsize
                self._cache = {}

            def get(self, key):
                return self._cache.get(key)

            def set(self, key, value):
                if len(self._cache) >= self.maxsize:
                    # Remove oldest entry (simplified)
                    first_key = next(iter(self._cache))
                    del self._cache[first_key]
                self._cache[key] = value

            def clear(self):
                self._cache.clear()

        return MockLRUCache

    def test_tokenize_text_caches_result(self):
        """Test that _tokenize_text caches tokenized results."""
        from deliberation_layer.impact_scorer import ImpactScorer

        # Create scorer with mocked dependencies
        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=False)

        # Verify cache exists (may be None if LRUCache not available)
        assert hasattr(scorer, '_tokenization_cache')

    def test_tokenize_text_returns_none_without_tokenizer(self):
        """Test that _tokenize_text returns None when tokenizer not available."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=False)
            result = scorer._tokenize_text("test text")
            assert result is None

    def test_tokenize_batch_handles_empty_list(self):
        """Test that _tokenize_batch handles empty list correctly."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=False)
            result = scorer._tokenize_batch([])
            assert result is None

    def test_clear_tokenization_cache(self):
        """Test that clear_tokenization_cache works correctly."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=False)
            # Should not raise even if cache is None
            scorer.clear_tokenization_cache()


class TestClassLevelCaching:
    """Tests for class-level tokenizer and model caching (singleton pattern)."""

    def test_reset_class_cache_clears_tokenizer(self):
        """Test that reset_class_cache clears tokenizer instance."""
        from deliberation_layer.impact_scorer import ImpactScorer

        # Set a dummy value
        ImpactScorer._tokenizer_instance = MagicMock()
        ImpactScorer._model_instance = MagicMock()
        ImpactScorer._cached_model_name = "test-model"

        # Reset
        ImpactScorer.reset_class_cache()

        assert ImpactScorer._tokenizer_instance is None
        assert ImpactScorer._model_instance is None
        assert ImpactScorer._cached_model_name is None

    def test_reset_class_cache_clears_onnx_session(self):
        """Test that reset_class_cache clears ONNX session cache."""
        from deliberation_layer.impact_scorer import ImpactScorer

        # Set a dummy value
        ImpactScorer._onnx_session_instance = MagicMock()
        ImpactScorer._cached_onnx_path = "/path/to/model.onnx"

        # Reset
        ImpactScorer.reset_class_cache()

        assert ImpactScorer._onnx_session_instance is None
        assert ImpactScorer._cached_onnx_path is None

    def test_scorer_singleton_pattern_works(self):
        """Test that get_impact_scorer returns singleton."""
        from deliberation_layer.impact_scorer import get_impact_scorer, reset_impact_scorer

        # Reset first to ensure clean state
        reset_impact_scorer()

        scorer1 = get_impact_scorer()
        scorer2 = get_impact_scorer()

        assert scorer1 is scorer2

        # Cleanup
        reset_impact_scorer()


class TestONNXSessionLazyLoading:
    """Tests for ONNX session lazy loading functionality."""

    def test_session_is_none_at_init(self):
        """Test that ONNX session is None at initialization (lazy loading)."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=True)
            # Session should be None until first inference
            assert scorer.session is None

    def test_onnx_enabled_flag_depends_on_availability(self):
        """Test that _onnx_enabled depends on ONNX_AVAILABLE."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=True)

            # _onnx_enabled should be False if TRANSFORMERS_AVAILABLE is False
            # (it requires both ONNX_AVAILABLE and TRANSFORMERS_AVAILABLE)
            assert scorer._onnx_enabled is False

    def test_onnx_model_path_priority(self):
        """Test ONNX model path resolution priority."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            # Test with instance-level path
            scorer = ImpactScorer(
                use_onnx=True,
                onnx_model_path="/custom/path/model.onnx"
            )
            assert scorer._onnx_model_path == "/custom/path/model.onnx"

    def test_get_onnx_model_path_returns_none_for_missing_file(self):
        """Test that _get_onnx_model_path returns None for non-existent file."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=True, onnx_model_path="/nonexistent/path.onnx")
            # Should return None since file doesn't exist
            path = scorer._get_onnx_model_path()
            assert path is None or not Path(path).exists()

    def test_ensure_onnx_session_returns_none_when_disabled(self):
        """Test that _ensure_onnx_session returns None when ONNX is disabled."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=False)
            session = scorer._ensure_onnx_session()
            assert session is None

    def test_ensure_onnx_session_returns_none_when_not_available(self):
        """Test that _ensure_onnx_session returns None when ONNX not available."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.ONNX_AVAILABLE', False):
            with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
                scorer = ImpactScorer(use_onnx=True)
                session = scorer._ensure_onnx_session()
                assert session is None


class TestBatchScoreImpact:
    """Tests for batch_score_impact functionality."""

    @pytest.fixture
    def scorer(self):
        """Create a scorer with mocked dependencies."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=False)
        return scorer

    def test_batch_empty_list_returns_empty(self, scorer):
        """Test batch inference with empty list returns empty list."""
        result = scorer.batch_score_impact([])
        assert result == []

    def test_batch_single_message(self, scorer):
        """Test batch inference with a single message."""
        messages = [{"content": "critical security alert"}]
        result = scorer.batch_score_impact(messages)

        assert len(result) == 1
        assert 0.0 <= result[0] <= 1.0
        assert result[0] > 0.5  # High-impact keywords should produce high score

    def test_batch_multiple_messages(self, scorer):
        """Test batch inference with multiple messages."""
        messages = [
            {"content": "critical security breach detected"},
            {"content": "simple status update"},
            {"content": "governance policy violation"},
        ]
        results = scorer.batch_score_impact(messages)

        assert len(results) == 3
        assert all(0.0 <= score <= 1.0 for score in results)
        # First and third should score higher than second
        assert results[0] > results[1]
        assert results[2] > results[1]

    def test_batch_with_contexts(self, scorer):
        """Test batch inference with context information."""
        messages = [
            {"content": "test message 1"},
            {"content": "test message 2"},
        ]
        contexts = [
            {"priority": "critical"},
            {"priority": "low"},
        ]
        results = scorer.batch_score_impact(messages, contexts)

        assert len(results) == 2
        assert results[0] > results[1]  # Critical priority should score higher

    def test_batch_context_length_mismatch_raises(self, scorer):
        """Test that mismatched context length raises ValueError."""
        messages = [{"content": "test 1"}, {"content": "test 2"}]
        contexts = [{"priority": "high"}]  # Only one context for two messages

        with pytest.raises(ValueError) as excinfo:
            scorer.batch_score_impact(messages, contexts)

        assert "contexts length" in str(excinfo.value)
        assert "messages length" in str(excinfo.value)

    def test_batch_preserves_order(self, scorer):
        """Test that batch results maintain input order."""
        messages = [
            {"content": f"message {i} with {'critical' if i % 2 == 0 else 'normal'} content"}
            for i in range(10)
        ]
        results = scorer.batch_score_impact(messages)

        assert len(results) == 10
        # Even-indexed messages have "critical" keyword, should score higher
        for i in range(0, 10, 2):
            if i + 1 < 10:
                assert results[i] >= results[i + 1]

    def test_batch_with_empty_content(self, scorer):
        """Test batch inference handles empty content gracefully."""
        messages = [
            {"content": ""},
            {"content": "critical alert"},
            {"content": ""},
        ]
        results = scorer.batch_score_impact(messages)

        assert len(results) == 3
        assert all(0.0 <= score <= 1.0 for score in results)
        # Empty content should have low scores
        assert results[1] > results[0]
        assert results[1] > results[2]

    def test_batch_scores_bounded(self, scorer):
        """Test that all batch scores are between 0 and 1."""
        messages = [
            {"content": "critical emergency security breach violation danger risk threat attack"},
            {"content": "simple message"},
            {"content": ""},
            {"content": "governance policy compliance audit financial blockchain"},
        ]
        results = scorer.batch_score_impact(messages)

        assert all(0.0 <= score <= 1.0 for score in results)

    def test_batch_consistency_with_sequential(self, scorer):
        """Test that batch results match sequential scoring."""
        messages = [
            {"content": "critical security alert"},
            {"content": "normal status check"},
            {"content": "governance policy update"},
        ]

        # Batch scoring
        batch_results = scorer.batch_score_impact(messages)

        # Sequential scoring
        sequential_results = [
            scorer.calculate_impact_score(msg) for msg in messages
        ]

        # Results should be identical
        assert len(batch_results) == len(sequential_results)
        for batch_score, seq_score in zip(batch_results, sequential_results):
            assert abs(batch_score - seq_score) < 1e-6

    def test_batch_large_batch_performance(self, scorer):
        """Test batch inference with a large number of messages."""
        messages = [
            {"content": f"test message {i} with security alert" if i % 5 == 0 else f"normal message {i}"}
            for i in range(50)
        ]

        start_time = time.time()
        results = scorer.batch_score_impact(messages)
        elapsed_time = time.time() - start_time

        assert len(results) == 50
        assert all(0.0 <= score <= 1.0 for score in results)
        # Should complete in reasonable time (< 2 seconds as per spec)
        assert elapsed_time < 2.0, f"Batch processing took {elapsed_time:.2f}s, expected < 2.0s"


class TestBatchScoreSequentialFallback:
    """Tests for _batch_score_sequential fallback functionality."""

    @pytest.fixture
    def scorer(self):
        """Create a scorer with mocked dependencies."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=False)
        return scorer

    def test_sequential_fallback_works(self, scorer):
        """Test that sequential fallback produces valid scores."""
        messages = [
            {"content": "critical security alert"},
            {"content": "normal message"},
        ]
        contexts = [None, None]

        results = scorer._batch_score_sequential(messages, contexts)

        assert len(results) == 2
        assert all(0.0 <= score <= 1.0 for score in results)

    def test_sequential_fallback_with_contexts(self, scorer):
        """Test sequential fallback with context information."""
        messages = [
            {"content": "test message"},
        ]
        contexts = [
            {"priority": "critical", "message_type": "governance_request"},
        ]

        results = scorer._batch_score_sequential(messages, contexts)

        assert len(results) == 1
        assert results[0] >= 0.5  # Should be high due to critical priority


class TestAsyncBatchCalculateImpact:
    """Tests for async batch_calculate_impact wrapper."""

    @pytest.fixture
    def scorer(self):
        """Create a scorer with mocked dependencies."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=False)
        return scorer

    @pytest.mark.asyncio
    async def test_async_batch_returns_scores(self, scorer):
        """Test that async batch_calculate_impact returns valid scores."""
        messages = [
            {"content": "critical security alert"},
            {"content": "normal message"},
        ]

        results = await scorer.batch_calculate_impact(messages)

        assert len(results) == 2
        assert all(0.0 <= score <= 1.0 for score in results)


class TestEdgeCases:
    """Tests for edge cases in optimized inference paths."""

    @pytest.fixture
    def scorer(self):
        """Create a scorer with mocked dependencies."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=False)
        return scorer

    def test_none_message_returns_base_score(self, scorer):
        """Test that None message returns base score."""
        score = scorer.calculate_impact_score(None)
        assert 0.0 <= score <= 1.0

    def test_empty_dict_message(self, scorer):
        """Test scoring of empty dict message."""
        score = scorer.calculate_impact_score({})
        assert 0.0 <= score <= 1.0

    def test_very_long_content(self, scorer):
        """Test scoring of very long content (edge case for truncation)."""
        long_content = "critical security " * 1000  # Very long content
        message = {"content": long_content}
        score = scorer.calculate_impact_score(message)

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should still detect high-impact keywords

    def test_special_characters_in_content(self, scorer):
        """Test scoring of content with special characters."""
        message = {"content": "critical! security@#$%^&*() breach!!!"}
        score = scorer.calculate_impact_score(message)

        assert 0.0 <= score <= 1.0
        assert score > 0.3  # Should still detect keywords

    def test_unicode_content(self, scorer):
        """Test scoring of content with unicode characters."""
        message = {"content": "critical security alert with unicode: \u4e2d\u6587 \u65e5\u672c\u8a9e"}
        score = scorer.calculate_impact_score(message)

        assert 0.0 <= score <= 1.0

    def test_nested_payload_extraction(self, scorer):
        """Test text extraction from deeply nested payload."""
        message = {
            "content": "outer content",
            "payload": {
                "message": "critical security issue in nested payload",
            },
        }
        score = scorer.calculate_impact_score(message)

        assert 0.0 <= score <= 1.0
        assert score > 0.3  # Should detect "critical" and "security"

    def test_malformed_priority(self, scorer):
        """Test handling of malformed priority value."""
        message = {
            "content": "test message",
            "priority": {"invalid": "priority"},
        }
        # Should not crash
        score = scorer.calculate_impact_score(message)
        assert 0.0 <= score <= 1.0

    def test_malformed_message_type(self, scorer):
        """Test handling of malformed message_type value."""
        message = {
            "content": "test message",
            "message_type": 12345,  # Non-string type
        }
        # Should not crash
        score = scorer.calculate_impact_score(message)
        assert 0.0 <= score <= 1.0


class TestComputeCombinedScore:
    """Tests for _compute_combined_score helper method."""

    @pytest.fixture
    def scorer(self):
        """Create a scorer with mocked dependencies."""
        from deliberation_layer.impact_scorer import ImpactScorer

        with patch('deliberation_layer.impact_scorer.TRANSFORMERS_AVAILABLE', False):
            scorer = ImpactScorer(use_onnx=False)
        return scorer

    def test_combined_score_with_high_semantic(self, scorer):
        """Test combined score with high semantic score."""
        message = {"content": "critical security breach"}
        score = scorer._compute_combined_score(message, None, 0.9)

        assert score >= 0.8  # Should trigger high_semantic_boost

    def test_combined_score_with_critical_priority(self, scorer):
        """Test combined score with critical priority."""
        message = {"content": "test"}
        context = {"priority": "critical"}
        score = scorer._compute_combined_score(message, context, 0.1)

        assert score >= 0.8  # Should trigger critical_priority_boost

    def test_combined_score_uses_max_semantic(self, scorer):
        """Test that combined score uses max of semantic and keyword scores."""
        message = {"content": "critical security breach"}
        # Low embedding score but high keyword score from content
        score = scorer._compute_combined_score(message, None, 0.1)

        # Should use keyword score (from content) not low semantic score
        assert score > 0.3


class TestCosineSimillaryFallback:
    """Tests for cosine_similarity_fallback function."""

    def test_cosine_similarity_fallback_normal(self):
        """Test cosine similarity fallback with normal vectors."""
        from deliberation_layer.impact_scorer import cosine_similarity_fallback

        a = np.array([1.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        sim = cosine_similarity_fallback(a, b)

        assert abs(sim - 1.0) < 1e-6  # Identical vectors should have similarity 1.0

    def test_cosine_similarity_fallback_orthogonal(self):
        """Test cosine similarity fallback with orthogonal vectors."""
        from deliberation_layer.impact_scorer import cosine_similarity_fallback

        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        sim = cosine_similarity_fallback(a, b)

        assert abs(sim) < 1e-6  # Orthogonal vectors should have similarity 0.0

    def test_cosine_similarity_fallback_empty(self):
        """Test cosine similarity fallback with empty vectors."""
        from deliberation_layer.impact_scorer import cosine_similarity_fallback

        a = np.array([])
        b = np.array([1.0, 0.0])
        sim = cosine_similarity_fallback(a, b)

        assert sim == 0.0

    def test_cosine_similarity_fallback_zero_norm(self):
        """Test cosine similarity fallback with zero norm vector."""
        from deliberation_layer.impact_scorer import cosine_similarity_fallback

        a = np.array([0.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        sim = cosine_similarity_fallback(a, b)

        assert sim == 0.0


class TestGlobalFunctions:
    """Tests for global functions in impact_scorer module."""

    def test_reset_impact_scorer_clears_global(self):
        """Test that reset_impact_scorer clears global scorer."""
        from deliberation_layer.impact_scorer import (
            get_impact_scorer,
            reset_impact_scorer,
        )

        # Get a scorer first
        scorer = get_impact_scorer()
        assert scorer is not None

        # Reset
        reset_impact_scorer()

        # Get new scorer - should be different instance
        new_scorer = get_impact_scorer()

        # Note: Can't directly compare with old scorer since it's been reset
        # But we can verify we get a valid scorer
        assert new_scorer is not None

        # Cleanup
        reset_impact_scorer()

    def test_calculate_message_impact_convenience(self):
        """Test calculate_message_impact convenience function."""
        from deliberation_layer.impact_scorer import calculate_message_impact, reset_impact_scorer

        reset_impact_scorer()

        message = MagicMock()
        message.content = "critical security alert"

        score = calculate_message_impact(message)

        assert 0.0 <= score <= 1.0

        reset_impact_scorer()

    def test_helper_functions_return_dicts(self):
        """Test that helper functions return empty dicts."""
        from deliberation_layer.impact_scorer import (
            get_gpu_decision_matrix,
            get_profiling_report,
            get_reasoning_matrix,
            get_risk_profile,
            get_vector_space_metrics,
        )

        assert get_gpu_decision_matrix() == {}
        assert get_reasoning_matrix() == {}
        assert get_risk_profile() == {}
        assert get_profiling_report() == {}
        assert get_vector_space_metrics() == {}


class TestScoringConfig:
    """Tests for ScoringConfig dataclass."""

    def test_default_config_values(self):
        """Test that ScoringConfig has correct default values."""
        from deliberation_layer.impact_scorer import ScoringConfig

        config = ScoringConfig()

        assert config.semantic_weight == 0.3
        assert config.permission_weight == 0.2
        assert config.volume_weight == 0.1
        assert config.context_weight == 0.1
        assert config.drift_weight == 0.1
        assert config.priority_weight == 0.1
        assert config.type_weight == 0.1
        assert config.critical_priority_boost == 0.9
        assert config.high_semantic_boost == 0.8

    def test_custom_config_values(self):
        """Test ScoringConfig with custom values."""
        from deliberation_layer.impact_scorer import ScoringConfig

        config = ScoringConfig(
            semantic_weight=0.5,
            critical_priority_boost=0.95,
        )

        assert config.semantic_weight == 0.5
        assert config.critical_priority_boost == 0.95


class TestImpactAnalysis:
    """Tests for ImpactAnalysis dataclass."""

    def test_impact_analysis_creation(self):
        """Test ImpactAnalysis dataclass creation."""
        from deliberation_layer.impact_scorer import ImpactAnalysis

        analysis = ImpactAnalysis(
            score=0.75,
            factors={"semantic": 0.8, "priority": 0.7},
            recommendation="escalate",
            requires_deliberation=True,
        )

        assert analysis.score == 0.75
        assert analysis.factors == {"semantic": 0.8, "priority": 0.7}
        assert analysis.recommendation == "escalate"
        assert analysis.requires_deliberation is True


# Entry point for running tests directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
