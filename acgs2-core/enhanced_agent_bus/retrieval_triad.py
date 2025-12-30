"""
ACGS-2 Retrieval Triad
Constitutional Hash: cdd01ef066bc6cf2

Implement the CEOS Retrieval Triad: Vector Search + Keyword/BM25 + Graph Traversal.
Provides a weighted ensemble of retrieval results for holistic enterprise queries.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

try:
    from enhanced_agent_bus.graph_database import GraphDatabaseManager
except ImportError:
    from .graph_database import GraphDatabaseManager

logger = logging.getLogger(__name__)


class RetrievalTriad:
    """
    Weighted ensemble of Vector, Keyword, and Graph retrieval.
    """

    def __init__(
        self,
        vector_manager: Any,
        graph_manager: GraphDatabaseManager,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.vector = vector_manager
        self.graph = graph_manager
        self.weights = weights or {"vector": 0.4, "keyword": 0.3, "graph": 0.3}

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Execute the Retrieval Triad.
        """
        logger.info(f"Executing Retrieval Triad for query: {query}")

        # Execute searches in parallel as per CEOS mandates
        tasks = [
            self._vector_search(query, limit),
            self._keyword_search(query, limit),
            self._graph_search(query, limit),
        ]
        results = await asyncio.gather(*tasks)
        vector_results, keyword_results, graph_results = results

        # Merge and rank results
        merged_results = self._merge_results(vector_results, keyword_results, graph_results, limit)

        # SDPC Phase 1: RAGuard Stability Check
        is_stable, stability_score = await self._check_stability(query, merged_results)
        for res in merged_results:
            res["raguard_stable"] = is_stable
            res["stability_score"] = stability_score

        return merged_results

    async def _check_stability(
        self, query: str, results: List[Dict[str, Any]]
    ) -> tuple[bool, float]:
        """
        Assess retrieval stability by comparing primary context with and without top-k.
        This provides a defense against misleading retrieval (RAGuard).
        """
        if not results:
            return True, 1.0

        # Placeholder for semantic overlap check between top-1 and top-3
        # In Phase 2, this will use an LLM-based hallucination detector (ASC/USC)
        top_score = results[0].get("score", 0.0)
        avg_score = sum(r.get("score", 0.0) for r in results) / len(results)

        stability = 1.0 - abs(top_score - avg_score)
        return stability > 0.7, stability

    async def _vector_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Simulate vector search."""
        # For now, we interact with the provided vector_manager or return dummy
        return [{"id": "v1", "content": "Vector result for " + query, "score": 0.9}]

    async def _keyword_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Simulate BM25/Keyword search."""
        # Implementation of BM25 logic or calling a service
        return [{"id": "k1", "content": "Keyword result for " + query, "score": 0.8}]

    async def _graph_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Multi-hop context via graph traversal."""
        # Extract entities from query (LLM task usually)
        # For demo, search for query terms in graph
        results = await self.graph.get_multi_hop_context(query)
        if results:
            return [{"id": "g1", "content": f"Graph Context: {results}", "score": 0.85}]
        return []

    def _merge_results(
        self,
        vector: List[Dict[str, Any]],
        keyword: List[Dict[str, Any]],
        graph: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        Merge results using Reciprocal Rank Fusion (RRF) or simple weighted scoring.
        """
        all_results = {}

        def add_to_merged(source_results, weight):
            for i, res in enumerate(source_results):
                doc_id = res["id"]
                # Score based on rank (1/(rank+k)) and weighted source
                score = (1.0 / (i + 1)) * weight
                if doc_id in all_results:
                    all_results[doc_id]["triad_score"] += score
                else:
                    res["triad_score"] = score
                    all_results[doc_id] = res

        add_to_merged(vector, self.weights["vector"])
        add_to_merged(keyword, self.weights["keyword"])
        add_to_merged(graph, self.weights["graph"])

        # Sort by triad_score
        sorted_results = sorted(all_results.values(), key=lambda x: x["triad_score"], reverse=True)
        return sorted_results[:limit]
