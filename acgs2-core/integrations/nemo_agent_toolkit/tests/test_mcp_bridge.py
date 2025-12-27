"""
Tests for MCP Bridge
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
from datetime import UTC, datetime

from nemo_agent_toolkit.mcp_bridge import (
    ACGS2MCPServer,
    ACGS2MCPClient,
    MCPToolDefinition,
    MCPToolResult,
    MCPToolType,
    ConstitutionalMCPTool,
    CONSTITUTIONAL_HASH,
)


class TestMCPToolDefinition:
    """Tests for MCPToolDefinition."""

    def test_create_definition(self):
        """Test creating a tool definition."""
        definition = MCPToolDefinition(
            name="test_tool",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {"arg1": {"type": "string"}},
            },
        )
        assert definition.name == "test_tool"
        assert definition.description == "A test tool"
        assert definition.constitutional_required is True

    def test_definition_without_constitutional(self):
        """Test definition without constitutional requirement."""
        definition = MCPToolDefinition(
            name="public_tool",
            description="Public tool",
            input_schema={},
            constitutional_required=False,
        )
        assert definition.constitutional_required is False


class TestMCPToolResult:
    """Tests for MCPToolResult."""

    def test_success_result(self):
        """Test successful result."""
        result = MCPToolResult(
            success=True,
            data={"key": "value"},
        )
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.constitutional_hash == CONSTITUTIONAL_HASH

    def test_error_result(self):
        """Test error result."""
        result = MCPToolResult(
            success=False,
            data=None,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = MCPToolResult(
            success=True,
            data={"test": 123},
        )
        data = result.to_dict()
        assert data["success"] is True
        assert data["data"] == {"test": 123}
        assert data["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert "timestamp" in data


class TestConstitutionalMCPTool:
    """Tests for ConstitutionalMCPTool."""

    def test_create_tool(self):
        """Test creating a constitutional MCP tool."""
        def handler(arg1: str) -> dict:
            return {"result": arg1}

        tool = ConstitutionalMCPTool(
            definition=MCPToolDefinition(
                name="test_tool",
                description="Test",
                input_schema={},
            ),
            handler=handler,
        )
        assert tool.definition.name == "test_tool"
        assert tool.requires_approval is False
        assert tool.audit_enabled is True

    def test_tool_with_approval(self):
        """Test tool requiring approval."""
        tool = ConstitutionalMCPTool(
            definition=MCPToolDefinition(
                name="sensitive_tool",
                description="Sensitive operation",
                input_schema={},
            ),
            handler=lambda: None,
            requires_approval=True,
        )
        assert tool.requires_approval is True


class TestACGS2MCPServer:
    """Tests for ACGS2MCPServer."""

    @pytest.fixture
    def server(self):
        """Create MCP server for testing."""
        return ACGS2MCPServer()

    def test_server_initialization(self, server):
        """Test server initializes with default tools."""
        tools = server.get_tool_definitions()
        tool_names = [t["name"] for t in tools]

        assert "acgs2_validate_constitutional" in tool_names
        assert "acgs2_check_compliance" in tool_names
        assert "acgs2_audit_action" in tool_names
        assert "acgs2_get_policies" in tool_names
        assert "acgs2_submit_approval" in tool_names
        assert "acgs2_check_governance" in tool_names

    def test_get_tool_definitions(self, server):
        """Test getting tool definitions."""
        tools = server.get_tool_definitions()
        assert len(tools) >= 6

        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    def test_register_custom_tool(self, server):
        """Test registering a custom tool."""
        def custom_handler(value: str) -> dict:
            return {"processed": value}

        tool = ConstitutionalMCPTool(
            definition=MCPToolDefinition(
                name="custom_tool",
                description="Custom tool",
                input_schema={
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                },
            ),
            handler=custom_handler,
        )
        server.register_tool(tool)

        tools = server.get_tool_definitions()
        tool_names = [t["name"] for t in tools]
        assert "custom_tool" in tool_names

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, server):
        """Test calling unknown tool."""
        result = await server.call_tool("unknown_tool", {})
        assert result.success is False
        assert "Unknown tool" in result.error

    @pytest.mark.asyncio
    async def test_call_validate_constitutional(self, server):
        """Test calling validate_constitutional tool."""
        result = await server.call_tool(
            "acgs2_validate_constitutional",
            {
                "agent_id": "test-agent",
                "action": "test_action",
                "context": {"key": "value"},
            },
        )
        assert result.success is True
        assert result.data is not None
        assert result.data.get("constitutional_hash") == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_call_check_compliance(self, server):
        """Test calling check_compliance tool."""
        result = await server.call_tool(
            "acgs2_check_compliance",
            {
                "context": {"action": "test"},
            },
        )
        assert result.success is True
        assert result.data.get("constitutional_hash") == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_call_audit_action(self, server):
        """Test calling audit_action tool."""
        result = await server.call_tool(
            "acgs2_audit_action",
            {
                "action": "test_action",
                "actor": "test_user",
                "resource": "test_resource",
                "outcome": "success",
            },
        )
        assert result.success is True
        assert result.data.get("recorded") is True

    @pytest.mark.asyncio
    async def test_call_get_policies(self, server):
        """Test calling get_policies tool."""
        result = await server.call_tool(
            "acgs2_get_policies",
            {},
        )
        assert result.success is True
        assert "policies" in result.data

    @pytest.mark.asyncio
    async def test_call_submit_approval(self, server):
        """Test calling submit_approval tool."""
        result = await server.call_tool(
            "acgs2_submit_approval",
            {
                "request_type": "test_approval",
                "payload": {"test": "data"},
            },
        )
        assert result.success is True
        assert result.data.get("submitted") is True

    @pytest.mark.asyncio
    async def test_call_check_governance(self, server):
        """Test calling check_governance tool."""
        result = await server.call_tool(
            "acgs2_check_governance",
            {"include_metrics": True},
        )
        assert result.success is True
        assert result.data.get("status") == "operational"
        assert result.data.get("constitutional_hash") == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_audit_logging(self, server):
        """Test audit logging is enabled."""
        await server.call_tool(
            "acgs2_validate_constitutional",
            {"agent_id": "test", "action": "test"},
        )
        audit_log = server.get_audit_log()
        assert len(audit_log) >= 1
        assert audit_log[-1]["tool_name"] == "acgs2_validate_constitutional"

    @pytest.mark.asyncio
    async def test_constitutional_hash_mismatch(self, server):
        """Test rejecting mismatched constitutional hash."""
        result = await server.call_tool(
            "acgs2_validate_constitutional",
            {
                "agent_id": "test",
                "action": "test",
                "constitutional_hash": "wrong_hash",
            },
        )
        assert result.success is False
        assert "Constitutional hash mismatch" in result.error


class TestACGS2MCPClient:
    """Tests for ACGS2MCPClient."""

    @pytest.fixture
    def client(self):
        """Create MCP client for testing."""
        return ACGS2MCPClient(
            server_url="https://test.acgs.io",
            api_key="test-key",
        )

    def test_client_initialization(self, client):
        """Test client initialization."""
        assert client._server_url == "https://test.acgs.io"
        assert client._api_key == "test-key"
        assert client._connected is False

    @pytest.mark.asyncio
    async def test_connect(self, client):
        """Test connecting to server."""
        await client.connect()
        assert client._connected is True

    @pytest.mark.asyncio
    async def test_disconnect(self, client):
        """Test disconnecting from server."""
        await client.connect()
        await client.disconnect()
        assert client._connected is False

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager."""
        async with client as c:
            assert c._connected is True
        assert client._connected is False

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self, client):
        """Test calling tool when not connected."""
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.call_tool("test_tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_connected(self, client):
        """Test calling tool when connected."""
        await client.connect()
        result = await client.call_tool("test_tool", {"arg": "value"})
        assert result.success is True
        assert result.data["arguments"]["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_validate_constitutional_convenience(self, client):
        """Test validate_constitutional convenience method."""
        await client.connect()
        result = await client.validate_constitutional(
            agent_id="test-agent",
            action="test-action",
            context={"key": "value"},
        )
        assert "tool" in result
        assert result["tool"] == "acgs2_validate_constitutional"

    @pytest.mark.asyncio
    async def test_check_compliance_convenience(self, client):
        """Test check_compliance convenience method."""
        await client.connect()
        result = await client.check_compliance(
            context={"action": "test"},
            policy_id="policy-123",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_audit_action_convenience(self, client):
        """Test audit_action convenience method."""
        await client.connect()
        result = await client.audit_action(
            action="test_action",
            actor="test_user",
            resource="test_resource",
            outcome="success",
        )
        assert result is not None


class TestMCPToolType:
    """Tests for MCPToolType enum."""

    def test_tool_type_values(self):
        """Test tool type enum values."""
        assert MCPToolType.VALIDATE_CONSTITUTIONAL.value == "validate_constitutional"
        assert MCPToolType.CHECK_COMPLIANCE.value == "check_compliance"
        assert MCPToolType.AUDIT_ACTION.value == "audit_action"
        assert MCPToolType.GET_POLICIES.value == "get_policies"
        assert MCPToolType.SUBMIT_APPROVAL.value == "submit_approval"
        assert MCPToolType.CHECK_GOVERNANCE.value == "check_governance"


class TestConstitutionalHashEnforcement:
    """Tests for constitutional hash enforcement in MCP."""

    def test_module_hash(self):
        """Test module-level constitutional hash."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_result_default_hash(self):
        """Test result default hash."""
        result = MCPToolResult(success=True, data={})
        assert result.constitutional_hash == "cdd01ef066bc6cf2"

    @pytest.mark.asyncio
    async def test_server_tools_include_hash(self):
        """Test server tool responses include hash."""
        server = ACGS2MCPServer()
        result = await server.call_tool(
            "acgs2_check_governance",
            {},
        )
        assert result.data.get("constitutional_hash") == "cdd01ef066bc6cf2"
