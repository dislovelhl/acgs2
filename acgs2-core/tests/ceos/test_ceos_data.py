"""
Tests for CEOS Phase 3: Cognitive Data
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
from enhanced_agent_bus.graph_database import create_graph_db_manager
from enhanced_agent_bus.retrieval_triad import RetrievalTriad
from enhanced_agent_bus.sql_agent import SQLAgent


@pytest.mark.asyncio
async def test_retrieval_triad_ensemble():
    """Test the weighted ensemble retrieval."""
    graph_manager = create_graph_db_manager("mock")
    # Mock vector manager
    vector_manager = None

    triad = RetrievalTriad(vector_manager, graph_manager)

    # Query involving supply chain (triggers mock graph results)
    results = await triad.search("Asian supply chain risks")

    assert len(results) > 0
    # The graph result should be present based on mockup logic in MockGraphManager
    has_graph = any("Graph Context" in r["content"] for r in results)
    assert has_graph
    assert results[0]["triad_score"] > 0


@pytest.mark.asyncio
async def test_sql_agent_self_correction():
    """Test SQL Agent schema reflection and self-correction loop."""
    agent = SQLAgent()

    # Simple query that will "fail" initially in our mock and then "succeed"
    response = await agent.execute_query("Total sales amount")

    assert response["status"] == "success"
    assert response["attempts"] > 1  # Verified self-correction loop ran
    assert "results" in response
    assert response["results"][0]["sum"] == 1200.50


@pytest.mark.asyncio
async def test_graph_multi_hop():
    """Test graph traversal context retrieval."""
    graph = create_graph_db_manager("mock")

    context = await graph.get_multi_hop_context("supply chain")

    assert len(context) == 2
    assert context[0]["relation"] == "EXTENDS_TO"
    assert "Asian" in context[0]["target"]
