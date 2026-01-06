import glob
import os
import re


def perform_recon():
    print("--- ACGS-2 RPC/gRPC Reconnaissance Report ---")
    print(f"Timestamp: {os.popen('date').read().strip()}")
    print(f"OS: {os.popen('uname -a').read().strip()}")
    print("-" * 45)

    # 1. Identify gRPC services
    print("\n[1] gRPC Interfaces (Proto files):")
    proto_files = glob.glob("**/*.proto", recursive=True)
    if not proto_files:
        # Search for gRPC in code if no .proto files found
        print("    No .proto files found. Searching for gRPC in source code...")
        grpc_mentions = os.popen('grep -r "gRPC" src/ | head -n 5').read().strip()
        if grpc_mentions:
            print(f"    gRPC mentioned in:\n{grpc_mentions}")
        else:
            print("    No gRPC mentions found in src/.")
    else:
        for f in proto_files:
            print(f"    - {f}")

    # 2. Identify JSON-RPC interfaces
    print("\n[2] JSON-RPC Interfaces (MCP Server):")
    mcp_files = glob.glob("src/core/enhanced_agent_bus/mcp_server/**/*.py", recursive=True)
    for f in mcp_files:
        if "handler.py" in f or "server.py" in f:
            print(f"    - {f}")
            with open(f, "r") as file:
                content = file.read()
                methods = re.findall(r'"([^"]+)"\s*:\s*self\._handle_', content)
                if methods:
                    print(f"      Methods: {', '.join(methods)}")

    # 3. Identify External RPC Clients
    print("\n[3] External RPC Clients (Blockchain):")
    audit_files = glob.glob("src/core/services/audit_service/blockchain/**/*.py", recursive=True)
    for f in audit_files:
        if "client.py" in f:
            print(f"    - {f}")
            with open(f, "r") as file:
                content = file.read()
                rpc_urls = re.findall(r'rpc_url["\']?\s*:\s*["\']([^"\']+)["\']', content)
                if rpc_urls:
                    print(f"      Default RPCs: {', '.join(rpc_urls)}")

    # 4. Analyze Startup Sequence (Race Window)
    print("\n[4] Startup Sequence Analysis (Potential Race Windows):")
    compose_files = ["docker-compose.dev.yml", "compose.yaml"]
    for cf in compose_files:
        if os.path.exists(cf):
            print(f"    - {cf}:")
            with open(cf, "r") as file:
                content = file.read()
                depends_on = re.findall(r"depends_on:\s*\n\s*-\s*([a-z-]+)", content)
                if depends_on:
                    print(f"      Dependencies: {', '.join(depends_on)}")

    print("\n" + "-" * 45)
    print("Reconnaissance Complete.")


if __name__ == "__main__":
    perform_recon()
