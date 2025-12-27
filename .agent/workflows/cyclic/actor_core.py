"""
ACGS-2 CEOS Actor Core
Constitutional Hash: cdd01ef066bc6cf2

Core engine for cyclic, stateful orchestration (Actor Model).
Nodes function strictly as State Reducers: (CurrentState) -> NewState.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Union, Awaitable
from .state_schema import GlobalState

logger = logging.getLogger(__name__)

# Type definition for a Node: (State) -> State
NodeCallable = Callable[[GlobalState], Awaitable[GlobalState]]

# Type definition for a Router: (State) -> str (Next Node Name)
RouterCallable = Callable[[GlobalState], Awaitable[str]]


class StateGraph:
    """
    Stateful Cyclic Graph for CEOS Orchestration.
    
    Manages nodes, routers, and the execution loop.
    Enforces the 'State Reducer' pattern.
    """

    def __init__(self, name: str):
        self.name = name
        self.nodes: Dict[str, NodeCallable] = {}
        self.routers: Dict[str, RouterCallable] = {}
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, node: NodeCallable):
        """Add a processing node to the graph."""
        self.nodes[name] = node
        return self

    def set_entry_point(self, name: str):
        """Set the starting node for the execution."""
        if name not in self.nodes:
            raise ValueError(f"Node '{name}' not found in graph.")
        self.entry_point = name
        return self

    def add_conditional_edges(self, source_node: str, router: RouterCallable):
        """Add a router to determine the next node from a source node."""
        if source_node not in self.nodes:
            raise ValueError(f"Source node '{source_node}' not found.")
        self.routers[source_node] = router
        return self

    async def execute(self, initial_state: Optional[GlobalState] = None) -> GlobalState:
        """
        Run the cyclic execution loop.
        
        The loop continues until a node sets 'is_finished=True' 
        or an interrupt is triggered.
        """
        if not self.entry_point:
            raise ValueError("Entry point not set for the graph.")

        state = initial_state or GlobalState()
        current_node_name = state.next_node or self.entry_point
        
        logger.info(f"Starting CEOS Execution: {self.name} | Session: {state.session_id}")

        while not state.is_finished:
            # Check for Interrupts
            if state.interrupt_required:
                logger.warning(f"Interrupt triggered at node '{current_node_name}'. Pausing execution.")
                state.next_node = current_node_name
                return state

            # Get the current node
            node_func = self.nodes.get(current_node_name)
            if not node_func:
                error_msg = f"Node '{current_node_name}' not found."
                state.add_error(error_msg)
                state.is_finished = True
                return state

            # Execute node (State Reducer)
            logger.debug(f"Executing node: {current_node_name}")
            try:
                state = await node_func(state)
                state.log_event(current_node_name, {"status": "success"})
            except Exception as e:
                logger.error(f"Error in node '{current_node_name}': {e}")
                state.add_error(f"Node '{current_node_name}' failed: {str(e)}")
                # Default error handling: go to Error_Handler if it exists
                if "error_handler" in self.nodes:
                    current_node_name = "error_handler"
                    continue
                else:
                    state.is_finished = True
                    return state

            # Determine next node via router if exists, else sequential (if implemented)
            router = self.routers.get(current_node_name)
            if router:
                next_node = await router(state)
                if next_node == "__end__":
                    state.is_finished = True
                else:
                    current_node_name = next_node
            else:
                # If no router, check state.next_node
                if state.next_node:
                    current_node_name = state.next_node
                    state.next_node = None
                else:
                    # No next node defined, stop
                    state.is_finished = True

        logger.info(f"Execution finished: {self.name} | Status: {'error' if state.errors else 'success'}")
        return state


__all__ = ["StateGraph", "GlobalState"]
