"""
Unit tests for CSV export functionality in ComplianceReportGenerator.

Tests the generate_csv_export() method including:
- Basic CSV generation with sample data
- CSV format validation (headers, columns, quoting)
- Tenant filtering
- Edge cases (empty data, special characters)
- Bytes export for attachments
"""

import csv
import io
import os
import sys
from datetime import datetime, timezone

import pytest  # noqa: F401 - used for test infrastructure

# Add the service path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.report_generator import ComplianceReportGenerator  # noqa: E402


# Sample test data
def create_sample_logs(tenant_id: str, count: int = 5):
    """Create sample decision logs for testing."""
    logs = []
    for i in range(count):
        logs.append(
            {
                "tenant_id": tenant_id,
                "agent_id": f"agent-{i:03d}",
                "decision": "ALLOW" if i % 3 != 0 else "DENY",
                "risk_score": 0.2 + (i * 0.15),
                "compliance_tags": ["POLICY", "PRIVACY"] if i % 2 == 0 else ["SAFETY"],
                "policy_version": "v1.0.0",
                "trace_id": f"trace-{i:06d}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    return logs


class TestCSVExportMethodExists:
    """Test CSV export method availability."""

    def test_generate_csv_export_method_exists(self):
        """Verify generate_csv_export method exists on the class."""
        assert hasattr(ComplianceReportGenerator, "generate_csv_export")
        assert callable(ComplianceReportGenerator.generate_csv_export)

    def test_generate_csv_bytes_method_exists(self):
        """Verify generate_csv_bytes method exists on the class."""
        assert hasattr(ComplianceReportGenerator, "generate_csv_bytes")
        assert callable(ComplianceReportGenerator.generate_csv_bytes)

    def test_generate_csv_export_signature(self):
        """Verify the method signature accepts required parameters."""
        import inspect

        sig = inspect.signature(ComplianceReportGenerator.generate_csv_export)
        params = list(sig.parameters.keys())

        # Required parameters
        assert "logs" in params
        assert "tenant_id" in params

        # Optional parameters with defaults
        assert "include_headers" in params


class TestCSVExportBasicFunctionality:
    """Test basic CSV export functionality."""

    def test_generate_csv_export_returns_string(self):
        """Verify CSV generation returns a string."""
        logs = create_sample_logs("tenant-001", count=3)
        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-001",
        )

        assert isinstance(csv_content, str)
        assert len(csv_content) > 0

    def test_generate_csv_export_has_headers(self):
        """Verify CSV has proper headers."""
        logs = create_sample_logs("tenant-002", count=2)
        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-002",
        )

        # Parse the CSV
        reader = csv.reader(io.StringIO(csv_content))
        headers = next(reader)

        expected_headers = [
            "timestamp",
            "agent_id",
            "decision",
            "risk_score",
            "compliance_tags",
            "policy_version",
            "trace_id",
        ]
        assert headers == expected_headers

    def test_generate_csv_export_correct_row_count(self):
        """Verify CSV has correct number of rows."""
        num_logs = 5
        logs = create_sample_logs("tenant-003", count=num_logs)
        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-003",
        )

        # Parse the CSV
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        # Should have header + data rows
        assert len(rows) == num_logs + 1

    def test_generate_csv_export_without_headers(self):
        """Test CSV generation without headers."""
        logs = create_sample_logs("tenant-004", count=3)
        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-004",
            include_headers=False,
        )

        # Parse the CSV
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        # Should have only data rows (no header)
        assert len(rows) == 3

        # First row should be data, not headers
        # Check that first column is a timestamp-like string, not "timestamp"
        assert rows[0][0] != "timestamp"


class TestCSVExportDataIntegrity:
    """Test data integrity in CSV export."""

    def test_csv_contains_correct_agent_ids(self):
        """Verify CSV contains correct agent IDs."""
        logs = create_sample_logs("tenant-005", count=3)
        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-005",
        )

        # Parse the CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        agent_ids = [row["agent_id"] for row in reader]

        assert "agent-000" in agent_ids
        assert "agent-001" in agent_ids
        assert "agent-002" in agent_ids

    def test_csv_contains_correct_decisions(self):
        """Verify CSV contains correct decision values."""
        logs = create_sample_logs("tenant-006", count=4)
        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-006",
        )

        # Parse the CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        decisions = [row["decision"] for row in reader]

        # Based on create_sample_logs: DENY for i=0,3 and ALLOW for i=1,2
        assert "ALLOW" in decisions
        assert "DENY" in decisions

    def test_csv_risk_score_formatted(self):
        """Verify risk scores are properly formatted."""
        logs = [
            {
                "tenant_id": "tenant-007",
                "agent_id": "agent-001",
                "decision": "ALLOW",
                "risk_score": 0.12345,
                "compliance_tags": [],
                "policy_version": "v1.0.0",
                "trace_id": "trace-001",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]

        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-007",
        )

        # Parse the CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)

        # Risk score should be formatted to 4 decimal places
        assert row["risk_score"] == "0.1235"

    def test_csv_compliance_tags_semicolon_separated(self):
        """Verify compliance tags are semicolon-separated."""
        logs = [
            {
                "tenant_id": "tenant-008",
                "agent_id": "agent-001",
                "decision": "ALLOW",
                "risk_score": 0.5,
                "compliance_tags": ["POLICY", "PRIVACY", "SAFETY"],
                "policy_version": "v1.0.0",
                "trace_id": "trace-001",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]

        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-008",
        )

        # Parse the CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)

        assert row["compliance_tags"] == "POLICY;PRIVACY;SAFETY"


class TestCSVExportTenantFiltering:
    """Test tenant filtering in CSV export."""

    def test_logs_filtered_by_tenant(self):
        """Test that logs from different tenants are properly filtered."""
        logs = [
            {
                "tenant_id": "tenant-009",
                "agent_id": "agent-001",
                "decision": "ALLOW",
                "risk_score": 0.5,
                "compliance_tags": [],
                "policy_version": "v1.0.0",
                "trace_id": "trace-001",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "tenant_id": "other-tenant",
                "agent_id": "agent-002",
                "decision": "DENY",
                "risk_score": 0.8,
                "compliance_tags": [],
                "policy_version": "v1.0.0",
                "trace_id": "trace-002",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "tenant_id": "tenant-009",
                "agent_id": "agent-003",
                "decision": "ALLOW",
                "risk_score": 0.3,
                "compliance_tags": [],
                "policy_version": "v1.0.0",
                "trace_id": "trace-003",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-009",
        )

        # Parse the CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        # Should only have 2 rows (from tenant-009)
        assert len(rows) == 2

        # Verify all rows are from tenant-009
        agent_ids = [row["agent_id"] for row in rows]
        assert "agent-001" in agent_ids
        assert "agent-003" in agent_ids
        assert "agent-002" not in agent_ids


class TestCSVExportEdgeCases:
    """Test edge cases for CSV export."""

    def test_empty_logs_generates_csv(self):
        """Test CSV generation with empty logs."""
        logs = []
        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-010",
        )

        # Should have only header row
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        assert len(rows) == 1  # Just header
        assert rows[0][0] == "timestamp"

    def test_empty_logs_without_headers(self):
        """Test CSV generation with empty logs and no headers."""
        logs = []
        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-011",
            include_headers=False,
        )

        # Should be empty string
        assert csv_content == ""

    def test_logs_with_missing_fields(self):
        """Test CSV handles missing fields gracefully."""
        logs = [
            {
                "tenant_id": "tenant-012",
                "agent_id": "agent-001",
                "decision": "ALLOW",
                # Missing: risk_score, compliance_tags, policy_version, trace_id, timestamp
            }
        ]

        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-012",
        )

        # Parse the CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)

        assert row["agent_id"] == "agent-001"
        assert row["decision"] == "ALLOW"
        assert row["risk_score"] == "0.0000"  # Default value
        assert row["compliance_tags"] == ""  # Empty list formatted as empty string

    def test_logs_with_special_characters(self):
        """Test CSV handles special characters (commas, quotes) correctly."""
        logs = [
            {
                "tenant_id": "tenant-013",
                "agent_id": 'agent-with-"quotes"',
                "decision": "ALLOW",
                "risk_score": 0.5,
                "compliance_tags": ["TAG,WITH,COMMAS", "NORMAL_TAG"],
                "policy_version": "v1.0.0",
                "trace_id": "trace-001",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]

        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-013",
        )

        # Parse the CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)

        # CSV should properly escape special characters
        assert row["agent_id"] == 'agent-with-"quotes"'
        assert "TAG,WITH,COMMAS" in row["compliance_tags"]

    def test_logs_with_none_values(self):
        """Test CSV handles None values gracefully."""
        logs = [
            {
                "tenant_id": "tenant-014",
                "agent_id": "agent-001",
                "decision": "ALLOW",
                "risk_score": None,
                "compliance_tags": None,
                "policy_version": None,
                "trace_id": None,
                "timestamp": None,
            }
        ]

        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-014",
        )

        # Should not raise an error
        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)

        assert row["agent_id"] == "agent-001"
        # None values should be handled gracefully
        assert row["risk_score"] == "0.0000"


class TestCSVBytesExport:
    """Test CSV bytes export for file attachments."""

    def test_generate_csv_bytes_returns_bytes(self):
        """Verify generate_csv_bytes returns bytes."""
        logs = create_sample_logs("tenant-015", count=3)
        csv_bytes = ComplianceReportGenerator.generate_csv_bytes(
            logs=logs,
            tenant_id="tenant-015",
        )

        assert isinstance(csv_bytes, bytes)
        assert len(csv_bytes) > 0

    def test_generate_csv_bytes_utf8_encoded(self):
        """Verify bytes are UTF-8 encoded."""
        logs = create_sample_logs("tenant-016", count=2)
        csv_bytes = ComplianceReportGenerator.generate_csv_bytes(
            logs=logs,
            tenant_id="tenant-016",
        )

        # Should be decodable as UTF-8
        csv_string = csv_bytes.decode("utf-8")
        assert "timestamp" in csv_string
        assert "agent_id" in csv_string

    def test_generate_csv_bytes_matches_string_export(self):
        """Verify bytes export matches string export when decoded."""
        logs = create_sample_logs("tenant-017", count=3)

        csv_string = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-017",
        )

        csv_bytes = ComplianceReportGenerator.generate_csv_bytes(
            logs=logs,
            tenant_id="tenant-017",
        )

        assert csv_bytes.decode("utf-8") == csv_string


class TestCSVExportWithObjectLogs:
    """Test CSV export with object-style logs (simulating DecisionLog objects)."""

    def test_logs_with_to_dict_method(self):
        """Test logs that have a to_dict() method."""

        class MockLog:
            def __init__(self):
                self.tenant_id = "tenant-018"
                self.agent_id = "agent-mock"
                self.decision = "ALLOW"
                self.risk_score = 0.42

            def to_dict(self):
                return {
                    "tenant_id": self.tenant_id,
                    "agent_id": self.agent_id,
                    "decision": self.decision,
                    "risk_score": self.risk_score,
                    "compliance_tags": ["MOCK"],
                    "policy_version": "v2.0.0",
                    "trace_id": "mock-trace",
                    "timestamp": "2024-01-01T00:00:00Z",
                }

        logs = [MockLog()]
        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-018",
        )

        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)

        assert row["agent_id"] == "agent-mock"
        assert row["decision"] == "ALLOW"
        assert row["risk_score"] == "0.4200"

    def test_logs_with_dict_attribute(self):
        """Test logs that use __dict__ attribute."""

        class SimpleLog:
            def __init__(self):
                self.tenant_id = "tenant-019"
                self.agent_id = "agent-simple"
                self.decision = "DENY"
                self.risk_score = 0.75
                self.compliance_tags = ["SIMPLE"]
                self.policy_version = "v1.5.0"
                self.trace_id = "simple-trace"
                self.timestamp = "2024-01-02T00:00:00Z"

        logs = [SimpleLog()]
        csv_content = ComplianceReportGenerator.generate_csv_export(
            logs=logs,
            tenant_id="tenant-019",
        )

        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)

        assert row["agent_id"] == "agent-simple"
        assert row["decision"] == "DENY"
        assert row["risk_score"] == "0.7500"
