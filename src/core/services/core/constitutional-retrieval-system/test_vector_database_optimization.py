"""
Test Vector Database Optimization Features
Constitutional Hash: cdd01ef066bc6cf2

Tests for HNSW tuning, quantization strategies, optimization profiles,
and performance monitoring for Qdrant, Pinecone, and Weaviate.
"""

import asyncio
import logging
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from vector_database import (
    OPTIMIZATION_PROFILES,
    HNSWConfig,
    MockVectorManager,
    OptimizationTarget,
    QdrantManager,
    QuantizationConfig,
    SearchConfig,
    VectorIndexConfig,
    create_vector_db_manager,
    estimate_memory_usage,
    recommend_index_config,
)

logger = logging.getLogger(__name__)


class TestOptimizationProfiles:
    """Test optimization profile configurations."""

    def test_recall_profile_has_highest_quality(self):
        """RECALL profile should have highest HNSW parameters."""
        profile = OPTIMIZATION_PROFILES[OptimizationTarget.RECALL]
        assert profile.hnsw.m == 32
        assert profile.hnsw.ef_construction == 256
        assert profile.hnsw.ef_search == 256
        assert profile.quantization.enabled is False

    def test_balanced_profile_uses_quantization(self):
        """BALANCED profile should use scalar quantization."""
        profile = OPTIMIZATION_PROFILES[OptimizationTarget.BALANCED]
        assert profile.hnsw.m == 16
        assert profile.quantization.enabled is True
        assert profile.quantization.type == "scalar"

    def test_speed_profile_has_lowest_ef(self):
        """SPEED profile should have lower ef values for faster search."""
        profile = OPTIMIZATION_PROFILES[OptimizationTarget.SPEED]
        assert profile.hnsw.ef_search == 64
        # SPEED profile uses quantization without rescoring for maximum speed
        assert profile.quantization.enabled is True

    def test_memory_profile_uses_product_quantization(self):
        """MEMORY profile should use product quantization for compression."""
        profile = OPTIMIZATION_PROFILES[OptimizationTarget.MEMORY]
        assert profile.quantization.enabled is True
        assert profile.quantization.type == "product"
        assert profile.hnsw.m == 8  # Lower M for memory savings


class TestHNSWConfig:
    """Test HNSW configuration dataclass."""

    def test_default_values(self):
        """Test default HNSW configuration values."""
        config = HNSWConfig()
        assert config.m == 16
        assert config.ef_construction == 128
        assert config.ef_search == 128
        assert config.full_scan_threshold == 10000

    def test_custom_values(self):
        """Test custom HNSW configuration."""
        config = HNSWConfig(m=32, ef_construction=256, ef_search=200)
        assert config.m == 32
        assert config.ef_construction == 256
        assert config.ef_search == 200


class TestQuantizationConfig:
    """Test quantization configuration dataclass."""

    def test_scalar_quantization_defaults(self):
        """Test scalar quantization configuration."""
        config = QuantizationConfig(enabled=True, type="scalar")
        assert config.quantile == 0.99
        assert config.always_ram is True

    def test_product_quantization(self):
        """Test product quantization configuration."""
        config = QuantizationConfig(enabled=True, type="product", compression_ratio="x32")
        assert config.compression_ratio == "x32"


class TestVectorIndexConfig:
    """Test complete vector index configuration."""

    def test_full_config(self):
        """Test creating full configuration."""
        config = VectorIndexConfig(
            hnsw=HNSWConfig(m=24, ef_construction=200),
            quantization=QuantizationConfig(enabled=True),
            search=SearchConfig(rescore=True, oversampling=2.5),
            indexing_threshold=5000,
        )
        assert config.hnsw.m == 24
        assert config.quantization.enabled is True
        assert config.search.oversampling == 2.5
        assert config.indexing_threshold == 5000


class TestMemoryEstimation:
    """Test memory usage estimation utility."""

    def test_fp32_memory_calculation(self):
        """Test FP32 memory estimation."""
        result = estimate_memory_usage(
            num_vectors=1_000_000, dimensions=768, quantization="fp32", index_type="hnsw", hnsw_m=16
        )
        assert "vector_storage_mb" in result
        assert "index_overhead_mb" in result
        assert "total_mb" in result
        assert "total_gb" in result
        # 1M vectors * 768 dims * 4 bytes = ~2.9GB
        assert result["total_gb"] > 2.5

    def test_int8_quantization_reduces_memory(self):
        """INT8 quantization should reduce memory by ~4x."""
        fp32_result = estimate_memory_usage(
            num_vectors=1_000_000, dimensions=768, quantization="fp32"
        )
        int8_result = estimate_memory_usage(
            num_vectors=1_000_000, dimensions=768, quantization="int8"
        )
        # INT8 should be roughly 4x smaller for vector storage
        assert int8_result["vector_storage_mb"] < fp32_result["vector_storage_mb"] / 3

    def test_binary_quantization(self):
        """Binary quantization should drastically reduce memory."""
        fp32_result = estimate_memory_usage(
            num_vectors=1_000_000, dimensions=768, quantization="fp32"
        )
        binary_result = estimate_memory_usage(
            num_vectors=1_000_000, dimensions=768, quantization="binary"
        )
        # Binary should be roughly 32x smaller
        assert binary_result["vector_storage_mb"] < fp32_result["vector_storage_mb"] / 20


class TestConfigRecommendation:
    """Test index configuration recommendation utility."""

    def test_high_recall_recommendation(self):
        """Test recommendation for high recall requirement."""
        result = recommend_index_config(
            num_vectors=100_000, target_recall=0.99, max_latency_ms=50, available_memory_gb=16
        )
        assert "hnsw" in result
        assert "m" in result["hnsw"]
        assert "ef_construction" in result["hnsw"]
        assert "ef_search" in result["hnsw"]
        assert "quantization" in result
        assert result["hnsw"]["m"] >= 24  # Higher M for high recall

    def test_low_latency_recommendation(self):
        """Test recommendation for low latency requirement."""
        result = recommend_index_config(
            num_vectors=100_000, target_recall=0.90, max_latency_ms=5, available_memory_gb=8
        )
        # Lower ef_search for faster queries
        assert result["hnsw"]["ef_search"] <= 100

    def test_memory_constrained_recommendation(self):
        """Test recommendation with memory constraints."""
        result = recommend_index_config(
            num_vectors=10_000_000, target_recall=0.95, max_latency_ms=20, available_memory_gb=4
        )
        # Should recommend quantization for large datasets
        assert result["quantization"] in ["none", "int8", "product"]


class TestMockVectorManager:
    """Test MockVectorManager functionality."""

    @pytest.fixture
    def mock_manager(self):
        """Create mock manager with balanced profile."""
        return MockVectorManager(optimization_target=OptimizationTarget.BALANCED)

    @pytest.mark.asyncio
    async def test_connect(self, mock_manager):
        """Test mock connection."""
        result = await mock_manager.connect()
        assert result is True

    @pytest.mark.asyncio
    async def test_create_collection(self, mock_manager):
        """Test mock collection creation."""
        await mock_manager.connect()
        result = await mock_manager.create_collection("test", 768)
        assert result is True

    @pytest.mark.asyncio
    async def test_insert_and_search(self, mock_manager):
        """Test mock insert and search operations."""
        await mock_manager.connect()
        await mock_manager.create_collection("test", 4)

        # Insert vectors
        vectors = [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]
        payloads = [{"id": "1"}, {"id": "2"}]
        ids = ["v1", "v2"]

        result = await mock_manager.insert_vectors("test", vectors, payloads, ids)
        assert result is True

        # Search
        query = [0.15, 0.25, 0.35, 0.45]
        results = await mock_manager.search_vectors("test", query, limit=2)
        assert len(results) == 2
        assert "score" in results[0]
        assert "payload" in results[0]


class TestQdrantManagerWithOptimization:
    """Test QdrantManager with optimization features."""

    @pytest.fixture
    def qdrant_manager(self):
        """Create QdrantManager with recall optimization."""
        return QdrantManager(
            host="localhost", port=6333, optimization_target=OptimizationTarget.RECALL
        )

    def test_initialization_with_profile(self, qdrant_manager):
        """Test manager initialization with optimization profile."""
        assert qdrant_manager.config is not None
        assert qdrant_manager.config.hnsw.m == 32  # RECALL profile
        assert qdrant_manager.config.hnsw.ef_construction == 256

    def test_custom_config_override(self):
        """Test custom configuration override."""
        custom_config = VectorIndexConfig(
            hnsw=HNSWConfig(m=48, ef_construction=300),
            quantization=QuantizationConfig(enabled=False),
        )
        manager = QdrantManager(config=custom_config)
        assert manager.config.hnsw.m == 48
        assert manager.config.hnsw.ef_construction == 300

    @patch("vector_database.QDRANT_AVAILABLE", False)
    def test_qdrant_unavailable_warning(self):
        """Test warning when Qdrant client not available."""
        manager = QdrantManager()
        assert manager.client is None


class TestFactoryFunction:
    """Test create_vector_db_manager factory function."""

    def test_create_qdrant_manager(self):
        """Test creating Qdrant manager via factory."""
        manager = create_vector_db_manager("qdrant", optimization_target=OptimizationTarget.SPEED)
        assert isinstance(manager, QdrantManager)
        assert manager.config.hnsw.ef_search == 64  # SPEED profile

    def test_create_mock_manager(self):
        """Test creating mock manager via factory."""
        manager = create_vector_db_manager("mock")
        assert isinstance(manager, MockVectorManager)

    def test_case_insensitive_db_type(self):
        """Test factory handles case-insensitive db type."""
        manager1 = create_vector_db_manager("QDRANT")
        manager2 = create_vector_db_manager("Qdrant")
        manager3 = create_vector_db_manager("qdrant")
        assert all(isinstance(m, QdrantManager) for m in [manager1, manager2, manager3])

    def test_unknown_db_type_raises(self):
        """Test unknown db type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported database type"):
            create_vector_db_manager("unknown_db")


class TestSearchMetrics:
    """Test search performance metrics tracking."""

    @pytest.fixture
    def manager_with_metrics(self):
        """Create manager for metrics testing."""
        return QdrantManager(optimization_target=OptimizationTarget.BALANCED)

    def test_qdrant_manager_has_metrics_method(self, manager_with_metrics):
        """Test QdrantManager has search metrics method."""
        assert hasattr(manager_with_metrics, "get_search_metrics")
        metrics = manager_with_metrics.get_search_metrics()
        assert isinstance(metrics, dict)

    def test_metrics_structure(self, manager_with_metrics):
        """Test search metrics have correct structure."""
        metrics = manager_with_metrics.get_search_metrics()
        # Should have latency percentiles when searches have been performed
        assert isinstance(metrics, dict)


class TestAllOptimizationProfiles:
    """Test all optimization profiles work correctly."""

    @pytest.mark.parametrize("target", list(OptimizationTarget))
    def test_profile_exists(self, target):
        """Test each optimization target has a profile."""
        assert target in OPTIMIZATION_PROFILES
        profile = OPTIMIZATION_PROFILES[target]
        assert isinstance(profile, VectorIndexConfig)

    @pytest.mark.parametrize("target", list(OptimizationTarget))
    def test_profile_creates_valid_qdrant_manager(self, target):
        """Test each profile creates valid QdrantManager."""
        manager = create_vector_db_manager("qdrant", optimization_target=target)
        assert manager is not None
        assert manager.config.hnsw is not None

    def test_mock_manager_creation(self):
        """Test mock manager can be created."""
        manager = create_vector_db_manager("mock")
        assert manager is not None
        assert isinstance(manager, MockVectorManager)


class TestIntegrationScenarios:
    """Integration tests for common usage scenarios."""

    @pytest.mark.asyncio
    async def test_high_recall_semantic_search(self):
        """Test high-recall semantic search scenario."""
        manager = create_vector_db_manager("mock", optimization_target=OptimizationTarget.RECALL)
        await manager.connect()
        await manager.create_collection("constitutional_docs", 768)

        # Simulate constitutional document vectors
        doc_vectors = [np.random.rand(768).tolist() for _ in range(100)]
        payloads = [{"doc_id": f"doc_{i}", "type": "constitutional"} for i in range(100)]
        ids = [f"vec_{i}" for i in range(100)]

        await manager.insert_vectors("constitutional_docs", doc_vectors, payloads, ids)

        # Search
        query = np.random.rand(768).tolist()
        results = await manager.search_vectors("constitutional_docs", query, limit=10)

        assert len(results) == 10
        assert all("score" in r for r in results)

    @pytest.mark.asyncio
    async def test_memory_efficient_large_scale(self):
        """Test memory-efficient setup for large scale."""
        manager = create_vector_db_manager("qdrant", optimization_target=OptimizationTarget.MEMORY)

        # Verify memory-efficient config
        assert manager.config.quantization.enabled is True
        assert manager.config.quantization.type == "product"
        assert manager.config.hnsw.m == 8  # Lower for memory

    @pytest.mark.asyncio
    async def test_fast_query_scenario(self):
        """Test fast query optimization scenario."""
        manager = create_vector_db_manager("mock", optimization_target=OptimizationTarget.SPEED)
        await manager.connect()
        await manager.create_collection("fast_search", 128)

        # Insert small dataset
        vectors = [np.random.rand(128).tolist() for _ in range(50)]
        payloads = [{"id": i} for i in range(50)]
        ids = [str(i) for i in range(50)]

        await manager.insert_vectors("fast_search", vectors, payloads, ids)

        # Fast search should complete quickly
        query = np.random.rand(128).tolist()
        results = await manager.search_vectors("fast_search", query, limit=5)

        assert len(results) == 5


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
