"""
Tests for CEOS Cyclic Orchestration
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest

from workflows.cyclic.actor_core import StateGraph
from workflows.cyclic.state_schema import GlobalState


@pytest.mark.asyncio
async def test_cyclic_graph_basic_loop():
    """Test a simple cyclic graph with a counter."""

    graph = StateGraph("counter-graph")

    async def increment_node(state: GlobalState) -> GlobalState:
        count = state.context.get("count", 0)
        state.context["count"] = count + 1
        return state

    async def router(state: GlobalState) -> str:
        count = state.context.get("count", 0)
        if count < 3:
            return "increment"
        return "__end__"

    graph.add_node("increment", increment_node)
    graph.set_entry_point("increment")
    graph.add_conditional_edges("increment", router)

    final_state = await graph.execute()

    assert final_state.context["count"] == 3
    assert final_state.is_finished
    assert len(final_state.history) == 3


@pytest.mark.asyncio
async def test_interrupt_and_resume():
    """Test the interrupt mechanism and resuming execution."""

    graph = StateGraph("interrupt-graph")

    async def step_one(state: GlobalState) -> GlobalState:
        state.context["step1"] = True
        state.interrupt_required = True
        state.interrupt_message = "Human check needed"
        return state

    async def step_two(state: GlobalState) -> GlobalState:
        state.context["step2"] = True
        state.is_finished = True
        return state

    async def router(s: GlobalState) -> str:
        return "step2"

    graph.add_node("step1", step_one)
    graph.add_node("step2", step_two)
    graph.set_entry_point("step1")
    graph.add_conditional_edges("step1", router)

    # 1. Execute until interrupt
    state = await graph.execute()
    assert state.context["step1"] is True
    assert "step2" not in state.context
    assert state.interrupt_required is True
    assert state.next_node == "step2"  # It was about to run step2

    # Simulate human intervention (patching state)
    state.interrupt_required = False
    state.next_node = "step2"  # Override next node

    # 2. Resume
    final_state = await graph.execute(state)
    assert final_state.context["step2"] is True
    assert final_state.is_finished is True


@pytest.mark.asyncio
async def test_error_handler():
    """Test error handler fallback."""

    graph = StateGraph("error-graph")

    async def failing_node(state: GlobalState) -> GlobalState:
        raise ValueError("Boom!")

    async def error_handler(state: GlobalState) -> GlobalState:
        state.context["handled"] = True
        state.is_finished = True
        return state

    graph.add_node("fail", failing_node)
    graph.add_node("error_handler", error_handler)
    graph.set_entry_point("fail")

    final_state = await graph.execute()

    assert final_state.context.get("handled") is True
    assert "fail" in final_state.errors[0]


@pytest.mark.asyncio
async def test_subgraph_execution():
    """Test that a StateGraph can be used as a node in another graph."""

    # 1. Child Graph
    child_graph = StateGraph("child")

    async def child_node(state: GlobalState) -> GlobalState:
        state.context["child_visited"] = True
        state.is_finished = True  # Signal end of child graph
        return state

    child_graph.add_node("child_node", child_node)
    child_graph.set_entry_point("child_node")

    # 2. Parent Graph
    parent_graph = StateGraph("parent")

    async def parent_start(state: GlobalState) -> GlobalState:
        state.context["parent_started"] = True
        return state

    async def parent_end(state: GlobalState) -> GlobalState:
        state.context["parent_ended"] = True
        state.is_finished = True
        return state

    parent_graph.add_node("start", parent_start)
    parent_graph.add_node("call_child", child_graph)  # CHILD GRAPH AS NODE
    parent_graph.add_node("end", parent_end)

    parent_graph.set_entry_point("start")
    parent_graph.add_conditional_edges("start", lambda s: "call_child")
    parent_graph.add_conditional_edges("call_child", lambda s: "end")

    # 3. Execute
    final_state = await parent_graph.execute()

    # 4. Verify
    assert final_state.context.get("parent_started") is True
    assert final_state.context.get("child_visited") is True
    assert final_state.context.get("parent_ended") is True
    assert final_state.is_finished is True
