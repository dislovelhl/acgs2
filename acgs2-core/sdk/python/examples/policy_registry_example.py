#!/usr/bin/env python3
"""
ACGS-2 Python SDK - Policy Registry Example
Constitutional Hash: cdd01ef066bc6cf2

This example demonstrates how to use the Policy Registry service
to manage policies, bundles, and authentication.
"""

import asyncio
import os

from acgs2_sdk import ACGS2Config, create_client


async def main():
    # Configuration
    config = ACGS2Config(
        base_url="http://localhost:8080",  # API Gateway URL
        tenant_id="example-tenant",
        # Add authentication as needed
        # api_key="your-api-key",
        # svid_token="your-svid-token",
    )

    async with create_client(config) as client:
        print("🛡️  ACGS-2 Policy Registry Example")
        print("=" * 50)

        # Get Policy Registry service
        policy_service = client.policy_registry

        try:
            # 1. Health Check
            print("\n1. Health Check")
            health = await policy_service.health_check()
            print(f"   Status: {health}")

            # 2. List Policies
            print("\n2. List Policies")
            policies = await policy_service.list_policies(limit=5)
            print(f"   Found {len(policies)} policies")
            if policies:
                policy = policies[0]
                print(f"   Example: {policy.name} (Status: {policy.status.value})")

            # 3. Create a Policy
            print("\n3. Create Policy")
            new_policy = await policy_service.create_policy(
                name="example-security-policy",
                rules=[
                    {
                        "effect": "allow",
                        "principal": "user:*",
                        "action": "read",
                        "resource": "document:*",
                        "conditions": {
                            "ip_address": {"type": "CIDR", "value": "192.168.1.0/24"}
                        }
                    }
                ],
                description="Example security policy with IP restrictions",
                tags=["security", "example"],
                compliance_tags=["gdpr", "sox"]
            )
            print(f"   Created policy: {new_policy.name} (ID: {new_policy.id})")

            # 4. Get Policy Details
            print("\n4. Get Policy Details")
            policy_details = await policy_service.get_policy(new_policy.id)
            print(f"   Policy: {policy_details.name}")
            print(f"   Rules: {len(policy_details.rules)}")
            print(f"   Status: {policy_details.status.value}")

            # 5. Verify Policy
            print("\n5. Verify Policy")
            verification = await policy_service.verify_policy(
                new_policy.id,
                {
                    "principal": "user:alice",
                    "action": "read",
                    "resource": "document:confidential",
                    "context": {
                        "ip_address": "192.168.1.100",
                        "time": "2024-01-15T10:00:00Z"
                    }
                }
            )
            print(f"   Verification: {'ALLOWED' if verification.allowed else 'DENIED'}")

            # 6. Get Policy Versions
            print("\n6. Get Policy Versions")
            versions = await policy_service.get_policy_versions(new_policy.id)
            print(f"   Policy has {len(versions)} versions")

            # 7. Create Policy Version
            print("\n7. Create Policy Version")
            new_version = await policy_service.create_policy_version(
                new_policy.id,
                rules=[
                    {
                        "effect": "allow",
                        "principal": "user:*",
                        "action": ["read", "write"],
                        "resource": "document:*",
                        "conditions": {
                            "ip_address": {"type": "CIDR", "value": "192.168.1.0/24"},
                            "department": {"type": "StringEquals", "value": "engineering"}
                        }
                    }
                ],
                description="Enhanced policy with write permissions and department restrictions"
            )
            print(f"   Created version: {new_version.version}")

            # 8. List Policy Bundles
            print("\n8. List Policy Bundles")
            bundles = await policy_service.list_bundles()
            print(f"   Found {len(bundles)} bundles")

            # 9. Create Policy Bundle
            print("\n9. Create Policy Bundle")
            bundle = await policy_service.create_bundle(
                name="security-bundle",
                policies=[new_policy.id],
                description="Bundle containing security policies"
            )
            print(f"   Created bundle: {bundle.name} (ID: {bundle.id})")

            # 10. Get Active Bundle
            print("\n10. Get Active Bundle")
            active_bundle = await policy_service.get_active_bundle()
            print(f"   Active bundle: {active_bundle.name}")

            # 11. Authentication (if credentials provided)
            if os.getenv("ACGS2_USERNAME") and os.getenv("ACGS2_PASSWORD"):
                print("\n11. Authentication")
                auth_result = await policy_service.authenticate(
                    os.getenv("ACGS2_USERNAME"),
                    os.getenv("ACGS2_PASSWORD")
                )
                print(f"   Authenticated as: {auth_result.user.username}")
                print(f"   Roles: {', '.join(auth_result.user.roles)}")

            print("\n✅ Policy Registry example completed successfully!")

        except Exception as e:
            print(f"\n❌ Example failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
