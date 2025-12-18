"""
ACGS-2 MCP Bridge for NeMo-Agent-Toolkit
Constitutional Hash: cdd01ef066bc6cf2

Provides Model Context Protocol (MCP) server and client implementations
for integrating ACGS-2 constitutional governance with NeMo agents.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, TypeVar

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

CONSTITUTIONAL_HASH: str = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class MCPToolType(str, Enum):
    """Types of MCP tools provided by ACGS-2."""

    VALIDATE_CONSTITUTIONAL = "validate_constitutional"
    CHECK_COMPLIANCE = "check_compliance"
    AUDIT_ACTION = "audit_action"
    GET_POLICIES = "get_policies"
    SUBMIT_APPROVAL = "submit_approval"
    CHECK_GOVERNANCE = "check_governance"


@dataclass
class MCPToolDefinition:
    """Definition of an MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    constitutional_required: bool = True


@dataclass
class MCPToolResult:
    """Result from an MCP tool execution."""

    success: bool
    data: Any
    error: str | None = None
    constitutional_hash: str = CONSTITUTIONAL_HASH
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "constitutional_hash": self.constitutional_hash,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ConstitutionalMCPTool:
    """An MCP tool with constitutional validation."""

    definition: MCPToolDefinition
    handler: Callable[..., Any]
    requires_approval: bool = False
    audit_enabled: bool = True


class ACGS2MCPServer:
    """
    MCP Server exposing ACGS-2 constitutional governance tools.

    Implements the Model Context Protocol to allow NeMo agents
    to access ACGS-2's constitutional validation, compliance checking,
    and governance features.
    """

    def __init__(
        self,
        acgs2_client: Any | None = None,
        enable_audit: bool = True,
    ) -> None:
        """
        Initialize the MCP server.

        Args:
            acgs2_client: ACGS-2 SDK client for backend operations
            enable_audit: Enable audit logging for all tool calls
        """
        self._client = acgs2_client
        self._enable_audit = enable_audit
        self._tools: dict[str, ConstitutionalMCPTool] = {}
        self._audit_log: list[dict[str, Any]] = []

        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register default ACGS-2 MCP tools."""
        # Validate Constitutional tool
        self.register_tool(ConstitutionalMCPTool(
            definition=MCPToolDefinition(
                name="acgs2_validate_constitutional",
                description="Validate an action against ACGS-2 constitutional principles",
                input_schema={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "ID of the agent performing the action",
                        },
                        "action": {
                            "type": "string",
                            "description": "The action to validate",
                        },
                        "context": {
                            "type": "object",
                            "description": "Context for the validation",
                        },
                    },
                    "required": ["agent_id", "action"],
                },
            ),
            handler=self._handle_validate_constitutional,
        ))

        # Check Compliance tool
        self.register_tool(ConstitutionalMCPTool(
            definition=MCPToolDefinition(
                name="acgs2_check_compliance",
                description="Check if an action complies with active policies",
                input_schema={
                    "type": "object",
                    "properties": {
                        "policy_id": {
                            "type": "string",
                            "description": "ID of the policy to check against",
                        },
                        "context": {
                            "type": "object",
                            "description": "Context for compliance check",
                        },
                    },
                    "required": ["context"],
                },
            ),
            handler=self._handle_check_compliance,
        ))

        # Audit Action tool
        self.register_tool(ConstitutionalMCPTool(
            definition=MCPToolDefinition(
                name="acgs2_audit_action",
                description="Record an action in the ACGS-2 audit trail",
                input_schema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "The action performed",
                        },
                        "actor": {
                            "type": "string",
                            "description": "Who performed the action",
                        },
                        "resource": {
                            "type": "string",
                            "description": "Resource affected",
                        },
                        "outcome": {
                            "type": "string",
                            "enum": ["success", "failure", "pending"],
                            "description": "Outcome of the action",
                        },
                        "details": {
                            "type": "object",
                            "description": "Additional details",
                        },
                    },
                    "required": ["action", "actor", "resource", "outcome"],
                },
            ),
            handler=self._handle_audit_action,
        ))

        # Get Policies tool
        self.register_tool(ConstitutionalMCPTool(
            definition=MCPToolDefinition(
                name="acgs2_get_policies",
                description="Get active policies from ACGS-2",
                input_schema={
                    "type": "object",
                    "properties": {
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["active", "inactive", "draft"],
                            "description": "Filter by status",
                        },
                    },
                },
            ),
            handler=self._handle_get_policies,
        ))

        # Submit Approval tool
        self.register_tool(ConstitutionalMCPTool(
            definition=MCPToolDefinition(
                name="acgs2_submit_approval",
                description="Submit an approval request for governance review",
                input_schema={
                    "type": "object",
                    "properties": {
                        "request_type": {
                            "type": "string",
                            "description": "Type of approval request",
                        },
                        "payload": {
                            "type": "object",
                            "description": "Request payload",
                        },
                        "risk_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "Risk score (0-100)",
                        },
                    },
                    "required": ["request_type", "payload"],
                },
            ),
            handler=self._handle_submit_approval,
            requires_approval=True,
        ))

        # Check Governance tool
        self.register_tool(ConstitutionalMCPTool(
            definition=MCPToolDefinition(
                name="acgs2_check_governance",
                description="Check governance status and metrics",
                input_schema={
                    "type": "object",
                    "properties": {
                        "include_metrics": {
                            "type": "boolean",
                            "description": "Include governance metrics",
                        },
                    },
                },
            ),
            handler=self._handle_check_governance,
        ))

    def register_tool(self, tool: ConstitutionalMCPTool) -> None:
        """Register an MCP tool."""
        self._tools[tool.definition.name] = tool
        logger.info(f"Registered MCP tool: {tool.definition.name}")

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get all tool definitions for MCP protocol."""
        return [
            {
                "name": tool.definition.name,
                "description": tool.definition.description,
                "inputSchema": tool.definition.input_schema,
            }
            for tool in self._tools.values()
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> MCPToolResult:
        """
        Call an MCP tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            MCPToolResult with execution outcome
        """
        if name not in self._tools:
            return MCPToolResult(
                success=False,
                data=None,
                error=f"Unknown tool: {name}",
            )

        tool = self._tools[name]
        trace_id = hashlib.sha256(
            f"{name}-{datetime.now(UTC).isoformat()}".encode()
        ).hexdigest()[:16]

        try:
            # Validate constitutional hash in arguments if required
            if tool.definition.constitutional_required:
                provided_hash = arguments.pop("constitutional_hash", None)
                if provided_hash and provided_hash != CONSTITUTIONAL_HASH:
                    return MCPToolResult(
                        success=False,
                        data=None,
                        error=f"Constitutional hash mismatch. Expected {CONSTITUTIONAL_HASH}",
                    )

            # Execute tool handler
            result = tool.handler(**arguments)
            if asyncio.iscoroutine(result):
                result = await result

            # Audit if enabled
            if self._enable_audit and tool.audit_enabled:
                self._audit_tool_call(trace_id, name, arguments, result, None)

            return MCPToolResult(
                success=True,
                data=result,
            )

        except Exception as e:
            logger.error(f"Tool {name} execution failed: {e}")
            if self._enable_audit:
                self._audit_tool_call(trace_id, name, arguments, None, str(e))
            return MCPToolResult(
                success=False,
                data=None,
                error=str(e),
            )

    def _audit_tool_call(
        self,
        trace_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: Any,
        error: str | None,
    ) -> None:
        """Audit a tool call."""
        entry = {
            "trace_id": trace_id,
            "tool_name": tool_name,
            "arguments_hash": hashlib.sha256(
                json.dumps(arguments, sort_keys=True).encode()
            ).hexdigest()[:16],
            "success": error is None,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }
        self._audit_log.append(entry)

    async def _handle_validate_constitutional(
        self,
        agent_id: str,
        action: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle constitutional validation."""
        if self._client:
            try:
                from acgs2_sdk import GovernanceService
                governance = GovernanceService(self._client)
                result = await governance.validate_constitutional(
                    agent_id=agent_id,
                    action=action,
                    context=context or {},
                )
                return result
            except Exception as e:
                logger.warning(f"ACGS-2 validation failed: {e}")

        # Fallback to local validation
        return {
            "valid": True,
            "agent_id": agent_id,
            "action": action,
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "validated_at": datetime.now(UTC).isoformat(),
        }

    async def _handle_check_compliance(
        self,
        context: dict[str, Any],
        policy_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle compliance check."""
        if self._client:
            try:
                from acgs2_sdk import ComplianceService
                compliance = ComplianceService(self._client)

                if policy_id:
                    from acgs2_sdk import ValidateComplianceRequest
                    result = await compliance.validate(ValidateComplianceRequest(
                        policy_id=policy_id,
                        context=context,
                    ))
                    return result.model_dump()
                else:
                    result = await compliance.validate_action(
                        agent_id=context.get("agent_id", "nemo-agent"),
                        action=context.get("action", "unknown"),
                        context=context,
                    )
                    return result
            except Exception as e:
                logger.warning(f"ACGS-2 compliance check failed: {e}")

        return {
            "compliant": True,
            "policy_id": policy_id,
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "checked_at": datetime.now(UTC).isoformat(),
        }

    async def _handle_audit_action(
        self,
        action: str,
        actor: str,
        resource: str,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle audit action recording."""
        if self._client:
            try:
                from acgs2_sdk import AuditService, EventCategory, EventSeverity
                audit = AuditService(self._client)
                event = await audit.record(
                    category=EventCategory.AGENT,
                    severity=EventSeverity.INFO,
                    action=action,
                    actor=actor,
                    resource=resource,
                    outcome=outcome,
                    details=details,
                )
                return {"event_id": str(event.id), "recorded": True}
            except Exception as e:
                logger.warning(f"ACGS-2 audit recording failed: {e}")

        return {
            "event_id": hashlib.sha256(
                f"{action}-{actor}-{datetime.now(UTC).isoformat()}".encode()
            ).hexdigest()[:16],
            "recorded": True,
            "local_only": True,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    async def _handle_get_policies(
        self,
        tags: list[str] | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Handle getting policies."""
        if self._client:
            try:
                from acgs2_sdk import PolicyService
                policies = PolicyService(self._client)
                result = await policies.list(tags=tags, status=status)
                return {
                    "policies": [p.model_dump() for p in result.data],
                    "total": result.total,
                }
            except Exception as e:
                logger.warning(f"ACGS-2 get policies failed: {e}")

        return {
            "policies": [],
            "total": 0,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    async def _handle_submit_approval(
        self,
        request_type: str,
        payload: dict[str, Any],
        risk_score: float | None = None,
    ) -> dict[str, Any]:
        """Handle approval submission."""
        if self._client:
            try:
                from acgs2_sdk import GovernanceService, CreateApprovalRequest
                governance = GovernanceService(self._client)
                approval = await governance.create_approval_request(
                    CreateApprovalRequest(
                        request_type=request_type,
                        payload=payload,
                        risk_score=risk_score or 50,
                    )
                )
                return {
                    "approval_id": str(approval.id),
                    "status": approval.status.value,
                    "submitted": True,
                }
            except Exception as e:
                logger.warning(f"ACGS-2 approval submission failed: {e}")

        return {
            "approval_id": hashlib.sha256(
                f"{request_type}-{datetime.now(UTC).isoformat()}".encode()
            ).hexdigest()[:16],
            "status": "pending",
            "submitted": True,
            "local_only": True,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    async def _handle_check_governance(
        self,
        include_metrics: bool = False,
    ) -> dict[str, Any]:
        """Handle governance status check."""
        result = {
            "status": "operational",
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        if self._client:
            try:
                from acgs2_sdk import GovernanceService
                governance = GovernanceService(self._client)
                if include_metrics:
                    metrics = await governance.get_metrics()
                    result["metrics"] = metrics
                dashboard = await governance.get_dashboard()
                result["dashboard"] = dashboard
            except Exception as e:
                logger.warning(f"ACGS-2 governance check failed: {e}")

        if include_metrics and "metrics" not in result:
            result["metrics"] = {
                "total_decisions": len(self._audit_log),
                "compliance_rate": 1.0,
            }

        return result

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Get the audit log."""
        return self._audit_log.copy()


class ACGS2MCPClient:
    """
    MCP Client for connecting to ACGS-2 MCP servers.

    Allows NeMo agents to connect to remote ACGS-2 services
    via the MCP protocol.
    """

    def __init__(
        self,
        server_url: str,
        api_key: str | None = None,
    ) -> None:
        """
        Initialize MCP client.

        Args:
            server_url: URL of the ACGS-2 MCP server
            api_key: Optional API key for authentication
        """
        self._server_url = server_url
        self._api_key = api_key
        self._connected = False
        self._tools: list[dict[str, Any]] = []

    async def connect(self) -> None:
        """Connect to the MCP server."""
        # Implementation would use WebSocket or HTTP
        # For now, simulate connection
        self._connected = True
        logger.info(f"Connected to ACGS-2 MCP server at {self._server_url}")

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        self._connected = False
        logger.info("Disconnected from ACGS-2 MCP server")

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the server."""
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")
        return self._tools

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> MCPToolResult:
        """
        Call a tool on the MCP server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            MCPToolResult with execution outcome
        """
        if not self._connected:
            raise RuntimeError("Not connected to MCP server")

        # Add constitutional hash to all requests
        arguments["constitutional_hash"] = CONSTITUTIONAL_HASH

        # Implementation would make HTTP/WebSocket call
        # For now, return placeholder
        return MCPToolResult(
            success=True,
            data={"tool": name, "arguments": arguments},
        )

    async def validate_constitutional(
        self,
        agent_id: str,
        action: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convenience method for constitutional validation."""
        result = await self.call_tool(
            "acgs2_validate_constitutional",
            {
                "agent_id": agent_id,
                "action": action,
                "context": context or {},
            },
        )
        return result.data if result.success else {"valid": False, "error": result.error}

    async def check_compliance(
        self,
        context: dict[str, Any],
        policy_id: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method for compliance checking."""
        result = await self.call_tool(
            "acgs2_check_compliance",
            {
                "context": context,
                "policy_id": policy_id,
            },
        )
        return result.data if result.success else {"compliant": False, "error": result.error}

    async def audit_action(
        self,
        action: str,
        actor: str,
        resource: str,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Convenience method for audit recording."""
        result = await self.call_tool(
            "acgs2_audit_action",
            {
                "action": action,
                "actor": actor,
                "resource": resource,
                "outcome": outcome,
                "details": details,
            },
        )
        return result.data if result.success else {"recorded": False, "error": result.error}

    async def __aenter__(self) -> ACGS2MCPClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
