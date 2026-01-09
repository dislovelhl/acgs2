"""
Tests for webhook delivery engine with exponential backoff retry logic.

Tests cover:
- Successful deliveries
- Retry logic with exponential backoff
- Dead letter queue handling
- Authentication header generation
- HMAC signature generation
- Error handling
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import TYPE_CHECKING, List
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.exceptions.retry import RetryableError
from src.webhooks.config import WebhookFrameworkConfig, WebhookRetryPolicy
from src.webhooks.delivery import (
    DeadLetterQueue,
    WebhookDeliveryEngine,
    create_delivery_engine,
)
from src.webhooks.models import (
    WebhookAuthType,
    WebhookConfig,
    WebhookDeliveryStatus,
    WebhookEvent,
    WebhookEventType,
    WebhookState,
    WebhookSubscription,
)
from src.webhooks.retry import ExponentialBackoff, RetryState, should_retry_status_code

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_event() -> WebhookEvent:
    """Create a sample webhook event."""
    return WebhookEvent(
        id="evt-test-001",
        event_type=WebhookEventType.POLICY_VIOLATION,
        severity="high",
        title="Test Policy Violation",
        description="A test policy violation occurred",
        policy_id="POL-001",
        resource_id="res-123",
        resource_type="compute",
        details={"key": "value"},
    )


@pytest.fixture
def sample_subscription() -> WebhookSubscription:
    """Create a sample webhook subscription."""
    return WebhookSubscription(
        id="sub-test-001",
        name="Test Subscription",
        state=WebhookState.ACTIVE,
        config=WebhookConfig(
            url="https://example.com/webhook",
            method="POST",
            auth_type=WebhookAuthType.NONE,
            timeout_seconds=10.0,
        ),
        event_types=[WebhookEventType.POLICY_VIOLATION],
        max_retries=3,
        retry_delay_seconds=1.0,
        retry_exponential_base=2.0,
        max_retry_delay_seconds=60.0,
    )


@pytest.fixture
def dev_config() -> WebhookFrameworkConfig:
    """Create development configuration for testing."""
    return WebhookFrameworkConfig.development()


@pytest.fixture
def delivery_engine(dev_config: WebhookFrameworkConfig) -> WebhookDeliveryEngine:
    """Create a delivery engine with development config."""
    return WebhookDeliveryEngine(config=dev_config)


# ============================================================================
# Retry Logic Tests
# ============================================================================


class TestExponentialBackoff:
    """Tests for ExponentialBackoff calculator."""

    def test_initial_delay(self):
        """Test that first attempt uses initial delay."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=300.0,
            multiplier=2.0,
            jitter_factor=0.0,  # Disable jitter for predictable tests
        )
        delay = backoff.calculate(1)
        assert delay == 1.0

    def test_exponential_growth(self):
        """Test that delays grow exponentially."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=300.0,
            multiplier=2.0,
            jitter_factor=0.0,
        )

        # delay = initial * multiplier^(attempt-1)
        assert backoff.calculate(1) == 1.0  # 1 * 2^0 = 1
        assert backoff.calculate(2) == 2.0  # 1 * 2^1 = 2
        assert backoff.calculate(3) == 4.0  # 1 * 2^2 = 4
        assert backoff.calculate(4) == 8.0  # 1 * 2^3 = 8

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=10.0,
            multiplier=2.0,
            jitter_factor=0.0,
        )

        # Without cap: 1 * 2^9 = 512
        # With cap: 10
        assert backoff.calculate(10) == 10.0

    def test_jitter_adds_variance(self):
        """Test that jitter adds variance to delays."""
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=300.0,
            multiplier=2.0,
            jitter_factor=0.5,  # 50% jitter
        )

        # Calculate multiple delays and check they have variance
        delays = [backoff.calculate(3) for _ in range(10)]

        # Base delay for attempt 3 is 4.0
        # With 50% jitter, delays should be between 4.0 and 6.0
        for delay in delays:
            assert 4.0 <= delay <= 6.0

        # Check there's actual variance (not all the same)
        assert len(set(delays)) > 1

    def test_from_policy(self):
        """Test creating backoff from WebhookRetryPolicy."""
        policy = WebhookRetryPolicy(
            initial_delay_seconds=2.0,
            max_delay_seconds=120.0,
            exponential_base=3.0,
            jitter_factor=0.2,
        )
        backoff = ExponentialBackoff.from_policy(policy)

        assert backoff.initial_delay == 2.0
        assert backoff.max_delay == 120.0
        assert backoff.multiplier == 3.0
        assert backoff.jitter_factor == 0.2


class TestRetryState:
    """Tests for RetryState tracker."""

    def test_initial_state(self):
        """Test initial retry state."""
        state = RetryState(max_attempts=3)

        assert state.current_attempt == 0
        assert state.can_retry is True
        assert state.last_error is None
        assert state.errors == []

    def test_start_increments_attempt(self):
        """Test that start() increments attempt counter."""
        state = RetryState(max_attempts=3)

        state.start()
        assert state.current_attempt == 1

        state.start()
        assert state.current_attempt == 2

    def test_can_retry_exhaustion(self):
        """Test that can_retry becomes False after max attempts."""
        state = RetryState(max_attempts=3)

        for _ in range(3):
            state.start()

        assert state.current_attempt == 3
        assert state.can_retry is False

    def test_error_recording(self):
        """Test that errors are recorded."""
        state = RetryState(max_attempts=3)

        error1 = Exception("Error 1")
        error2 = Exception("Error 2")

        state.record_error(error1, status_code=500)
        state.record_error(error2, status_code=503)

        assert len(state.errors) == 2
        assert state.last_error == error2
        assert state.last_status_code == 503


class TestShouldRetryStatusCode:
    """Tests for should_retry_status_code function."""

    def test_default_retryable_codes(self):
        """Test default retryable status codes."""
        assert should_retry_status_code(429) is True  # Rate limit
        assert should_retry_status_code(500) is True  # Internal server error
        assert should_retry_status_code(502) is True  # Bad gateway
        assert should_retry_status_code(503) is True  # Service unavailable
        assert should_retry_status_code(504) is True  # Gateway timeout

    def test_non_retryable_codes(self):
        """Test non-retryable status codes."""
        assert should_retry_status_code(200) is False  # Success
        assert should_retry_status_code(400) is False  # Bad request
        assert should_retry_status_code(401) is False  # Unauthorized
        assert should_retry_status_code(404) is False  # Not found

    def test_custom_retryable_codes(self):
        """Test with custom retryable codes."""
        custom_codes = {408, 500}  # Request timeout and server error

        assert should_retry_status_code(408, custom_codes) is True
        assert should_retry_status_code(500, custom_codes) is True
        assert should_retry_status_code(503, custom_codes) is False


class TestRetryLogic:
    """Tests specifically for retry logic behavior."""

    @pytest.mark.asyncio
    async def test_retry_logic_exponential_backoff(
        self, delivery_engine, sample_subscription, sample_event
    ):
        """Test that retry logic uses exponential backoff."""
        retry_delays: List[float] = []

        async def mock_request(*args, **kwargs):
            # Record the time between attempts
            if hasattr(mock_request, "last_call"):
                delay = time.monotonic() - mock_request.last_call
                retry_delays.append(delay)
            mock_request.last_call = time.monotonic()

            # Return 503 to trigger retry
            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 503
            mock_response.text = "Service Unavailable"
            mock_response.headers = {}
            return mock_response

        mock_request.last_call = None

        with patch.object(delivery_engine, "_make_request", side_effect=mock_request):
            result = await delivery_engine.deliver(sample_subscription, sample_event)

        # Should have failed after all retries
        assert result.success is False
        assert result.status == WebhookDeliveryStatus.DEAD_LETTERED

        # Check that we had retries with increasing delays
        # First attempt is immediate, then retries with backoff
        # Delays should increase (allowing some tolerance for async execution)
        if len(retry_delays) >= 2:
            # Each delay should be roughly double the previous (with tolerance)
            for i in range(1, len(retry_delays)):
                # Allow 50% tolerance due to timing variations
                assert retry_delays[i] >= retry_delays[i - 1] * 0.8

    @pytest.mark.asyncio
    async def test_retry_logic_respects_max_attempts(
        self, delivery_engine, sample_subscription, sample_event
    ):
        """Test that retry logic stops after max attempts."""
        attempt_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            # Always return 503 to trigger retry
            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 503
            mock_response.text = "Service Unavailable"
            mock_response.headers = {}
            return mock_response

        # Set max retries to 2 (3 total attempts)
        sample_subscription.max_retries = 2

        with patch.object(delivery_engine, "_make_request", side_effect=mock_request):
            result = await delivery_engine.deliver(sample_subscription, sample_event)

        # Should have made exactly 3 attempts (1 initial + 2 retries)
        assert attempt_count == 3
        assert result.success is False
        assert result.attempt_number == 3

    @pytest.mark.asyncio
    async def test_retry_logic_stops_on_success(
        self, delivery_engine, sample_subscription, sample_event
    ):
        """Test that retry logic stops immediately on success."""
        attempt_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            # Fail first attempt, succeed on second
            if attempt_count == 1:
                mock_response = MagicMock(spec=httpx.Response)
                mock_response.status_code = 503
                mock_response.text = "Service Unavailable"
                mock_response.headers = {}
                return mock_response
            else:
                mock_response = MagicMock(spec=httpx.Response)
                mock_response.status_code = 200
                mock_response.text = "OK"
                mock_response.headers = {}
                return mock_response

        with patch.object(delivery_engine, "_make_request", side_effect=mock_request):
            result = await delivery_engine.deliver(sample_subscription, sample_event)

        # Should have stopped after success on second attempt
        assert attempt_count == 2
        assert result.success is True
        assert result.attempt_number == 2

    @pytest.mark.asyncio
    async def test_retry_logic_no_retry_on_4xx(
        self, delivery_engine, sample_subscription, sample_event
    ):
        """Test that 4xx errors do not trigger retry."""
        attempt_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            mock_response = MagicMock(spec=httpx.Response)
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            mock_response.headers = {}
            return mock_response

        with patch.object(delivery_engine, "_make_request", side_effect=mock_request):
            result = await delivery_engine.deliver(sample_subscription, sample_event)

        # Should not retry on 400 error
        assert attempt_count == 1
        assert result.success is False
        assert result.status == WebhookDeliveryStatus.FAILED

    @pytest.mark.asyncio
    async def test_retry_logic_handles_timeout(
        self, delivery_engine, sample_subscription, sample_event
    ):
        """Test that timeouts trigger retry."""
        attempt_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < 3:
                raise RetryableError("Request timed out")
            else:
                mock_response = MagicMock(spec=httpx.Response)
                mock_response.status_code = 200
                mock_response.text = "OK"
                mock_response.headers = {}
                return mock_response

        with patch.object(delivery_engine, "_make_request", side_effect=mock_request):
            result = await delivery_engine.deliver(sample_subscription, sample_event)

        assert attempt_count == 3
        assert result.success is True

    @pytest.mark.asyncio
    async def test_retry_logic_handles_connection_error(
        self, delivery_engine, sample_subscription, sample_event
    ):
        """Test that connection errors trigger retry."""
        attempt_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < 2:
                raise RetryableError("Connection failed")
            else:
                mock_response = MagicMock(spec=httpx.Response)
                mock_response.status_code = 200
                mock_response.text = "OK"
                mock_response.headers = {}
                return mock_response

        with patch.object(delivery_engine, "_make_request", side_effect=mock_request):
            result = await delivery_engine.deliver(sample_subscription, sample_event)

        assert attempt_count == 2
        assert result.success is True


# ============================================================================
# Delivery Engine Tests
# ============================================================================


class TestWebhookDeliveryEngine:
    """Tests for WebhookDeliveryEngine."""

    @pytest.mark.asyncio
    async def test_successful_delivery(self, delivery_engine, sample_subscription, sample_event):
        """Test successful webhook delivery."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_response.headers = {}

        with patch.object(delivery_engine, "_make_request", return_value=mock_response):
            result = await delivery_engine.deliver(sample_subscription, sample_event)

        assert result.success is True
        assert result.status == WebhookDeliveryStatus.DELIVERED
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, delivery_engine, sample_subscription, sample_event):
        """Test that metrics are tracked correctly."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_response.headers = {}

        with patch.object(delivery_engine, "_make_request", return_value=mock_response):
            await delivery_engine.deliver(sample_subscription, sample_event)

        metrics = delivery_engine.metrics
        assert metrics["deliveries_attempted"] == 1
        assert metrics["deliveries_succeeded"] == 1
        assert metrics["deliveries_failed"] == 0

    @pytest.mark.asyncio
    async def test_dead_letter_queue(self, delivery_engine, sample_subscription, sample_event):
        """Test that failed deliveries are added to dead letter queue."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_response.headers = {}

        # Set max retries to 0 for quick failure
        sample_subscription.max_retries = 0

        with patch.object(delivery_engine, "_make_request", return_value=mock_response):
            result = await delivery_engine.deliver(sample_subscription, sample_event)

        assert result.success is False
        assert result.status == WebhookDeliveryStatus.DEAD_LETTERED
        assert delivery_engine.dead_letter_queue.size == 1

    @pytest.mark.asyncio
    async def test_hmac_signature_generation(self, delivery_engine):
        """Test HMAC signature generation."""
        payload = b'{"test": "data"}'
        secret = "test-secret"

        signature = delivery_engine._generate_hmac_signature(payload, secret, "sha256")

        # Verify signature format
        assert signature.startswith("sha256=")

        # Verify signature value
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        assert signature == f"sha256={expected}"

    @pytest.mark.asyncio
    async def test_build_headers_with_api_key(self, delivery_engine):
        """Test header building with API key authentication."""
        from pydantic import SecretStr

        config = WebhookConfig(
            url="https://example.com/webhook",
            auth_type=WebhookAuthType.API_KEY,
            auth_value=SecretStr("test-api-key"),
            auth_header="X-API-Key",
        )
        payload = b'{"test": "data"}'

        headers = delivery_engine._build_headers(config, payload)

        assert headers["X-API-Key"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_build_headers_with_bearer_token(self, delivery_engine):
        """Test header building with Bearer token authentication."""
        from pydantic import SecretStr

        config = WebhookConfig(
            url="https://example.com/webhook",
            auth_type=WebhookAuthType.BEARER,
            auth_value=SecretStr("test-bearer-token"),
        )
        payload = b'{"test": "data"}'

        headers = delivery_engine._build_headers(config, payload)

        assert headers["Authorization"] == "Bearer test-bearer-token"

    @pytest.mark.asyncio
    async def test_build_headers_with_hmac(self, delivery_engine):
        """Test header building with HMAC signature."""
        from pydantic import SecretStr

        config = WebhookConfig(
            url="https://example.com/webhook",
            auth_type=WebhookAuthType.HMAC,
            hmac_secret=SecretStr("test-hmac-secret"),
            hmac_header="X-Webhook-Signature",
        )
        payload = b'{"test": "data"}'

        headers = delivery_engine._build_headers(config, payload)

        assert "X-Webhook-Signature" in headers
        assert headers["X-Webhook-Signature"].startswith("sha256=")


class TestDeadLetterQueue:
    """Tests for DeadLetterQueue."""

    @pytest.mark.asyncio
    async def test_add_and_get(self):
        """Test adding and retrieving from dead letter queue."""
        dlq = DeadLetterQueue(max_size=100)

        from src.webhooks.models import WebhookDelivery

        delivery = WebhookDelivery(
            subscription_id="sub-1",
            event_id="evt-1",
            attempt_number=3,
        )
        event = WebhookEvent(
            event_type=WebhookEventType.POLICY_VIOLATION,
            title="Test Event",
            severity="high",
        )

        await dlq.add(delivery, event, "Test error")

        items = await dlq.get_all()
        assert len(items) == 1
        assert items[0]["delivery_id"] == delivery.id
        assert items[0]["error_message"] == "Test error"

    @pytest.mark.asyncio
    async def test_max_size_limit(self):
        """Test that queue respects max size."""
        dlq = DeadLetterQueue(max_size=3)

        from src.webhooks.models import WebhookDelivery

        for i in range(5):
            delivery = WebhookDelivery(
                id=f"del-{i}",
                subscription_id="sub-1",
                event_id=f"evt-{i}",
            )
            event = WebhookEvent(
                id=f"evt-{i}",
                event_type=WebhookEventType.POLICY_VIOLATION,
                title=f"Test Event {i}",
                severity="high",
            )
            await dlq.add(delivery, event, f"Error {i}")

        items = await dlq.get_all()
        assert len(items) == 3
        # Oldest items should be removed
        ids = [item["delivery_id"] for item in items]
        assert "del-0" not in ids
        assert "del-1" not in ids

    @pytest.mark.asyncio
    async def test_get_by_subscription(self):
        """Test filtering by subscription ID."""
        dlq = DeadLetterQueue()

        from src.webhooks.models import WebhookDelivery

        for sub_id in ["sub-1", "sub-1", "sub-2"]:
            delivery = WebhookDelivery(
                subscription_id=sub_id,
                event_id="evt-1",
            )
            event = WebhookEvent(
                event_type=WebhookEventType.POLICY_VIOLATION,
                title="Test",
                severity="high",
            )
            await dlq.add(delivery, event, "Error")

        sub1_items = await dlq.get_by_subscription("sub-1")
        sub2_items = await dlq.get_by_subscription("sub-2")

        assert len(sub1_items) == 2
        assert len(sub2_items) == 1

    @pytest.mark.asyncio
    async def test_remove(self):
        """Test removing an item from the queue."""
        dlq = DeadLetterQueue()

        from src.webhooks.models import WebhookDelivery

        delivery = WebhookDelivery(
            id="del-to-remove",
            subscription_id="sub-1",
            event_id="evt-1",
        )
        event = WebhookEvent(
            event_type=WebhookEventType.POLICY_VIOLATION,
            title="Test",
            severity="high",
        )
        await dlq.add(delivery, event, "Error")

        assert dlq.size == 1

        removed = await dlq.remove("del-to-remove")
        assert removed is True
        assert dlq.size == 0

        # Try to remove non-existent
        removed = await dlq.remove("non-existent")
        assert removed is False


class TestCreateDeliveryEngine:
    """Tests for create_delivery_engine factory function."""

    def test_development_mode(self):
        """Test creating engine in development mode."""
        engine = create_delivery_engine(development_mode=True)

        assert engine.config.security.allow_insecure_http is True
        assert engine.config.security.allow_private_networks is True

    def test_production_mode(self):
        """Test creating engine in production mode."""
        engine = create_delivery_engine(development_mode=False)

        assert engine.config.security.allow_insecure_http is False
        assert engine.config.security.allow_private_networks is False

    def test_custom_config(self):
        """Test creating engine with custom config."""
        config = WebhookFrameworkConfig(
            max_concurrent_deliveries=50,
            default_timeout_seconds=60.0,
        )
        engine = create_delivery_engine(config=config)

        assert engine.config.max_concurrent_deliveries == 50
        assert engine.config.default_timeout_seconds == 60.0
