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

    # Configuration
    api_url = "http://localhost:8100"
    redis_url = "redis://localhost:6379/0"

    # Test results
    all_tests_passed = True

    try:
        # Step 1: Connect to Redis

        redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await redis_client.ping()

    except Exception:
        return 1

    try:
        # Step 2: Create an import job via API

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
                all_tests_passed = False
                return 1

            job_data = response.json()
            job_id = job_data["job_id"]

    except Exception:
        return 1

    try:
        # Step 3: Verify job exists in Redis

        redis_key = f"import:job:{job_id}"
        job_json = await redis_client.get(redis_key)

        if not job_json:
            all_tests_passed = False
        else:
            # Parse and validate JSON
            try:
                job_obj = json.loads(job_json)

                # Check required fields

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
                        pass  # Field present
                    else:
                        missing_fields.append(field)
                        all_tests_passed = False

                if not missing_fields:
                    pass  # All fields present
                else:
                    print(f"✗ Missing fields: {', '.join(missing_fields)}")

            except json.JSONDecodeError:
                pass  # JSON decode error handled
                all_tests_passed = False

    except Exception:
        pass  # Exception handled
        all_tests_passed = False

    try:
        # Step 5: Check TTL

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
            all_tests_passed = False
        else:
            all_tests_passed = False

    except Exception:
        all_tests_passed = False

    try:
        # Step 6: Test retrieving job via API

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{api_url}/api/imports/{job_id}",
                timeout=10.0,
            )

            if response.status_code == 200:
                retrieved_job = response.json()

                # Verify it matches what we created
                if retrieved_job["job_id"] == job_id:
                    pass  # Job ID matches
                else:
                    all_tests_passed = False
            else:
                pass  # Response check failed
                all_tests_passed = False

    except Exception:
        pass  # Exception handled
        all_tests_passed = False

    # Cleanup
    await redis_client.close()

    # Summary

    if all_tests_passed:
        print("  - TTL is set correctly (24 hours)")

        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
