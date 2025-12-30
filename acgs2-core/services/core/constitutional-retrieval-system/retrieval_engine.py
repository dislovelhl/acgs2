"""
Retrieval Engine for Constitutional Retrieval System

Implements RAG (Retrieval-Augmented Generation) for retrieving similar
constitutional precedents and documents to enhance decision making.
"""

import logging
from datetime import timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from document_processor import DocumentProcessor
from vector_database import VectorDatabaseManager

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """Engine for retrieving and ranking constitutional documents and precedents."""

    def __init__(self, vector_db: VectorDatabaseManager, doc_processor: DocumentProcessor):
        """
        Initialize retrieval engine.

        Args:
            vector_db: Vector database manager
            doc_processor: Document processor for embeddings
        """
        self.vector_db = vector_db
        self.doc_processor = doc_processor
        self.collection_name = "constitutional_documents"

    async def initialize_collections(self) -> bool:
        """Initialize vector database collections."""
        try:
            vector_dim = self.doc_processor.vector_dim
            success = await self.vector_db.create_collection(self.collection_name, vector_dim)
            if success:
                logger.info(f"Initialized collection: {self.collection_name}")
            return success
        except Exception as e:
            logger.error(f"Failed to initialize collections: {e}")
            return False

    async def index_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Index documents into the vector database.

        Args:
            documents: List of document chunks with metadata

        Returns:
            Success status
        """
        try:
            if not documents:
                logger.warning("No documents to index")
                return True

            # Extract texts and metadata
            texts = [doc["content"] for doc in documents]
            payloads = [doc["metadata"] for doc in documents]

            # Generate embeddings
            embeddings = self.doc_processor.generate_embeddings(texts)

            # Generate IDs
            ids = [payload.get("chunk_id", f"doc_{i}") for i, payload in enumerate(payloads)]

            # Insert into vector database
            success = await self.vector_db.insert_vectors(
                self.collection_name, embeddings, payloads, ids
            )

            if success:
                logger.info(f"Indexed {len(documents)} document chunks")
            return success

        except Exception as e:
            logger.error(f"Failed to index documents: {e}")
            return False

    async def retrieve_similar_documents(
        self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar documents using semantic search.

        Args:
            query: Search query
            limit: Maximum number of results
            filters: Optional metadata filters

        Returns:
            List of similar documents with scores
        """
        try:
            # Generate query embedding
            query_embedding = self.doc_processor.generate_embeddings([query])[0]

            # Search vector database
            results = await self.vector_db.search_vectors(
                self.collection_name, query_embedding, limit, filters
            )

            # Enhance results with additional processing
            enhanced_results = []
            for result in results:
                enhanced_result = result.copy()
                enhanced_result["relevance_score"] = self._calculate_relevance_score(query, result)
                enhanced_results.append(enhanced_result)

            # Sort by relevance score
            enhanced_results.sort(key=lambda x: x["relevance_score"], reverse=True)

            logger.info(
                f"Retrieved {len(enhanced_results)} similar documents for query: {query[:50]}..."
            )
            return enhanced_results

        except Exception as e:
            logger.error(f"Failed to retrieve similar documents: {e}")
            return []

    async def retrieve_precedents_for_case(
        self, case_description: str, legal_domain: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant legal precedents for a case description.

        Args:
            case_description: Description of the current case
            legal_domain: Specific legal domain filter
            limit: Maximum precedents to retrieve

        Returns:
            List of relevant precedents
        """
        try:
            # Build filters for precedents
            filters = {"doc_type": "precedent"}
            if legal_domain:
                filters["legal_domain"] = legal_domain

            # Retrieve similar precedents
            precedents = await self.retrieve_similar_documents(case_description, limit, filters)

            # Enhance with precedent-specific analysis
            for precedent in precedents:
                precedent["precedent_relevance"] = self._analyze_precedent_relevance(
                    case_description, precedent
                )

            # Sort by precedent relevance
            precedents.sort(key=lambda x: x.get("precedent_relevance", 0), reverse=True)

            logger.info(f"Retrieved {len(precedents)} relevant precedents")
            return precedents

        except Exception as e:
            logger.error(f"Failed to retrieve precedents: {e}")
            return []

    async def retrieve_constitutional_provisions(
        self, query: str, constitutional_rights: Optional[List[str]] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant constitutional provisions.

        Args:
            query: Query describing the constitutional issue
            constitutional_rights: Specific rights to focus on
            limit: Maximum provisions to retrieve

        Returns:
            List of relevant constitutional provisions
        """
        try:
            # Build filters for constitutional documents
            filters = {"doc_type": "constitution"}

            # Search for provisions
            provisions = await self.retrieve_similar_documents(query, limit, filters)

            # Filter by specific rights if provided
            if constitutional_rights:
                filtered_provisions = []
                for provision in provisions:
                    content_lower = provision.get("payload", {}).get("content", "").lower()
                    if any(right.lower() in content_lower for right in constitutional_rights):
                        filtered_provisions.append(provision)
                provisions = filtered_provisions[:limit]

            logger.info(f"Retrieved {len(provisions)} constitutional provisions")
            return provisions

        except Exception as e:
            logger.error(f"Failed to retrieve constitutional provisions: {e}")
            return []

    async def hybrid_search(
        self,
        query: str,
        keyword_filters: Optional[List[str]] = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword-based retrieval.

        Args:
            query: Search query
            keyword_filters: Additional keyword filters
            semantic_weight: Weight for semantic similarity (0-1)
            keyword_weight: Weight for keyword matching (0-1)
            limit: Maximum results

        Returns:
            Ranked search results
        """
        try:
            # Get semantic results
            semantic_results = await self.retrieve_similar_documents(query, limit * 2)

            # Apply keyword filtering if provided
            if keyword_filters:
                filtered_results = []
                for result in semantic_results:
                    content = result.get("payload", {}).get("content", "").lower()
                    if any(kw.lower() in content for kw in keyword_filters):
                        filtered_results.append(result)
                semantic_results = filtered_results

            # Calculate hybrid scores
            for result in semantic_results:
                semantic_score = result.get("score", 0.0)
                keyword_score = self._calculate_keyword_score(query, result, keyword_filters)

                result["hybrid_score"] = (
                    semantic_weight * semantic_score + keyword_weight * keyword_score
                )

            # Sort by hybrid score and limit results
            semantic_results.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
            final_results = semantic_results[:limit]

            logger.info(f"Hybrid search returned {len(final_results)} results")
            return final_results

        except Exception as e:
            logger.error(f"Failed to perform hybrid search: {e}")
            return []

    def _calculate_relevance_score(self, query: str, result: Dict[str, Any]) -> float:
        """Calculate relevance score for a search result."""
        base_score = result.get("score", 0.0)

        # Boost score based on metadata relevance
        payload = result.get("payload", {})
        boost_factors = {
            "doc_type": {"constitution": 1.2, "precedent": 1.1},
            "recency": self._calculate_recency_boost(payload.get("date")),
            "authority": self._calculate_authority_boost(payload),
        }

        total_boost = 1.0
        for factor, boosts in boost_factors.items():
            if isinstance(boosts, dict):
                key = payload.get(factor)
                total_boost *= boosts.get(key, 1.0)
            else:
                total_boost *= boosts

        return base_score * total_boost

    def _calculate_recency_boost(self, date_str: Optional[str]) -> float:
        """Calculate boost factor based on document recency."""
        if not date_str:
            return 1.0

        try:
            doc_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            current_date = datetime.now(timezone.utc)
            days_diff = (current_date - doc_date).days

            # More recent documents get higher boost
            if days_diff < 365:  # Within last year
                return 1.3
            elif days_diff < 365 * 5:  # Within last 5 years
                return 1.1
            else:
                return 0.9
        except (ValueError, TypeError, AttributeError):
            # Date parsing failed, return neutral boost
            return 1.0

    def _calculate_authority_boost(self, payload: Dict[str, Any]) -> float:
        """Calculate boost based on document authority."""
        # Higher courts, official sources get boost
        court = payload.get("court", "").lower()
        source = payload.get("source", "").lower()

        boost = 1.0
        if "supreme" in court:
            boost *= 1.5
        elif "appeal" in court:
            boost *= 1.2

        if "official" in source or "government" in source:
            boost *= 1.3

        return boost

    def _analyze_precedent_relevance(
        self, case_description: str, precedent: Dict[str, Any]
    ) -> float:
        """Analyze how relevant a precedent is to the current case."""
        # Simple relevance analysis - could be enhanced with ML
        case_lower = case_description.lower()
        precedent_content = precedent.get("payload", {}).get("content", "").lower()

        # Count overlapping keywords
        case_words = set(case_lower.split())
        precedent_words = set(precedent_content.split())

        overlap = len(case_words.intersection(precedent_words))
        total_words = len(case_words.union(precedent_words))

        if total_words == 0:
            return 0.0

        return overlap / total_words

    def _calculate_keyword_score(
        self, query: str, result: Dict[str, Any], keyword_filters: Optional[List[str]] = None
    ) -> float:
        """Calculate keyword-based relevance score."""
        content = result.get("payload", {}).get("content", "").lower()
        query_lower = query.lower()

        # Count query term matches
        query_terms = query_lower.split()
        matches = sum(1 for term in query_terms if term in content)

        base_score = matches / len(query_terms) if query_terms else 0.0

        # Add keyword filter matches
        if keyword_filters:
            filter_matches = sum(1 for kw in keyword_filters if kw.lower() in content)
            filter_score = filter_matches / len(keyword_filters)
            base_score = (base_score + filter_score) / 2

        return base_score

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed collection."""
        # This would need to be implemented based on specific vector DB capabilities
        # For now, return basic info
        return {
            "collection_name": self.collection_name,
            "vector_dimension": self.doc_processor.vector_dim,
            "status": "active",
        }
