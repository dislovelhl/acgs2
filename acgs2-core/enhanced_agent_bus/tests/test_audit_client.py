"""
ACGS-2 Enhanced Agent Bus - Audit Client Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive tests for the AuditClient class.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, asdict
from typing import Dict, Any

from audit_client import AuditClient


# =============================================================================
# Test Data Classes
# =============================================================================

@dataclass
class MockValidationResult:
    """Mock validation result with to_dict method."""
    is_valid: bool
    message_id: str
    constitutional_hash: str
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "message_id": self.message_id,
            "constitutional_hash": self.constitutional_hash,
            "errors": self.errors,
        }


@dataclass
class PlainDataclass:
    """Plain dataclass without to_dict method."""
    field1: str
    field2: int


# =============================================================================
# Initialization Tests
# =============================================================================

class TestAuditClientInitialization:
    """Tests for AuditClient initialization."""

    def test_default_initialization(self) -> None:
        """Test initialization with default parameters."""
        client = AuditClient()
        assert client.service_url == "http://localhost:8001"
        assert client.client is not None

    def test_custom_service_url(self) -> None:
        """Test initialization with custom service URL."""
        url = "http://audit.example.com:9000"
        client = AuditClient(service_url=url)
        assert client.service_url == url

    def test_client_has_http_client(self) -> None:
        """Test that client has an httpx AsyncClient."""
        client = AuditClient()
        assert hasattr(client, "client")


# =============================================================================
# report_validation Tests
# =============================================================================

class TestReportValidation:
    """Tests for report_validation method."""

    @pytest.mark.asyncio
    async def test_report_validation_with_to_dict(self) -> None:
        """Test reporting validation with object having to_dict method."""
        client = AuditClient()
        result = MockValidationResult(
            is_valid=True,
            message_id="msg-123",
            constitutional_hash="cdd01ef066bc6cf2",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry_hash": "test_hash_123"}

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            audit_hash = await client.report_validation(result)
            assert audit_hash == "test_hash_123"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_report_validation_with_plain_dataclass(self) -> None:
        """Test reporting validation with plain dataclass."""
        client = AuditClient()
        result = PlainDataclass(field1="test", field2=42)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry_hash": "test_hash_456"}

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            audit_hash = await client.report_validation(result)
            assert audit_hash == "test_hash_456"

    @pytest.mark.asyncio
    async def test_report_validation_with_dict(self) -> None:
        """Test reporting validation with raw dictionary."""
        client = AuditClient()
        result = {
            "is_valid": True,
            "message_id": "msg-456",
            "constitutional_hash": "cdd01ef066bc6cf2",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry_hash": "test_hash_789"}

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            audit_hash = await client.report_validation(result)
            assert audit_hash == "test_hash_789"

    @pytest.mark.asyncio
    async def test_report_validation_with_invalid_result(self) -> None:
        """Test reporting an invalid validation result."""
        client = AuditClient()
        result = MockValidationResult(
            is_valid=False,
            message_id="msg-789",
            constitutional_hash="invalid-hash",
            errors=["Hash mismatch"],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry_hash": "invalid_hash_result"}

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            audit_hash = await client.report_validation(result)
            assert audit_hash == "invalid_hash_result"

    @pytest.mark.asyncio
    async def test_report_validation_exception_handling(self) -> None:
        """Test that exceptions are handled gracefully."""
        client = AuditClient()

        # Create an object that will cause to_dict to fail
        class FailingObject:
            def to_dict(self):
                raise ValueError("Intentional failure")

        audit_hash = await client.report_validation(FailingObject())

        assert audit_hash is None

    @pytest.mark.asyncio
    async def test_report_validation_none_input(self) -> None:
        """Test reporting with None input returns None (error case)."""
        client = AuditClient()

        # None causes an error when trying to access .get() on it
        audit_hash = await client.report_validation(None)

        # Returns None because the exception is caught and logged
        assert audit_hash is None

    @pytest.mark.asyncio
    async def test_report_validation_with_empty_dict(self) -> None:
        """Test reporting with empty dictionary."""
        client = AuditClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry_hash": "empty_dict_hash"}

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            audit_hash = await client.report_validation({})
            assert audit_hash == "empty_dict_hash"


# =============================================================================
# get_stats Tests
# =============================================================================

class TestGetStats:
    """Tests for get_stats method."""

    @pytest.mark.asyncio
    async def test_get_stats_success(self) -> None:
        """Test successful stats retrieval."""
        client = AuditClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "total_records": 1000,
            "valid_count": 950,
            "invalid_count": 50,
        }

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            stats = await client.get_stats()

            assert stats["total_records"] == 1000
            assert stats["valid_count"] == 950
            mock_get.assert_called_once_with("http://localhost:8001/stats")

    @pytest.mark.asyncio
    async def test_get_stats_with_custom_url(self) -> None:
        """Test stats retrieval with custom service URL."""
        custom_url = "http://custom-audit:8080"
        client = AuditClient(service_url=custom_url)

        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "healthy"}

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            await client.get_stats()

            mock_get.assert_called_once_with(f"{custom_url}/stats")

    @pytest.mark.asyncio
    async def test_get_stats_connection_error(self) -> None:
        """Test stats retrieval when connection fails."""
        client = AuditClient()

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            stats = await client.get_stats()

            assert stats == {}

    @pytest.mark.asyncio
    async def test_get_stats_timeout_error(self) -> None:
        """Test stats retrieval when request times out."""
        client = AuditClient()

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = TimeoutError("Request timed out")

            stats = await client.get_stats()

            assert stats == {}

    @pytest.mark.asyncio
    async def test_get_stats_json_decode_error(self) -> None:
        """Test stats retrieval when JSON decode fails."""
        client = AuditClient()

        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            stats = await client.get_stats()

            assert stats == {}


# =============================================================================
# close Tests
# =============================================================================

class TestClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_client(self) -> None:
        """Test closing the HTTP client."""
        client = AuditClient()

        with patch.object(client.client, "aclose", new_callable=AsyncMock) as mock_close:
            await client.close()

            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_multiple_times(self) -> None:
        """Test that close can be called multiple times."""
        client = AuditClient()

        with patch.object(client.client, "aclose", new_callable=AsyncMock) as mock_close:
            await client.close()
            await client.close()

            assert mock_close.call_count == 2


# =============================================================================
# Integration Tests
# =============================================================================

class TestAuditClientIntegration:
    """Integration tests for AuditClient."""

    @pytest.mark.asyncio
    async def test_full_workflow(self) -> None:
        """Test a complete audit client workflow."""
        client = AuditClient()

        # Report a validation result
        result = MockValidationResult(
            is_valid=True,
            message_id="integration-msg",
            constitutional_hash="cdd01ef066bc6cf2",
        )
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"entry_hash": "full_workflow_hash"}

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_post_response
            audit_hash = await client.report_validation(result)
            assert audit_hash == "full_workflow_hash"

        # Mock stats response
        mock_response = MagicMock()
        mock_response.json.return_value = {"total_records": 1}

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            stats = await client.get_stats()
            assert stats.get("total_records") == 1

        # Close the client
        with patch.object(client.client, "aclose", new_callable=AsyncMock):
            await client.close()

    @pytest.mark.asyncio
    async def test_multiple_validations(self) -> None:
        """Test reporting multiple validations."""
        client = AuditClient()

        results = [
            MockValidationResult(True, f"msg-{i}", "cdd01ef066bc6cf2")
            for i in range(5)
        ]

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"entry_hash": "multi_test_hash"}

        hashes = []
        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_post_response
            for result in results:
                audit_hash = await client.report_validation(result)
                hashes.append(audit_hash)

        assert len(hashes) == 5
        assert all(h == "multi_test_hash" for h in hashes)

    @pytest.mark.asyncio
    async def test_mixed_validation_results(self) -> None:
        """Test reporting mixed valid and invalid validations."""
        client = AuditClient()

        # Valid result
        valid_result = MockValidationResult(
            is_valid=True,
            message_id="valid-msg",
            constitutional_hash="cdd01ef066bc6cf2",
        )

        # Invalid result
        invalid_result = MockValidationResult(
            is_valid=False,
            message_id="invalid-msg",
            constitutional_hash="bad-hash",
            errors=["Constitutional hash mismatch"],
        )

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"entry_hash": "mixed_test_hash"}

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_post_response
            valid_hash = await client.report_validation(valid_result)
            invalid_hash = await client.report_validation(invalid_result)

        assert valid_hash == "mixed_test_hash"
        assert invalid_hash == "mixed_test_hash"

