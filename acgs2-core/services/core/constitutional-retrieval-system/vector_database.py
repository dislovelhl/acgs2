"""
Vector Database Manager for Constitutional Retrieval System

Supports Qdrant and Milvus vector databases for storing and retrieving
constitutional documents and historical precedents.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False

logger = logging.getLogger(__name__)


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
    async def insert_vectors(self, collection_name: str, vectors: List[List[float]],
                           payloads: List[Dict[str, Any]], ids: Optional[List[str]] = None) -> bool:
        """Insert vectors with payloads into collection."""
        pass

    @abstractmethod
    async def search_vectors(self, collection_name: str, query_vector: List[float],
                           limit: int = 10, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        pass

    @abstractmethod
    async def delete_vectors(self, collection_name: str, ids: List[str]) -> bool:
        """Delete vectors by IDs."""
        pass

    @abstractmethod
    async def update_vectors(self, collection_name: str, ids: List[str],
                           vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> bool:
        """Update existing vectors."""
        pass


class QdrantManager(VectorDatabaseManager):
    """Qdrant vector database implementation."""

    def __init__(self, host: str = "localhost", port: int = 6333, api_key: Optional[str] = None):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.client: Optional[QdrantClient] = None

    async def connect(self) -> bool:
        """Connect to Qdrant database."""
        try:
            if not QDRANT_AVAILABLE:
                logger.error("Qdrant client not available")
                return False

            self.client = QdrantClient(host=self.host, port=self.port, api_key=self.api_key)
            # Test connection
            self.client.get_collections()
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
        """Create Qdrant collection."""
        try:
            if not self.client:
                return False

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE)
            )
            logger.info(f"Created Qdrant collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False

    async def insert_vectors(self, collection_name: str, vectors: List[List[float]],
                           payloads: List[Dict[str, Any]], ids: Optional[List[str]] = None) -> bool:
        """Insert vectors into Qdrant."""
        try:
            if not self.client:
                return False

            points = []
            for i, (vector, payload) in enumerate(zip(vectors, payloads)):
                point_id = ids[i] if ids else str(i)
                points.append({
                    "id": point_id,
                    "vector": vector,
                    "payload": payload
                })

            self.client.upsert(collection_name=collection_name, points=points)
            logger.info(f"Inserted {len(points)} vectors into {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to insert vectors: {e}")
            return False

    async def search_vectors(self, collection_name: str, query_vector: List[float],
                           limit: int = 10, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search vectors in Qdrant."""
        try:
            if not self.client:
                return []

            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=filter_dict
            )

            results = []
            for hit in search_result:
                results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                })

            return results
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []

    async def delete_vectors(self, collection_name: str, ids: List[str]) -> bool:
        """Delete vectors from Qdrant."""
        try:
            if not self.client:
                return False

            self.client.delete(collection_name=collection_name, points_selector=ids)
            logger.info(f"Deleted {len(ids)} vectors from {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False

    async def update_vectors(self, collection_name: str, ids: List[str],
                           vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> bool:
        """Update vectors in Qdrant."""
        try:
            if not self.client:
                return False

            points = []
            for vector_id, vector, payload in zip(ids, vectors, payloads):
                points.append({
                    "id": vector_id,
                    "vector": vector,
                    "payload": payload
                })

            self.client.upsert(collection_name=collection_name, points=points)
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

            connections.connect(
                alias=self.connection_alias,
                host=self.host,
                port=self.port
            )
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
                FieldSchema(name="payload", dtype=DataType.JSON)
            ]

            schema = CollectionSchema(fields, description="Constitutional documents and precedents")
            collection = Collection(name=collection_name, schema=schema)

            # Create index
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            collection.create_index(field_name="vector", index_params=index_params)

            logger.info(f"Created Milvus collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False

    async def insert_vectors(self, collection_name: str, vectors: List[List[float]],
                           payloads: List[Dict[str, Any]], ids: Optional[List[str]] = None) -> bool:
        """Insert vectors into Milvus."""
        try:
            collection = Collection(collection_name)

            data = []
            for i, (vector, payload) in enumerate(zip(vectors, payloads)):
                vector_id = ids[i] if ids else f"vec_{i}_{datetime.now().timestamp()}"
                data.append({
                    "id": vector_id,
                    "vector": vector,
                    "payload": payload
                })

            collection.insert(data)
            collection.flush()

            logger.info(f"Inserted {len(data)} vectors into {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to insert vectors: {e}")
            return False

    async def search_vectors(self, collection_name: str, query_vector: List[float],
                           limit: int = 10, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
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
                        conditions.append(f'{key} == {value}')
                expr = " and ".join(conditions)

            results = collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=limit,
                expr=expr,
                output_fields=["payload"]
            )

            search_results = []
            for hits in results:
                for hit in hits:
                    search_results.append({
                        "id": hit.id,
                        "score": hit.score,
                        "payload": hit.entity.get("payload", {})
                    })

            return search_results
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []

    async def delete_vectors(self, collection_name: str, ids: List[str]) -> bool:
        """Delete vectors from Milvus."""
        try:
            collection = Collection(collection_name)
            expr = f'id in {ids}'
            collection.delete(expr)
            logger.info(f"Deleted vectors with IDs {ids} from {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False

    async def update_vectors(self, collection_name: str, ids: List[str],
                           vectors: List[List[float]], payloads: List[Dict[str, Any]]) -> bool:
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


def create_vector_db_manager(db_type: str = "qdrant", **kwargs) -> VectorDatabaseManager:
    """Factory function to create vector database manager."""
    if db_type.lower() == "qdrant":
        return QdrantManager(**kwargs)
    elif db_type.lower() == "milvus":
        return MilvusManager(**kwargs)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")