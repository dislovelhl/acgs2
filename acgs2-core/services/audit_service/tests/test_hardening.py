import asyncio
import os
import json
from services.audit_service.blockchain.solana.solana_client import SolanaClient

async def test_env_wallet_loading():
    print("\n--- Testing Environment Wallet Loading ---")
    # Mock a private key (array of 64 bytes)
    mock_key = [1] * 64
    os.environ["SOLANA_PRIVATE_KEY"] = json.dumps(mock_key)

    client = SolanaClient({"live": True})
    loaded = await client._load_wallet()

    if loaded and client._keypair:
        print(f"PASS: Wallet loaded from ENV. Pubkey: {client._keypair.pubkey()}")
    else:
        print("FAIL: Wallet NOT loaded from ENV")

    del os.environ["SOLANA_PRIVATE_KEY"]

async def test_retry_logic():
    print("\n--- Testing Retry Logic ---")
    client = SolanaClient({"retry_count": 2, "retry_delay": 0.1})

    call_count = 0
    async def failing_func():
        nonlocal call_count
        call_count += 1
        raise Exception("Simulated RPC Failure")

    print("Executing failing func with retry...")
    try:
        await client._with_retry(failing_func)
    except Exception as e:
        print(f"Caught expected exception: {e}")

    if call_count == 3: # 1 initial + 2 retries
        print(f"PASS: Function called {call_count} times as expected")
    else:
        print(f"FAIL: Function called {call_count} times, expected 3")

async def test_network_stats():
    print("\n--- Testing Network Stats ---")
    client = SolanaClient({"compute_unit_price": 5000})
    stats = await client.get_network_stats()
    print(f"Stats: {json.dumps(stats, indent=2)}")

    if stats["compute_unit_price"] == 5000:
        print("PASS: Compute unit price correctly reported")
    else:
        print("FAIL: Compute unit price NOT correctly reported")

async def main():
    await test_env_wallet_loading()
    await test_retry_logic()
    await test_network_stats()

if __name__ == "__main__":
    asyncio.run(main())
