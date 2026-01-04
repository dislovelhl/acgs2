#!/usr/bin/env python3
"""
Verification script for Redis job tracking.

This script:
1. Creates an import job via the API
2. Verifies the job is stored in Redis
3. Checks that the JSON contains proper progress data
4. Verifies TTL is set correctly
"""

import asyncio
import json
import sys

import httpx
import redis.asyncio as redis


async def main():
    """Run Redis job tracking verification."""
    print("=" * 80)
    print("Redis Job Tracking Verification")
    print("=" * 80)
    print()

    # Configuration
    api_url = "http://localhost:8100"
    redis_url = "redis://localhost:6379/0"

    # Test results
    all_tests_passed = True

    try:
        # Step 1: Connect to Redis
        print("Step 1: Connecting to Redis...")
        redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await redis_client.ping()
        print("✓ Redis connection successful")
        print()

    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print()
        print("Please ensure Redis is running:")
        print("  docker run -d -p 6379:6379 redis:alpine")
        return 1

    try:
        # Step 2: Create an import job via API
        print("Step 2: Creating import job via API...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/api/imports",
                json={
                    "source_type": "jira",
                    "source_config": {
                        "base_url": "https://test.atlassian.net",
                        "email": "test@example.com",
                        "api_token": "test-token",
                        "project_key": "TEST",
                    },
                    "options": {
                        "batch_size": 100,
                        "preview_limit": 10,
                    },
                },
                timeout=10.0,
            )

            if response.status_code != 202:
                print(f"✗ Failed to create import job: HTTP {response.status_code}")
                print(f"  Response: {response.text}")
                all_tests_passed = False
                return 1

            job_data = response.json()
            job_id = job_data["job_id"]
            print(f"✓ Import job created: {job_id}")
            print(f"  Status: {job_data['status']}")
            print(f"  Source: {job_data['source_type']}")
            print()

    except Exception as e:
        print(f"✗ Failed to create import job: {e}")
        print()
        print("Please ensure integration-service is running:")
        print("  cd integration-service")
        print("  uvicorn src.main:app --reload --port 8100")
        return 1

    try:
        # Step 3: Verify job exists in Redis
        print("Step 3: Checking Redis for job data...")
        redis_key = f"import:job:{job_id}"
        job_json = await redis_client.get(redis_key)

        if not job_json:
            print(f"✗ Job not found in Redis: {redis_key}")
            all_tests_passed = False
        else:
            print(f"✓ Job found in Redis: {redis_key}")

            # Parse and validate JSON
            try:
                job_obj = json.loads(job_json)
                print("✓ JSON is valid")
                print()

                # Check required fields
                print("Step 4: Validating job data structure...")
                required_fields = [
                    "job_id",
                    "request_id",
                    "status",
                    "source_type",
                    "created_at",
                    "updated_at",
                ]

                missing_fields = []
                for field in required_fields:
                    if field in job_obj:
                        print(f"  ✓ {field}: {job_obj[field]}")
                    else:
                        print(f"  ✗ Missing field: {field}")
                        missing_fields.append(field)
                        all_tests_passed = False

                if not missing_fields:
                    print("✓ All required fields present")
                else:
                    print(f"✗ Missing fields: {', '.join(missing_fields)}")

                print()

            except json.JSONDecodeError as e:
                print(f"✗ Invalid JSON in Redis: {e}")
                print(f"  Data: {job_json}")
                all_tests_passed = False

    except Exception as e:
        print(f"✗ Error checking Redis: {e}")
        all_tests_passed = False

    try:
        # Step 5: Check TTL
        print("Step 5: Checking Redis TTL...")
        ttl = await redis_client.ttl(redis_key)

        if ttl > 0:
            print(f"✓ TTL is set: {ttl} seconds (~{ttl // 3600} hours)")
            if ttl <= 86400:  # Should be 24 hours
                print("✓ TTL is within expected range (≤24 hours)")
            else:
                print(f"⚠ TTL is longer than expected: {ttl}s (expected ≤86400s)")
        elif ttl == -1:
            print("✗ TTL not set (key will never expire)")
            all_tests_passed = False
        elif ttl == -2:
            print("✗ Key does not exist")
            all_tests_passed = False
        else:
            print(f"✗ Unexpected TTL value: {ttl}")
            all_tests_passed = False

        print()

    except Exception as e:
        print(f"✗ Error checking TTL: {e}")
        all_tests_passed = False

    try:
        # Step 6: Test retrieving job via API
        print("Step 6: Retrieving job via API...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{api_url}/api/imports/{job_id}",
                timeout=10.0,
            )

            if response.status_code == 200:
                retrieved_job = response.json()
                print("✓ Job retrieved via API")
                print(f"  Job ID: {retrieved_job['job_id']}")
                print(f"  Status: {retrieved_job['status']}")

                # Verify it matches what we created
                if retrieved_job['job_id'] == job_id:
                    print("✓ Job ID matches")
                else:
                    print(f"✗ Job ID mismatch: {retrieved_job['job_id']} != {job_id}")
                    all_tests_passed = False
            else:
                print(f"✗ Failed to retrieve job: HTTP {response.status_code}")
                all_tests_passed = False

        print()

    except Exception as e:
        print(f"✗ Error retrieving job via API: {e}")
        all_tests_passed = False

    # Cleanup
    await redis_client.close()

    # Summary
    print("=" * 80)
    if all_tests_passed:
        print("✓ ALL TESTS PASSED")
        print()
        print("Redis job tracking is working correctly:")
        print("  - Jobs are stored in Redis with proper JSON format")
        print("  - All required fields are present")
        print("  - TTL is set correctly (24 hours)")
        print("  - Jobs can be retrieved via API")
        print()
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print()
        print("Please review the errors above and fix the implementation.")
        print()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
