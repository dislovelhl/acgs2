"""
ACGS-2 Supervisor Node
Constitutional Hash: cdd01ef066bc6cf2

Implement the Supervisor-Worker topology for CEOS.
The Supervisor plans, delegates, and critiques.
"""

from typing import List, Dict, Any, Optional, Callable, Awaitable
import json
from ..cyclic.state_schema import GlobalState
from ..cyclic.actor_core import NodeCallable

class SupervisorNode:
    """
    Supervisor Node for CEOS Orchestration.

    A Supervisor directs the workflow by deciding which worker to invoke next.
    It maintains a planning-execution-critique loop.
    """

    def __init__(self, name: str = "supervisor", llm_client: Any = None):
        self.name = name
        self.llm_client = llm_client

    async def __call__(self, state: GlobalState) -> GlobalState:
        """
        State Reducer for the Supervisor.

        Analyzes the history and context to decide the next_node.
        """
        state.update_timestamp()

        # 1. Check if we need to critique previous worker output
        if state.history and state.history[-1]["node"].startswith("worker_"):
            last_worker_node = state.history[-1]["node"]
            last_worker_result = state.context.get(f"{last_worker_node}_result")

            # Critique logic (simplified: always positive or check for 'error' in context)
            if last_worker_result and last_worker_result.get("status") == "error":
                state.log_event(self.name, {"action": "critique", "status": "fail", "reason": "Worker error"})
                # Retry or pivot
                state.next_node = last_worker_node
                return state

            state.log_event(self.name, {"action": "critique", "status": "pass"})

        # 2. Planning Logic
        plan = state.context.get("ceos_plan", [])
        plan_idx = state.context.get("ceos_plan_idx", 0)

        if not plan:
            # First run: Generate plan based on initial context/user request
            # In a real system, this would call the LLM
            user_request = state.context.get("user_request", "")
            plan = self._generate_plan(user_request)
            state.context["ceos_plan"] = plan
            state.context["ceos_plan_idx"] = 0
            state.log_event(self.name, {"action": "planning", "steps": plan})

        # 3. Delegation Logic
        if plan_idx < len(plan):
            next_worker = plan[plan_idx]
            state.next_node = next_worker
            state.context["ceos_plan_idx"] = plan_idx + 1
            state.log_event(self.name, {"action": "delegation", "target": next_worker})
        else:
            # Final check / synthesis
            state.is_finished = True
            state.log_event(self.name, {"action": "completion"})

        return state

    def _generate_plan(self, request: str) -> List[str]:
        """Dummy planner logic."""
        # This would be where DSPy / LLM logic resides
        if "code" in request.lower():
            return ["worker_research", "worker_coder", "worker_validator"]
        return ["worker_research", "worker_analyst"]


class WorkerNode:
    """
    A specialized worker node that performs a specific task.
    """

    def __init__(self, name: str, task_fn: Callable[[GlobalState], Awaitable[GlobalState]]):
        self.name = name
        self.task_fn = task_fn

    async def __call__(self, state: GlobalState) -> GlobalState:
        state.log_event(self.name, {"status": "started"})
        try:
            state = await self.task_fn(state)
            state.log_event(self.name, {"status": "completed"})
        except Exception as e:
            state.log_event(self.name, {"status": "error", "error": str(e)})
            state.context[f"{self.name}_result"] = {"status": "error", "message": str(e)}
            # Do NOT finish here; let supervisor handle failure

        # Always return to supervisor unless specified
        state.next_node = "supervisor"
        return state


__all__ = ["SupervisorNode", "WorkerNode"]
