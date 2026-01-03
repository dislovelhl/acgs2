"""
ACGS-2 VaultCryptoService - Usage Examples
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive examples demonstrating VaultCryptoService capabilities including:
- Key generation with different algorithms
- Signing and verification
- Encryption and decryption
- Key rotation
- Policy signature integration
- Audit logging
- Health monitoring

Requirements:
- HashiCorp Vault or OpenBao server (optional - fallback mode available)
- Python 3.11+
- Required packages: cryptography, httpx (optional), hvac (optional)
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# Configure logging for examples
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Add parent directories to path
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.services.vault_crypto_service import (  # noqa: E402
    CONSTITUTIONAL_HASH,
    VaultConfig,
    VaultCryptoService,
    VaultOperation,
    create_vault_crypto_service,
)

# Separator for output formatting
SEPARATOR = "=" * 60


async def example_basic_initialization():
    """Example 1: Basic service initialization with fallback mode."""
    logger.info(f"\n{SEPARATOR}")
    logger.info("Example 1: Basic Initialization")
    logger.info(SEPARATOR)

    # Create service with fallback enabled (works without Vault)
    service = VaultCryptoService(fallback_enabled=True)

    # Initialize the service
    result = await service.initialize()

    logger.info(f"Initialization successful: {result['success']}")
    logger.info(f"Vault available: {result['vault_available']}")
    logger.info(f"Fallback available: {result['fallback_available']}")
    logger.info(f"Constitutional hash: {result['constitutional_hash']}")

    # Check health
    health = await service.health_check()
    logger.info(f"Service health: {health['service']}")
    logger.info(f"Constitutional valid: {health['constitutional_valid']}")


async def example_key_generation():
    """Example 2: Key generation with different algorithms."""
    logger.info(f"\n{SEPARATOR}")
    logger.info("Example 2: Key Generation")
    logger.info(SEPARATOR)

    async with VaultCryptoService(fallback_enabled=True) as service:
        # Generate Ed25519 key (default)
        ed_result = await service.generate_keypair(
            key_name="example-ed25519",
            key_type="ed25519",
        )
        logger.info("\nEd25519 Key:")
        logger.info(f"  Success: {ed_result['success']}")
        logger.info(f"  Key name: {ed_result['key_name']}")
        logger.info(f"  Vault path: {ed_result['vault_path']}")
        logger.info(f"  Public key (truncated): {ed_result['public_key'][:32]}...")

        # Generate ECDSA-P256 key
        ecdsa_result = await service.generate_keypair(
            key_name="example-ecdsa",
            key_type="ecdsa-p256",
        )
        logger.info("\nECDSA-P256 Key:")
        logger.info(f"  Success: {ecdsa_result['success']}")
        logger.info(f"  Key name: {ecdsa_result['key_name']}")

        # Generate RSA-2048 key
        rsa_result = await service.generate_keypair(
            key_name="example-rsa",
            key_type="rsa-2048",
        )
        logger.info("\nRSA-2048 Key:")
        logger.info(f"  Success: {rsa_result['success']}")
        logger.info(f"  Key name: {rsa_result['key_name']}")


async def example_signing_verification():
    """Example 3: Signing and verification operations."""
    logger.info(f"\n{SEPARATOR}")
    logger.info("Example 3: Signing and Verification")
    logger.info(SEPARATOR)

    async with VaultCryptoService(fallback_enabled=True) as service:
        # Generate a signing key
        await service.generate_keypair(key_name="signing-key", key_type="ed25519")

        # Data to sign
        original_data = b"This is important constitutional governance data"
        logger.info(f"\nOriginal data: {original_data.decode()}")

        # Sign the data
        signature = await service.sign(key_name="signing-key", data=original_data)
        logger.info(f"Signature (truncated): {signature[:40]}...")

        # Verify the signature
        is_valid = await service.verify(
            key_name="signing-key",
            data=original_data,
            signature=signature,
        )
        logger.info(f"Signature valid: {is_valid}")

        # Try with tampered data
        tampered_data = b"This data has been tampered with!"
        is_tampered_valid = await service.verify(
            key_name="signing-key",
            data=tampered_data,
            signature=signature,
        )
        logger.info(f"Tampered data valid: {is_tampered_valid} (should be False)")


async def example_encryption_decryption():
    """Example 4: Encryption and decryption operations."""
    logger.info(f"\n{SEPARATOR}")
    logger.info("Example 4: Encryption and Decryption")
    logger.info(SEPARATOR)

    async with VaultCryptoService(fallback_enabled=True) as service:
        # Secret data
        secret_data = b"Constitutional governance secrets - TOP SECRET"
        logger.info(f"\nOriginal plaintext: {secret_data.decode()}")

        # Encrypt the data
        ciphertext = await service.encrypt(
            key_name="encryption-key",
            plaintext=secret_data,
        )
        logger.info(f"Ciphertext: {ciphertext[:50]}...")

        # Decrypt the data
        decrypted = await service.decrypt(
            key_name="encryption-key",
            ciphertext=ciphertext,
        )
        logger.info(f"Decrypted: {decrypted.decode()}")
        logger.info(f"Match: {decrypted == secret_data}")


async def example_key_rotation():
    """Example 5: Key rotation operations."""
    logger.info(f"\n{SEPARATOR}")
    logger.info("Example 5: Key Rotation")
    logger.info(SEPARATOR)

    async with VaultCryptoService(fallback_enabled=True) as service:
        # Generate initial key
        await service.generate_keypair(key_name="rotate-key")
        original_public_key = await service.get_public_key(key_name="rotate-key")
        logger.info(f"\nOriginal public key: {original_public_key[:32]}...")

        # Rotate the key
        rotate_result = await service.rotate_key(key_name="rotate-key")
        logger.info(f"Rotation success: {rotate_result['success']}")

        # Get new public key
        new_public_key = await service.get_public_key(key_name="rotate-key")
        logger.info(f"New public key: {new_public_key[:32]}...")
        logger.info(f"Keys different: {original_public_key != new_public_key}")


async def example_policy_signature():
    """Example 6: Policy signature creation and verification."""
    logger.info(f"\n{SEPARATOR}")
    logger.info("Example 6: Policy Signature")
    logger.info(SEPARATOR)

    async with VaultCryptoService(fallback_enabled=True) as service:
        # Generate a policy signing key
        await service.generate_keypair(key_name="policy-signing-key")

        # Define a policy
        policy_content = {
            "policy_id": "constitutional-policy-001",
            "name": "Data Access Governance Policy",
            "version": "1.0.0",
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "rules": [
                {
                    "id": "rule-1",
                    "description": "Allow read access to governance documents",
                    "action": "allow",
                    "resource": "governance/*",
                },
                {
                    "id": "rule-2",
                    "description": "Deny access to classified data without clearance",
                    "action": "deny",
                    "resource": "classified/*",
                    "unless": {"clearance_level": ">=3"},
                },
            ],
            "effective_date": "2025-01-15",
            "expires_at": "2026-01-15",
        }

        logger.info(f"\nPolicy: {policy_content['name']}")
        logger.info(f"Version: {policy_content['version']}")
        logger.info(f"Rules: {len(policy_content['rules'])}")

        # Create policy signature
        signature = await service.create_policy_signature(
            policy_id=policy_content["policy_id"],
            version=policy_content["version"],
            content=policy_content,
            key_name="policy-signing-key",
        )

        logger.info("\nSignature created:")
        logger.info(f"  Signature ID: {signature.signature_id}")
        logger.info(f"  Policy ID: {signature.policy_id}")
        logger.info(f"  Version: {signature.version}")
        logger.info(f"  Algorithm: {signature.algorithm}")
        logger.info(f"  Key fingerprint: {signature.key_fingerprint[:16]}...")

        # Verify the signature
        is_valid = await service.verify_policy_signature(
            content=policy_content,
            signature=signature,
            key_name="policy-signing-key",
        )
        logger.info(f"Signature valid: {is_valid}")

        # Try with tampered content
        tampered_policy = policy_content.copy()
        tampered_policy["name"] = "Malicious Policy"

        is_tampered_valid = await service.verify_policy_signature(
            content=tampered_policy,
            signature=signature,
            key_name="policy-signing-key",
        )
        logger.info(f"Tampered policy valid: {is_tampered_valid} (should be False)")


async def example_audit_logging():
    """Example 7: Audit logging and monitoring."""
    logger.info(f"\n{SEPARATOR}")
    logger.info("Example 7: Audit Logging")
    logger.info(SEPARATOR)

    service = VaultCryptoService(fallback_enabled=True, audit_enabled=True)
    await service.initialize()

    # Perform various operations
    await service.generate_keypair(key_name="audit-key-1")
    await service.generate_keypair(key_name="audit-key-2")
    await service.get_public_key(key_name="audit-key-1")

    test_data = b"Audit test data"
    await service.sign(key_name="audit-key-1", data=test_data)

    # Get audit log
    audit_log = service.get_audit_log()
    logger.info(f"\nTotal audit entries: {len(audit_log)}")

    logger.info("\nRecent operations:")
    for entry in audit_log[-5:]:
        logger.info(
            f"  - {entry['operation']}: key={entry['key_name']}, success={entry['success']}"
        )

    # Filter by operation type
    key_gen_entries = service.get_audit_log(operation=VaultOperation.GENERATE_KEY)
    logger.info(f"\nKey generation operations: {len(key_gen_entries)}")

    # Filter by key name
    key1_entries = service.get_audit_log(key_name="audit-key-1")
    logger.info(f"Operations on audit-key-1: {len(key1_entries)}")

    # Clear audit log
    cleared = service.clear_audit_log()
    logger.info(f"\nCleared {cleared} audit entries")


async def example_caching():
    """Example 8: Public key caching for performance."""
    logger.info(f"\n{SEPARATOR}")
    logger.info("Example 8: Caching")
    logger.info(SEPARATOR)

    import time

    service = VaultCryptoService(
        fallback_enabled=True,
        cache_ttl=60,  # 1 minute cache
    )
    await service.initialize()

    # Generate a key
    await service.generate_keypair(key_name="cached-key")

    # First access (cache miss)
    start = time.perf_counter()
    pk1 = await service.get_public_key(key_name="cached-key")
    time1 = (time.perf_counter() - start) * 1000

    # Second access (cache hit)
    start = time.perf_counter()
    pk2 = await service.get_public_key(key_name="cached-key")
    time2 = (time.perf_counter() - start) * 1000

    logger.info(f"\nFirst access (cache miss): {time1:.3f}ms")
    logger.info(f"Second access (cache hit): {time2:.3f}ms")
    logger.info(f"Keys match: {pk1 == pk2}")

    # Check cache status
    health = await service.health_check()
    logger.info(f"Cache entries: {health['cache_entries']}")


async def example_with_vault_server():
    """Example 9: Using with actual Vault server."""
    logger.info(f"\n{SEPARATOR}")
    logger.info("Example 9: Vault Server Integration")
    logger.info(SEPARATOR)

    # Check for Vault configuration
    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")

    if not vault_addr or not vault_token:
        logger.info("\nVault not configured. Set VAULT_ADDR and VAULT_TOKEN to test.")
        logger.info("Example: export VAULT_ADDR=http://127.0.0.1:8200")
        logger.info("         export VAULT_TOKEN=hvs.your-token")
        logger.info("\nSkipping Vault server example...")
        return

    logger.info(f"\nConnecting to Vault at: {vault_addr}")

    config = VaultConfig(
        address=vault_addr,
        token=vault_token,
        transit_mount="transit",
        kv_mount="secret",
    )

    service = VaultCryptoService(config=config, fallback_enabled=False)

    try:
        result = await service.initialize()

        if result["vault_available"]:
            logger.info("Successfully connected to Vault!")

            # Check Vault health
            health = await service.health_check()
            if "vault_health" in health:
                vault_health = health["vault_health"]
                logger.info(f"Vault version: {vault_health.get('version', 'unknown')}")
                logger.info(f"Vault sealed: {vault_health.get('sealed', 'unknown')}")

            # Generate a key in Vault
            import uuid

            key_name = f"example-{uuid.uuid4().hex[:8]}"
            key_result = await service.generate_keypair(key_name=key_name)

            if key_result["success"]:
                logger.info(f"\nCreated key in Vault: {key_name}")
                logger.info(f"Vault path: {key_result['vault_path']}")

                # Sign some data
                test_data = b"Data signed with Vault Transit"
                signature = await service.sign(key_name=key_name, data=test_data)
                logger.info("Signed data with Vault Transit")

                # Verify the signature
                is_valid = await service.verify(
                    key_name=key_name,
                    data=test_data,
                    signature=signature,
                )
                logger.info(f"Signature verified: {is_valid}")
        else:
            logger.info("Could not connect to Vault")
            logger.info(f"Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.info(f"Error connecting to Vault: {e}")


async def example_context_manager():
    """Example 10: Using async context manager."""
    logger.info(f"\n{SEPARATOR}")
    logger.info("Example 10: Context Manager")
    logger.info(SEPARATOR)

    # Using async context manager for automatic cleanup
    async with VaultCryptoService(fallback_enabled=True) as service:
        logger.info("\nService initialized via context manager")

        result = await service.generate_keypair(key_name="context-key")
        logger.info(f"Key generated: {result['success']}")

        health = await service.health_check()
        logger.info(f"Service healthy: {health['constitutional_valid']}")

    logger.info("Service automatically cleaned up")


async def example_helper_function():
    """Example 11: Using helper function for quick setup."""
    logger.info(f"\n{SEPARATOR}")
    logger.info("Example 11: Helper Function")
    logger.info(SEPARATOR)

    # Quick initialization with helper function
    service = await create_vault_crypto_service(
        fallback_enabled=True,
    )

    logger.info("\nService created with helper function")
    logger.info(f"Initialized: {service._initialized}")
    logger.info(f"Vault available: {service._vault_available}")

    # Use the service
    await service.generate_keypair(key_name="helper-key")
    pk = await service.get_public_key(key_name="helper-key")
    logger.info(f"Generated key with public: {pk[:32]}...")


async def example_error_handling():
    """Example 12: Error handling patterns."""
    logger.info(f"\n{SEPARATOR}")
    logger.info("Example 12: Error Handling")
    logger.info(SEPARATOR)

    async with VaultCryptoService(fallback_enabled=True) as service:
        # Try to get non-existent key
        logger.info("\nAttempting to get non-existent key...")
        try:
            await service.get_public_key(key_name="does-not-exist")
        except RuntimeError as e:
            logger.info(f"Caught expected error: {e}")

        # Generate a key for testing
        await service.generate_keypair(key_name="error-test-key")

        # Try to verify with invalid signature
        logger.info("\nAttempting to verify with invalid signature...")
        is_valid = await service.verify(
            key_name="error-test-key",
            data=b"test data",
            signature="not-a-valid-signature",
        )
        logger.info(f"Invalid signature result: {is_valid} (expected False)")

        # Key generation with Vault unavailable and fallback disabled
        logger.info("\nAttempting operation with disabled fallback...")
        no_fallback_service = VaultCryptoService(fallback_enabled=False)
        await no_fallback_service.initialize()

        result = await no_fallback_service.generate_keypair(key_name="will-fail")
        if not result["success"]:
            logger.info(f"Expected failure: {result.get('error', 'Unknown error')}")


async def main():
    """Run all examples."""
    logger.info(SEPARATOR)
    logger.info("ACGS-2 VaultCryptoService Examples")
    logger.info(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info(SEPARATOR)

    examples = [
        example_basic_initialization,
        example_key_generation,
        example_signing_verification,
        example_encryption_decryption,
        example_key_rotation,
        example_policy_signature,
        example_audit_logging,
        example_caching,
        example_with_vault_server,
        example_context_manager,
        example_helper_function,
        example_error_handling,
    ]

    for example in examples:
        try:
            await example()
        except Exception as e:
            logger.info(f"\nError in {example.__name__}: {e}")
            import traceback

            traceback.print_exc()

    logger.info(f"\n{SEPARATOR}")
    logger.info("All examples completed!")
    logger.info(SEPARATOR)


if __name__ == "__main__":
    asyncio.run(main())
