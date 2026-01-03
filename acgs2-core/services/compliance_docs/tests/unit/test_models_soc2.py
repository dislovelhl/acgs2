"""
Unit tests for SOC 2 compliance models
"""

import pytest
from datetime import date

from src.models.soc2 import (
    SOC2ControlMapping,
    SOC2Evidence,
    SOC2TrustServiceCriteria,
    SOC2ComplianceReport
)


class TestSOC2Models:
    """Test cases for SOC 2 data models"""

    def test_soc2_control_mapping_creation(self):
        """Test SOC 2 control mapping model creation"""
        control = SOC2ControlMapping(
            control_id="CC1.1",
            control_name="Control Environment",
            criteria=SOC2TrustServiceCriteria.SECURITY,
            description="The entity demonstrates a commitment to integrity and ethical values",
            guardrail_mapping=["intent_classifier", "pacar_verifier"],
            evidence_sources=["audit_logs", "policy_evaluations"],
            testing_frequency="Quarterly",
            last_tested=date(2024, 12, 31),
            test_results="Passed"
        )

        assert control.control_id == "CC1.1"
        assert control.control_name == "Control Environment"
        assert control.criteria == SOC2TrustServiceCriteria.SECURITY
        assert len(control.guardrail_mapping) == 2
        assert control.last_tested == date(2024, 12, 31)

    def test_soc2_evidence_validation(self):
        """Test SOC 2 evidence model validation"""
        # Valid evidence
        evidence = SOC2Evidence(
            criteria=SOC2TrustServiceCriteria.SECURITY,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 12, 31),
            controls=[]
        )

        assert evidence.criteria == SOC2TrustServiceCriteria.SECURITY
        assert evidence.period_start == date(2024, 1, 1)
        assert evidence.period_end == date(2024, 12, 31)

    def test_soc2_evidence_invalid_period(self):
        """Test SOC 2 evidence model rejects invalid date ranges"""
        with pytest.raises(ValueError, match="period_end must be after period_start"):
            SOC2Evidence(
                criteria=SOC2TrustServiceCriteria.SECURITY,
                period_start=date(2024, 12, 31),
                period_end=date(2024, 1, 1),  # End before start
                controls=[]
            )

    def test_soc2_compliance_report_creation(self):
        """Test SOC 2 compliance report model creation"""
        report = SOC2ComplianceReport(
            metadata={
                "organization_name": "ACGS-2 Platform",
                "report_period": "January 1, 2024 - December 31, 2024",
                "auditor_name": "Independent Auditor",
                "criteria_covered": [SOC2TrustServiceCriteria.SECURITY],
                "report_date": date(2024, 12, 31)
            },
            evidence=SOC2Evidence(
                criteria=SOC2TrustServiceCriteria.SECURITY,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 12, 31),
                controls=[]
            ),
            executive_summary="All SOC 2 controls are effectively implemented",
            control_effectiveness={"CC1.1": "Effective"},
            recommendations=[]
        )

        assert report.metadata["organization_name"] == "ACGS-2 Platform"
        assert report.executive_summary == "All SOC 2 controls are effectively implemented"
        assert len(report.control_effectiveness) == 1
