"""
Storage Service for Policy Registry
Constitutional Hash: cdd01ef066bc6cf2
"""

import os
import shutil
import logging
from typing import Optional, BinaryIO
from shared.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    """
    Service for managing persistent storage of policy bundles.
    Supports local filesystem and prepares for S3/MinIO integration.
    """
    
    def __init__(self):
        self.base_path = settings.bundle.storage_path
        self.s3_bucket = settings.bundle.s3_bucket
        
        # Ensure base path exists for local storage
        if not self.s3_bucket:
            os.makedirs(self.base_path, exist_ok=True)
            logger.info(f"Local storage initialized at {self.base_path}")
            
    async def save_bundle(self, bundle_id: str, data: bytes) -> str:
        """
        Save a policy bundle to storage.
        Returns the storage path or URI.
        """
        # Normalize ID for filesystem safety
        safe_id = bundle_id.replace(":", "_")
        
        if self.s3_bucket:
            # TODO: Implement S3 upload
            logger.warning("S3 storage not yet implemented, falling back to local")
        
        file_path = os.path.join(self.base_path, f"{safe_id}.tar.gz")
        with open(file_path, "wb") as f:
            f.write(data)
            
        logger.info(f"Bundle {bundle_id} saved to {file_path}")
        return file_path

    async def get_bundle(self, bundle_id: str) -> Optional[bytes]:
        """
        Retrieve a policy bundle from storage.
        """
        safe_id = bundle_id.replace(":", "_")
        file_path = os.path.join(self.base_path, f"{safe_id}.tar.gz")
        
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                return f.read()
        
        logger.warning(f"Bundle {bundle_id} not found in storage")
        return None

    async def delete_bundle(self, bundle_id: str):
        """
        Delete a policy bundle from storage.
        """
        safe_id = bundle_id.replace(":", "_")
        file_path = os.path.join(self.base_path, f"{safe_id}.tar.gz")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Bundle {bundle_id} deleted from storage")
