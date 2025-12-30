"""
Tests for CEOS Supervisor-Worker Topology
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest

from workflows.coordination.supervisor import SupervisorNode, WorkerNode
from workflows.cyclic.actor_core import StateGraph
from workflows.cyclic.state_schema import GlobalState


@pytest.mark.asyncio
async def test_supervisor_worker_cycle():
    """Test a full supervisor-worker cycle."""

    graph = StateGraph("ceos-test-graph")

    # 1. Define Worker tasks
    async def research_task(state: GlobalState) -> GlobalState:
        state.context["research_data"] = "Found information about ACGS-2"
        state.context["worker_research_result"] = {"status": "success"}
        return state

    async def coder_task(state: GlobalState) -> GlobalState:
        state.context["code"] = "print('Hello ACGS-2')"
        state.context["worker_coder_result"] = {"status": "success"}
        return state

    # 2. Setup Nodes
    supervisor = SupervisorNode("supervisor")
    worker_res = WorkerNode("worker_research", research_task)
    worker_code = WorkerNode("worker_coder", coder_task)

    graph.add_node("supervisor", supervisor)
    graph.add_node("worker_research", worker_res)
    graph.add_node("worker_coder", worker_code)

    graph.set_entry_point("supervisor")

    # 3. Execute
    initial_state = GlobalState()
    initial_state.context["user_request"] = "Research and write code for ACGS-2"

    final_state = await graph.execute(initial_state)

    # Filter history to see the sequence of nodes that were executed
    # Note: we filter out consecutive duplicates for the sequence check
    nodes_executed = []
    for event in final_state.history:
        node = event["node"]
        if not nodes_executed or nodes_executed[-1] != node:
            nodes_executed.append(node)

    assert nodes_executed[0] == "supervisor"
    assert nodes_executed[1] == "worker_research"
    assert nodes_executed[2] == "supervisor"
    assert nodes_executed[3] == "worker_coder"
    assert final_state.context["research_data"] == "Found information about ACGS-2"
    assert final_state.context["code"] == "print('Hello ACGS-2')"
    assert final_state.is_finished
