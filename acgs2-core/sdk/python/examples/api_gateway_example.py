#!/usr/bin/env python3
"""
ACGS-2 Python SDK - API Gateway Example
Constitutional Hash: cdd01ef066bc6cf2

This example demonstrates how to use the API Gateway service
for health checks, feedback submission, and service discovery.
"""

import asyncio

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
        print("🌐 ACGS-2 API Gateway Example")
        print("=" * 50)

        # Get API Gateway service
        gateway_service = client.api_gateway

        try:
            # 1. Health Check
            print("\n1. Health Check")
            health = await gateway_service.health_check()
            print(f"   Status: {health.healthy}")
            if health.healthy:
                print(f"   Version: {health.version}")
                print(f"   Constitutional Hash: {health.constitutional_hash}")
            else:
                print("   Service is currently unhealthy")

            # 2. Submit Feedback
            print("\n2. Submit Feedback")
            feedback = await gateway_service.submit_feedback(
                user_id="example-user-123",
                category="feature",
                rating=5,
                title="Excellent SDK Experience",
                description="The new SDK makes integration much easier with comprehensive type safety and retry logic.",
                metadata={
                    "sdk_version": "2.0.0",
                    "language": "python",
                    "use_case": "policy_management",
                },
            )
            print(f"   Feedback submitted with ID: {feedback.id}")
            print(f"   Status: {feedback.status}")

            # 3. Get Feedback Statistics
            print("\n3. Get Feedback Statistics")
            stats = await gateway_service.get_feedback_stats()
            print(f"   Total feedback: {stats.total_feedback}")
            print(f"   Average rating: {stats.average_rating:.1f}/5.0")

            if stats.category_breakdown:
                print("   Category breakdown:")
                for category, count in stats.category_breakdown.items():
                    print(f"     {category}: {count}")

            if stats.recent_feedback:
                print("   Recent feedback:")
                for fb in stats.recent_feedback[:3]:  # Show first 3
                    print(f"     {fb.rating}⭐ '{fb.title}' by {fb.user_id}")

            # 4. List Available Services
            print("\n4. Service Discovery")
            services_response = await gateway_service.list_services()

            print(f"   Gateway Version: {services_response.gateway.version}")
            print(f"   Uptime: {services_response.gateway.uptime} seconds")
            print(f"   Active Connections: {services_response.gateway.active_connections}")

            print(f"\n   Available Services ({len(services_response.services)}):")
            for service in services_response.services:
                status_icon = (
                    "✅"
                    if service.status == "healthy"
                    else "⚠️" if service.status == "degraded" else "❌"
                )
                print(f"     {status_icon} {service.name}")
                print(f"         Status: {service.status}")
                print(f"         Version: {service.version}")
                if service.description:
                    print(f"         Description: {service.description}")
                if service.endpoints:
                    print(
                        f"         Endpoints: {', '.join(service.endpoints[:3])}{'...' if len(service.endpoints) > 3 else ''}"
                    )

            print("\n✅ API Gateway example completed successfully!")

        except Exception as e:
            print(f"\n❌ Example failed: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
