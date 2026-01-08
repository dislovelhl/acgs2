import asyncio
import logging
import os

import pytest
from src.core.services.audit_service.blockchain.solana.solana_client import SolanaClient


@pytest_asyncio.fixture
def solana_config():
    return {
        "network": "devnet",
        "rpc_url": "https://api.devnet.solana.com",
        "commitment": "confirmed",
        "live": True,  # Test live connectivity
        "wallet_path": os.path.expanduser("~/.config/solana/id.json"),
    }


@pytest_asyncio.fixture
async def client(solana_config):
    client = SolanaClient(solana_config)
    # We only connect, we don't necessarily submit in the fixture
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("SOLANA_LIVE_TESTS") != "1",
    reason="Skipping live Solana tests. Set SOLANA_LIVE_TESTS=1 to enable.",
)
class TestSolanaClientLive:
    async def test_live_connect(self, solana_config):
        client = SolanaClient(solana_config)
        success = await client.connect()
        assert success is True
        assert client.is_connected() is True

        stats = await client.get_network_stats()
        assert stats["connected"] is True
        assert "wallet_balance_sol" in stats
        logging.info(f"\nWallet Balance: {stats['wallet_balance_sol']} SOL")

        await client.disconnect()

    async def test_live_submit_memo(self, client):
        """测试向测试网提交真实的 Memo 交易"""
        batch_data = {
            "batch_id": f"test_live_{int(asyncio.get_event_loop().time())}",
            "root_hash": "live_integration_test_hash_phase_2",
        }

        signature = await client.submit_audit_batch(batch_data)
        assert signature is not None
        logging.info(f"\nLive Transaction Signature: {signature}")
        # Signature should be a base58 string, usually long
        assert len(signature) > 30

    async def test_get_stats_live(self, client):
        stats = await client.get_network_stats()
        assert stats["blockchain_type"] == "solana"
        assert "Solana Devnet" in stats["network_name"]
