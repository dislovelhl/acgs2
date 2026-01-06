"""
Core Reasoning Engine (CRE) Implementation

The CRE performs structured, iterative reasoning using chain-of-thought,
planning, critique, and reflection techniques to solve complex problems.

Key responsibilities:
- Plan generation and validation
- Tool orchestration (without direct tool calls)
- Response synthesis from tool results
- Memory write coordination
- Safety-aware reasoning with refusals
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.shared.security import safe_eval_expr

from ..core.interfaces import CoreReasoningEngineInterface
from ..core.schemas import (
    ContextBundle,
    CoreEnvelope,
    MemoryRecord,
    MultiStepPlan,
    ReasoningPlan,
    RecordType,
    ToolCallRequest,
    ToolResult,
)

logger = logging.getLogger(__name__)


class CoreReasoningEngine(CoreReasoningEngineInterface):
    """Core Reasoning Engine - Structured reasoning with tool orchestration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._running = True

        # Reasoning traces for debugging
        self.reasoning_traces: Dict[str, List[Dict[str, Any]]] = {}

        logger.info("CRE initialized with structured reasoning capabilities")

    @property
    def component_name(self) -> str:
        return "CRE"

    async def health_check(self) -> Dict[str, Any]:
        """Health check for CRE."""
        return {
            "component": self.component_name,
            "status": "healthy" if self._running else "unhealthy",
            "active_traces": len(self.reasoning_traces),
            "reasoning_model": self.config.get("reasoning_model", "chain-of-thought"),
        }

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("CRE shutting down")
        self._running = False
        self.reasoning_traces.clear()

    async def reason(self, envelope: CoreEnvelope, context: ContextBundle) -> Dict[str, Any]:
        """
        Perform reasoning and return response with tool orchestration.

        This implements the core reasoning loop:
        1. Analyze query and context
        2. Generate reasoning plan
        3. Determine tool needs
        4. Return plan for validation (SAS will check)
        5. If approved, orchestrate tool execution
        6. Synthesize final response
        7. Coordinate memory writes
        """
        if not self._running:
            return {
                "status": "error",
                "response": "Reasoning engine is unavailable",
            }

        request_id = envelope.request_id
        query = envelope.payload.get("query", "")

        # Initialize reasoning trace
        self.reasoning_traces[request_id] = [
            {
                "step": "start",
                "timestamp": envelope.timestamp,
                "query": query,
                "context_summary": f"{len(context.session_history)} turns, {len(context.facts)} facts",
            }
        ]

        try:
            # Step 1: Check if this requires multi-step planning
            multi_step_plan = await self.generate_multi_step_plan(query, context)

            if multi_step_plan:
                # Execute multi-step plan
                self._add_trace_step(
                    request_id,
                    "multi_step_plan_generated",
                    {
                        "plan_id": multi_step_plan.plan_id,
                        "steps": len(multi_step_plan.steps),
                        "dependencies": multi_step_plan.dependencies,
                    },
                )

                result = await self.execute_multi_step_plan(multi_step_plan, envelope)

                self._add_trace_step(
                    request_id,
                    "multi_step_execution_completed",
                    {
                        "status": result.get("status"),
                        "completed_steps": result.get("completed_steps"),
                        "total_steps": result.get("total_steps"),
                    },
                )

                # Memory write for orchestration result
                memory_record = MemoryRecord(
                    record_type=RecordType.SUMMARY,
                    content=f"Multi-step task completed: {result.get('completed_steps', 0)}/{result.get('total_steps', 0)} steps | Status: {result.get('status', 'unknown')}",
                    provenance={
                        "source": "orchestration",
                        "request_id": request_id,
                        "plan_id": multi_step_plan.plan_id,
                    },
                    retention={"ttl_days": 30, "pii": False},
                )

                return {
                    "status": result.get("status", "success"),
                    "response": result.get("response", ""),
                    "plan_result": result,
                    "memory_write": memory_record,
                }

            # Step 2: Generate single-step plan
            plan = await self.generate_plan(query, context)

            self._add_trace_step(
                request_id,
                "plan_generated",
                {
                    "plan": plan.__dict__ if plan else None,
                    "requires_tool": plan.requires_tool if plan else False,
                },
            )

            # Step 3: Check if tools are needed
            if not plan or not plan.requires_tool:
                # Direct response without tools
                response = await self.synthesize_response(query, [], context)
                self._add_trace_step(
                    request_id,
                    "response_synthesized",
                    {
                        "response_length": len(response),
                        "tool_results_used": 0,
                    },
                )

                # Memory write for conversation
                memory_record = MemoryRecord(
                    record_type=RecordType.SUMMARY,
                    content=f"Query: {query} | Response: {response[:100]}...",
                    provenance={
                        "source": "model",
                        "request_id": request_id,
                        "reasoning_type": "direct_response",
                    },
                    retention={"ttl_days": 30, "pii": False},
                )

                return {
                    "status": "success",
                    "response": response,
                    "tool_result": None,
                    "memory_write": memory_record,
                }

            # Step 3: Tool is needed - prepare for orchestration
            # Note: Actual tool execution happens via TMS after SAS validation
            tool_request = ToolCallRequest(
                tool_name=plan.tool,
                capability=plan.capability,
                args=plan.args,
                idempotency_key=f"{request_id}_{plan.tool}",
            )

            self._add_trace_step(
                request_id,
                "tool_orchestration_prepared",
                {
                    "tool": plan.tool,
                    "capability": plan.capability,
                    "args_keys": list(plan.args.keys()),
                },
            )

            return {
                "status": "tool_required",
                "response": "Processing your request...",
                "tool_request": tool_request,
                "plan": plan,
            }

        except Exception as e:
            logger.error(f"Reasoning failed for {request_id}: {e}")
            self._add_trace_step(request_id, "error", {"error": str(e)})

            return {
                "status": "error",
                "response": "I encountered an error while processing your request.",
            }

    async def generate_plan(self, query: str, context: ContextBundle) -> Optional[ReasoningPlan]:
        """
        Generate execution plan based on query analysis.

        This uses simple heuristics - in production would use LLM for planning.
        """
        query_lower = query.lower()

        # Check if we already have relevant context
        relevant_facts = []
        for fact in context.facts:
            if any(word in fact.get("content", "").lower() for word in query_lower.split()):
                relevant_facts.append(fact)

        # Simple planning heuristics
        if any(word in query_lower for word in ["search", "find", "look up", "what is"]):
            return ReasoningPlan(
                requires_tool=True,
                tool="search",
                capability="search",
                args={"query": query},
            )

        elif any(word in query_lower for word in ["calculate", "compute", "math", "solve"]):
            return ReasoningPlan(
                requires_tool=True,
                tool="calculator",
                capability="compute",
                args={"expression": self._extract_math_expression(query)},
            )

        elif any(word in query_lower for word in ["weather", "temperature", "forecast"]):
            location = self._extract_location(query)
            if location:
                return ReasoningPlan(
                    requires_tool=True,
                    tool="weather",
                    capability="api_call",
                    args={"location": location},
                )

        # No tool needed - direct response
        return ReasoningPlan(requires_tool=False)

    async def synthesize_response(
        self, query: str, tool_results: List[ToolResult], context: ContextBundle
    ) -> str:
        """
        Synthesize final response from tool results and context.

        In production, this would use an LLM to generate natural responses.
        """
        if not tool_results:
            # Direct response based on context
            if context.facts:
                fact_summaries = [f.get("content", "") for f in context.facts[:3]]
                return f"Based on available information: {'; '.join(fact_summaries)}"
            else:
                return f"I understand you're asking about '{query}'. How can I help you further?"

        # Synthesize from tool results
        responses = []

        for result in tool_results:
            if result.status == result.status.OK:
                if result.tool_name == "search":
                    results = result.result.get("results", [])
                    if results:
                        responses.append(f"Search results: {len(results)} found")
                    else:
                        responses.append("No search results found")

                elif result.tool_name == "calculator":
                    calc_result = result.result.get("result")
                    responses.append(f"Calculation result: {calc_result}")

                elif result.tool_name == "weather":
                    weather_data = result.result
                    responses.append(
                        f"Weather in {weather_data.get('location', 'unknown')}: "
                        f"{weather_data.get('temperature', 'N/A')}°F, "
                        f"{weather_data.get('conditions', 'unknown')}"
                    )

        if responses:
            return " ".join(responses)
        else:
            return "I processed your request but couldn't generate a specific response."

    async def handle_refusal(
        self, decision, session_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate appropriate refusal message with escalating responses.

        Args:
            decision: SafetyDecision with denial details
            session_context: Optional context about session denial history
        """
        rationale = decision.rationale_codes

        # Base messages that don't leak policy internals
        base_messages = {
            "BLOCKED_PATTERN": [
                "I can't assist with that request as it may violate our usage guidelines.",
                "That type of request isn't permitted. Please try rephrasing your question.",
                "I'm unable to help with requests of that nature for safety reasons.",
            ],
            "SESSION_RISK_TOO_HIGH": [
                "This conversation session has reached its safety limits. Please start a new session.",
                "For security reasons, this session is now closed. Please begin a new conversation.",
                "Session terminated due to safety protocol. Please start fresh.",
            ],
            "BLOCKED_TOOL": [
                "The requested operation isn't available.",
                "That tool or action is restricted.",
                "I don't have access to that capability.",
            ],
        }

        # Get denial count for escalation
        denial_count = 0
        if session_context and "denial_history" in session_context:
            denial_count = len(session_context["denial_history"])

        # Select escalating message based on denial count
        for code in rationale:
            if code in base_messages:
                messages = base_messages[code]
                # Cycle through messages based on denial count
                message_index = min(denial_count, len(messages) - 1)
                return messages[message_index]

        # Default refusal
        default_messages = [
            "I must decline this request.",
            "I'm unable to assist with that.",
            "This request cannot be processed.",
        ]
        message_index = min(denial_count, len(default_messages) - 1)
        return default_messages[message_index]

    async def get_reasoning_trace(self, request_id: str) -> List[Dict[str, Any]]:
        """Get reasoning trace for debugging."""
        return self.reasoning_traces.get(request_id, [])

    def _add_trace_step(self, request_id: str, step_name: str, data: Dict[str, Any]) -> None:
        """Add step to reasoning trace."""
        if request_id not in self.reasoning_traces:
            self.reasoning_traces[request_id] = []

        import time

        trace_entry = {
            "step": step_name,
            "timestamp": time.time(),
            **data,
        }

        self.reasoning_traces[request_id].append(trace_entry)

        # Limit trace length
        max_steps = self.config.get("max_trace_steps", 20)
        if len(self.reasoning_traces[request_id]) > max_steps:
            self.reasoning_traces[request_id] = self.reasoning_traces[request_id][-max_steps:]

    def _extract_math_expression(self, query: str) -> str:
        """Extract mathematical expression from query."""
        # Very basic extraction - would be more sophisticated in production
        import re

        # Look for patterns like "2 + 2", "calculate 5 * 3", etc.
        patterns = [
            r"(\d+\s*[\+\-\*\/]\s*\d+)",  # Simple arithmetic
            r"calculate\s+(.+?)(?:\s|$)",  # "calculate X"
            r"what\s+is\s+(.+?)(?:\?|$)",  # "what is X"
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return query  # Fallback

    def _extract_location(self, query: str) -> Optional[str]:
        """Extract location from weather query."""
        # Basic location extraction
        locations = ["New York", "London", "Tokyo", "Paris", "Sydney", "Berlin"]

        for location in locations:
            if location.lower() in query.lower():
                return location

        # Look for city-like patterns
        import re

        city_match = re.search(r"in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", query)
        if city_match:
            return city_match.group(1)

        return None

    async def get_reasoning_stats(self) -> Dict[str, Any]:
        """Get reasoning engine statistics."""
        total_traces = len(self.reasoning_traces)
        total_steps = sum(len(trace) for trace in self.reasoning_traces.values())

        tool_requests = sum(
            1
            for trace in self.reasoning_traces.values()
            for step in trace
            if step.get("step") == "tool_orchestration_prepared"
        )

        return {
            "active_traces": total_traces,
            "total_reasoning_steps": total_steps,
            "avg_steps_per_request": total_steps / max(total_traces, 1),
            "tool_orchestration_requests": tool_requests,
        }

    async def generate_multi_step_plan(
        self, query: str, context: ContextBundle
    ) -> Optional[MultiStepPlan]:
        """
        Generate multi-step execution plan for complex tasks.

        Analyzes query complexity and creates dependent tool execution steps.
        """
        query_lower = query.lower()

        # Simple heuristic for multi-step tasks
        if "research" in query_lower and ("and" in query_lower or "then" in query_lower):
            # Research task with multiple components
            return MultiStepPlan(
                plan_id=f"research_{len(context.session_history)}",
                request_id="",  # Will be set by caller
                session_id="",  # Will be set by caller
                steps=[
                    ReasoningPlan(
                        requires_tool=True,
                        tool="search",
                        capability="search",
                        args={"query": self._extract_research_topic(query)},
                    ),
                    ReasoningPlan(
                        requires_tool=True,
                        tool="search",
                        capability="search",
                        args={
                            "query": f"latest developments in {self._extract_research_topic(query)}"
                        },
                    ),
                ],
                dependencies={1: [0]},  # Step 1 depends on step 0
                checkpoints=["search_results", "latest_info"],
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        elif "calculate" in query_lower and ("and" in query_lower or "then" in query_lower):
            # Multi-calculation task
            expressions = self._extract_multiple_expressions(query)
            if len(expressions) > 1:
                steps = []
                dependencies = {}

                for i, expr in enumerate(expressions):
                    steps.append(
                        ReasoningPlan(
                            requires_tool=True,
                            tool="calculator",
                            capability="compute",
                            args={"expression": expr},
                        )
                    )
                    if i > 0:
                        dependencies[i] = [i - 1]  # Each step depends on previous

                return MultiStepPlan(
                    plan_id=f"calc_multi_{len(expressions)}",
                    request_id="",  # Will be set by caller
                    session_id="",  # Will be set by caller
                    steps=steps,
                    dependencies=dependencies,
                    checkpoints=[f"calc_{i}" for i in range(len(expressions))],
                    created_at=datetime.now(timezone.utc).isoformat(),
                )

        # Not a multi-step task
        return None

    async def execute_multi_step_plan(
        self, plan: MultiStepPlan, envelope: CoreEnvelope
    ) -> Dict[str, Any]:
        """
        Execute multi-step plan with checkpointing and error handling.

        Implements dependency resolution, checkpointing, and compensation.
        """
        if not self._running:
            return {"status": "error", "message": "Reasoning engine unavailable"}

        plan.request_id = envelope.request_id
        plan.session_id = envelope.session_id

        results = []
        completed_steps = set()
        failed_steps = set()

        # Execute steps in dependency order
        for step_idx in range(len(plan.steps)):
            if step_idx in failed_steps:
                continue

            # Check dependencies
            deps = plan.dependencies.get(step_idx, [])
            if not all(dep in completed_steps for dep in deps):
                logger.warning(f"Step {step_idx} dependencies not satisfied: {deps}")
                failed_steps.add(step_idx)
                continue

            step = plan.steps[step_idx]

            try:
                # Execute step (this would call TMS in real implementation)
                logger.info(f"Executing step {step_idx}: {step.tool}")

                # For now, simulate tool execution
                if step.tool == "search":
                    result = {
                        "status": "OK",
                        "result": {
                            "results": [
                                {"title": f"Result for {step.args.get('query', 'unknown')}"}
                            ]
                        },
                    }
                elif step.tool == "calculator":
                    # Simulate calculation using safe evaluator
                    expr = step.args.get("expression", "0")
                    try:
                        result_val = safe_eval_expr(expr)
                        result = {"status": "OK", "result": {"result": result_val}}
                    except Exception as e:
                        result = {
                            "status": "ERROR",
                            "error": {
                                "code": "CALC_ERROR",
                                "message": f"Invalid expression: {str(e)}",
                            },
                        }
                else:
                    result = {
                        "status": "ERROR",
                        "error": {"code": "UNKNOWN_TOOL", "message": f"Unknown tool: {step.tool}"},
                    }

                # Checkpoint result to DMS
                checkpoint_id = (
                    plan.checkpoints[step_idx]
                    if step_idx < len(plan.checkpoints)
                    else f"step_{step_idx}"
                )
                await self._checkpoint_step_result(plan, step_idx, result, envelope)

                results.append(result)
                completed_steps.add(step_idx)

                # Check if we should continue (e.g., if this step failed critically)
                if result.get("status") == "ERROR":
                    # Implement compensation logic here
                    logger.warning(f"Step {step_idx} failed, implementing compensation")
                    # For now, just mark as failed
                    failed_steps.add(step_idx)

            except Exception as e:
                logger.error(f"Step {step_idx} execution failed: {e}")
                failed_steps.add(step_idx)

                # Checkpoint failure
                await self._checkpoint_step_result(
                    plan, step_idx, {"status": "ERROR", "error": str(e)}, envelope
                )

        # Synthesize final result
        successful_steps = len(completed_steps)
        total_steps = len(plan.steps)

        if successful_steps == total_steps:
            status = "success"
            response = f"Completed all {total_steps} steps successfully"
        elif successful_steps > 0:
            status = "partial_success"
            response = f"Completed {successful_steps}/{total_steps} steps"
        else:
            status = "failed"
            response = "All steps failed"

        return {
            "status": status,
            "response": response,
            "plan_id": plan.plan_id,
            "completed_steps": successful_steps,
            "total_steps": total_steps,
            "results": results,
        }

    async def _checkpoint_step_result(
        self, plan: MultiStepPlan, step_idx: int, result: Dict[str, Any], envelope: CoreEnvelope
    ) -> None:
        """Checkpoint step execution result to DMS."""
        # This would need DMS dependency injection to work properly
        # For now, we'll just log it

    def _extract_research_topic(self, query: str) -> str:
        """Extract research topic from query."""
        # Simple extraction - could be more sophisticated
        import re

        # Look for "research X" or "about X"
        match = re.search(r"research\s+(.+?)(?:\s+and|\s*$)", query, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        match = re.search(r"about\s+(.+?)(?:\s+and|\s*$)", query, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return query

    def _extract_multiple_expressions(self, query: str) -> List[str]:
        """Extract multiple mathematical expressions from query."""
        import re

        # Find all expressions like "2+2", "calculate 5*3", etc.
        expressions = []

        # Pattern for "calculate X and Y"
        calc_match = re.search(r"calculate\s+(.+?)\s+and\s+(.+)", query, re.IGNORECASE)
        if calc_match:
            expressions.extend([calc_match.group(1).strip(), calc_match.group(2).strip()])
            return expressions

        # Look for comma-separated expressions
        if "," in query:
            parts = [p.strip() for p in query.split(",")]
            expressions.extend(parts)

        return expressions if len(expressions) > 1 else [query]
