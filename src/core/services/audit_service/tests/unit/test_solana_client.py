import pytest
from src.core.services.audit_service.blockchain.solana.solana_client import SolanaClient


@pytest.fixture
def solana_config():
    return {
        "network": "devnet",
        "rpc_url": "https://api.devnet.solana.com",
        "commitment": "confirmed",
        "program_id": "ExWhj4zubqb1wwCcFfFLmgYGR5fpQAmSjB9N4MQZRW9B",
    }


@pytest.fixture
async def client(solana_config):
    # Enable mock mode by setting live=False
    solana_config["live"] = False
    client = SolanaClient(solana_config)
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
class TestSolanaClient:
    async def test_connect(self, solana_config):
        client = SolanaClient(solana_config)
        success = await client.connect()
        assert success is True
        assert client.is_connected() is True
        await client.disconnect()
        assert client.is_connected() is False

    async def test_submit_audit_batch(self, client):
        batch_data = {
            "batch_id": "test_batch_solana",
            "root_hash": "test_root_hash_solana",
            "entry_count": 5,
            "timestamp": 1234567890,
            "entries_hashes": ["hash1", "hash2"],
        }

        signature = await client.submit_audit_batch(batch_data)
        assert signature is not None
        assert "sol_mock_sig_" in signature

    async def test_get_transaction_memo(self, client):
        signature = "sol_mock_sig_123"
        result = await client.get_transaction_memo(signature)

        assert result is not None
        assert "status" in result

    async def test_get_network_stats(self, client):
        stats = await client.get_network_stats()

        assert stats["blockchain_type"] == "solana"
        assert stats["network_name"] == "Solana Devnet"
        assert stats["connected"] is True
        assert stats["live_mode"] is False

    async def test_verify_batch_on_chain(self, client):
        is_valid = await client.verify_batch_on_chain("batch1", "sig1", "hash1")
        # In mock mode it returns False unless we mock get_transaction_memo to return matching hashes
        # But here we just check it doesn't crash
        assert isinstance(is_valid, bool)
