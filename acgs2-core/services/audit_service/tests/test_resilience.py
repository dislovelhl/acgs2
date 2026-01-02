import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from services.audit_service.blockchain.solana.solana_client import SolanaClient, HAS_SOLANA
import logging


async def test_multi_rpc_failover():
    logging.info("\n--- Testing Multi-RPC Failover ---")
    config = {
        "network": "devnet",
        "rpc_urls": ["http://rpc1.com", "http://rpc2.com"],
        "retry_count": 2,
        "retry_delay": 0.1,
        "live": True,
    }

    with patch("services.audit_service.blockchain.solana.solana_client.AsyncClient") as MockClient:
        # Client 1 fails, Client 2 succeeds
        mock1 = AsyncMock()
        mock1.get_version.side_effect = Exception("RPC 1 Down")

        mock2 = AsyncMock()
        mock2.get_version.return_value = MagicMock(value=MagicMock(solana_core="1.17.0"))

        MockClient.side_effect = [mock1, mock2]

        client = SolanaClient(config)
        success = await client.connect()

        logging.info(f"Connect success: {success}")
        logging.info(f"Current RPC Index: {client.current_rpc_index}")
        logging.info(f"Failover Count: {client.failover_count}")

        if success and client.current_rpc_index == 1 and client.failover_count > 0:
            logging.error("PASS: Successfully failed over to second RPC")
        else:
            logging.info("FAIL: Failover logic did not work as expected")


async def test_transaction_confirmation():
    logging.info("\n--- Testing Transaction Confirmation Polling ---")
    config = {"network": "devnet", "rpc_url": "http://mock.com", "live": True}

    with patch("services.audit_service.blockchain.solana.solana_client.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        # First check: unknown, Second check: confirmed
        resp1 = MagicMock(value=[None])
        resp2 = MagicMock(value=[MagicMock(confirmation_status="confirmed", confirmations=1)])

        mock_client.get_signature_statuses.side_effect = [resp1, resp2]
        MockClient.return_value = mock_client

        client = SolanaClient(config)
        await client.connect()

        valid_sig = "58bACmwLMyieZbX1qx6vRxYT8VZSfhHSG5nUsn5jcW7TrtNvYsz6KWaVigYysYj5riphcpkYFdKgMS23Pni8zDh9"
        success = await client.confirm_transaction(valid_sig, max_retries=5, delay=0.1)
        logging.info(f"Confirmation success: {success}")

        if success:
            logging.info("PASS: Transaction confirmed after polling")
        else:
            logging.error("FAIL: Transaction confirmation failed")


async def test_enhanced_stats():
    logging.info("\n--- Testing Enhanced Network Stats ---")
    config = {"network": "devnet", "rpc_urls": ["http://rpc1.com", "http://rpc2.com"], "live": True}
    client = SolanaClient(config)
    client.connected = True
    client.failover_count = 5
    client.current_rpc_index = 1

    stats = await client.get_network_stats()
    logging.info(f"Stats: {json.dumps(stats, indent=2)}")

    if stats["rpc_pool_size"] == 2 and stats["failover_count"] == 5:
        logging.info("PASS: Enhanced stats reported correctly")
    else:
        logging.info("FAIL: Enhanced stats missing fields")


if __name__ == "__main__":
    asyncio.run(test_multi_rpc_failover())
    asyncio.run(test_transaction_confirmation())
    asyncio.run(test_enhanced_stats())
