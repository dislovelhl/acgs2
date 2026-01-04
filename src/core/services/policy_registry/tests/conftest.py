"""
ACGS-2 Policy Registry - Test Configuration
Constitutional Hash: cdd01ef066bc6cf2

Shared test fixtures for Policy Registry service tests.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add parent directories to path for imports
policy_registry_dir = os.path.dirname(os.path.dirname(__file__))
services_dir = os.path.dirname(policy_registry_dir)
project_root = os.path.dirname(services_dir)
shared_dir = os.path.join(project_root, "shared")

if policy_registry_dir not in sys.path:
    sys.path.insert(0, policy_registry_dir)
if services_dir not in sys.path:
    sys.path.insert(0, services_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if shared_dir not in sys.path:
    sys.path.insert(0, shared_dir)

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def constitutional_hash() -> str:
    """Return the valid constitutional hash."""
    return CONSTITUTIONAL_HASH


@pytest.fixture
def mock_vault_response():
    """Create mock Vault API response factory."""

    def _make_response(data: Dict[str, Any] = None, errors: list = None):
        response = {
            "request_id": "test-request-id",
            "lease_id": "",
            "renewable": False,
            "lease_duration": 0,
        }
        if data:
            response["data"] = data
        if errors:
            response["errors"] = errors
        return response

    return _make_response


@pytest.fixture
def mock_transit_key_response(mock_vault_response):
    """Create mock Transit key response."""
    return mock_vault_response(
        data={
            "type": "ed25519",
            "deletion_allowed": False,
            "derived": False,
            "exportable": False,
            "allow_plaintext_backup": False,
            "keys": {
                "1": {
                    "creation_time": "2025-01-15T00:00:00Z",
                    "public_key": "dGVzdC1wdWJsaWMta2V5LWJhc2U2NA==",  # base64 test key
                }
            },
            "min_decryption_version": 1,
            "min_encryption_version": 0,
            "name": "test-key",
            "supports_encryption": True,
            "supports_decryption": True,
            "supports_derivation": False,
            "supports_signing": True,
            "latest_version": 1,
        }
    )


@pytest.fixture
def mock_sign_response(mock_vault_response):
    """Create mock Transit sign response."""
    return mock_vault_response(
        data={
            "signature": "vault:v1:dGVzdC1zaWduYXR1cmUtYmFzZTY0",
        }
    )


@pytest.fixture
def mock_verify_response(mock_vault_response):
    """Create mock Transit verify response."""
    return mock_vault_response(
        data={
            "valid": True,
        }
    )


@pytest.fixture
def mock_encrypt_response(mock_vault_response):
    """Create mock Transit encrypt response."""
    return mock_vault_response(
        data={
            "ciphertext": "vault:v1:dGVzdC1jaXBoZXJ0ZXh0",
        }
    )


@pytest.fixture
def mock_decrypt_response(mock_vault_response):
    """Create mock Transit decrypt response."""
    import base64

    return mock_vault_response(
        data={
            "plaintext": base64.b64encode(b"decrypted-test-data").decode(),
        }
    )


@pytest.fixture
def mock_health_response():
    """Create mock Vault health response."""
    return {
        "initialized": True,
        "sealed": False,
        "standby": False,
        "performance_standby": False,
        "replication_performance_mode": "disabled",
        "replication_dr_mode": "disabled",
        "server_time_utc": 1705276800,
        "version": "1.15.0",
        "cluster_name": "vault-cluster-test",
        "cluster_id": "test-cluster-id",
    }


@pytest.fixture
def mock_httpx_client(
    mock_transit_key_response,
    mock_sign_response,
    mock_verify_response,
    mock_encrypt_response,
    mock_decrypt_response,
    mock_health_response,
):
    """Create mock httpx AsyncClient."""
    mock = MagicMock()

    async def mock_request(method, path, **kwargs):
        response = MagicMock()
        response.raise_for_status = MagicMock()

        # Route based on path
        if "/sys/health" in path:
            response.json.return_value = mock_health_response
            response.text = "health"
        elif "/keys/" in path and method == "GET":
            response.json.return_value = mock_transit_key_response
            response.text = "key"
        elif "/sign/" in path:
            response.json.return_value = mock_sign_response
            response.text = "sign"
        elif "/verify/" in path:
            response.json.return_value = mock_verify_response
            response.text = "verify"
        elif "/encrypt/" in path:
            response.json.return_value = mock_encrypt_response
            response.text = "encrypt"
        elif "/decrypt/" in path:
            response.json.return_value = mock_decrypt_response
            response.text = "decrypt"
        elif "/keys/" in path and method == "POST":
            response.json.return_value = {}
            response.text = ""
        elif "/rotate" in path:
            response.json.return_value = {}
            response.text = ""
        elif "/data/" in path:  # KV v2
            if method == "GET":
                response.json.return_value = {
                    "data": {
                        "data": {"secret_key": "secret_value"},
                        "metadata": {"version": 1},
                    }
                }
            else:
                response.json.return_value = {}
            response.text = "kv"
        else:
            response.json.return_value = {}
            response.text = ""

        return response

    mock.request = AsyncMock(side_effect=mock_request)
    mock.get = AsyncMock(side_effect=lambda path, **kwargs: mock_request("GET", path, **kwargs))
    mock.post = AsyncMock(side_effect=lambda path, **kwargs: mock_request("POST", path, **kwargs))
    mock.aclose = AsyncMock()

    return mock


@pytest.fixture
def mock_hvac_client(
    mock_transit_key_response,
    mock_health_response,
):
    """Create mock hvac Client."""
    mock = MagicMock()
    mock.is_authenticated.return_value = True

    # Mock sys.read_health_status
    mock.sys = MagicMock()
    mock.sys.read_health_status.return_value = mock_health_response

    # Mock adapter for direct requests
    mock.adapter = MagicMock()
    mock.adapter.request = MagicMock(return_value=MagicMock(json=lambda: {}))

    return mock


@pytest.fixture
def vault_config():
    """Create test Vault configuration."""
    from app.services.vault_crypto_service import VaultConfig

    return VaultConfig(
        address="http://127.0.0.1:8200",
        token="test-token",
        transit_mount="transit",
        kv_mount="secret",
        kv_version=2,
        timeout=10.0,
        verify_tls=False,
    )


@pytest.fixture
def fixed_timestamp() -> datetime:
    """Return a fixed timestamp for deterministic tests."""
    return datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_policy_content() -> Dict[str, Any]:
    """Sample policy content for signing tests."""
    return {
        "policy_id": "test-policy-001",
        "name": "Test Constitutional Policy",
        "version": "1.0.0",
        "rules": [
            {"id": "rule-1", "action": "allow", "resource": "governance/*"},
            {"id": "rule-2", "action": "deny", "resource": "admin/*"},
        ],
        "constitutional_hash": CONSTITUTIONAL_HASH,
    }


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "vault: mark test as requiring Vault connection")
    config.addinivalue_line("markers", "integration: mark test as integration test")
