"""
ACGS-2 Policy Registry - Storage Service Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive test coverage for StorageService including:
- Local filesystem storage operations
- S3/MinIO cloud storage operations
- Fallback behavior
- Bundle existence checking
- Error handling
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# Mock settings for testing
# =============================================================================

class MockBundleSettings:
    """Mock bundle settings for testing."""
    def __init__(self, storage_path: str, s3_bucket: str = None):
        self.storage_path = storage_path
        self.s3_bucket = s3_bucket


class MockSettings:
    """Mock settings object."""
    def __init__(self, storage_path: str, s3_bucket: str = None):
        self.bundle = MockBundleSettings(storage_path, s3_bucket)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for local storage tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_settings_local(temp_storage_dir):
    """Create mock settings for local storage."""
    return MockSettings(storage_path=temp_storage_dir, s3_bucket=None)


@pytest.fixture
def mock_settings_s3(temp_storage_dir):
    """Create mock settings for S3 storage."""
    return MockSettings(storage_path=temp_storage_dir, s3_bucket="test-bucket")


@pytest.fixture
def mock_s3_client():
    """Create mock S3 client."""
    mock = MagicMock()
    mock.head_bucket = MagicMock()
    mock.put_object = MagicMock()
    mock.get_object = MagicMock()
    mock.delete_object = MagicMock()
    mock.head_object = MagicMock()
    return mock


@pytest.fixture
def sample_bundle_data():
    """Sample bundle data for testing."""
    return b"test policy bundle data with constitutional hash cdd01ef066bc6cf2"


# =============================================================================
# Local Storage Tests
# =============================================================================

class TestLocalStorage:
    """Tests for local filesystem storage operations."""

    @pytest.mark.asyncio
    async def test_save_bundle_local(self, temp_storage_dir, sample_bundle_data):
        """Test saving a bundle to local storage."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import StorageService

            service = StorageService()
            bundle_id = "test-bundle-001"

            path = await service.save_bundle(bundle_id, sample_bundle_data)

            assert path.endswith(".tar.gz")
            assert os.path.exists(path)
            with open(path, "rb") as f:
                assert f.read() == sample_bundle_data

    @pytest.mark.asyncio
    async def test_get_bundle_local(self, temp_storage_dir, sample_bundle_data):
        """Test retrieving a bundle from local storage."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import StorageService

            service = StorageService()
            bundle_id = "test-bundle-002"

            # First save the bundle
            await service.save_bundle(bundle_id, sample_bundle_data)

            # Then retrieve it
            data = await service.get_bundle(bundle_id)

            assert data == sample_bundle_data

    @pytest.mark.asyncio
    async def test_get_nonexistent_bundle_returns_none(self, temp_storage_dir):
        """Test retrieving a non-existent bundle returns None."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import StorageService

            service = StorageService()

            data = await service.get_bundle("nonexistent-bundle")

            assert data is None

    @pytest.mark.asyncio
    async def test_delete_bundle_local(self, temp_storage_dir, sample_bundle_data):
        """Test deleting a bundle from local storage."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import StorageService

            service = StorageService()
            bundle_id = "test-bundle-003"

            # Save and then delete
            path = await service.save_bundle(bundle_id, sample_bundle_data)
            assert os.path.exists(path)

            result = await service.delete_bundle(bundle_id)

            assert result is True
            assert not os.path.exists(path)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_bundle_returns_false(self, temp_storage_dir):
        """Test deleting a non-existent bundle returns False."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import StorageService

            service = StorageService()

            result = await service.delete_bundle("nonexistent-bundle")

            assert result is False

    @pytest.mark.asyncio
    async def test_bundle_exists_local(self, temp_storage_dir, sample_bundle_data):
        """Test checking if a bundle exists in local storage."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import StorageService

            service = StorageService()
            bundle_id = "test-bundle-004"

            # Before saving
            assert await service.bundle_exists(bundle_id) is False

            # After saving
            await service.save_bundle(bundle_id, sample_bundle_data)
            assert await service.bundle_exists(bundle_id) is True

    @pytest.mark.asyncio
    async def test_bundle_id_with_colons_is_sanitized(self, temp_storage_dir, sample_bundle_data):
        """Test that bundle IDs with colons are properly sanitized."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import StorageService

            service = StorageService()
            bundle_id = "policy:v1:latest"

            path = await service.save_bundle(bundle_id, sample_bundle_data)

            # Colons should be replaced with underscores
            assert ":" not in os.path.basename(path)
            assert "_" in os.path.basename(path)


# =============================================================================
# S3 Storage Tests
# =============================================================================

class TestS3Storage:
    """Tests for S3/MinIO cloud storage operations."""

    @pytest.mark.asyncio
    async def test_save_bundle_s3(self, temp_storage_dir, sample_bundle_data, mock_s3_client):
        """Test saving a bundle to S3."""
        mock_settings = MockSettings(temp_storage_dir, s3_bucket="test-bucket")

        with patch("app.services.storage_service.settings", mock_settings), \
             patch("app.services.storage_service.S3_AVAILABLE", True), \
             patch("app.services.storage_service.boto3") as mock_boto3:

            mock_boto3.client.return_value = mock_s3_client

            from app.services.storage_service import StorageService
            service = StorageService()
            service._s3_client = mock_s3_client

            bundle_id = "test-bundle-s3"
            uri = await service.save_bundle(bundle_id, sample_bundle_data)

            assert uri.startswith("s3://test-bucket/")
            mock_s3_client.put_object.assert_called_once()
            call_kwargs = mock_s3_client.put_object.call_args[1]
            assert call_kwargs["Bucket"] == "test-bucket"
            assert call_kwargs["Body"] == sample_bundle_data
            assert call_kwargs["Metadata"]["constitutional-hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_get_bundle_s3(self, temp_storage_dir, sample_bundle_data, mock_s3_client):
        """Test retrieving a bundle from S3."""
        mock_settings = MockSettings(temp_storage_dir, s3_bucket="test-bucket")

        # Mock S3 response
        mock_body = MagicMock()
        mock_body.read.return_value = sample_bundle_data
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        with patch("app.services.storage_service.settings", mock_settings), \
             patch("app.services.storage_service.S3_AVAILABLE", True):

            from app.services.storage_service import StorageService
            service = StorageService()
            service._s3_client = mock_s3_client
            service.s3_bucket = "test-bucket"

            bundle_id = "test-bundle-s3"
            data = await service.get_bundle(bundle_id)

            assert data == sample_bundle_data
            mock_s3_client.get_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_bundle_s3(self, temp_storage_dir, mock_s3_client):
        """Test deleting a bundle from S3."""
        mock_settings = MockSettings(temp_storage_dir, s3_bucket="test-bucket")

        with patch("app.services.storage_service.settings", mock_settings), \
             patch("app.services.storage_service.S3_AVAILABLE", True):

            from app.services.storage_service import StorageService
            service = StorageService()
            service._s3_client = mock_s3_client
            service.s3_bucket = "test-bucket"

            bundle_id = "test-bundle-s3"
            result = await service.delete_bundle(bundle_id)

            assert result is True
            mock_s3_client.delete_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_bundle_exists_s3(self, temp_storage_dir, mock_s3_client):
        """Test checking if a bundle exists in S3."""
        mock_settings = MockSettings(temp_storage_dir, s3_bucket="test-bucket")

        with patch("app.services.storage_service.settings", mock_settings), \
             patch("app.services.storage_service.S3_AVAILABLE", True):

            from app.services.storage_service import StorageService
            service = StorageService()
            service._s3_client = mock_s3_client
            service.s3_bucket = "test-bucket"

            bundle_id = "test-bundle-s3"
            result = await service.bundle_exists(bundle_id)

            assert result is True
            mock_s3_client.head_object.assert_called_once()


# =============================================================================
# S3 Fallback Tests
# =============================================================================

class TestS3Fallback:
    """Tests for S3 fallback to local storage."""

    @pytest.mark.asyncio
    async def test_s3_upload_failure_falls_back_to_local(
        self, temp_storage_dir, sample_bundle_data, mock_s3_client
    ):
        """Test that S3 upload failure falls back to local storage."""
        from botocore.exceptions import ClientError

        mock_settings = MockSettings(temp_storage_dir, s3_bucket="test-bucket")

        # Make S3 put_object fail
        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal error"}},
            "PutObject"
        )

        with patch("app.services.storage_service.settings", mock_settings), \
             patch("app.services.storage_service.S3_AVAILABLE", True):

            from app.services.storage_service import StorageService
            service = StorageService()
            service._s3_client = mock_s3_client
            service.s3_bucket = "test-bucket"

            bundle_id = "test-bundle-fallback"
            path = await service.save_bundle(bundle_id, sample_bundle_data)

            # Should fall back to local storage
            assert not path.startswith("s3://")
            assert os.path.exists(path)

    @pytest.mark.asyncio
    async def test_s3_download_failure_falls_back_to_local(
        self, temp_storage_dir, sample_bundle_data, mock_s3_client
    ):
        """Test that S3 download failure falls back to local storage."""
        from botocore.exceptions import ClientError

        mock_settings = MockSettings(temp_storage_dir, s3_bucket="test-bucket")

        # Make S3 get_object fail with NoSuchKey
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject"
        )

        with patch("app.services.storage_service.settings", mock_settings), \
             patch("app.services.storage_service.S3_AVAILABLE", True):

            from app.services.storage_service import StorageService
            service = StorageService()
            service._s3_client = mock_s3_client
            service.s3_bucket = "test-bucket"

            # First save locally
            await service._save_to_local("test-bundle", sample_bundle_data)

            # Now try to get it - S3 should fail, then local should succeed
            data = await service.get_bundle("test-bundle")

            assert data == sample_bundle_data


# =============================================================================
# Path Generation Tests
# =============================================================================

class TestPathGeneration:
    """Tests for storage path generation."""

    def test_get_s3_key_format(self, temp_storage_dir):
        """Test S3 key generation format."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import StorageService

            service = StorageService()

            key = service._get_s3_key("test-bundle-001")

            assert key == "bundles/test-bundle-001.tar.gz"

    def test_get_s3_key_sanitizes_colons(self, temp_storage_dir):
        """Test that S3 key generation sanitizes colons."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import StorageService

            service = StorageService()

            key = service._get_s3_key("policy:v1:latest")

            assert ":" not in key
            assert key == "bundles/policy_v1_latest.tar.gz"

    def test_get_local_path_format(self, temp_storage_dir):
        """Test local path generation format."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import StorageService

            service = StorageService()

            path = service._get_local_path("test-bundle-001")

            assert path.endswith("test-bundle-001.tar.gz")
            assert temp_storage_dir in path

    def test_get_local_path_sanitizes_colons(self, temp_storage_dir):
        """Test that local path generation sanitizes colons."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import StorageService

            service = StorageService()

            path = service._get_local_path("policy:v1:latest")

            assert ":" not in os.path.basename(path)
            assert "policy_v1_latest.tar.gz" in path


# =============================================================================
# Singleton Pattern Tests
# =============================================================================

class TestSingletonPattern:
    """Tests for the singleton pattern implementation."""

    def test_get_storage_service_returns_same_instance(self, temp_storage_dir):
        """Test that get_storage_service returns the same instance."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import get_storage_service

            # Clear the cache first
            get_storage_service.cache_clear()

            service1 = get_storage_service()
            service2 = get_storage_service()

            assert service1 is service2


# =============================================================================
# Initialization Tests
# =============================================================================

class TestStorageInitialization:
    """Tests for storage service initialization."""

    def test_local_storage_creates_base_directory(self, temp_storage_dir):
        """Test that local storage initialization creates the base directory."""
        storage_path = os.path.join(temp_storage_dir, "new_subdir")

        with patch("app.services.storage_service.settings", MockSettings(storage_path)):
            from app.services.storage_service import StorageService

            service = StorageService()

            assert os.path.exists(storage_path)

    def test_s3_initialization_with_missing_credentials(self, temp_storage_dir):
        """Test S3 initialization falls back to local when credentials missing."""
        mock_settings = MockSettings(temp_storage_dir, s3_bucket="test-bucket")

        with patch("app.services.storage_service.settings", mock_settings), \
             patch("app.services.storage_service.S3_AVAILABLE", True), \
             patch("app.services.storage_service.boto3") as mock_boto3:

            from botocore.exceptions import NoCredentialsError
            mock_boto3.client.side_effect = NoCredentialsError()

            from app.services.storage_service import StorageService
            service = StorageService()

            # Should fall back to local storage
            assert service._s3_client is None
            assert os.path.exists(service.base_path)


# =============================================================================
# Constitutional Compliance Tests
# =============================================================================

class TestConstitutionalCompliance:
    """Tests for constitutional compliance in storage operations."""

    @pytest.mark.asyncio
    async def test_s3_upload_includes_constitutional_hash_metadata(
        self, temp_storage_dir, sample_bundle_data, mock_s3_client
    ):
        """Test that S3 uploads include constitutional hash in metadata."""
        mock_settings = MockSettings(temp_storage_dir, s3_bucket="test-bucket")

        with patch("app.services.storage_service.settings", mock_settings), \
             patch("app.services.storage_service.S3_AVAILABLE", True):

            from app.services.storage_service import StorageService
            service = StorageService()
            service._s3_client = mock_s3_client
            service.s3_bucket = "test-bucket"

            await service.save_bundle("test-bundle", sample_bundle_data)

            call_kwargs = mock_s3_client.put_object.call_args[1]
            assert "Metadata" in call_kwargs
            assert call_kwargs["Metadata"]["constitutional-hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_bundle_data_integrity(self, temp_storage_dir, sample_bundle_data):
        """Test that bundle data maintains integrity through save/load cycle."""
        with patch("app.services.storage_service.settings", MockSettings(temp_storage_dir)):
            from app.services.storage_service import StorageService

            service = StorageService()
            bundle_id = "integrity-test"

            await service.save_bundle(bundle_id, sample_bundle_data)
            loaded_data = await service.get_bundle(bundle_id)

            assert loaded_data == sample_bundle_data
            # Verify constitutional hash is in the data
            assert CONSTITUTIONAL_HASH.encode() in loaded_data
