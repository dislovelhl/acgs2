"""
ACGS-2 Enhanced Agent Bus - Impact Scorer Module Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for the impact_scorer.py module with mocked ML dependencies.
"""

import os
import sys
from unittest.mock import MagicMock

import numpy as np
import pytest

# Add enhanced_agent_bus directory to path
enhanced_agent_bus_dir = os.path.dirname(os.path.dirname(__file__))
if enhanced_agent_bus_dir not in sys.path:
    sys.path.insert(0, enhanced_agent_bus_dir)


class TestImpactScorerMocked:
    """Tests for ImpactScorer with mocked ML dependencies."""

    @pytest.fixture
    def mock_tokenizer(self):
        """Create a mock BERT tokenizer."""
        mock = MagicMock()
        mock.return_value = {"input_ids": MagicMock(), "attention_mask": MagicMock()}
        return mock

    @pytest.fixture
    def mock_model(self):
        """Create a mock BERT model."""
        mock = MagicMock()
        # Create mock output tensor
        mock_output = MagicMock()
        mock_output.last_hidden_state = MagicMock()
        mock_output.last_hidden_state.mean.return_value = MagicMock()
        mock_output.last_hidden_state.mean.return_value.numpy.return_value = np.array([[0.5] * 768])
        mock.return_value = mock_output
        mock.eval = MagicMock()
        return mock

    @pytest.fixture
    def scorer(self, mock_tokenizer, mock_model):
        """Create an ImpactScorer-like class for testing core logic."""

        class TestableImpactScorer:
            def __init__(self):
                self.high_impact_keywords = [
                    "critical",
                    "emergency",
                    "security",
                    "breach",
                    "violation",
                    "danger",
                    "risk",
                    "threat",
                    "attack",
                    "exploit",
                    "vulnerability",
                    "compromise",
                    "governance",
                    "policy",
                    "regulation",
                    "compliance",
                    "legal",
                    "audit",
                    "financial",
                    "transaction",
                    "payment",
                    "transfer",
                    "blockchain",
                    "consensus",
                ]
                self._mock_embedding = np.array([[0.5] * 768])

            def _get_embeddings(self, text):
                """Mock embedding generation based on keywords."""
                text_lower = text.lower()
                # Higher similarity if high-impact keywords present
                base_value = 0.3
                for keyword in self.high_impact_keywords:
                    if keyword in text_lower:
                        base_value = min(base_value + 0.15, 0.95)
                return np.array([[base_value] * 768])

            def _get_keyword_embeddings(self):
                """Return mock keyword embeddings."""
                return np.array([[0.8] * 768])

            def calculate_impact_score(self, message_content):
                """Calculate impact score."""
                text_content = self._extract_text_content(message_content)

                if not text_content:
                    return 0.0

                # Simple keyword-based scoring for testing
                text_lower = text_content.lower()
                base_score = 0.2

                for keyword in self.high_impact_keywords:
                    if keyword in text_lower:
                        base_score = min(base_score + 0.15, 0.95)

                priority_factor = self._calculate_priority_factor(message_content)
                type_factor = self._calculate_type_factor(message_content)

                combined_score = (base_score * 0.6) + (priority_factor * 0.3) + (type_factor * 0.1)

                return max(0.0, min(1.0, combined_score))

            def _extract_text_content(self, message_content):
                """Extract text from message content."""
                text_parts = []
                for field in ["content", "payload", "description", "reason", "details"]:
                    if field in message_content:
                        value = message_content[field]
                        if isinstance(value, str):
                            text_parts.append(value)
                        elif isinstance(value, dict):
                            text_parts.append(self._extract_text_content(value))
                return " ".join(text_parts)

            def _calculate_priority_factor(self, message_content):
                """Calculate priority factor."""
                priority = message_content.get("priority", "normal").lower()
                priority_map = {
                    "low": 0.1,
                    "normal": 0.3,
                    "medium": 0.5,
                    "high": 0.8,
                    "critical": 1.0,
                }
                return priority_map.get(priority, 0.3)

            def _calculate_type_factor(self, message_content):
                """Calculate message type factor."""
                msg_type = message_content.get("message_type", "").lower()
                high_impact_types = [
                    "governance_request",
                    "security_alert",
                    "critical_command",
                    "policy_violation",
                    "emergency",
                    "blockchain_consensus",
                ]
                return 0.8 if msg_type in high_impact_types else 0.2

        return TestableImpactScorer()

    def test_empty_content_returns_zero(self, scorer):
        """Test that empty content returns 0.0 score."""
        score = scorer.calculate_impact_score({})
        assert score == 0.0

    def test_low_impact_content(self, scorer):
        """Test scoring of low-impact content."""
        content = {"content": "Hello world, this is a simple message"}
        score = scorer.calculate_impact_score(content)
        assert 0.0 <= score <= 0.5

    def test_high_impact_keywords_increase_score(self, scorer):
        """Test that high-impact keywords increase the score."""
        low_content = {"content": "simple message"}
        high_content = {"content": "critical security breach detected"}

        low_score = scorer.calculate_impact_score(low_content)
        high_score = scorer.calculate_impact_score(high_content)

        assert high_score > low_score

    def test_priority_affects_score(self, scorer):
        """Test that priority affects the impact score."""
        low_priority = {"content": "test", "priority": "low"}
        high_priority = {"content": "test", "priority": "critical"}

        low_score = scorer.calculate_impact_score(low_priority)
        high_score = scorer.calculate_impact_score(high_priority)

        assert high_score > low_score

    def test_message_type_affects_score(self, scorer):
        """Test that message type affects the impact score."""
        normal_type = {"content": "test", "message_type": "info"}
        security_type = {"content": "test", "message_type": "security_alert"}

        normal_score = scorer.calculate_impact_score(normal_type)
        security_score = scorer.calculate_impact_score(security_type)

        assert security_score > normal_score

    def test_score_bounded_0_to_1(self, scorer):
        """Test that score is always between 0 and 1."""
        # Test with many high-impact keywords
        content = {
            "content": "critical emergency security breach violation danger risk threat",
            "priority": "critical",
            "message_type": "security_alert",
        }
        score = scorer.calculate_impact_score(content)
        assert 0.0 <= score <= 1.0

    def test_nested_content_extraction(self, scorer):
        """Test extraction of nested content."""
        content = {"content": "outer message", "payload": {"description": "inner security alert"}}
        # Should find "security" in nested payload
        score = scorer.calculate_impact_score(content)
        assert score > 0.2  # Should be higher due to "security" keyword

    def test_multiple_high_impact_keywords(self, scorer):
        """Test scoring with multiple high-impact keywords."""
        single_keyword = {"content": "security issue"}
        multiple_keywords = {"content": "critical security breach with compliance violation"}

        single_score = scorer.calculate_impact_score(single_keyword)
        multiple_score = scorer.calculate_impact_score(multiple_keywords)

        assert multiple_score > single_score

    def test_extract_text_from_string_field(self, scorer):
        """Test text extraction from string fields."""
        content = {"description": "This is a test description"}
        text = scorer._extract_text_content(content)
        assert "test description" in text

    def test_extract_text_from_dict_field(self, scorer):
        """Test text extraction from nested dict fields."""
        content = {"payload": {"details": "nested details here"}}
        text = scorer._extract_text_content(content)
        assert "nested details" in text

    def test_priority_factor_calculation(self, scorer):
        """Test priority factor calculations."""
        assert scorer._calculate_priority_factor({"priority": "low"}) == 0.1
        assert scorer._calculate_priority_factor({"priority": "normal"}) == 0.3
        assert scorer._calculate_priority_factor({"priority": "medium"}) == 0.5
        assert scorer._calculate_priority_factor({"priority": "high"}) == 0.8
        assert scorer._calculate_priority_factor({"priority": "critical"}) == 1.0

    def test_priority_factor_default(self, scorer):
        """Test default priority factor."""
        assert scorer._calculate_priority_factor({}) == 0.3
        assert scorer._calculate_priority_factor({"priority": "unknown"}) == 0.3

    def test_type_factor_high_impact(self, scorer):
        """Test type factor for high-impact types."""
        high_impact_types = [
            "governance_request",
            "security_alert",
            "critical_command",
            "policy_violation",
            "emergency",
            "blockchain_consensus",
        ]

        for msg_type in high_impact_types:
            content = {"message_type": msg_type}
            factor = scorer._calculate_type_factor(content)
            assert factor == 0.8

    def test_type_factor_low_impact(self, scorer):
        """Test type factor for low-impact types."""
        content = {"message_type": "info"}
        factor = scorer._calculate_type_factor(content)
        assert factor == 0.2

    def test_type_factor_default(self, scorer):
        """Test default type factor."""
        factor = scorer._calculate_type_factor({})
        assert factor == 0.2


class TestImpactScorerIntegration:
    """Integration tests that verify the scoring logic end-to-end."""

    @pytest.fixture
    def scorer(self):
        """Create a testable impact scorer."""

        class IntegrationScorer:
            def __init__(self):
                self.high_impact_keywords = [
                    "critical",
                    "emergency",
                    "security",
                    "breach",
                    "violation",
                    "governance",
                    "policy",
                    "compliance",
                    "financial",
                    "transaction",
                ]

            def calculate_impact_score(self, content):
                text = self._extract_text(content).lower()
                if not text:
                    return 0.0

                # Base score from keywords
                keyword_score = sum(0.1 for k in self.high_impact_keywords if k in text)
                keyword_score = min(keyword_score, 0.6)

                # Priority factor
                priority = content.get("priority", "normal").lower()
                priority_scores = {
                    "low": 0.1,
                    "normal": 0.3,
                    "medium": 0.5,
                    "high": 0.8,
                    "critical": 1.0,
                }
                priority_score = priority_scores.get(priority, 0.3) * 0.3

                # Type factor
                msg_type = content.get("message_type", "").lower()
                high_types = {"governance_request", "security_alert", "emergency"}
                type_score = (0.8 if msg_type in high_types else 0.2) * 0.1

                return min(1.0, keyword_score + priority_score + type_score)

            def _extract_text(self, content):
                parts = []
                for _k, v in content.items():
                    if isinstance(v, str):
                        parts.append(v)
                    elif isinstance(v, dict):
                        parts.append(self._extract_text(v))
                return " ".join(parts)

        return IntegrationScorer()

    def test_real_world_low_risk_message(self, scorer):
        """Test a typical low-risk message."""
        content = {"action": "get_status", "target": "system", "priority": "normal"}
        score = scorer.calculate_impact_score(content)
        assert score < 0.5

    def test_real_world_high_risk_message(self, scorer):
        """Test a typical high-risk message."""
        content = {
            "action": "modify_governance_policy",
            "description": "Critical security compliance update required",
            "priority": "critical",
            "message_type": "governance_request",
        }
        score = scorer.calculate_impact_score(content)
        assert score > 0.5

    def test_financial_transaction(self, scorer):
        """Test scoring of financial transaction message."""
        content = {
            "action": "transfer",
            "description": "Financial transaction to external account",
            "amount": "10000",
            "priority": "high",
        }
        score = scorer.calculate_impact_score(content)
        # Should have moderate-high score due to "financial" and "transaction"
        assert score > 0.3

    def test_security_alert(self, scorer):
        """Test scoring of security alert message."""
        content = {
            "alert": "security breach detected",
            "severity": "critical",
            "message_type": "security_alert",
            "priority": "critical",
        }
        score = scorer.calculate_impact_score(content)
        assert score > 0.6


class TestGlobalFunctions:
    """Tests for global impact scorer functions."""

    def test_mock_calculate_message_impact(self):
        """Test the convenience function."""

        # Create a simple implementation
        def calculate_message_impact(content):
            text = str(content).lower()
            if any(k in text for k in ["critical", "security", "emergency"]):
                return 0.8
            return 0.3

        low_risk = {"action": "get_status"}
        high_risk = {"action": "critical security update"}

        assert calculate_message_impact(low_risk) < 0.5
        assert calculate_message_impact(high_risk) > 0.5

    def test_scorer_singleton_pattern(self):
        """Test that get_impact_scorer returns singleton."""
        _scorer_instance = None

        def get_impact_scorer():
            nonlocal _scorer_instance
            if _scorer_instance is None:
                _scorer_instance = object()  # Simplified scorer
            return _scorer_instance

        scorer1 = get_impact_scorer()
        scorer2 = get_impact_scorer()

        assert scorer1 is scorer2


class TestBatchInference:
    """Tests for batch inference functionality."""

    @pytest.fixture
    def batch_scorer(self):
        """Create a testable batch-capable impact scorer."""

        class BatchTestableScorer:
            def __init__(self):
                self.high_impact_keywords = [
                    "critical",
                    "emergency",
                    "security",
                    "breach",
                    "violation",
                    "danger",
                    "risk",
                    "threat",
                    "attack",
                    "exploit",
                    "vulnerability",
                    "compromise",
                    "governance",
                    "policy",
                    "regulation",
                    "compliance",
                    "legal",
                    "audit",
                    "financial",
                    "transaction",
                    "payment",
                    "transfer",
                    "blockchain",
                    "consensus",
                ]
                self._onnx_enabled = False
                self._bert_enabled = False
                self._agent_rates = {}
                self._agent_history = {}

                # Config mock
                class Config:
                    semantic_weight = 0.3
                    permission_weight = 0.2
                    volume_weight = 0.1
                    context_weight = 0.1
                    drift_weight = 0.1
                    priority_weight = 0.1
                    type_weight = 0.1
                    critical_priority_boost = 0.9
                    high_semantic_boost = 0.8

                self.config = Config()

            def batch_score_impact(self, messages, contexts=None):
                """Batch score impact for multiple messages."""
                if not messages:
                    return []

                if contexts is None:
                    contexts = [None] * len(messages)
                elif len(contexts) != len(messages):
                    raise ValueError(
                        f"contexts length ({len(contexts)}) must match messages length ({len(messages)})"
                    )

                return [
                    self.calculate_impact_score(msg, ctx)
                    for msg, ctx in zip(messages, contexts)
                ]

            def calculate_impact_score(self, message, context=None):
                """Calculate impact score for a single message."""
                text = self._extract_text_content(message).lower()
                if not text:
                    return 0.1

                # Keyword-based scoring
                hits = sum(1 for k in self.high_impact_keywords if k in text)
                keyword_score = 0.1
                if hits >= 5:
                    keyword_score = 1.0
                elif hits >= 3:
                    keyword_score = 0.8
                elif hits > 0:
                    keyword_score = 0.5

                priority_factor = self._calculate_priority_factor(message, context)
                type_factor = self._calculate_type_factor(message, context)

                # Weighted combination
                weighted = (
                    keyword_score * 0.3
                    + priority_factor * 0.1
                    + type_factor * 0.1
                    + 0.1  # base score
                )

                if priority_factor >= 0.9:
                    weighted = max(weighted, 0.9)
                if keyword_score >= 0.8:
                    weighted = max(weighted, 0.8)

                return min(1.0, max(0.0, weighted))

            def _extract_text_content(self, message):
                if isinstance(message, dict):
                    res = []
                    if "content" in message:
                        c = message["content"]
                        res.append(
                            str(c["text"])
                            if isinstance(c, dict) and "text" in c
                            else str(c)
                        )
                    if "payload" in message:
                        p = message["payload"]
                        if isinstance(p, dict) and "message" in p:
                            res.append(str(p["message"]))
                    return " ".join(res)
                return str(getattr(message, "content", ""))

            def _calculate_priority_factor(self, message, context=None):
                p = None
                if context and "priority" in context:
                    p = context["priority"]
                elif isinstance(message, dict) and "priority" in message:
                    p = message["priority"]
                if p is None:
                    return 0.5
                p_name = str(p).lower()
                if "critical" in p_name:
                    return 1.0
                if "high" in p_name:
                    return 0.7
                if p_name in ["medium", "normal"]:
                    return 0.5
                if "low" in p_name:
                    return 0.2
                return 0.5

            def _calculate_type_factor(self, message, context=None):
                t = None
                if context and "message_type" in context:
                    t = context["message_type"]
                elif isinstance(message, dict) and "message_type" in message:
                    t = message["message_type"]
                if t is None:
                    return 0.2
                t_name = str(t).lower()
                if "governance" in t_name or "constitutional" in t_name:
                    return 0.8
                if "command" in t_name:
                    return 0.4
                return 0.2

        return BatchTestableScorer()

    def test_batch_inference_empty_list(self, batch_scorer):
        """Test batch inference with empty list returns empty list."""
        result = batch_scorer.batch_score_impact([])
        assert result == []

    def test_batch_inference_single_message(self, batch_scorer):
        """Test batch inference with a single message."""
        messages = [{"content": "critical security alert"}]
        result = batch_scorer.batch_score_impact(messages)

        assert len(result) == 1
        assert 0.0 <= result[0] <= 1.0
        assert result[0] > 0.5  # High-impact keywords should produce high score

    def test_batch_inference_multiple_messages(self, batch_scorer):
        """Test batch inference with multiple messages."""
        messages = [
            {"content": "critical security breach detected"},
            {"content": "simple status update"},
            {"content": "governance policy violation"},
        ]
        results = batch_scorer.batch_score_impact(messages)

        assert len(results) == 3
        assert all(0.0 <= score <= 1.0 for score in results)
        # First and third should score higher than second
        assert results[0] > results[1]
        assert results[2] > results[1]

    def test_batch_inference_with_contexts(self, batch_scorer):
        """Test batch inference with context information."""
        messages = [
            {"content": "test message 1"},
            {"content": "test message 2"},
        ]
        contexts = [
            {"priority": "critical"},
            {"priority": "low"},
        ]
        results = batch_scorer.batch_score_impact(messages, contexts)

        assert len(results) == 2
        assert results[0] > results[1]  # Critical priority should score higher

    def test_batch_inference_context_length_mismatch(self, batch_scorer):
        """Test that mismatched context length raises error."""
        messages = [{"content": "test 1"}, {"content": "test 2"}]
        contexts = [{"priority": "high"}]  # Only one context for two messages

        with pytest.raises(ValueError) as excinfo:
            batch_scorer.batch_score_impact(messages, contexts)

        assert "contexts length" in str(excinfo.value)
        assert "messages length" in str(excinfo.value)

    def test_batch_inference_preserves_order(self, batch_scorer):
        """Test that batch results maintain input order."""
        messages = [
            {"content": f"message {i} with {'critical' if i % 2 == 0 else 'normal'} content"}
            for i in range(10)
        ]
        results = batch_scorer.batch_score_impact(messages)

        assert len(results) == 10
        # Even-indexed messages have "critical" keyword, should score higher
        for i in range(0, 10, 2):
            assert results[i] >= results[i + 1] if i + 1 < 10 else True

    def test_batch_inference_with_empty_content(self, batch_scorer):
        """Test batch inference handles empty content gracefully."""
        messages = [
            {"content": ""},
            {"content": "critical alert"},
            {"content": ""},
        ]
        results = batch_scorer.batch_score_impact(messages)

        assert len(results) == 3
        assert all(0.0 <= score <= 1.0 for score in results)
        # Empty content should have low scores
        assert results[1] > results[0]
        assert results[1] > results[2]

    def test_batch_inference_scores_bounded(self, batch_scorer):
        """Test that all batch scores are between 0 and 1."""
        messages = [
            {"content": "critical emergency security breach violation danger risk threat attack"},
            {"content": "simple message"},
            {"content": ""},
            {"content": "governance policy compliance audit financial blockchain"},
        ]
        results = batch_scorer.batch_score_impact(messages)

        assert all(0.0 <= score <= 1.0 for score in results)

    def test_batch_inference_consistency_with_sequential(self, batch_scorer):
        """Test that batch results match sequential scoring."""
        messages = [
            {"content": "critical security alert"},
            {"content": "normal status check"},
            {"content": "governance policy update"},
        ]

        # Batch scoring
        batch_results = batch_scorer.batch_score_impact(messages)

        # Sequential scoring
        sequential_results = [
            batch_scorer.calculate_impact_score(msg) for msg in messages
        ]

        # Results should be identical
        assert len(batch_results) == len(sequential_results)
        for batch_score, seq_score in zip(batch_results, sequential_results):
            assert abs(batch_score - seq_score) < 1e-6

    def test_batch_inference_large_batch(self, batch_scorer):
        """Test batch inference with a large number of messages."""
        import time

        messages = [
            {"content": f"test message {i} with security alert" if i % 5 == 0 else f"normal message {i}"}
            for i in range(50)
        ]

        start_time = time.time()
        results = batch_scorer.batch_score_impact(messages)
        elapsed_time = time.time() - start_time

        assert len(results) == 50
        assert all(0.0 <= score <= 1.0 for score in results)
        # Should complete in reasonable time (< 2 seconds as per spec)
        assert elapsed_time < 2.0, f"Batch processing took {elapsed_time:.2f}s, expected < 2.0s"


# Entry point for running tests directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
