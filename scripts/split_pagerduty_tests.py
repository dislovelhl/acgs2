#!/usr/bin/env python3
"""
Script to split the large test_pagerduty.py file into smaller, focused test modules.
"""

import re
from pathlib import Path


def split_pagerduty_tests():
    """Split the large test file into smaller modules."""

    source_file = Path(
        "src/integration-service/integration-service/tests/integrations/test_pagerduty.py"
    )
    target_dir = Path("src/integration-service/integration-service/tests/integrations/pagerduty")

    target_dir.mkdir(exist_ok=True)

    with open(source_file, "r") as f:
        content = f.read()

    # Find the end of the header (imports and fixtures) before the first class
    header_end_pattern = r"(.*?)(\n\nclass Test)"
    header_match = re.match(header_end_pattern, content, re.DOTALL)

    if not header_match:
        print("Could not find header end pattern")
        return

    header_content = header_match.group(1)

    # Process each class
    class_mapping = {
        "TestPagerDutyValidation": "test_validation.py",
        "TestPagerDutyConnectionTesting": "test_connection_testing.py",
        "TestPagerDutyIncidentCreation": "test_incident_creation.py",
        "TestPagerDutyIncidentPayload": "test_incident_payload.py",
        "TestPagerDutySeverityMapping": "test_severity_mapping.py",
        "TestPagerDutyIncidentLifecycle": "test_incident_lifecycle.py",
        "TestPagerDutyEventScenarios": "test_event_scenarios.py",
        "TestPagerDutyTicketMapping": "test_ticket_mapping.py",
    }

    for class_name, filename in class_mapping.items():
        # Find the class content
        class_pattern = rf"(class\s+{class_name}.*?)(?=\nclass\s+Test|\n# =+|\Z)"
        class_match = re.search(class_pattern, content, re.DOTALL)

        if class_match:
            class_content = class_match.group(1)

            # Create the file content
            file_content = f'''"""
Tests for PagerDuty {class_name.replace('TestPagerDuty', '').lower()}.

Tests cover:
- {class_name.replace('TestPagerDuty', '').lower()} functionality
- Error handling and edge cases
- Integration with PagerDuty APIs
"""

{header_content.strip()}

{class_content.strip()}
'''

            target_file = target_dir / filename
            with open(target_file, "w") as f:
                f.write(file_content)

            print(f"Created {target_file}")

    print("Test file splitting completed!")


if __name__ == "__main__":
    split_pagerduty_tests()
