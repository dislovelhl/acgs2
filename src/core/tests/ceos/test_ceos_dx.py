"""
Tests for CEOS Phase 5: DX & Ecosystem
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
from src.core.enhanced_agent_bus.dx_ecosystem import GenUIController, MCPBridge


@pytest.mark.asyncio
async def test_mcp_bridge_registration():
    """Test registering tools as MCP compliant."""
    bridge = MCPBridge("ceos-test-project")

    success = await bridge.register_tool_as_mcp(
        "sql_query_tool", {"description": "Query the enterprise DB", "schema": {"type": "object"}}
    )

    assert success
    manifest = bridge.get_manifest()
    assert len(manifest["tools"]) == 1
    assert manifest["tools"][0]["name"] == "sql_query_tool"


def test_gen_ui_schema_generation():
    """Test generating dynamic UI schemas."""
    controller = GenUIController()

    data = {
        "stats": [
            {"label": "P99 Latency", "value": "0.2ms"},
            {"label": "Compliance", "value": "100%"},
        ]
    }

    schema = controller.generate_component_schema("dashboard", data)

    assert schema["type"] == "Grid"
    assert len(schema["children"]) == 2
    assert schema["children"][0]["type"] == "StatCard"
    assert schema["children"][0]["props"]["label"] == "P99 Latency"
