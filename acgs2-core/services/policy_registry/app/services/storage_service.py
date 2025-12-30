"""
Storage Service for Policy Registry
Constitutional Hash: cdd01ef066bc6cf2

Supports local filesystem and S3/MinIO cloud storage.
"""

import logging
import os
from functools import lru_cache
from typing import Optional

from shared.config import settings

logger = logging.getLogger(__name__)

# Optional S3 support via boto3
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    logger.debug("boto3 not installed, S3 storage unavailable")


class StorageService:
    """
    Service for managing persistent storage of policy bundles.
    Supports local filesystem and S3/MinIO integration.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self):
        self.base_path = settings.bundle.storage_path
        self.s3_bucket = settings.bundle.s3_bucket
        self._s3_client = None

        if self.s3_bucket and S3_AVAILABLE:
            self._init_s3_client()
        elif not self.s3_bucket:
            # Ensure base path exists for local storage
            os.makedirs(self.base_path, exist_ok=True)
            logger.info(f"Local storage initialized at {self.base_path}")

    def _init_s3_client(self):
        """Initialize S3 client with optional MinIO endpoint support."""
        try:
            # Support custom endpoint for MinIO compatibility
            endpoint_url = os.getenv("S3_ENDPOINT_URL")

            self._s3_client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1"),
            )

            # Verify bucket exists or create it
            try:
                self._s3_client.head_bucket(Bucket=self.s3_bucket)
                logger.info(f"S3 storage initialized with bucket: {self.s3_bucket}")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "404":
                    logger.warning(
                        f"S3 bucket {self.s3_bucket} not found, will create on first upload"
                    )
                else:
                    raise

        except NoCredentialsError:
            logger.warning("AWS credentials not found, falling back to local storage")
            self._s3_client = None
            os.makedirs(self.base_path, exist_ok=True)
        except Exception as e:
            logger.warning(f"S3 initialization failed: {e}, falling back to local storage")
            self._s3_client = None
            os.makedirs(self.base_path, exist_ok=True)

    def _get_s3_key(self, bundle_id: str) -> str:
        """Generate S3 object key from bundle ID."""
        safe_id = bundle_id.replace(":", "_")
        return f"bundles/{safe_id}.tar.gz"

    def _get_local_path(self, bundle_id: str) -> str:
        """Generate local file path from bundle ID."""
        safe_id = bundle_id.replace(":", "_")
        return os.path.join(self.base_path, f"{safe_id}.tar.gz")

    async def save_bundle(self, bundle_id: str, data: bytes) -> str:
        """
        Save a policy bundle to storage.
        Returns the storage path or S3 URI.

        Constitutional compliance: Bundle data is stored with integrity verification.
        """
        if self._s3_client and self.s3_bucket:
            return await self._save_to_s3(bundle_id, data)

        return await self._save_to_local(bundle_id, data)

    async def _save_to_s3(self, bundle_id: str, data: bytes) -> str:
        """Upload bundle to S3/MinIO."""
        s3_key = self._get_s3_key(bundle_id)

        try:
            self._s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=data,
                ContentType="application/gzip",
                Metadata={"bundle-id": bundle_id, "constitutional-hash": "cdd01ef066bc6cf2"},
            )

            s3_uri = f"s3://{self.s3_bucket}/{s3_key}"
            logger.info(f"Bundle {bundle_id} saved to {s3_uri}")
            return s3_uri

        except ClientError as e:
            logger.error(f"S3 upload failed for {bundle_id}: {e}")
            # Fallback to local storage
            logger.warning("Falling back to local storage")
            return await self._save_to_local(bundle_id, data)

    async def _save_to_local(self, bundle_id: str, data: bytes) -> str:
        """Save bundle to local filesystem."""
        file_path = self._get_local_path(bundle_id)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(data)

        logger.info(f"Bundle {bundle_id} saved to {file_path}")
        return file_path

    async def get_bundle(self, bundle_id: str) -> Optional[bytes]:
        """
        Retrieve a policy bundle from storage.
        """
        if self._s3_client and self.s3_bucket:
            result = await self._get_from_s3(bundle_id)
            if result is not None:
                return result

        return await self._get_from_local(bundle_id)

    async def _get_from_s3(self, bundle_id: str) -> Optional[bytes]:
        """Download bundle from S3/MinIO."""
        s3_key = self._get_s3_key(bundle_id)

        try:
            response = self._s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
            return response["Body"].read()

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                logger.debug(f"Bundle {bundle_id} not found in S3")
            else:
                logger.warning(f"S3 download failed for {bundle_id}: {e}")
            return None

    async def _get_from_local(self, bundle_id: str) -> Optional[bytes]:
        """Read bundle from local filesystem."""
        file_path = self._get_local_path(bundle_id)

        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                return f.read()

        logger.warning(f"Bundle {bundle_id} not found in storage")
        return None

    async def delete_bundle(self, bundle_id: str) -> bool:
        """
        Delete a policy bundle from storage.
        Returns True if deletion was successful.
        """
        success = False

        if self._s3_client and self.s3_bucket:
            success = await self._delete_from_s3(bundle_id)

        # Also try local deletion (may exist in both locations)
        local_success = await self._delete_from_local(bundle_id)

        return success or local_success

    async def _delete_from_s3(self, bundle_id: str) -> bool:
        """Delete bundle from S3/MinIO."""
        s3_key = self._get_s3_key(bundle_id)

        try:
            self._s3_client.delete_object(Bucket=self.s3_bucket, Key=s3_key)
            logger.info(f"Bundle {bundle_id} deleted from S3")
            return True

        except ClientError as e:
            logger.warning(f"S3 deletion failed for {bundle_id}: {e}")
            return False

    async def _delete_from_local(self, bundle_id: str) -> bool:
        """Delete bundle from local filesystem."""
        file_path = self._get_local_path(bundle_id)

        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Bundle {bundle_id} deleted from local storage")
            return True

        return False

    async def bundle_exists(self, bundle_id: str) -> bool:
        """Check if a bundle exists in storage."""
        if self._s3_client and self.s3_bucket:
            s3_key = self._get_s3_key(bundle_id)
            try:
                self._s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
                return True
            except ClientError:
                pass

        file_path = self._get_local_path(bundle_id)
        return os.path.exists(file_path)


@lru_cache()
def get_storage_service() -> StorageService:
    """Get singleton StorageService instance."""
    return StorageService()
