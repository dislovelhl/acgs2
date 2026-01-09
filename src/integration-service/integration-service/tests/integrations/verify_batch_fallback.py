#!/usr/bin/env python3
"""
Verification script for Jira and ServiceNow batch processing fallback behavior.

This script verifies that adapters without native batch support (Jira and ServiceNow)
correctly inherit and use the default batch implementation from BaseIntegration,
which sends events one-by-one.

Run this script to manually verify the batch fallback behavior.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add integration-service/src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pydantic import SecretStr

from integrations import (
    EventSeverity,
    IntegrationEvent,
    JiraAdapter,
    JiraCredentials,
    ServiceNowAdapter,
    ServiceNowCredentials,
)


def create_test_events(count: int = 3) -> list[IntegrationEvent]:
    """Create test events for batch processing"""
    events = []
    for i in range(count):
        event = IntegrationEvent(
            event_id=f"test-event-{i + 1}",
            event_type="policy_violation",
            severity=EventSeverity.MEDIUM,
            title=f"Test Event {i + 1}",
            description=f"This is test event {i + 1} for batch processing verification",
            source="verification_script",
            timestamp=datetime.now(timezone.utc),
        )
        events.append(event)
    return events


async def verify_jira_batch_fallback():
    """Verify Jira adapter uses default batch fallback"""
    print("\n" + "=" * 70)
    print("VERIFYING JIRA ADAPTER BATCH FALLBACK")
    print("=" * 70)

    # Create Jira adapter (with dummy credentials - we won't authenticate)
    credentials = JiraCredentials(
        integration_name="Test Jira",
        base_url="https://test.atlassian.net",
        username="test@example.com",
        api_token=SecretStr("dummy-token"),
        project_key="TEST",
    )
    adapter = JiraAdapter(credentials)

    # Check that send_events_batch method exists
    print("\n1. Checking JiraAdapter has send_events_batch method...")
    assert hasattr(adapter, "send_events_batch"), "JiraAdapter missing send_events_batch"
    print("   ✓ send_events_batch method exists")

    # Check that _do_send_events_batch is not overridden
    print("\n2. Checking JiraAdapter uses default _do_send_events_batch...")
    from integrations.base import BaseIntegration

    jira_batch_method = adapter._do_send_events_batch
    base_batch_method = BaseIntegration._do_send_events_batch

    # Check if the method is from BaseIntegration
    if jira_batch_method.__func__ is base_batch_method:
        print("   ✓ JiraAdapter uses BaseIntegration._do_send_events_batch (default)")
    else:
        print("   ✗ JiraAdapter has overridden _do_send_events_batch")
        return False

    # Check that _do_send_event IS implemented
    print("\n3. Checking JiraAdapter has _do_send_event implementation...")
    assert hasattr(adapter, "_do_send_event"), "JiraAdapter missing _do_send_event"
    print("   ✓ _do_send_event method exists")

    print("\n✓ JIRA ADAPTER VERIFICATION PASSED")
    print("  - Inherits send_events_batch() from BaseIntegration")
    print("  - Uses default batch implementation (sends one-by-one)")
    print("  - Implements _do_send_event() for individual event sending")

    await adapter.close()
    return True


async def verify_servicenow_batch_fallback():
    """Verify ServiceNow adapter uses default batch fallback"""
    print("\n" + "=" * 70)
    print("VERIFYING SERVICENOW ADAPTER BATCH FALLBACK")
    print("=" * 70)

    # Create ServiceNow adapter (with dummy credentials - we won't authenticate)
    credentials = ServiceNowCredentials(
        integration_name="Test ServiceNow",
        instance="test-instance",
        username="test_user",
        password=SecretStr("dummy-password"),
    )
    adapter = ServiceNowAdapter(credentials)

    # Check that send_events_batch method exists
    print("\n1. Checking ServiceNowAdapter has send_events_batch method...")
    assert hasattr(adapter, "send_events_batch"), "ServiceNowAdapter missing send_events_batch"
    print("   ✓ send_events_batch method exists")

    # Check that _do_send_events_batch is not overridden
    print("\n2. Checking ServiceNowAdapter uses default _do_send_events_batch...")
    from integrations.base import BaseIntegration

    snow_batch_method = adapter._do_send_events_batch
    base_batch_method = BaseIntegration._do_send_events_batch

    # Check if the method is from BaseIntegration
    if snow_batch_method.__func__ is base_batch_method:
        print("   ✓ ServiceNowAdapter uses BaseIntegration._do_send_events_batch (default)")
    else:
        print("   ✗ ServiceNowAdapter has overridden _do_send_events_batch")
        return False

    # Check that _do_send_event IS implemented
    print("\n3. Checking ServiceNowAdapter has _do_send_event implementation...")
    assert hasattr(adapter, "_do_send_event"), "ServiceNowAdapter missing _do_send_event"
    print("   ✓ _do_send_event method exists")

    print("\n✓ SERVICENOW ADAPTER VERIFICATION PASSED")
    print("  - Inherits send_events_batch() from BaseIntegration")
    print("  - Uses default batch implementation (sends one-by-one)")
    print("  - Implements _do_send_event() for individual event sending")

    await adapter.close()
    return True


async def main():
    """Run all verification checks"""
    print("\n" + "=" * 70)
    print("BATCH PROCESSING FALLBACK VERIFICATION")
    print("=" * 70)
    print("\nThis script verifies that Jira and ServiceNow adapters correctly")
    print("inherit the default batch processing behavior from BaseIntegration.")
    print("\nThe default behavior sends events one-by-one when the adapter")
    print("doesn't provide a custom batch implementation.")

    results = []

    try:
        # Verify Jira adapter
        jira_result = await verify_jira_batch_fallback()
        results.append(("Jira", jira_result))

        # Verify ServiceNow adapter
        snow_result = await verify_servicenow_batch_fallback()
        results.append(("ServiceNow", snow_result))

        # Print summary
        print("\n" + "=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        for adapter_name, result in results:
            status = "✓ PASSED" if result else "✗ FAILED"
            print(f"{adapter_name:20s} {status}")

        all_passed = all(result for _, result in results)
        if all_passed:
            print("\n✓ ALL VERIFICATIONS PASSED")
            print("\nBoth Jira and ServiceNow adapters are correctly configured to use")
            print("the default batch processing behavior, which sends events one-by-one.")
            return 0
        else:
            print("\n✗ SOME VERIFICATIONS FAILED")
            return 1

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
