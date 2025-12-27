"""
Tests for CEOS Cyclic Orchestration
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
import asyncio
from typing import Dict, Any
from workflows.cyclic.state_schema import GlobalState
from workflows.cyclic.actor_core import StateGraph


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
    assert state.next_node == "step2" # It was about to run step2

    # Simulate human intervention (patching state)
    state.interrupt_required = False
    state.next_node = "step2" # Override next node

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
