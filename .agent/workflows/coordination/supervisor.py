"""
ACGS-2 Supervisor Node
Constitutional Hash: cdd01ef066bc6cf2

Implement the Supervisor-Worker topology for CEOS.
The Supervisor plans, delegates, and critiques.
"""

import logging
from typing import Any, Awaitable, Callable

from ..cyclic.state_schema import GlobalState
from .signatures import CEOSPoncho, CritiqueSignature, PlanningSignature

logger = logging.getLogger(__name__)


class SupervisorNode:
    """
    Refined Supervisor Node for CEOS Orchestration.

    Uses CEOS Signatures (DSPy-style) for structured planning and critiquing.
    Maintains a planning-execution-critique loop with constitutional feedback.
    """

    def __init__(self, name: str = "supervisor", llm_client: Any = None):
        self.name = name
        self.orchestrator = CEOSPoncho(llm_client)

    async def __call__(self, state: GlobalState) -> GlobalState:
        """
        State Reducer for the Supervisor.
        """
        state.update_timestamp()

        # 1. Critique Phase
        if state.history and state.history[-1]["node"].startswith("worker_"):
            last_worker_node = state.history[-1]["node"]
            last_worker_result = state.context.get(f"{last_worker_node}_result", {})

            # Use Critique Signature
            critique = await self.orchestrator(
                CritiqueSignature,
                task_desc=f"Execute step for {last_worker_node}",
                worker_output=last_worker_result,
                constitutional_constraints=[state.metadata.constitutional_hash],
            )

            if not critique["is_passed"]:
                state.log_event(
                    self.name,
                    {"action": "critique", "status": "fail", "feedback": critique["feedback"]},
                )
                # Re-run the node with feedback
                state.next_node = last_worker_node
                state.context["last_feedback"] = critique["feedback"]
                return state

            state.log_event(self.name, {"action": "critique", "status": "pass"})

        # 2. Planning Phase
        plan = state.context.get("ceos_plan", [])
        plan_idx = state.context.get("ceos_plan_idx", 0)

        if not plan:
            user_request = state.context.get("user_request", "")
            # Use Planning Signature
            planning_result = await self.orchestrator(
                PlanningSignature,
                user_request=user_request,
                context=state.context,
                available_workers=[
                    "worker_research",
                    "worker_coder",
                    "worker_validator",
                    "worker_analyst",
                ],
            )

            plan = planning_result["plan"]
            state.context["ceos_plan"] = plan
            state.context["ceos_plan_idx"] = 0
            state.context["planning_reasoning"] = planning_result["reasoning"]
            state.log_event(
                self.name,
                {"action": "planning", "steps": plan, "reasoning": planning_result["reasoning"]},
            )

        # 3. Delegation Phase
        if plan_idx < len(plan):
            next_worker = plan[plan_idx]
            state.next_node = next_worker
            state.context["ceos_plan_idx"] = plan_idx + 1
            state.log_event(self.name, {"action": "delegation", "target": next_worker})
        else:
            state.is_finished = True
            state.log_event(self.name, {"action": "completion"})

        return state


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
