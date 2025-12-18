"""
ACGS-2 Enhanced Agent Bus - Actual Policy Client Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests that exercise the actual policy_client.py module.
"""

import pytest
import os
import sys
import importlib.util
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path for local imports
_parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, _parent_dir)

# Import models directly first
from models import AgentMessage, MessageType, MessagePriority
from validators import ValidationResult

# Now load policy_client with mocked relative imports
_policy_client_path = os.path.join(_parent_dir, "policy_client.py")

# Read source and patch relative imports
with open(_policy_client_path, 'r') as f:
    _source = f.read()

# Replace relative imports with absolute
_source = _source.replace(
    "from .models import AgentMessage",
    "from models import AgentMessage"
)
_source = _source.replace(
    "from .validators import ValidationResult",
    "from validators import ValidationResult"
)

# Create module namespace
_policy_ns = {
    '__name__': 'policy_client',
    '__file__': _policy_client_path,
}

# Execute in namespace
exec(compile(_source, _policy_client_path, 'exec'), _policy_ns)

# Extract classes/functions
PolicyRegistryClient = _policy_ns['PolicyRegistryClient']
get_policy_client = _policy_ns['get_policy_client']
initialize_policy_client = _policy_ns['initialize_policy_client']
close_policy_client = _policy_ns['close_policy_client']

# Store namespace for accessing _policy_client
_policy_module = _policy_ns


# ============================================================================
# PolicyRegistryClient Tests
# ============================================================================

class TestPolicyRegistryClientActual:
    """Test actual PolicyRegistryClient class."""

    def test_init_defaults(self):
        """Test default initialization."""
        client = PolicyRegistryClient()
        assert client.registry_url == "http://localhost:8000"
        assert client.timeout == 5.0
        assert client.cache_ttl == 300
        assert client._cache == {}
        assert client._http_client is None

    def test_init_custom(self):
        """Test custom initialization."""
        client = PolicyRegistryClient(
            registry_url="http://custom:9000/",
            timeout=10.0,
            cache_ttl=600
        )
        assert client.registry_url == "http://custom:9000"
        assert client.timeout == 10.0
        assert client.cache_ttl == 600

    def test_url_strips_trailing_slash(self):
        """Test URL trailing slash is stripped."""
        client = PolicyRegistryClient(registry_url="http://test.com/api/")
        assert not client.registry_url.endswith("/")

    @pytest.mark.asyncio
    async def test_aenter_initializes(self):
        """Test context manager calls initialize."""
        client = PolicyRegistryClient()
        with patch.object(client, 'initialize', new_callable=AsyncMock) as mock_init:
            with patch.object(client, 'close', new_callable=AsyncMock):
                result = await client.__aenter__()
                mock_init.assert_called_once()
                assert result is client

    @pytest.mark.asyncio
    async def test_aexit_closes(self):
        """Test context manager calls close."""
        client = PolicyRegistryClient()
        with patch.object(client, 'close', new_callable=AsyncMock) as mock_close:
            await client.__aexit__(None, None, None)
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_creates_client(self):
        """Test initialize creates HTTP client."""
        client = PolicyRegistryClient()
        await client.initialize()
        assert client._http_client is not None
        await client.close()

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Test multiple initializes keep same client."""
        client = PolicyRegistryClient()
        await client.initialize()
        first = client._http_client
        await client.initialize()
        assert client._http_client is first
        await client.close()

    @pytest.mark.asyncio
    async def test_close_clears_client(self):
        """Test close clears HTTP client."""
        client = PolicyRegistryClient()
        await client.initialize()
        assert client._http_client is not None
        await client.close()
        assert client._http_client is None

    @pytest.mark.asyncio
    async def test_close_safe_when_none(self):
        """Test close is safe when no client."""
        client = PolicyRegistryClient()
        await client.close()  # Should not raise
        assert client._http_client is None


class TestGetPolicyContentActual:
    """Test get_policy_content with mocked HTTP."""

    @pytest.fixture
    def client(self):
        """Create client with mocked HTTP."""
        client = PolicyRegistryClient()
        client._http_client = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_success(self, client):
        """Test successful policy fetch."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"rule": "value"}
        mock_resp.raise_for_status = MagicMock()
        client._http_client.get = AsyncMock(return_value=mock_resp)

        result = await client.get_policy_content("test_policy")
        assert result == {"rule": "value"}

    @pytest.mark.asyncio
    async def test_with_client_id(self, client):
        """Test fetch with client_id parameter."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"variant": "B"}
        mock_resp.raise_for_status = MagicMock()
        client._http_client.get = AsyncMock(return_value=mock_resp)

        result = await client.get_policy_content("policy", client_id="abc123")
        assert result == {"variant": "B"}
        call_args = client._http_client.get.call_args
        assert call_args[1]["params"] == {"client_id": "abc123"}

    @pytest.mark.asyncio
    async def test_404_returns_none(self, client):
        """Test 404 returns None."""
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        error = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_resp)
        client._http_client.get = AsyncMock(side_effect=error)

        result = await client.get_policy_content("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_raises(self, client):
        """Test timeout exception is raised."""
        import httpx
        client._http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(httpx.TimeoutException):
            await client.get_policy_content("policy")

    @pytest.mark.asyncio
    async def test_connect_error_raises(self, client):
        """Test connection error is raised."""
        import httpx
        client._http_client.get = AsyncMock(side_effect=httpx.ConnectError("Failed"))

        with pytest.raises(httpx.ConnectError):
            await client.get_policy_content("policy")


class TestValidateMessageActual:
    """Test validate_message_signature with actual module."""

    @pytest.fixture
    def client(self):
        """Create client."""
        return PolicyRegistryClient()

    @pytest.fixture
    def message(self):
        """Create test message."""
        return AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"action": "test", "topics": ["general"]},
            from_agent="sender",
            to_agent="receiver",
            priority=MessagePriority.NORMAL,
        )

    @pytest.mark.asyncio
    async def test_no_policy_returns_warning(self, client, message):
        """Test no policy returns valid with warning."""
        with patch.object(client, 'get_policy_content', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            result = await client.validate_message_signature(message)
            assert result.is_valid is True
            assert any("unavailable" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_valid_content_passes(self, client, message):
        """Test valid content passes."""
        policy = {
            "max_response_length": 10000,
            "allowed_topics": ["general"],
            "prohibited_content": []
        }
        with patch.object(client, 'get_policy_content', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = policy
            result = await client.validate_message_signature(message)
            assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_exceeds_length_fails(self, client):
        """Test message exceeding max length fails."""
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"data": "x" * 500},
            from_agent="sender",
            to_agent="receiver",
        )
        policy = {
            "max_response_length": 100,
            "prohibited_content": []
        }
        with patch.object(client, 'get_policy_content', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = policy
            result = await client.validate_message_signature(message)
            assert result.is_valid is False
            assert any("exceeds" in e.lower() or "maximum" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_prohibited_content_fails(self, client):
        """Test prohibited content fails."""
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"text": "contains FORBIDDEN word"},
            from_agent="sender",
            to_agent="receiver",
        )
        policy = {
            "max_response_length": 10000,
            "prohibited_content": ["forbidden"]
        }
        with patch.object(client, 'get_policy_content', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = policy
            result = await client.validate_message_signature(message)
            assert result.is_valid is False
            assert any("prohibited" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_topic_warning(self, client):
        """Test topic not in allowed list warns."""
        message = AgentMessage(
            message_type=MessageType.TASK_REQUEST,
            content={"text": "test", "topics": ["unknown"]},
            from_agent="sender",
            to_agent="receiver",
        )
        policy = {
            "max_response_length": 10000,
            "allowed_topics": ["finance", "tech"],
            "prohibited_content": []
        }
        with patch.object(client, 'get_policy_content', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = policy
            result = await client.validate_message_signature(message)
            assert result.is_valid is True
            assert any("topic" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_network_error_returns_warning(self, client, message):
        """Test network error returns valid with warning."""
        import httpx
        with patch.object(client, 'get_policy_content', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Timeout")
            result = await client.validate_message_signature(message)
            assert result.is_valid is True
            assert any("network" in w.lower() for w in result.warnings)


class TestHealthCheckActual:
    """Test health_check with actual module."""

    @pytest.fixture
    def client(self):
        """Create client with mocked HTTP."""
        client = PolicyRegistryClient()
        client._http_client = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_healthy(self, client):
        """Test healthy response."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "healthy"}
        mock_resp.raise_for_status = MagicMock()
        client._http_client.get = AsyncMock(return_value=mock_resp)

        result = await client.health_check()
        assert result == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_http_error(self, client):
        """Test HTTP error returns unhealthy."""
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        error = httpx.HTTPStatusError("Error", request=MagicMock(), response=mock_resp)
        client._http_client.get = AsyncMock(side_effect=error)

        result = await client.health_check()
        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_timeout(self, client):
        """Test timeout returns unhealthy."""
        import httpx
        client._http_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        result = await client.health_check()
        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_connect_error(self, client):
        """Test connection error returns unhealthy."""
        import httpx
        client._http_client.get = AsyncMock(side_effect=httpx.ConnectError("Failed"))

        result = await client.health_check()
        assert result["status"] == "unhealthy"


class TestGetPublicKeyActual:
    """Test get_current_public_key with actual module."""

    @pytest.fixture
    def client(self):
        """Create client with mocked HTTP."""
        client = PolicyRegistryClient()
        client._http_client = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_success(self, client):
        """Test successful key fetch."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"current_public_key": "key123"}
        mock_resp.raise_for_status = MagicMock()
        client._http_client.get = AsyncMock(return_value=mock_resp)

        result = await client.get_current_public_key()
        assert result == "key123"

    @pytest.mark.asyncio
    async def test_error_returns_none(self, client):
        """Test error returns None."""
        import httpx
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        error = httpx.HTTPStatusError("Error", request=MagicMock(), response=mock_resp)
        client._http_client.get = AsyncMock(side_effect=error)

        result = await client.get_current_public_key()
        assert result is None


# ============================================================================
# Global Function Tests
# ============================================================================

class TestGlobalFunctionsActual:
    """Test global policy client functions."""

    def test_get_policy_client_creates_singleton(self):
        """Test get_policy_client returns singleton."""
        _policy_module['_policy_client'] = None

        client1 = get_policy_client()
        client2 = get_policy_client()
        assert client1 is client2

        _policy_module['_policy_client'] = None

    @pytest.mark.asyncio
    async def test_initialize_policy_client(self):
        """Test initialize_policy_client creates and initializes."""
        _policy_module['_policy_client'] = None

        await initialize_policy_client("http://test:8000")

        assert _policy_module['_policy_client'] is not None
        assert _policy_module['_policy_client'].registry_url == "http://test:8000"

        await close_policy_client()

    @pytest.mark.asyncio
    async def test_close_policy_client(self):
        """Test close_policy_client clears global."""
        await initialize_policy_client()

        await close_policy_client()

        assert _policy_module['_policy_client'] is None

    @pytest.mark.asyncio
    async def test_close_when_none(self):
        """Test close safe when no client."""
        _policy_module['_policy_client'] = None
        await close_policy_client()  # Should not raise
