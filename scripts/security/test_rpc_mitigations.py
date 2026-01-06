import asyncio
import logging

from src.core.enhanced_agent_bus.mcp_server.config import MCPConfig
from src.core.enhanced_agent_bus.mcp_server.protocol.types import ToolDefinition
from src.core.enhanced_agent_bus.mcp_server.server import MCPServer
from src.core.services.audit_service.blockchain.solana.solana_client import SolanaClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestMitigations")


async def test_mcp_registration_lock():
    print("\n--- Testing MCP Registration Lock ---")
    config = MCPConfig(server_name="test-server")
    server = MCPServer(config=config)

    # Start server (this should lock registration)
    # We use a mock start to avoid blocking on transports
    await server.connect_adapters()
    if server._handler:
        server._handler.lock_registration()
    server._running = True

    print("Server started and registration locked.")

    # Try to register a new tool
    try:

        def mock_handler(params):
            return {}

        tool_def = ToolDefinition(name="malicious_tool", description="attacker tool")
        server._handler.register_tool(tool_def, mock_handler)
        print("FAIL: Successfully registered tool after lock!")
        return False
    except RuntimeError as e:
        print(f"PASS: Caught expected error: {e}")
        return True


async def test_solana_rpc_hardening():
    print("\n--- Testing Solana RPC Hardening ---")

    # Test case 1: Insecure URL in mainnet
    config = {"network": "mainnet-beta", "rpc_url": "http://malicious-rpc.com", "live": True}
    print("Attempting to use insecure HTTP RPC in mainnet-beta...")
    try:
        client = SolanaClient(config)
        if "http://malicious-rpc.com" in client.rpc_urls:
            print("FAIL: Insecure RPC URL was accepted in mainnet!")
            return False
        else:
            print("PASS: Insecure RPC URL was blocked/removed.")
    except ValueError as e:
        print(f"PASS: Caught expected error: {e}")

    # Test case 2: Secure URL
    config = {"network": "mainnet-beta", "rpc_url": "https://secure-rpc.com", "live": True}
    print("Attempting to use secure HTTPS RPC...")
    client = SolanaClient(config)
    if "https://secure-rpc.com" in client.rpc_urls:
        print("PASS: Secure RPC URL was accepted.")
        return True
    else:
        print("FAIL: Secure RPC URL was rejected!")
        return False


async def main():
    mcp_pass = await test_mcp_registration_lock()
    solana_pass = await test_solana_rpc_hardening()

    if mcp_pass and solana_pass:
        print("\nALL SECURITY MITIGATION TESTS PASSED ✅")
    else:
        print("\nSOME SECURITY MITIGATION TESTS FAILED ❌")


if __name__ == "__main__":
    asyncio.run(main())
