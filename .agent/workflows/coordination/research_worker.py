"""
ACGS-2 CEOS Research Worker
Constitutional Hash: cdd01ef066bc6cf2

A specialized worker that uses the RetrievalTriad for cognitive data gathering.
"""

import logging
from typing import Any, Optional

from ..cyclic.state_schema import GlobalState
from .supervisor import WorkerNode

# Attempt to import RetrievalTriad
try:
    from src.core.enhanced_agent_bus.graph_database import create_graph_db_manager
    from src.core.enhanced_agent_bus.retrieval_triad import RetrievalTriad

    HAS_TRIAD = True
except ImportError:
    HAS_TRIAD = False

logger = logging.getLogger(__name__)


class ResearchWorker(WorkerNode):
    """
    Research Worker utilizing GraphRAG (RetrievalTriad).
    """

    def __init__(self, name: str = "worker_research", triad: Optional[Any] = None):
        super().__init__(name, self._research_task)
        self.triad = triad

    async def _research_task(self, state: GlobalState) -> GlobalState:
        """Execute the research task using RetrievalTriad."""
        query = state.context.get("user_request", "general query")

        # If we have feedback from supervisor, refine the query
        feedback = state.context.get("last_feedback")
        if feedback:
            logger.info(f"ResearchWorker refining query based on feedback: {feedback}")
            query = f"{query} (Feedback: {feedback})"

        if not self.triad and HAS_TRIAD:
            graph_manager = create_graph_db_manager("mock")
            self.triad = RetrievalTriad(None, graph_manager)

        if self.triad:
            results = await self.triad.search(query)
            state.context[f"{self.name}_result"] = {
                "status": "success",
                "results": results,
                "summary": f"Found {len(results)} relevant items via RetrievalTriad.",
            }
        else:
            state.context[f"{self.name}_result"] = {
                "status": "success",
                "results": [],
                "summary": "RetrievalTriad not available, returning empty results.",
            }

        return state


__all__ = ["ResearchWorker"]
