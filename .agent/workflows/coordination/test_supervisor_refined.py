"""
Tests for Refined CEOS Supervisor
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest

from workflows.coordination.research_worker import ResearchWorker
from workflows.coordination.supervisor import SupervisorNode, WorkerNode
from workflows.cyclic.actor_core import StateGraph
from workflows.cyclic.state_schema import GlobalState


@pytest.mark.asyncio
async def test_supervisor_planning_and_delegation():
    """Test that supervisor generates a plan and delegates to workers."""

    # 1. Setup Graph
    graph = StateGraph("ceos-test-graph")
    supervisor = SupervisorNode()

    # Real research worker
    worker_research = ResearchWorker()

    # Simple worker that succeeds
    async def task_ok(state: GlobalState) -> GlobalState:
        # Get the actual node name from history if possible, or use a default
        node_name = state.history[-1]["node"] if state.history else "worker_analyst"
        state.context[f"{node_name}_result"] = {"status": "success", "data": "all good"}
        return state

    worker_analyst = WorkerNode("worker_analyst", task_ok)

    graph.add_node("supervisor", supervisor)
    graph.add_node("worker_research", worker_research)
    graph.add_node("worker_analyst", worker_analyst)
    graph.set_entry_point("supervisor")

    # 2. Execute
    initial_state = GlobalState()
    # Query that triggers GraphRAG results in mock
    initial_state.context["user_request"] = "Asian supply chain risks"

    final_state = await graph.execute(initial_state)

    # 3. Verify
    assert final_state.is_finished
    assert "worker_research" in final_state.context["ceos_plan"]

    # Check if research results are present
    research_res = final_state.context.get("worker_research_result")
    assert research_res["status"] == "success"
    # If TRIAD was available, we should have results
    if len(research_res.get("results", [])) > 0:
        assert any("Graph Context" in r["content"] for r in research_res["results"])


@pytest.mark.asyncio
async def test_supervisor_critique_loop():
    """Test that supervisor detects failure and re-runs worker."""

    graph = StateGraph("critique-test-graph")
    supervisor = SupervisorNode()

    # Worker that fails once, then succeeds
    async def task_flaky(state: GlobalState) -> GlobalState:
        if "retried" not in state.context:
            state.context["worker_research_result"] = {"status": "error", "msg": "first try failed"}
            state.context["retried"] = True
        else:
            state.context["worker_research_result"] = {"status": "success"}
        return state

    worker_research = WorkerNode("worker_research", task_flaky)

    graph.add_node("supervisor", supervisor)
    graph.add_node("worker_research", worker_research)
    graph.set_entry_point("supervisor")

    # Execute
    initial_state = GlobalState()
    initial_state.context["user_request"] = "Do something flaky"

    final_state = await graph.execute(initial_state)

    # Verify
    assert final_state.is_finished
    # Should have a critique 'fail' event in history
    critique_events = [
        h for h in final_state.history if h.get("data", {}).get("action") == "critique"
    ]
    assert any(c["data"]["status"] == "fail" for c in critique_events)
    assert final_state.context["retried"] is True
