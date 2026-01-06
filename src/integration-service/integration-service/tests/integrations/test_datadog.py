"""
Tests for DataDog Integration Adapter
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from src.integrations.base import (
    AuthenticationError,
    EventSeverity,
    IntegrationEvent,
    RateLimitError,
)
from src.integrations.datadog_adapter import DataDogAdapter, DataDogCredentials


@pytest.fixture
def datadog_credentials():
    return DataDogCredentials(
        integration_name="test-datadog", api_key=SecretStr("test-api-key"), site="datadoghq.com"
    )


@pytest.fixture
def datadog_adapter(datadog_credentials):
    return DataDogAdapter(credentials=datadog_credentials)


@pytest.fixture
def sample_event():
    return IntegrationEvent(
        event_type="security_violation",
        title="Test Security Violation",
        severity=EventSeverity.CRITICAL,
        details={"reason": "unauthorized_access"},
        timestamp=datetime.now(timezone.utc),
        tags=["env:test"],
    )


@pytest.mark.asyncio
async def test_datadog_send_event_success(datadog_adapter, sample_event):
    mock_response = MagicMock()
    mock_response.status_code = 202

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch.object(datadog_adapter, "get_http_client", return_value=mock_client):
        result = await datadog_adapter._do_send_event(sample_event)

        assert result.success is True
        assert result.operation == "send_event"

        # Verify call arguments
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert kwargs["headers"]["DD-API-KEY"] == "test-api-key"
        assert kwargs["json"]["message"] == "Governance Event: security_violation"
        assert kwargs["json"]["governance_event"]["event_id"] == sample_event.event_id


@pytest.mark.asyncio
async def test_datadog_send_events_batch_success(datadog_adapter, sample_event):
    mock_response = MagicMock()
    mock_response.status_code = 202

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    events = [sample_event, sample_event]

    with patch.object(datadog_adapter, "get_http_client", return_value=mock_client):
        results = await datadog_adapter._do_send_events_batch(events)

        assert len(results) == 2
        assert all(r.success for r in results)

        mock_client.post.assert_called_once()
        assert isinstance(mock_client.post.call_args[1]["json"], list)
        assert len(mock_client.post.call_args[1]["json"]) == 2


@pytest.mark.asyncio
async def test_datadog_authentication_error(datadog_adapter, sample_event):
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch.object(datadog_adapter, "get_http_client", return_value=mock_client):
        with pytest.raises(AuthenticationError):
            await datadog_adapter._do_send_event(sample_event)


@pytest.mark.asyncio
async def test_datadog_rate_limit_error(datadog_adapter, sample_event):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Too Many Requests"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch.object(datadog_adapter, "get_http_client", return_value=mock_client):
        with pytest.raises(RateLimitError):
            await datadog_adapter._do_send_event(sample_event)


def test_datadog_intake_url_regional():
    # US1 (Default)
    creds_us = DataDogCredentials(
        integration_name="dd", api_key=SecretStr("k"), site="datadoghq.com"
    )
    assert creds_us.intake_url == "https://http-intake.logs.datadoghq.com/api/v2/logs"

    # EU
    creds_eu = DataDogCredentials(
        integration_name="dd", api_key=SecretStr("k"), site="datadoghq.eu"
    )
    assert creds_eu.intake_url == "https://http-intake.logs.datadoghq.eu/api/v2/logs"

    # US5
    creds_us5 = DataDogCredentials(
        integration_name="dd", api_key=SecretStr("k"), site="us5.datadoghq.com"
    )
    assert creds_us5.intake_url == "https://http-intake.logs.us5.datadoghq.com/api/v2/logs"

    # Gov
    creds_gov = DataDogCredentials(
        integration_name="dd", api_key=SecretStr("k"), site="ddog-gov.com"
    )
    assert creds_gov.intake_url == "https://http-intake.logs.ddog-gov.com/api/v2/logs"
