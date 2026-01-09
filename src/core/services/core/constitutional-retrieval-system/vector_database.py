"""Constitutional Hash: cdd01ef066bc6cf2
Vector Database Manager for Constitutional Retrieval System

Supports Qdrant, Milvus, Pinecone, and Weaviate vector databases for storing
and retrieving constitutional documents and historical precedents.

Features:
- HNSW parameter tuning for recall/latency optimization
- Quantization support (scalar, product, binary)
- Performance monitoring and benchmarking
- Multiple optimization profiles (recall, balanced, speed, memory)
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.http.models import (
        CompressionRatio,
        Distance,
        HnswConfigDiff,
        OptimizersConfigDiff,
        ProductQuantization,
        ProductQuantizationConfig,
        QuantizationSearchParams,
        ScalarQuantization,
        ScalarQuantizationConfig,
        ScalarType,
        SearchParams,
        VectorParams,
    )

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections

    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False

try:
    from pinecone import Pinecone, PodSpec, ServerlessSpec

    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

try:
    import weaviate
    from weaviate.classes.config import Configure, Property
    from weaviate.classes.config import DataType as WeaviateDataType

    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# Optimization Profiles and Configuration Classes
# =============================================================================


class OptimizationTarget(Enum):
    """Optimization targets for different use cases."""

    RECALL = "recall"  # Maximum accuracy (99%+ recall)
    BALANCED = "balanced"  # Good recall + speed (95% recall)
    SPEED = "speed"  # Fast queries (90% recall)
    MEMORY = "memory"  # Minimum memory footprint


@dataclass
class HNSWConfig:
    """HNSW index configuration parameters."""

    m: int = 16  # Connections per node (8-64)
    ef_construction: int = 128  # Build quality (64-512)
    ef_search: int = 128  # Search quality (32-512)
    full_scan_threshold: int = 10000  # Switch to exact search below this


@dataclass
class QuantizationConfig:
    """Vector quantization configuration."""

    enabled: bool = False
    type: str = "scalar"  # "scalar", "product", "binary"
    quantile: float = 0.99  # For scalar quantization
    always_ram: bool = True  # Keep quantized vectors in RAM
    compression_ratio: str = "x16"  # For product quantization


@dataclass
class SearchConfig:
    """Search optimization configuration."""

    rescore: bool = True  # Re-rank with original vectors
    oversampling: float = 2.0  # Candidates multiplier for rescoring
    exact_threshold: int = 1000  # Use exact search below this


@dataclass
class VectorIndexConfig:
    """Complete vector index configuration."""

    hnsw: HNSWConfig = field(default_factory=HNSWConfig)
    quantization: QuantizationConfig = field(default_factory=QuantizationConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    distance_metric: str = "cosine"  # cosine, euclidean, dot

    # Optimizer settings
    indexing_threshold: int = 20000
    memmap_threshold: int = 50000


# Pre-configured optimization profiles
OPTIMIZATION_PROFILES: Dict[OptimizationTarget, VectorIndexConfig] = {
    OptimizationTarget.RECALL: VectorIndexConfig(
        hnsw=HNSWConfig(m=32, ef_construction=256, ef_search=256),
        quantization=QuantizationConfig(enabled=False),
        search=SearchConfig(rescore=True, oversampling=3.0),
        indexing_threshold=10000,
    ),
    OptimizationTarget.BALANCED: VectorIndexConfig(
        hnsw=HNSWConfig(m=16, ef_construction=128, ef_search=128),
        quantization=QuantizationConfig(enabled=True, type="scalar", quantile=0.99),
        search=SearchConfig(rescore=True, oversampling=2.0),
    ),
    OptimizationTarget.SPEED: VectorIndexConfig(
        hnsw=HNSWConfig(m=16, ef_construction=64, ef_search=64),
        quantization=QuantizationConfig(enabled=True, type="scalar", quantile=0.95),
        search=SearchConfig(rescore=False, oversampling=1.5),
    ),
    OptimizationTarget.MEMORY: VectorIndexConfig(
        hnsw=HNSWConfig(m=8, ef_construction=64, ef_search=64),
        quantization=QuantizationConfig(
            enabled=True, type="product", compression_ratio="x32", always_ram=False
        ),
        search=SearchConfig(rescore=True, oversampling=2.0),
        memmap_threshold=10000,
    ),
}


@dataclass
class SearchMetrics:
    """Performance metrics for vector search operations."""

    latency_ms: float
    recall: float = 0.0
    candidates_evaluated: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class VectorDatabaseManager(ABC):
    """Abstract base class for vector database operations."""

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the vector database."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the vector database."""
        pass

    @abstractmethod
    async def create_collection(self, collection_name: str, vector_dim: int) -> bool:
        """Create a new collection for vectors."""
        pass

    @abstractmethod
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> bool:
        """Insert vectors with payloads into collection."""
        pass

    @abstractmethod
    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        pass

    @abstractmethod
    async def delete_vectors(self, collection_name: str, ids: List[str]) -> bool:
        """Delete vectors by IDs."""
        pass

    @abstractmethod
    async def update_vectors(
        self,
        collection_name: str,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> bool:
        """Update existing vectors."""
        pass


class QdrantManager(VectorDatabaseManager):
    """Qdrant vector database implementation with HNSW optimization."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: Optional[str] = None,
        optimization_target: OptimizationTarget = OptimizationTarget.BALANCED,
        config: Optional[VectorIndexConfig] = None,
    ):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.config = config or OPTIMIZATION_PROFILES[optimization_target]
        self.client: Optional[AsyncQdrantClient] = None
        self._search_metrics: List[SearchMetrics] = []

    async def connect(self) -> bool:
        """Connect to Qdrant database with optimized settings."""
        try:
            if not QDRANT_AVAILABLE:
                logger.error("Qdrant client not available")
                return False

            self.client = AsyncQdrantClient(
                host=self.host,
                port=self.port,
                api_key=self.api_key,
                timeout=30,
                prefer_grpc=True,  # gRPC is faster for batch operations
            )
            # Test connection
            await self.client.get_collections()
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Qdrant."""
        if self.client:
            # Qdrant client doesn't have explicit disconnect
            self.client = None
            logger.info("Disconnected from Qdrant")

    async def create_collection(self, collection_name: str, vector_dim: int) -> bool:
        """Create Qdrant collection with basic settings (backward compatible)."""
        return await self.create_optimized_collection(collection_name, vector_dim)

    async def create_optimized_collection(
        self,
        collection_name: str,
        vector_dim: int,
        config: Optional[VectorIndexConfig] = None,
    ) -> bool:
        """Create Qdrant collection with optimized HNSW and quantization settings."""
        try:
            if not self.client:
                return False

            cfg = config or self.config

            # Build HNSW configuration
            hnsw_config = HnswConfigDiff(
                m=cfg.hnsw.m,
                ef_construct=cfg.hnsw.ef_construction,
                full_scan_threshold=cfg.hnsw.full_scan_threshold,
            )

            # Build quantization configuration
            quantization_config = None
            if cfg.quantization.enabled:
                if cfg.quantization.type == "scalar":
                    quantization_config = ScalarQuantization(
                        scalar=ScalarQuantizationConfig(
                            type=ScalarType.INT8,
                            quantile=cfg.quantization.quantile,
                            always_ram=cfg.quantization.always_ram,
                        )
                    )
                elif cfg.quantization.type == "product":
                    compression = getattr(
                        CompressionRatio,
                        cfg.quantization.compression_ratio.upper(),
                        CompressionRatio.X16,
                    )
                    quantization_config = ProductQuantization(
                        product=ProductQuantizationConfig(
                            compression=compression,
                            always_ram=cfg.quantization.always_ram,
                        )
                    )

            # Build optimizer configuration
            optimizers_config = OptimizersConfigDiff(
                indexing_threshold=cfg.indexing_threshold,
                memmap_threshold=cfg.memmap_threshold,
            )

            # Map distance metric
            distance_map = {
                "cosine": Distance.COSINE,
                "euclidean": Distance.EUCLID,
                "dot": Distance.DOT,
            }
            distance = distance_map.get(cfg.distance_metric.lower(), Distance.COSINE)

            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_dim, distance=distance),
                hnsw_config=hnsw_config,
                quantization_config=quantization_config,
                optimizers_config=optimizers_config,
            )
            logger.info(
                f"Created optimized Qdrant collection: {collection_name} "
                f"(M={cfg.hnsw.m}, ef_construction={cfg.hnsw.ef_construction}, "
                f"quantization={cfg.quantization.type if cfg.quantization.enabled else 'none'})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False

    def _get_search_params(self, target_recall: float = 0.95) -> Any:
        """Get optimized search parameters for target recall."""
        cfg = self.config

        # Adjust ef based on recall target
        if target_recall >= 0.99:
            ef = max(256, cfg.hnsw.ef_search)
            ignore_quantization = True
        elif target_recall >= 0.95:
            ef = cfg.hnsw.ef_search
            ignore_quantization = False
        else:
            ef = min(64, cfg.hnsw.ef_search)
            ignore_quantization = False

        quantization_params = None
        if cfg.quantization.enabled:
            quantization_params = QuantizationSearchParams(
                ignore=ignore_quantization,
                rescore=cfg.search.rescore,
                oversampling=cfg.search.oversampling,
            )

        return SearchParams(
            hnsw_ef=ef,
            exact=False,
            quantization=quantization_params,
        )

    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> bool:
        """Insert vectors into Qdrant."""
        try:
            if not self.client:
                return False

            points = []
            for i, (vector, payload) in enumerate(zip(vectors, payloads, strict=False)):
                point_id = ids[i] if ids else str(i)
                points.append({"id": point_id, "vector": vector, "payload": payload})

            await self.client.upsert(collection_name=collection_name, points=points)
            logger.info(f"Inserted {len(points)} vectors into {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to insert vectors: {e}")
            return False

    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search vectors in Qdrant (backward compatible)."""
        return await self.search_vectors_optimized(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            filter_dict=filter_dict,
        )

    async def search_vectors_optimized(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
        target_recall: float = 0.95,
        track_metrics: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search vectors with optimized parameters and performance tracking."""
        try:
            if not self.client:
                return []

            start_time = time.perf_counter()

            search_result = await self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=filter_dict,
                search_params=self._get_search_params(target_recall),
            )

            latency_ms = (time.perf_counter() - start_time) * 1000

            results = []
            for hit in search_result:
                results.append({"id": hit.id, "score": hit.score, "payload": hit.payload})

            # Track metrics
            if track_metrics:
                metrics = SearchMetrics(
                    latency_ms=latency_ms,
                    candidates_evaluated=len(results),
                )
                self._search_metrics.append(metrics)
                # Keep only last 1000 metrics
                if len(self._search_metrics) > 1000:
                    self._search_metrics = self._search_metrics[-1000:]

            return results
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []

    def get_search_metrics(self) -> Dict[str, Any]:
        """Get aggregated search performance metrics."""
        if not self._search_metrics:
            return {"error": "No metrics collected"}

        latencies = [m.latency_ms for m in self._search_metrics]
        import statistics

        return {
            "count": len(latencies),
            "latency_p50_ms": statistics.median(latencies),
            "latency_p95_ms": sorted(latencies)[int(len(latencies) * 0.95)]
            if len(latencies) > 1
            else latencies[0],
            "latency_p99_ms": sorted(latencies)[int(len(latencies) * 0.99)]
            if len(latencies) > 1
            else latencies[0],
            "latency_avg_ms": statistics.mean(latencies),
            "latency_min_ms": min(latencies),
            "latency_max_ms": max(latencies),
        }

    async def delete_vectors(self, collection_name: str, ids: List[str]) -> bool:
        """Delete vectors from Qdrant."""
        try:
            if not self.client:
                return False

            await self.client.delete(collection_name=collection_name, points_selector=ids)
            logger.info(f"Deleted {len(ids)} vectors from {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False

    async def update_vectors(
        self,
        collection_name: str,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> bool:
        """Update vectors in Qdrant."""
        try:
            if not self.client:
                return False

            points = []
            for vector_id, vector, payload in zip(ids, vectors, payloads, strict=False):
                points.append({"id": vector_id, "vector": vector, "payload": payload})

            await self.client.upsert(collection_name=collection_name, points=points)
            logger.info(f"Updated {len(points)} vectors in {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update vectors: {e}")
            return False


class MilvusManager(VectorDatabaseManager):
    """Milvus vector database implementation."""

    def __init__(self, host: str = "localhost", port: str = "19530"):
        self.host = host
        self.port = port
        self.connection_alias = "constitutional_retrieval"

    async def connect(self) -> bool:
        """Connect to Milvus database."""
        try:
            if not MILVUS_AVAILABLE:
                logger.error("Milvus client not available")
                return False

            connections.connect(alias=self.connection_alias, host=self.host, port=self.port)
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Milvus."""
        try:
            connections.disconnect(alias=self.connection_alias)
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Error disconnecting from Milvus: {e}")

    async def create_collection(self, collection_name: str, vector_dim: int) -> bool:
        """Create Milvus collection."""
        try:
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
                FieldSchema(name="payload", dtype=DataType.JSON),
            ]

            schema = CollectionSchema(fields, description="Constitutional documents and precedents")
            collection = Collection(name=collection_name, schema=schema)

            # Create index
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024},
            }
            collection.create_index(field_name="vector", index_params=index_params)

            logger.info(f"Created Milvus collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False

    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> bool:
        """Insert vectors into Milvus."""
        try:
            collection = Collection(collection_name)

            data = []
            for i, (vector, payload) in enumerate(zip(vectors, payloads, strict=False)):
                vector_id = ids[i] if ids else f"vec_{i}_{datetime.now().timestamp()}"
                data.append({"id": vector_id, "vector": vector, "payload": payload})

            collection.insert(data)
            collection.flush()

            logger.info(f"Inserted {len(data)} vectors into {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to insert vectors: {e}")
            return False

    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search vectors in Milvus."""
        try:
            collection = Collection(collection_name)
            collection.load()

            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

            expr = None
            if filter_dict:
                # Convert filter dict to Milvus expression
                conditions = []
                for key, value in filter_dict.items():
                    if isinstance(value, str):
                        conditions.append(f'{key} == "{value}"')
                    else:
                        conditions.append(f"{key} == {value}")
                expr = " and ".join(conditions)

            results = collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=limit,
                expr=expr,
                output_fields=["payload"],
            )

            search_results = []
            for hits in results:
                for hit in hits:
                    search_results.append(
                        {"id": hit.id, "score": hit.score, "payload": hit.entity.get("payload", {})}
                    )

            return search_results
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []

    async def delete_vectors(self, collection_name: str, ids: List[str]) -> bool:
        """Delete vectors from Milvus."""
        try:
            collection = Collection(collection_name)
            expr = f"id in {ids}"
            collection.delete(expr)
            logger.info(f"Deleted vectors with IDs {ids} from {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False

    async def update_vectors(
        self,
        collection_name: str,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> bool:
        """Update vectors in Milvus (delete and re-insert)."""
        try:
            # Delete old vectors
            await self.delete_vectors(collection_name, ids)
            # Insert new ones
            await self.insert_vectors(collection_name, vectors, payloads, ids)
            logger.info(f"Updated {len(ids)} vectors in {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update vectors: {e}")
            return False


class MockVectorManager(VectorDatabaseManager):
    """Mock implementation for testing and development."""

    def __init__(self, **kwargs):
        self.vectors = {}

    async def connect(self) -> bool:
        return True

    async def disconnect(self) -> None:
        pass

    async def create_collection(self, collection_name: str, vector_dim: int) -> bool:
        return True

    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> bool:
        for i, vector in enumerate(vectors):
            vec_id = ids[i] if ids else f"{len(self.vectors)}"
            self.vectors[vec_id] = {"vector": vector, "payload": payloads[i]}
        return True

    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        # Return mock results
        return [
            {"id": vid, "score": 0.95, "payload": data["payload"]}
            for vid, data in list(self.vectors.items())[:limit]
        ]

    async def delete_vectors(self, collection_name: str, ids: List[str]) -> bool:
        for vid in ids:
            self.vectors.pop(vid, None)
        return True

    async def update_vectors(
        self,
        collection_name: str,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> bool:
        await self.insert_vectors(collection_name, vectors, payloads, ids)
        return True


class PineconeManager(VectorDatabaseManager):
    """Pinecone vector database implementation with serverless/pod support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        environment: str = "serverless",  # "serverless" or "pod"
        cloud: str = "aws",
        region: str = "us-east-1",
        pod_type: str = "p1.x1",
        **kwargs,
    ):
        if not PINECONE_AVAILABLE:
            raise ImportError(
                "pinecone package not installed. Install with: pip install pinecone-client"
            )

        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.environment = environment
        self.cloud = cloud
        self.region = region
        self.pod_type = pod_type
        self.pc: Optional[Pinecone] = None
        self._indexes: Dict[str, Any] = {}

    async def connect(self) -> bool:
        """Connect to Pinecone."""
        try:
            self.pc = Pinecone(api_key=self.api_key)
            # Test connection by listing indexes
            self.pc.list_indexes()
            logger.info("Connected to Pinecone")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Pinecone."""
        self.pc = None
        self._indexes.clear()
        logger.info("Disconnected from Pinecone")

    async def create_collection(self, collection_name: str, vector_dim: int) -> bool:
        """Create Pinecone index (collection)."""
        try:
            if not self.pc:
                return False

            if self.environment == "serverless":
                spec = ServerlessSpec(cloud=self.cloud, region=self.region)
            else:
                spec = PodSpec(
                    environment=f"{self.cloud}-{self.region}",
                    pod_type=self.pod_type,
                )

            self.pc.create_index(
                name=collection_name,
                dimension=vector_dim,
                metric="cosine",
                spec=spec,
            )
            logger.info(f"Created Pinecone index: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create Pinecone index {collection_name}: {e}")
            return False

    def _get_index(self, index_name: str):
        """Get or create index handle with connection pooling."""
        if index_name not in self._indexes:
            self._indexes[index_name] = self.pc.Index(index_name, pool_threads=30)
        return self._indexes[index_name]

    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> bool:
        """Insert vectors into Pinecone with batching."""
        try:
            if not self.pc:
                return False

            index = self._get_index(collection_name)

            # Prepare vectors for upsert
            upsert_data = []
            for i, (vector, payload) in enumerate(zip(vectors, payloads, strict=False)):
                vec_id = ids[i] if ids else f"vec_{i}_{datetime.now(timezone.utc).timestamp()}"
                upsert_data.append((vec_id, vector, payload))

            # Batch upsert (100 vectors per batch)
            batch_size = 100
            for i in range(0, len(upsert_data), batch_size):
                batch = upsert_data[i : i + batch_size]
                index.upsert(vectors=batch)

            logger.info(
                f"Inserted {len(upsert_data)} vectors into Pinecone index {collection_name}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert vectors into Pinecone: {e}")
            return False

    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search vectors in Pinecone."""
        try:
            if not self.pc:
                return []

            index = self._get_index(collection_name)

            results = index.query(
                vector=query_vector,
                top_k=limit,
                filter=filter_dict,
                include_metadata=True,
            )

            return [
                {"id": match.id, "score": match.score, "payload": match.metadata or {}}
                for match in results.matches
            ]
        except Exception as e:
            logger.error(f"Failed to search vectors in Pinecone: {e}")
            return []

    async def delete_vectors(self, collection_name: str, ids: List[str]) -> bool:
        """Delete vectors from Pinecone."""
        try:
            if not self.pc:
                return False

            index = self._get_index(collection_name)
            index.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} vectors from Pinecone index {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors from Pinecone: {e}")
            return False

    async def update_vectors(
        self,
        collection_name: str,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> bool:
        """Update vectors in Pinecone (upsert)."""
        return await self.insert_vectors(collection_name, vectors, payloads, ids)


class WeaviateManager(VectorDatabaseManager):
    """Weaviate vector database implementation with HNSW optimization."""

    def __init__(
        self,
        url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        optimization_target: OptimizationTarget = OptimizationTarget.BALANCED,
        **kwargs,
    ):
        if not WEAVIATE_AVAILABLE:
            raise ImportError(
                "weaviate-client package not installed. Install with: pip install weaviate-client"
            )

        self.url = url
        self.api_key = api_key
        self.config = OPTIMIZATION_PROFILES[optimization_target]
        self.client = None

    async def connect(self) -> bool:
        """Connect to Weaviate cluster."""
        try:
            if self.api_key:
                self.client = weaviate.connect_to_wcs(
                    cluster_url=self.url,
                    auth_credentials=weaviate.auth.AuthApiKey(self.api_key),
                )
            else:
                # Parse URL for local connection
                host = self.url.replace("http://", "").replace("https://", "").split(":")[0]
                port = int(self.url.split(":")[-1]) if ":" in self.url else 8080
                self.client = weaviate.connect_to_local(host=host, port=port)

            if self.client.is_ready():
                logger.info(f"Connected to Weaviate at {self.url}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Weaviate."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("Disconnected from Weaviate")

    async def create_collection(self, collection_name: str, vector_dim: int) -> bool:
        """Create Weaviate collection with optimized HNSW settings."""
        try:
            if not self.client:
                return False

            cfg = self.config

            # Build HNSW vector index config
            vector_index = Configure.VectorIndex.hnsw(
                ef_construction=cfg.hnsw.ef_construction,
                max_connections=cfg.hnsw.m,
                dynamic_ef_min=100,
                dynamic_ef_max=500,
                dynamic_ef_factor=8,
            )

            # Default properties for constitutional documents
            properties = [
                Property(name="content", data_type=WeaviateDataType.TEXT),
                Property(name="source", data_type=WeaviateDataType.TEXT),
                Property(name="category", data_type=WeaviateDataType.TEXT),
                Property(name="timestamp", data_type=WeaviateDataType.DATE),
            ]

            self.client.collections.create(
                name=collection_name,
                properties=properties,
                vector_index_config=vector_index,
                vectorizer_config=Configure.Vectorizer.none(),  # Bring your own vectors
            )
            logger.info(f"Created Weaviate collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create Weaviate collection {collection_name}: {e}")
            return False

    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> bool:
        """Insert vectors into Weaviate."""
        try:
            if not self.client:
                return False

            collection = self.client.collections.get(collection_name)

            with collection.batch.dynamic() as batch:
                for i, (vector, payload) in enumerate(zip(vectors, payloads, strict=False)):
                    uuid = ids[i] if ids else None
                    batch.add_object(properties=payload, vector=vector, uuid=uuid)

            logger.info(
                f"Inserted {len(vectors)} vectors into Weaviate collection {collection_name}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to insert vectors into Weaviate: {e}")
            return False

    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search vectors in Weaviate."""
        try:
            if not self.client:
                return []

            collection = self.client.collections.get(collection_name)

            response = collection.query.near_vector(
                near_vector=query_vector,
                limit=limit,
                return_metadata=["distance"],
            )

            results = []
            for obj in response.objects:
                # Convert distance to similarity score (1 - distance for cosine)
                score = 1.0 - (obj.metadata.distance or 0.0) if obj.metadata else 0.95
                results.append(
                    {
                        "id": str(obj.uuid),
                        "score": score,
                        "payload": obj.properties,
                    }
                )

            return results
        except Exception as e:
            logger.error(f"Failed to search vectors in Weaviate: {e}")
            return []

    async def delete_vectors(self, collection_name: str, ids: List[str]) -> bool:
        """Delete vectors from Weaviate."""
        try:
            if not self.client:
                return False

            collection = self.client.collections.get(collection_name)
            for vec_id in ids:
                collection.data.delete_by_id(vec_id)

            logger.info(f"Deleted {len(ids)} vectors from Weaviate collection {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors from Weaviate: {e}")
            return False

    async def update_vectors(
        self,
        collection_name: str,
        ids: List[str],
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
    ) -> bool:
        """Update vectors in Weaviate."""
        try:
            if not self.client:
                return False

            collection = self.client.collections.get(collection_name)

            for vec_id, vector, payload in zip(ids, vectors, payloads, strict=False):
                collection.data.update(
                    uuid=vec_id,
                    properties=payload,
                    vector=vector,
                )

            logger.info(f"Updated {len(ids)} vectors in Weaviate collection {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update vectors in Weaviate: {e}")
            return False


def create_vector_db_manager(
    db_type: str = "qdrant",
    optimization_target: OptimizationTarget = OptimizationTarget.BALANCED,
    **kwargs,
) -> VectorDatabaseManager:
    """Factory function to create vector database manager.

    Args:
        db_type: Database type ("qdrant", "milvus", "pinecone", "weaviate", "mock")
        optimization_target: Performance optimization profile
        **kwargs: Additional arguments passed to the manager constructor

    Returns:
        VectorDatabaseManager instance

    Example:
        # Create high-recall Qdrant manager for constitutional retrieval
        manager = create_vector_db_manager(
            db_type="qdrant",
            optimization_target=OptimizationTarget.RECALL,
            host="localhost",
            port=6333,
        )
    """
    db_type_lower = db_type.lower()

    if db_type_lower == "qdrant":
        return QdrantManager(optimization_target=optimization_target, **kwargs)
    elif db_type_lower == "milvus":
        return MilvusManager(**kwargs)
    elif db_type_lower == "pinecone":
        return PineconeManager(**kwargs)
    elif db_type_lower == "weaviate":
        return WeaviateManager(optimization_target=optimization_target, **kwargs)
    elif db_type_lower == "mock":
        return MockVectorManager(**kwargs)
    else:
        raise ValueError(
            f"Unsupported database type: {db_type}. Supported: qdrant, milvus, pinecone, weaviate, mock"
        )


# =============================================================================
# Utility Functions for Index Tuning
# =============================================================================


def estimate_memory_usage(
    num_vectors: int,
    dimensions: int,
    quantization: str = "fp32",
    index_type: str = "hnsw",
    hnsw_m: int = 16,
) -> Dict[str, float]:
    """Estimate memory usage for different configurations.

    Args:
        num_vectors: Number of vectors to store
        dimensions: Vector dimensions
        quantization: Quantization type (fp32, fp16, int8, pq, binary)
        index_type: Index type (hnsw, ivf, flat)
        hnsw_m: HNSW M parameter (connections per node)

    Returns:
        Dictionary with memory estimates in MB and GB
    """
    bytes_per_dimension = {
        "fp32": 4,
        "fp16": 2,
        "int8": 1,
        "pq": 0.05,  # Approximate for product quantization
        "binary": 0.125,
    }

    vector_bytes = num_vectors * dimensions * bytes_per_dimension.get(quantization, 4)

    # Index overhead
    if index_type == "hnsw":
        # Each node has ~M*2 edges, each edge is 4 bytes (int32)
        index_bytes = num_vectors * hnsw_m * 2 * 4
    elif index_type == "ivf":
        # Inverted lists + centroids
        index_bytes = num_vectors * 8 + 65536 * dimensions * 4
    else:
        index_bytes = 0

    total_bytes = vector_bytes + index_bytes

    return {
        "vector_storage_mb": vector_bytes / 1024 / 1024,
        "index_overhead_mb": index_bytes / 1024 / 1024,
        "total_mb": total_bytes / 1024 / 1024,
        "total_gb": total_bytes / 1024 / 1024 / 1024,
    }


def recommend_index_config(
    num_vectors: int,
    target_recall: float = 0.95,
    max_latency_ms: float = 10,
    available_memory_gb: float = 8,
) -> Dict[str, Any]:
    """Recommend index configuration based on requirements.

    Args:
        num_vectors: Expected number of vectors
        target_recall: Target recall rate (0.0-1.0)
        max_latency_ms: Maximum acceptable search latency
        available_memory_gb: Available memory in GB

    Returns:
        Recommended configuration dictionary
    """
    # Base recommendations by scale
    if num_vectors < 100_000:
        m = 16
        ef_construction = 100
        quantization = "none"
    elif num_vectors < 1_000_000:
        m = 32
        ef_construction = 200
        quantization = "scalar"
    else:
        m = 48
        ef_construction = 256
        quantization = "product"

    # Adjust for recall target
    if target_recall >= 0.99:
        ef_search = 256
        quantization = "none"  # Disable quantization for max recall
    elif target_recall >= 0.95:
        ef_search = 128
    else:
        ef_search = 64

    # Adjust for latency
    if max_latency_ms < 5:
        ef_search = min(ef_search, 64)
        m = min(m, 16)

    return {
        "hnsw": {"m": m, "ef_construction": ef_construction, "ef_search": ef_search},
        "quantization": quantization,
        "notes": f"Recommended for {num_vectors:,} vectors, {target_recall:.0%} recall, <{max_latency_ms}ms latency",
    }
