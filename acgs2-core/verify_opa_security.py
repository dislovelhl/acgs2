
import asyncio
import json
from enhanced_agent_bus.opa_client import OPAClient

async def test_opa_security():
    client = OPAClient(mode="fallback")

    print("--- Testing Policy Path Validation ---")
    res = await client.evaluate_policy({"test": 1}, "data.acgs..invalid")
    if res["allowed"] is False and "Path traversal" in res["reason"]:
        print("PASS: Caught invalid path (..)")
    else:
        print(f"FAIL: Result: {res}")

    res = await client.evaluate_policy({"test": 1}, "data.acgs;injection")
    if res["allowed"] is False and "Invalid policy path" in res["reason"]:
        print("PASS: Caught injection path (;)")
    else:
        print(f"FAIL: Result: {res}")

    print("\n--- Testing Input Size Validation ---")
    large_input = {"data": "x" * (1024 * 600)}  # > 512KB
    res = await client.evaluate_policy(large_input, "data.acgs.allow")
    if res["allowed"] is False and "exceeds maximum allowed size" in res["reason"]:
        print("PASS: Caught large input")
    else:
        print(f"FAIL: Result: {res}")

    print("\n--- Testing Error Sanitization ---")
    # Wrap a fake error
    try:
        raise Exception("Sensitive URL: https://admin:password@opa.internal/v1/data?token=secret123")
    except Exception as e:
        sanitized = client._sanitize_error(e)
        print(f"Original: {e}")
        print(f"Sanitized: {sanitized}")
        if "password" not in sanitized and "secret123" not in sanitized:
            print("PASS: Error sanitized")
        else:
            print("FAIL: Error NOT sanitized")

if __name__ == "__main__":
    asyncio.run(test_opa_security())
