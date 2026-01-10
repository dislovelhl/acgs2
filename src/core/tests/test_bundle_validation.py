import json
import unittest
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric import ed25519
from src.core.enhanced_agent_bus.bundle_registry import (
    CONSTITUTIONAL_HASH,
    BundleManifest,
)


class TestBundleVerification(unittest.TestCase):
    def setUp(self):
        # Create a valid manifest first
        self.manifest_data = {
            "version": "1.0.0",
            "revision": "a1b2c3d",
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "roots": ["acgs/governance"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signatures": [],
            "metadata": {},
        }
        self.manifest = BundleManifest(**self.manifest_data)

    def test_manifest_validation(self):
        # Valid manifest should not raise
        self.manifest.validate()

        # Invalid hash should be caught in __post_init__
        with self.assertRaises(ValueError):
            BundleManifest(
                version="1.0.0", revision="abc", constitutional_hash="WRONG_HASH", roots=["root"]
            )

        # Missing required field in validate (jsonschema)
        invalid_data = self.manifest_data.copy()
        del invalid_data["version"]
        # We need to bypass __post_init__ validation or use a raw dict to test jsonschema directly
        # BundleManifest(**invalid_data) would fail on missing arg, so we test schema via dict
        if self.manifest._schema:
            import jsonschema

            with self.assertRaises(jsonschema.exceptions.ValidationError):
                jsonschema.validate(instance=invalid_data, schema=self.manifest._schema)

    def test_signature_verification(self):
        # Generate keys
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        public_key_hex = public_key.public_bytes_raw().hex()

        # Sign manifest
        # Note: sign method in bundle_registry.py isn't implemented to take a private key object,
        # but the class has a structure. Let's mock a signature.

        manifest_dict = self.manifest.to_dict()
        if "signatures" in manifest_dict:
            del manifest_dict["signatures"]
        content = json.dumps(manifest_dict, sort_keys=True).encode()
        signature = private_key.sign(content)

        self.manifest.add_signature(
            keyid="test-key", signature=signature.hex(), algorithm="ed25519"
        )

        # Verify
        self.assertTrue(self.manifest.verify_signature(public_key_hex))

        # Verify with wrong key
        wrong_private = ed25519.Ed25519PrivateKey.generate()
        wrong_public_hex = wrong_private.public_key().public_bytes_raw().hex()
        self.assertFalse(self.manifest.verify_signature(wrong_public_hex))


if __name__ == "__main__":
    unittest.main()
