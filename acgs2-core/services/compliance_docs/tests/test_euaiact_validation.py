"""
Unit tests for EU AI Act compliance validation
Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import date

import pytest
from src.api.euaiact_routes import ComplianceValidationRequest, _perform_compliance_validation
from src.models.euaiact import (
    ComplianceStatus,
    EUAIActComplianceChecklist,
    EUAIActComplianceFinding,
    FindingSeverity,
    HighRiskCategory,
)


@pytest.mark.asyncio
async def test_compliance_validation_basic():
    """Test basic compliance validation."""
    request = ComplianceValidationRequest(
        system_name="Test AI System",
        system_version="1.0.0",
        high_risk_category=HighRiskCategory.EMPLOYMENT_WORKPLACE,
    )

    findings = await _perform_compliance_validation(request)

    assert len(findings) > 0
    assert all(isinstance(f, EUAIActComplianceFinding) for f in findings)
    assert any(f.article == "Article 9" for f in findings)
    assert any(f.article == "Article 14" for f in findings)


@pytest.mark.asyncio
async def test_compliance_validation_findings_structure():
    """Test that findings have required fields."""
    request = ComplianceValidationRequest(
        system_name="Test System",
        system_version="1.0.0",
        high_risk_category=HighRiskCategory.CRITICAL_INFRASTRUCTURE,
    )

    findings = await _perform_compliance_validation(request)

    for finding in findings:
        assert finding.finding_id
        assert finding.article
        assert finding.requirement
        assert finding.status in ComplianceStatus
        assert finding.severity in FindingSeverity
        assert finding.description


def test_compliance_checklist_model():
    """Test EUAIActComplianceChecklist model validation."""
    checklist = EUAIActComplianceChecklist(
        system_name="Test System",
        system_version="1.0.0",
        organization_name="Test Org",
        assessment_date=date.today(),
        assessor_name="John Doe",
        assessor_role="Compliance Officer",
        high_risk_category=HighRiskCategory.BIOMETRIC_IDENTIFICATION,
        findings=[],
        overall_status=ComplianceStatus.COMPLIANT,
    )

    assert checklist.system_name == "Test System"
    assert checklist.overall_status == ComplianceStatus.COMPLIANT


def test_compliance_checklist_future_date_validation():
    """Test that assessment date cannot be in the future."""
    from datetime import timedelta

    future_date = date.today() + timedelta(days=1)

    with pytest.raises(ValueError, match="cannot be in the future"):
        EUAIActComplianceChecklist(
            system_name="Test System",
            system_version="1.0.0",
            organization_name="Test Org",
            assessment_date=future_date,
            assessor_name="John Doe",
            assessor_role="Compliance Officer",
            high_risk_category=HighRiskCategory.BIOMETRIC_IDENTIFICATION,
            findings=[],
            overall_status=ComplianceStatus.COMPLIANT,
        )
