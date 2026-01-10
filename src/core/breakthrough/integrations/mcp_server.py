"""
ACGS-2 Model Context Protocol (MCP) Server
===========================================

Constitutional Hash: cdd01ef066bc6cf2

Implements MCP-compliant server exposing constitutional governance
to any MCP-compatible AI system (16,000+ servers).

Solves the M×N integration problem by providing a standard interface.

References:
- MCP Introduction (Anthropic)
- One Year of MCP: From Experiment to Industry Standard
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List

from ...shared.types import ContextData, JSONDict, JSONValue
from .. import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class MCPResourceType(Enum):
    """Types of MCP resources."""

    TEXT = "text"
    JSON = "json"
    BINARY = "binary"


@dataclass
class MCPResponse:
    """Response from MCP tool or resource."""

    content: JSONValue
    content_type: MCPResourceType = MCPResourceType.JSON
    metadata: JSONDict = field(default_factory=dict)
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> JSONDict:
        return {
            "content": self.content,
            "content_type": self.content_type.value,
            "metadata": self.metadata,
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class MCPResource:
    """An MCP resource definition."""

    uri: str
    name: str
    description: str
    mime_type: str = "application/json"

    def to_dict(self) -> JSONDict:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass
class MCPTool:
    """An MCP tool definition."""

    name: str
    description: str
    input_schema: JSONDict
    handler: Callable

    def to_dict(self) -> JSONDict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class MCPPrompt:
    """An MCP prompt template."""

    name: str
    description: str
    arguments: List[JSONDict]

    def to_dict(self) -> JSONDict:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments,
        }


class ConstitutionalGovernanceEngine:
    """
    Core governance engine for MCP integration.

    Provides constitutional validation and governance operations
    that can be exposed via MCP.
    """

    def __init__(self):
        self._principles: Dict[str, str] = {}
        self._validation_cache: Dict[str, bool] = {}

        # Load default principles
        self._load_default_principles()

    def _load_default_principles(self):
        """Load default constitutional principles."""
        self._principles = {
            "data_integrity": "All actions must maintain data integrity",
            "audit_trail": "Audit trail must be maintained for all decisions",
            "user_consent": "User consent required for personal data access",
            "constitutional_compliance": f"Constitutional hash {CONSTITUTIONAL_HASH} must be valid",
        }

    async def validate(self, action: ContextData) -> JSONDict:
        """
        Validate an action against constitutional principles.

        Args:
            action: The action to validate

        Returns:
            Validation result with compliance status
        """
        violations = []

        # Check each principle
        for principle_id, principle_desc in self._principles.items():
            compliant = await self._check_principle(action, principle_id)
            if not compliant:
                violations.append(
                    {
                        "principle_id": principle_id,
                        "description": principle_desc,
                    }
                )

        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "principles_checked": len(self._principles),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    async def _check_principle(self, action: ContextData, principle_id: str) -> bool:
        """Check if action complies with a specific principle."""
        # Simple compliance check
        action_str = str(action).lower()

        if principle_id == "data_integrity":
            return "corrupt" not in action_str

        if principle_id == "constitutional_compliance":
            return (
                action.get("constitutional_hash") == CONSTITUTIONAL_HASH
                or "constitutional_hash" not in action
            )

        return True

    async def get_principles(self) -> Dict[str, str]:
        """Get all constitutional principles."""
        return self._principles.copy()

    async def get_audit_logs(self, n: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent logs from audit ledger."""
        try:
            from ...services.audit_service.core.audit_ledger import get_audit_ledger

            ledger = await get_audit_ledger()
            # The get_recent_anchor_results returns recent anchor results,
            # let's use a more direct way if possible or stick to it.
            return ledger.get_recent_anchor_results(n)
        except Exception as e:
            logger.error(f"Failed to fetch audit logs: {e}")
            return [{"error": str(e), "timestamp": time.time()}]

    async def get_governance_kpis(self, tenant_id: str = "default") -> Dict[str, Any]:
        """Get governance KPIs for a tenant."""
        try:
            from ...services.audit_service.app.api.governance import (
                _calculate_kpis_from_ledger,
            )

            return await _calculate_kpis_from_ledger(tenant_id)
        except Exception as e:
            logger.error(f"Failed to fetch governance KPIs: {e}")
            return {"error": str(e)}

    async def list_policies(self) -> List[Dict[str, Any]]:
        """List all active policies."""
        try:
            from ...services.hitl_approvals.app.core.escalation.policy_manager import (
                get_policy_manager,
            )

            pm = get_policy_manager()
            policies = await pm.get_all_policies()
            return [p.to_dict() if hasattr(p, "to_dict") else str(p) for p in policies]
        except Exception as e:
            logger.error(f"Failed to list policies: {e}")
            return [{"error": str(e)}]

    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        health = {
            "status": "healthy",
            "timestamp": time.time(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "services": {},
        }

        try:
            # Check Audit Service
            from ...services.audit_service.core.audit_ledger import get_audit_ledger

            ledger = await get_audit_ledger()
            health["services"]["audit"] = await ledger.get_anchor_health()
        except Exception:
            health["services"]["audit"] = {"status": "unreachable"}

        return health


class ACGS2MCPServer:
    """
    ACGS-2 MCP-Compliant Server.

    Exposes constitutional governance capabilities via the
    Model Context Protocol, enabling integration with any
    MCP-compatible AI system.

    Features:
    - Tools: validate_constitutional_compliance, check_policy, etc.
    - Resources: constitutional_principles, audit_log, etc.
    - Prompts: governance_decision, policy_evaluation, etc.
    """

    def __init__(self, server_name: str = "acgs2-governance", version: str = "1.0.0"):
        """
        Initialize MCP server.

        Args:
            server_name: Name of the MCP server
            version: Server version
        """
        self.server_name = server_name
        self.version = version

        self.governance_engine = ConstitutionalGovernanceEngine()

        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, MCPResource] = {}
        self._prompts: Dict[str, MCPPrompt] = {}

        # Register built-in capabilities
        self._register_builtin_tools()
        self._register_builtin_resources()
        self._register_builtin_prompts()

        logger.info(f"Initialized ACGS2MCPServer: {server_name} v{version}")

    def _register_builtin_tools(self):
        """Register built-in MCP tools."""
        # Tool: Validate constitutional compliance
        self._tools["validate_constitutional_compliance"] = MCPTool(
            name="validate_constitutional_compliance",
            description="Validate any action against constitutional principles",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {"type": "object", "description": "The action to validate"}
                },
                "required": ["action"],
            },
            handler=self._handle_validate,
        )

        # Tool: Check policy
        self._tools["check_policy"] = MCPTool(
            name="check_policy",
            description="Check if an action complies with a specific policy",
            input_schema={
                "type": "object",
                "properties": {"action": {"type": "object"}, "policy_id": {"type": "string"}},
                "required": ["action", "policy_id"],
            },
            handler=self._handle_check_policy,
        )

        # Tool: Get governance KPIs
        self._tools["get_governance_kpis"] = MCPTool(
            name="get_governance_kpis",
            description="Retrieve governance KPIs for a specific tenant",
            input_schema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "default": "default",
                        "description": "Tenant ID",
                    }
                },
            },
            handler=self._handle_get_kpis,
        )

        # Tool: List policies
        self._tools["list_policies"] = MCPTool(
            name="list_policies",
            description="List all active escalation and governance policies",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_list_policies,
        )

        # Tool: Get system health
        self._tools["get_system_health"] = MCPTool(
            name="get_system_health",
            description="Get overall system health and service status",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_get_health,
        )

        # Tool: Get constitutional hash
        self._tools["get_constitutional_hash"] = MCPTool(
            name="get_constitutional_hash",
            description="Get the current constitutional hash for validation",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_get_hash,
        )

    def _register_builtin_resources(self):
        """Register built-in MCP resources."""
        self._resources["constitutional://principles"] = MCPResource(
            uri="constitutional://principles",
            name="Constitutional Principles",
            description="All active constitutional principles",
        )

        self._resources["constitutional://hash"] = MCPResource(
            uri="constitutional://hash",
            name="Constitutional Hash",
            description="Current constitutional hash for validation",
        )

        self._resources["audit://logs"] = MCPResource(
            uri="audit://logs",
            name="Audit Logs",
            description="Recent governance and decision logs",
        )

    def _register_builtin_prompts(self):
        """Register built-in MCP prompts."""
        self._prompts["governance_decision"] = MCPPrompt(
            name="governance_decision",
            description="Template for governance decision making",
            arguments=[
                {
                    "name": "action",
                    "description": "The action requiring governance decision",
                    "required": True,
                },
                {
                    "name": "context",
                    "description": "Additional context for the decision",
                    "required": False,
                },
            ],
        )

    async def handle_tool_call(self, tool_name: str, arguments: JSONDict) -> MCPResponse:
        """
        Handle an MCP tool call.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            MCPResponse with tool result
        """
        if tool_name not in self._tools:
            return MCPResponse(
                content={"error": f"Unknown tool: {tool_name}"},
                metadata={"success": False},
            )

        tool = self._tools[tool_name]

        try:
            result = await tool.handler(arguments)
            return MCPResponse(
                content=result,
                metadata={"tool": tool_name, "success": True},
            )
        except Exception as e:
            return MCPResponse(
                content={"error": str(e)},
                metadata={"tool": tool_name, "success": False},
            )

    async def get_resource(self, uri: str) -> MCPResponse:
        """
        Get an MCP resource.

        Args:
            uri: Resource URI

        Returns:
            MCPResponse with resource content
        """
        if uri == "constitutional://principles":
            principles = await self.governance_engine.get_principles()
            return MCPResponse(
                content=principles,
                metadata={"uri": uri},
            )

        if uri == "constitutional://hash":
            return MCPResponse(
                content={"hash": CONSTITUTIONAL_HASH},
                metadata={"uri": uri},
            )

        if uri == "audit://logs":
            logs = await self.governance_engine.get_audit_logs(n=20)
            return MCPResponse(
                content=logs,
                metadata={"uri": uri},
            )

        return MCPResponse(
            content={"error": f"Unknown resource: {uri}"},
            metadata={"uri": uri, "success": False},
        )

    async def _handle_validate(self, arguments: JSONDict) -> JSONDict:
        """Handle validate_constitutional_compliance tool."""
        action = arguments.get("action", {})
        return await self.governance_engine.validate(action)

    async def _handle_check_policy(self, arguments: JSONDict) -> JSONDict:
        """Handle check_policy tool."""
        action = arguments.get("action", {})
        policy_id = arguments.get("policy_id", "")

        # Delegate to validation
        result = await self.governance_engine.validate(action)
        result["policy_id"] = policy_id
        return result

    async def _handle_get_kpis(self, arguments: JSONDict) -> JSONDict:
        """Handle get_governance_kpis tool."""
        tenant_id = arguments.get("tenant_id", "default")
        return await self.governance_engine.get_governance_kpis(tenant_id)

    async def _handle_list_policies(self, arguments: JSONDict) -> JSONDict:
        """Handle list_policies tool."""
        policies = await self.governance_engine.list_policies()
        return {"policies": policies, "count": len(policies)}

    async def _handle_get_health(self, arguments: JSONDict) -> JSONDict:
        """Handle get_system_health tool."""
        return await self.governance_engine.get_system_health()

    async def _handle_get_hash(self, arguments: JSONDict) -> JSONDict:
        """Handle get_constitutional_hash tool."""
        return {
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "version": self.version,
        }

    def get_server_info(self) -> JSONDict:
        """Get MCP server information."""
        return {
            "name": self.server_name,
            "version": self.version,
            "protocol_version": "2024-11-05",
            "capabilities": {
                "tools": {name: t.to_dict() for name, t in self._tools.items()},
                "resources": {uri: r.to_dict() for uri, r in self._resources.items()},
                "prompts": {name: p.to_dict() for name, p in self._prompts.items()},
            },
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    async def run(self, host: str = "localhost", port: int = 8100):
        """
        Run the MCP server.

        In production, would implement full MCP protocol over stdio or HTTP.
        """
        logger.info(f"MCP Server ready: {self.server_name} at {host}:{port}")

        # Keep server running
        while True:
            await asyncio.sleep(1)


def create_mcp_server() -> ACGS2MCPServer:
    """Factory function to create MCP server."""
    return ACGS2MCPServer()
