"""
ACGS-2 Policy Bundle Manager
Constitutional Hash: cdd01ef066bc6cf2

Handles compilation, signing, and (simulated) distribution of OPA bundles.
"""

import base64
import hashlib
import json
import logging
import os
import tarfile
from datetime import datetime, timezone
from typing import Any, Dict

# Try to import CryptoService from policy_registry
try:
    import sys

    sys.path.append(os.path.join(os.getcwd(), "services/policy_registry"))
    from app.services.crypto_service import CryptoService
except ImportError:
    # Fallback mock if not available
    class CryptoService:  # type: ignore
        """Mock CryptoService for testing."""

        @staticmethod
        def sign_policy_content(content: Dict[str, Any], private_key: str) -> str:
            """Mock signing."""
            return "mock_sig_" + base64.b64encode(os.urandom(32)).decode()

        @staticmethod
        def generate_keypair():
            """Mock keypair."""
            return "mock_pub", "mock_priv"


logger = logging.getLogger(__name__)
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class PolicyBundleManager:
    """Manages OPA policy bundles with OCI-like distribution patterns."""

    def __init__(self, storage_path: str = "runtime/policy_bundles"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def create_bundle(self, source_dir: str, bundle_name: str, version: str) -> str:
        """
        Create a .tar.gz bundle from source directory.

        Args:
            source_dir: Directory containing .rego and data.json files
            bundle_name: Name of the bundle
            version: Version string

        Returns:
            Path to the created bundle
        """
        bundle_filename = f"{bundle_name}-{version}.tar.gz"
        bundle_path = os.path.join(self.storage_path, bundle_filename)

        with tarfile.open(bundle_path, "w:gz") as tar:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.endswith(".rego") or file == "data.json":
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, source_dir)
                        tar.add(full_path, arcname=rel_path)

        logger.info(f"Created bundle: {bundle_path}")
        return bundle_path

    def sign_bundle(self, bundle_path: str, private_key_b64: str) -> Dict[str, Any]:
        """
        Sign a bundle file.

        Args:
            bundle_path: Path to the .tar.gz bundle
            private_key_b64: Base64 encoded private key

        Returns:
            Metadata containing signature and hash
        """
        with open(bundle_path, "rb") as f:
            bundle_data = f.read()
            bundle_hash = hashlib.sha256(bundle_data).hexdigest()

        metadata = {
            "bundle_name": os.path.basename(bundle_path),
            "hash": bundle_hash,
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": bundle_path.split("-")[-1].replace(".tar.gz", ""),
        }

        signature = CryptoService.sign_policy_content(metadata, private_key_b64)
        metadata["signature"] = signature

        # Save metadata
        meta_path = bundle_path + ".meta.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Signed bundle: {bundle_path}, saved to {meta_path}")
        return metadata

    def simulate_oci_push(
        self, bundle_path: str, registry_url: str = "oci://acgs-registry/policies"
    ):
        """Simulate pushing bundle to OCI registry."""
        meta_path = bundle_path + ".meta.json"
        if not os.path.exists(meta_path):
            raise FileNotFoundError("Metadata file not found. Sign first.")

        logger.info(f"Pushing {bundle_path} to {registry_url}...")
        # In a real implementation, this would use 'oras' or OCI API
        logger.info("Push successful (simulated)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = PolicyBundleManager()

    # Example usage
    source_path = "policies/rego"
    if os.path.exists(source_path):
        # Generate a mock key for demonstration if needed
        pub, priv = CryptoService.generate_keypair()

        bundle_file = manager.create_bundle(source_path, "acgs-governance", "v1.0.0")
        meta_data = manager.sign_bundle(bundle_file, priv)
        manager.simulate_oci_push(bundle_file)
    else:
        logging.info(f"Source directory {source_path} not found.")
