"""
Tests for Linear webhook handler and signature verification.

Tests cover:
- HMAC signature verification (valid and invalid)
- Webhook payload parsing (Issue, Comment, StatusChange events)
- Malformed payload handling
- Missing/expired signatures
- Event queueing
- Status endpoint
- Test endpoint (without signature verification)
"""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import SecretStr

from src.api.linear_webhooks import (
    _webhook_events,
    _webhook_stats,
    queue_webhook_event,
    router,
)
from src.integrations.linear.webhook_auth import verify_linear_signature_sync


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def app():
    """Create a FastAPI test app with Linear webhook routes."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def webhook_secret():
    """Get the webhook secret for testing."""
    return SecretStr("test-linear-webhook-secret-12345")


@pytest.fixture
def mock_linear_config(webhook_secret):
    """Mock Linear configuration."""
    config = MagicMock()
    config.linear_webhook_secret = webhook_secret
    config.linear_api_key = SecretStr("test-api-key")
    config.linear_api_url = "https://api.linear.app/graphql"
    config.linear_team_id = "team-123"
    config.linear_project_id = None
    config.linear_timeout_seconds = 30.0
    config.linear_max_retries = 3
    return config


@pytest.fixture(autouse=True)
def reset_webhook_state():
    """Reset webhook state between tests."""
    _webhook_events.clear()
    _webhook_stats["total_received"] = 0
    _webhook_stats["total_processed"] = 0
    _webhook_stats["total_failed"] = 0
    yield
    # Cleanup after test
    _webhook_events.clear()
    _webhook_stats["total_received"] = 0
    _webhook_stats["total_processed"] = 0
    _webhook_stats["total_failed"] = 0


@pytest.fixture
def sample_issue_webhook_payload() -> Dict[str, Any]:
    """Create a sample Linear issue webhook payload."""
    return {
        "action": "create",
        "type": "Issue",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "organizationId": "org-123",
        "webhookId": "webhook-456",
        "url": "https://linear.app/org/issue/ENG-123",
        "data": {
            "id": "issue-789",
            "identifier": "ENG-123",
            "title": "Test Issue",
            "description": "This is a test issue",
            "priority": 2,
            "team": {
                "id": "team-123",
                "name": "Engineering",
                "key": "ENG",
            },
            "state": {
                "id": "state-123",
                "name": "Todo",
                "type": "unstarted",
            },
            "url": "https://linear.app/org/issue/ENG-123",
            "createdAt": "2024-01-01T00:00:00.000Z",
            "updatedAt": "2024-01-01T00:00:00.000Z",
        },
    }


@pytest.fixture
def sample_comment_webhook_payload() -> Dict[str, Any]:
    """Create a sample Linear comment webhook payload."""
    return {
        "action": "create",
        "type": "Comment",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "organizationId": "org-123",
        "webhookId": "webhook-789",
        "url": "https://linear.app/org/issue/ENG-123#comment-abc",
        "data": {
            "id": "comment-abc",
            "body": "This is a test comment",
            "createdAt": "2024-01-01T00:00:00.000Z",
            "updatedAt": "2024-01-01T00:00:00.000Z",
            "user": {
                "id": "user-123",
                "name": "Test User",
            },
        },
    }


@pytest.fixture
def sample_status_change_payload() -> Dict[str, Any]:
    """Create a sample Linear issue status change webhook payload."""
    return {
        "action": "update",
        "type": "Issue",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "organizationId": "org-123",
        "webhookId": "webhook-999",
        "url": "https://linear.app/org/issue/ENG-123",
        "data": {
            "id": "issue-789",
            "identifier": "ENG-123",
            "title": "Test Issue",
            "description": "This is a test issue",
            "priority": 2,
            "team": {
                "id": "team-123",
                "name": "Engineering",
                "key": "ENG",
            },
            "state": {
                "id": "state-456",
                "name": "In Progress",
                "type": "started",
            },
            "url": "https://linear.app/org/issue/ENG-123",
            "createdAt": "2024-01-01T00:00:00.000Z",
            "updatedAt": "2024-01-01T00:01:00.000Z",
        },
        "updatedFrom": {
            "state": {
                "id": "state-123",
                "name": "Todo",
                "type": "unstarted",
            }
        },
    }


def compute_linear_signature(payload: Dict[str, Any], secret: SecretStr) -> str:
    """
    Compute Linear webhook signature for testing.

    This mimics the Linear signature generation process using HMAC-SHA256.
    """
    import hashlib
    import hmac

    # Convert payload to JSON bytes
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    # Compute HMAC-SHA256
    signature = hmac.new(
        secret.get_secret_value().encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    return signature


# ============================================================================
# Signature Verification Tests
# ============================================================================


class TestLinearWebhookSignatureVerification:
    """Tests for Linear webhook signature verification."""

    @pytest.mark.asyncio
    async def test_valid_signature_accepted(
        self, client, sample_issue_webhook_payload, webhook_secret, mock_linear_config
    ):
        """Test that webhooks with valid signatures are accepted."""
        # Mock the config
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            # Compute valid signature
            signature = compute_linear_signature(sample_issue_webhook_payload, webhook_secret)

            # Make request with valid signature
            response = client.post(
                "/webhooks/linear",
                json=sample_issue_webhook_payload,
                headers={
                    "X-Linear-Signature": signature,
                    "Content-Type": "application/json",
                },
            )

            # Should be accepted
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["queued"] is True
            assert "event_id" in data

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(
        self, client, sample_issue_webhook_payload, mock_linear_config
    ):
        """Test that webhooks with invalid signatures are rejected."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            # Use an invalid signature
            response = client.post(
                "/webhooks/linear",
                json=sample_issue_webhook_payload,
                headers={
                    "X-Linear-Signature": "invalid-signature-12345",
                    "Content-Type": "application/json",
                },
            )

            # Should be rejected with 401 Unauthorized
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_missing_signature_rejected(
        self, client, sample_issue_webhook_payload, mock_linear_config
    ):
        """Test that webhooks without signature headers are rejected."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            # Make request without signature header
            response = client.post(
                "/webhooks/linear",
                json=sample_issue_webhook_payload,
                headers={"Content-Type": "application/json"},
            )

            # Should be rejected with 401 Unauthorized
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            data = response.json()
            assert "Missing X-Linear-Signature header" in data["detail"]

    @pytest.mark.asyncio
    async def test_signature_with_tampered_payload(
        self, client, sample_issue_webhook_payload, webhook_secret, mock_linear_config
    ):
        """Test that signature verification fails when payload is tampered."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            # Compute signature for original payload
            signature = compute_linear_signature(sample_issue_webhook_payload, webhook_secret)

            # Tamper with the payload
            tampered_payload = sample_issue_webhook_payload.copy()
            tampered_payload["data"]["title"] = "Tampered Title"

            # Make request with tampered payload but original signature
            response = client.post(
                "/webhooks/linear",
                json=tampered_payload,
                headers={
                    "X-Linear-Signature": signature,
                    "Content-Type": "application/json",
                },
            )

            # Should be rejected
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verify_linear_signature_sync_valid(
        self, sample_issue_webhook_payload, webhook_secret
    ):
        """Test synchronous signature verification with valid signature."""
        payload_bytes = json.dumps(
            sample_issue_webhook_payload, separators=(",", ":")
        ).encode("utf-8")
        signature = compute_linear_signature(sample_issue_webhook_payload, webhook_secret)

        result = verify_linear_signature_sync(payload_bytes, signature, webhook_secret)

        assert result is True

    def test_verify_linear_signature_sync_invalid(
        self, sample_issue_webhook_payload, webhook_secret
    ):
        """Test synchronous signature verification with invalid signature."""
        payload_bytes = json.dumps(
            sample_issue_webhook_payload, separators=(",", ":")
        ).encode("utf-8")

        result = verify_linear_signature_sync(
            payload_bytes, "invalid-signature", webhook_secret
        )

        assert result is False


# ============================================================================
# Webhook Payload Parsing Tests
# ============================================================================


class TestLinearWebhookPayloadParsing:
    """Tests for Linear webhook payload parsing."""

    @pytest.mark.asyncio
    async def test_parse_issue_create_event(
        self, client, sample_issue_webhook_payload, webhook_secret, mock_linear_config
    ):
        """Test parsing Issue create webhook event."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            signature = compute_linear_signature(sample_issue_webhook_payload, webhook_secret)

            response = client.post(
                "/webhooks/linear",
                json=sample_issue_webhook_payload,
                headers={"X-Linear-Signature": signature},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "Issue" in data["message"]
            assert "create" in data["message"]

    @pytest.mark.asyncio
    async def test_parse_comment_create_event(
        self, client, sample_comment_webhook_payload, webhook_secret, mock_linear_config
    ):
        """Test parsing Comment create webhook event."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            signature = compute_linear_signature(sample_comment_webhook_payload, webhook_secret)

            response = client.post(
                "/webhooks/linear",
                json=sample_comment_webhook_payload,
                headers={"X-Linear-Signature": signature},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "Comment" in data["message"]

    @pytest.mark.asyncio
    async def test_parse_status_change_event(
        self, client, sample_status_change_payload, webhook_secret, mock_linear_config
    ):
        """Test parsing Issue status change webhook event."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            signature = compute_linear_signature(sample_status_change_payload, webhook_secret)

            response = client.post(
                "/webhooks/linear",
                json=sample_status_change_payload,
                headers={"X-Linear-Signature": signature},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            # Verify status change was detected in event queue
            assert len(_webhook_events) == 1

    @pytest.mark.asyncio
    async def test_malformed_json_payload(self, client, mock_linear_config):
        """Test handling of malformed JSON payload."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            # Send invalid JSON
            response = client.post(
                "/webhooks/linear",
                data="invalid json {{{",
                headers={
                    "X-Linear-Signature": "dummy-signature",
                    "Content-Type": "application/json",
                },
            )

            # Should return 400 Bad Request or be handled gracefully
            # (depending on signature verification order)
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_401_UNAUTHORIZED,
            ]

    @pytest.mark.asyncio
    async def test_invalid_webhook_payload_structure(
        self, client, webhook_secret, mock_linear_config
    ):
        """Test handling of payload with invalid structure (missing required fields)."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            invalid_payload = {
                "action": "create",
                # Missing 'type', 'data', and other required fields
            }
            signature = compute_linear_signature(invalid_payload, webhook_secret)

            response = client.post(
                "/webhooks/linear",
                json=invalid_payload,
                headers={"X-Linear-Signature": signature},
            )

            # Should still return 200 to prevent retries but mark as failed
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False
            assert data["queued"] is False

    @pytest.mark.asyncio
    async def test_unknown_webhook_type(
        self, client, webhook_secret, mock_linear_config
    ):
        """Test handling of unknown webhook type."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            unknown_payload = {
                "action": "create",
                "type": "UnknownType",
                "createdAt": "2024-01-01T00:00:00.000Z",
                "organizationId": "org-123",
                "url": "https://linear.app/org/unknown/123",
                "data": {
                    "id": "unknown-123",
                    "createdAt": "2024-01-01T00:00:00.000Z",
                    "updatedAt": "2024-01-01T00:00:00.000Z",
                },
            }
            signature = compute_linear_signature(unknown_payload, webhook_secret)

            response = client.post(
                "/webhooks/linear",
                json=unknown_payload,
                headers={"X-Linear-Signature": signature},
            )

            # Should handle gracefully (validation may fail)
            assert response.status_code == status.HTTP_200_OK


# ============================================================================
# Event Queueing Tests
# ============================================================================


class TestLinearWebhookEventQueueing:
    """Tests for webhook event queueing."""

    def test_queue_webhook_event(self, sample_issue_webhook_payload):
        """Test queueing a webhook event."""
        event_id = queue_webhook_event(sample_issue_webhook_payload)

        assert event_id is not None
        assert len(_webhook_events) == 1
        assert _webhook_stats["total_received"] == 1

        queued_event = _webhook_events[0]
        assert queued_event["event_id"] == event_id
        assert queued_event["data"] == sample_issue_webhook_payload
        assert queued_event["processed"] is False

    def test_queue_multiple_events(
        self, sample_issue_webhook_payload, sample_comment_webhook_payload
    ):
        """Test queueing multiple webhook events."""
        event_id_1 = queue_webhook_event(sample_issue_webhook_payload)
        event_id_2 = queue_webhook_event(sample_comment_webhook_payload)

        assert event_id_1 != event_id_2
        assert len(_webhook_events) == 2
        assert _webhook_stats["total_received"] == 2

    def test_queue_event_limit(self, sample_issue_webhook_payload):
        """Test that event queue maintains a max size (100 events)."""
        # Queue 150 events
        for i in range(150):
            payload = sample_issue_webhook_payload.copy()
            payload["webhookId"] = f"webhook-{i}"
            queue_webhook_event(payload)

        # Should only keep last 100
        assert len(_webhook_events) <= 100
        assert _webhook_stats["total_received"] == 150

    @pytest.mark.asyncio
    async def test_event_queued_on_webhook_receive(
        self, client, sample_issue_webhook_payload, webhook_secret, mock_linear_config
    ):
        """Test that events are queued when webhook is received."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            signature = compute_linear_signature(sample_issue_webhook_payload, webhook_secret)

            response = client.post(
                "/webhooks/linear",
                json=sample_issue_webhook_payload,
                headers={"X-Linear-Signature": signature},
            )

            assert response.status_code == status.HTTP_200_OK

            # Verify event was queued
            assert len(_webhook_events) == 1
            assert _webhook_stats["total_received"] == 1


# ============================================================================
# Status Endpoint Tests
# ============================================================================


class TestLinearWebhookStatusEndpoint:
    """Tests for webhook status endpoint."""

    @pytest.mark.asyncio
    async def test_get_webhook_status_empty(self, client, mock_linear_config):
        """Test getting webhook status when no events have been received."""
        with patch(
                "src.integrations.linear.webhook_auth.is_linear_webhook_configured",
                return_value=True,
            ):
            response = client.get("/webhooks/linear/status")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["configured"] is True
            assert data["total_received"] == 0
            assert data["total_processed"] == 0
            assert data["total_failed"] == 0
            assert data["recent_events"] == []

    @pytest.mark.asyncio
    async def test_get_webhook_status_with_events(
        self, client, sample_issue_webhook_payload, webhook_secret, mock_linear_config
    ):
        """Test getting webhook status after receiving events."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            with patch(
                "src.integrations.linear.webhook_auth.is_linear_webhook_configured",
                return_value=True,
            ):
                # Send a webhook
                signature = compute_linear_signature(sample_issue_webhook_payload, webhook_secret)
                client.post(
                    "/webhooks/linear",
                    json=sample_issue_webhook_payload,
                    headers={"X-Linear-Signature": signature},
                )

                # Get status
                response = client.get("/webhooks/linear/status")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["configured"] is True
                assert data["total_received"] == 1
                assert len(data["recent_events"]) == 1

                recent_event = data["recent_events"][0]
                assert recent_event["action"] == "create"
                assert recent_event["type"] == "Issue"
                assert recent_event["processed"] is False

    @pytest.mark.asyncio
    async def test_status_shows_recent_events_limit(
        self, client, sample_issue_webhook_payload, webhook_secret, mock_linear_config
    ):
        """Test that status endpoint shows only last 10 events."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            with patch(
                "src.integrations.linear.webhook_auth.is_linear_webhook_configured",
                return_value=True,
            ):
                # Send 15 webhooks
                for i in range(15):
                    payload = sample_issue_webhook_payload.copy()
                    payload["webhookId"] = f"webhook-{i}"
                    signature = compute_linear_signature(payload, webhook_secret)
                    client.post(
                        "/webhooks/linear",
                        json=payload,
                        headers={"X-Linear-Signature": signature},
                    )

                # Get status
                response = client.get("/webhooks/linear/status")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["total_received"] == 15
                # Should only show last 10
                assert len(data["recent_events"]) == 10


# ============================================================================
# Test Endpoint Tests
# ============================================================================


class TestLinearWebhookTestEndpoint:
    """Tests for webhook test endpoint (without signature verification)."""

    @pytest.mark.asyncio
    async def test_test_endpoint_without_signature(
        self, client, sample_issue_webhook_payload
    ):
        """Test that test endpoint accepts webhooks without signature."""
        response = client.post(
            "/webhooks/linear/test",
            json=sample_issue_webhook_payload,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["queued"] is True
        assert "event_id" in data

    @pytest.mark.asyncio
    async def test_test_endpoint_with_invalid_payload(self, client):
        """Test that test endpoint rejects invalid payloads."""
        invalid_payload = {"invalid": "payload"}

        response = client.post(
            "/webhooks/linear/test",
            json=invalid_payload,
        )

        # Should reject with 400 Bad Request
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_test_endpoint_malformed_json(self, client):
        """Test that test endpoint handles malformed JSON."""
        response = client.post(
            "/webhooks/linear/test",
            data="invalid json {{{",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestLinearWebhookErrorHandling:
    """Tests for webhook error handling."""

    @pytest.mark.asyncio
    async def test_webhook_handler_exception_returns_200(
        self, client, webhook_secret, mock_linear_config
    ):
        """Test that exceptions in webhook handler still return 200 to prevent retries."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            # Create a valid payload
            payload = {
                "action": "create",
                "type": "Issue",
                "createdAt": "2024-01-01T00:00:00.000Z",
                "organizationId": "org-123",
                "url": "https://linear.app/org/issue/ENG-123",
                "data": {
                    "id": "issue-123",
                    "identifier": "ENG-123",
                    "title": "Test",
                    "team": {"id": "team-123", "name": "Eng", "key": "ENG"},
                    "state": {"id": "state-123", "name": "Todo", "type": "unstarted"},
                    "url": "https://linear.app/org/issue/ENG-123",
                    "createdAt": "2024-01-01T00:00:00.000Z",
                    "updatedAt": "2024-01-01T00:00:00.000Z",
                },
            }
            signature = compute_linear_signature(payload, webhook_secret)

            # Mock queue_webhook_event to raise an exception
            with patch(
                "src.api.linear_webhooks.queue_webhook_event",
                side_effect=Exception("Test error"),
            ):
                response = client.post(
                    "/webhooks/linear",
                    json=payload,
                    headers={"X-Linear-Signature": signature},
                )

                # Should still return 200 to prevent retries
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is False
                assert "processing failed" in data["message"]

    @pytest.mark.asyncio
    async def test_webhook_not_configured_error(self, client, sample_issue_webhook_payload):
        """Test webhook handler when LINEAR_WEBHOOK_SECRET is not configured."""
        mock_config = MagicMock()
        mock_config.linear_webhook_secret = None  # Not configured

        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_config,
        ):
            response = client.post(
                "/webhooks/linear",
                json=sample_issue_webhook_payload,
                headers={"X-Linear-Signature": "dummy"},
            )

            # Should return 500 Internal Server Error
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ============================================================================
# Integration Tests
# ============================================================================


class TestLinearWebhookIntegration:
    """Integration tests for complete webhook flow."""

    @pytest.mark.asyncio
    async def test_complete_webhook_flow(
        self, client, sample_issue_webhook_payload, webhook_secret, mock_linear_config
    ):
        """Test complete webhook flow from receipt to queueing."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            with patch(
                "src.integrations.linear.webhook_auth.is_linear_webhook_configured",
                return_value=True,
            ):
                # 1. Receive webhook
                signature = compute_linear_signature(sample_issue_webhook_payload, webhook_secret)
                webhook_response = client.post(
                    "/webhooks/linear",
                    json=sample_issue_webhook_payload,
                    headers={"X-Linear-Signature": signature},
                )

                assert webhook_response.status_code == status.HTTP_200_OK
                webhook_data = webhook_response.json()
                event_id = webhook_data["event_id"]

                # 2. Verify event was queued
                assert len(_webhook_events) == 1
                queued_event = _webhook_events[0]
                assert queued_event["event_id"] == event_id
                assert queued_event["data"]["type"] == "Issue"

                # 3. Check status endpoint
                status_response = client.get("/webhooks/linear/status")
                status_data = status_response.json()
                assert status_data["total_received"] == 1
                assert len(status_data["recent_events"]) == 1
                assert status_data["recent_events"][0]["event_id"] == event_id

    @pytest.mark.asyncio
    async def test_multiple_webhook_types_flow(
        self,
        client,
        sample_issue_webhook_payload,
        sample_comment_webhook_payload,
        webhook_secret,
        mock_linear_config,
    ):
        """Test receiving multiple types of webhooks."""
        with patch(
            "src.integrations.linear.webhook_auth.get_linear_config",
            return_value=mock_linear_config,
        ):
            with patch(
                "src.integrations.linear.webhook_auth.is_linear_webhook_configured",
                return_value=True,
            ):
                # Send Issue webhook
                issue_sig = compute_linear_signature(sample_issue_webhook_payload, webhook_secret)
                client.post(
                    "/webhooks/linear",
                    json=sample_issue_webhook_payload,
                    headers={"X-Linear-Signature": issue_sig},
                )

                # Send Comment webhook
                comment_sig = compute_linear_signature(
                    sample_comment_webhook_payload, webhook_secret
                )
                client.post(
                    "/webhooks/linear",
                    json=sample_comment_webhook_payload,
                    headers={"X-Linear-Signature": comment_sig},
                )

                # Verify both were queued
                assert len(_webhook_events) == 2
                assert _webhook_stats["total_received"] == 2

                # Verify status shows both
                status_response = client.get("/webhooks/linear/status")
                status_data = status_response.json()
                assert status_data["total_received"] == 2
                assert len(status_data["recent_events"]) == 2

                # Verify different types
                event_types = {event["type"] for event in status_data["recent_events"]}
                assert "Issue" in event_types
                assert "Comment" in event_types
