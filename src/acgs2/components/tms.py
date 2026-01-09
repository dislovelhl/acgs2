"""
Tool Mediation System (TMS) Implementation

The TMS executes external tools in a sandboxed environment with normalization
of inputs/outputs and comprehensive telemetry recording.

Key features:
- Sandboxed tool execution
- I/O normalization and validation
- Telemetry and performance monitoring
- Tool registry with capability management
- Error handling and retry logic
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from src.core.shared.security import safe_eval_expr

from ..core.interfaces import (
    AuditLedgerInterface,
    ObservabilitySystemInterface,
    ToolMediationSystemInterface,
)
from ..core.schemas import (
    AuditEntry,
    CoreEnvelope,
    TelemetryEvent,
    ToolCallRequest,
    ToolResult,
    ToolStatus,
)

logger = logging.getLogger(__name__)


class ToolMediationSystem(ToolMediationSystemInterface):
    """Tool Mediation System - Sandboxed tool execution with telemetry."""

    def __init__(
        self,
        config: Dict[str, Any],
        obs: ObservabilitySystemInterface = None,
        aud: AuditLedgerInterface = None,
    ):
        self.config = config
        self.obs = obs
        self.aud = aud
        self._running = True

        # Tool registry: name -> (capability, handler_function, metadata)
        self.tool_registry: Dict[str, Dict[str, Any]] = {}

        # Execution statistics
        self.execution_stats: Dict[str, Dict[str, Any]] = {}

        # Built-in tools will be registered lazily

        logger.info(f"TMS initialized with {len(self.tool_registry)} built-in tools")

    @property
    def component_name(self) -> str:
        return "TMS"

    async def health_check(self) -> Dict[str, Any]:
        """Health check for TMS."""
        return {
            "component": self.component_name,
            "status": "healthy" if self._running else "unhealthy",
            "registered_tools": len(self.tool_registry),
            "total_executions": sum(
                stats.get("total_calls", 0) for stats in self.execution_stats.values()
            ),
        }

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("TMS shutting down")
        self._running = False
        self.tool_registry.clear()

    async def execute(self, request: ToolCallRequest, envelope: CoreEnvelope) -> ToolResult:
        """
        Execute tool after safety validation (SAS should have already validated).

        This implements sandboxed execution with timeout, resource limits,
        and comprehensive error handling.
        """
        if not self._running:
            return ToolResult(
                tool_name=request.tool_name,
                status=ToolStatus.ERROR,
                error={"code": "TMS_UNAVAILABLE", "message": "Tool system is shutting down"},
            )

        # Ensure built-in tools are registered
        if not self.tool_registry:
            await self._register_builtin_tools()

        # Validate tool exists
        if request.tool_name not in self.tool_registry:
            logger.warning(f"Unknown tool requested: {request.tool_name}")
            return ToolResult(
                tool_name=request.tool_name,
                status=ToolStatus.ERROR,
                error={
                    "code": "TOOL_NOT_FOUND",
                    "message": f"Tool '{request.tool_name}' not registered",
                },
            )

        tool_info = self.tool_registry[request.tool_name]
        handler = tool_info["handler"]

        # Validate arguments
        validation_result = await self.validate_tool_args(request.tool_name, request.args)
        if not validation_result:
            return ToolResult(
                tool_name=request.tool_name,
                status=ToolStatus.ERROR,
                error={"code": "INVALID_ARGS", "message": "Tool arguments failed validation"},
            )

        # Execute with sandboxing
        start_time = time.time()
        try:
            # Apply sandbox profile
            sandbox_config = self._get_sandbox_config(request.sandbox_profile)

            # Execute with timeout
            timeout = self.config.get("tool_timeout_seconds", 30)
            result = await asyncio.wait_for(
                self._execute_with_sandbox(handler, request.args, sandbox_config), timeout=timeout
            )

            execution_time = time.time() - start_time

            # Record successful execution
            await self._record_execution(request.tool_name, True, execution_time)

            tool_result = ToolResult(
                tool_name=request.tool_name,
                status=ToolStatus.OK,
                result=result,
                telemetry={
                    "latency_ms": int(execution_time * 1000),
                    "sandbox_profile": request.sandbox_profile,
                    "resource_cost": self._estimate_resource_cost(request, execution_time),
                },
            )

            # Emit telemetry and audit for successful tool execution
            await self._emit_tool_events(request, envelope, tool_result, execution_time)

            return tool_result

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            await self._record_execution(request.tool_name, False, execution_time, "TIMEOUT")

            tool_result = ToolResult(
                tool_name=request.tool_name,
                status=ToolStatus.ERROR,
                error={"code": "TIMEOUT", "message": f"Tool execution timed out after {timeout}s"},
                telemetry={"latency_ms": int(execution_time * 1000)},
            )

            await self._emit_tool_events(request, envelope, tool_result, execution_time)
            return tool_result

        except Exception as e:
            execution_time = time.time() - start_time
            error_code = type(e).__name__.upper()
            await self._record_execution(request.tool_name, False, execution_time, error_code)

            logger.error(f"Tool {request.tool_name} execution failed: {e}")

            tool_result = ToolResult(
                tool_name=request.tool_name,
                status=ToolStatus.ERROR,
                error={"code": error_code, "message": str(e)},
                telemetry={"latency_ms": int(execution_time * 1000)},
            )

            await self._emit_tool_events(request, envelope, tool_result, execution_time)
            return tool_result

    async def register_tool(self, name: str, capability: str, handler: Callable) -> bool:
        """Register new tool capability."""
        try:
            self.tool_registry[name] = {
                "capability": capability,
                "handler": handler,
                "registered_at": time.time(),
                "metadata": {
                    "async": asyncio.iscoroutinefunction(handler),
                },
            }

            # Initialize stats
            self.execution_stats[name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_latency_ms": 0,
                "error_types": {},
            }

            logger.info(f"Registered tool: {name} ({capability})")
            return True

        except Exception as e:
            logger.error(f"Failed to register tool {name}: {e}")
            return False

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools with metadata."""
        tools = []
        for name, info in self.tool_registry.items():
            stats = self.execution_stats.get(name, {})
            tools.append(
                {
                    "name": name,
                    "capability": info["capability"],
                    "stats": {
                        "total_calls": stats.get("total_calls", 0),
                        "success_rate": self._calculate_success_rate(stats),
                        "avg_latency_ms": self._calculate_avg_latency(stats),
                    },
                }
            )
        return tools

    async def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """Get execution statistics for tool."""
        if tool_name not in self.execution_stats:
            return {"error": "Tool not found"}

        stats = self.execution_stats[tool_name]
        return {
            "tool_name": tool_name,
            "total_calls": stats["total_calls"],
            "successful_calls": stats["successful_calls"],
            "failed_calls": stats["failed_calls"],
            "success_rate": self._calculate_success_rate(stats),
            "avg_latency_ms": self._calculate_avg_latency(stats),
            "error_breakdown": stats["error_types"],
        }

    async def validate_tool_args(self, tool_name: str, args: Dict[str, Any]) -> bool:
        """Validate tool arguments."""
        if tool_name not in self.tool_registry:
            return False

        self.tool_registry[tool_name]

        # Basic validation - could be enhanced with JSON schema
        if not isinstance(args, dict):
            return False

        # Tool-specific validation
        if tool_name == "search":
            return "query" in args and isinstance(args["query"], str) and len(args["query"]) > 0
        elif tool_name == "calculator":
            return "expression" in args and isinstance(args["expression"], str)
        elif tool_name == "weather":
            return "location" in args and isinstance(args["location"], str)

        # Default: accept any non-empty args
        return len(args) > 0

    async def _register_builtin_tools(self) -> None:
        """Register built-in tools."""

        # Search tool
        async def search_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            query = args.get("query", "")
            # Mock search implementation
            return {
                "results": [
                    {
                        "title": f"Result for '{query}'",
                        "url": f"https://example.com/{query.replace(' ', '_')}",
                    },
                    {
                        "title": f"Another result for '{query}'",
                        "url": f"https://example.com/another_{query.replace(' ', '_')}",
                    },
                ]
            }

        await self.register_tool("search", "search", search_tool)

        # Calculator tool
        async def calculator_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            expression = args.get("expression", "")
            try:
                # Use safe AST-based evaluation for all expressions
                result = safe_eval_expr(expression)
                return {"result": result}

            except Exception as e:
                raise ValueError(f"Invalid expression: {expression}") from e

        await self.register_tool("calculator", "compute", calculator_tool)

        # Weather tool
        async def weather_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            location = args.get("location", "")
            # Mock weather implementation
            return {
                "location": location,
                "temperature": 72,
                "conditions": "sunny",
                "humidity": 45,
            }

        await self.register_tool("weather", "api_call", weather_tool)

    async def _execute_with_sandbox(
        self, handler: Callable, args: Dict[str, Any], sandbox_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool within sandbox constraints."""
        # In a real implementation, this would use containerization, resource limits, etc.
        # For now, just call the handler directly

        if asyncio.iscoroutinefunction(handler):
            return await handler(args)
        else:
            # Run in thread pool for sync functions
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, handler, args)

    def _get_sandbox_config(self, profile: str) -> Dict[str, Any]:
        """Get sandbox configuration for profile."""
        profiles = {
            "default": {
                "memory_limit": "100MB",
                "cpu_limit": "0.5",
                "network_access": True,
            },
            "restricted": {
                "memory_limit": "50MB",
                "cpu_limit": "0.2",
                "network_access": False,
            },
            "networkless": {
                "memory_limit": "100MB",
                "cpu_limit": "0.5",
                "network_access": False,
            },
        }
        return profiles.get(profile, profiles["default"])

    async def _record_execution(
        self, tool_name: str, success: bool, latency: float, error_type: Optional[str] = None
    ) -> None:
        """Record tool execution statistics."""
        if tool_name not in self.execution_stats:
            self.execution_stats[tool_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_latency_ms": 0,
                "error_types": {},
            }

        stats = self.execution_stats[tool_name]
        stats["total_calls"] += 1
        stats["total_latency_ms"] += latency * 1000

        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
            if error_type:
                stats["error_types"][error_type] = stats["error_types"].get(error_type, 0) + 1

    def _calculate_success_rate(self, stats: Dict[str, Any]) -> float:
        """Calculate success rate from stats."""
        total = stats.get("total_calls", 0)
        if total == 0:
            return 0.0
        successful = stats.get("successful_calls", 0)
        return successful / total

    def _calculate_avg_latency(self, stats: Dict[str, Any]) -> float:
        """Calculate average latency from stats."""
        total_calls = stats.get("total_calls", 0)
        total_latency = stats.get("total_latency_ms", 0)
        if total_calls == 0:
            return 0.0
        return total_latency / total_calls

    def _estimate_resource_cost(self, request: ToolCallRequest, execution_time: float) -> str:
        """Estimate resource cost of tool execution."""
        # Simple estimation based on tool type and execution time
        base_cost = 0.01  # Base cost per execution

        if request.capability == "api_call":
            base_cost *= 2  # API calls are more expensive
        elif request.capability == "compute":
            base_cost *= 1.5  # Computation is moderately expensive

        time_factor = min(execution_time, 60) / 10  # Cap at 60 seconds, normalize to decaseconds

        return f"${base_cost * (1 + time_factor):.4f}"

    async def _emit_tool_events(
        self,
        request: ToolCallRequest,
        envelope: CoreEnvelope,
        result: ToolResult,
        execution_time: float,
    ) -> None:
        """Emit telemetry and audit events for tool execution."""
        if not self.obs or not self.aud:
            return

        timestamp = datetime.now(timezone.utc).isoformat()
        latency_ms = int(execution_time * 1000)

        # Emit telemetry
        telemetry_event = TelemetryEvent(
            timestamp=timestamp,
            request_id=envelope.request_id,
            component=self.component_name,
            event_type="tool_execution",
            latency_ms=latency_ms,
            metadata={
                "tool_name": result.tool_name,
                "capability": request.capability,
                "status": result.status.name,
                "resource_cost": result.telemetry.get("resource_cost", "N/A"),
                "error_code": result.error.get("code") if result.error else None,
            },
        )
        await self.obs.emit_event(telemetry_event)

        # Emit audit entry
        audit_entry = AuditEntry(
            entry_id=f"{envelope.request_id}_tool_{result.tool_name}",
            timestamp=timestamp,
            request_id=envelope.request_id,
            session_id=envelope.session_id,
            actor=self.component_name,
            action_type="tool_execution",
            payload={
                "tool_name": result.tool_name,
                "capability": request.capability,
                "status": result.status.name,
                "latency_ms": latency_ms,
                "resource_cost": result.telemetry.get("resource_cost"),
                "args_summary": {k: str(type(v).__name__) for k, v in request.args.items()},
                "error": result.error if result.error else None,
                "result_summary": (
                    str(result.result)[:200] + "..."
                    if result.result and len(str(result.result)) > 200
                    else str(result.result)
                ),
            },
        )
        await self.aud.append_entry(audit_entry)
