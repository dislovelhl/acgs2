from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from src.core.services.compliance_docs.src.main import app


@pytest.fixture
def test_client():
    """FastAPI test client fixture"""
    return TestClient(app)


@pytest.fixture
def sample_soc2_evidence():
    """Sample SOC 2 evidence data for testing"""
    return {
        "framework": "soc2",
        "criteria": "security",
        "period_start": "2024-01-01",
        "period_end": "2024-12-31",
        "controls": [
            {
                "control_id": "CC1.1",
                "control_name": "Control Environment",
                "criteria": "security",
                "description": "The entity demonstrates a commitment to integrity and ethical values",
                "guardrail_mapping": ["intent_classifier", "pacar_verifier"],
                "evidence_sources": ["audit_logs", "policy_evaluations"],
                "testing_frequency": "Quarterly",
                "last_tested": "2024-12-31",
                "test_results": "Passed",
            }
        ],
        "generated_at": "2024-01-01T00:00:00Z",
        "version": "1.0",
    }


@pytest.fixture
def sample_gdpr_record():
    """Sample GDPR Article 30 record for testing"""
    return {
        "controller_name": "ACGS-2 Platform",
        "controller_representative": "ACGS Team",
        "dpo_contact": "dpo@acgs2.com",
        "record_date": "2024-01-01",
        "processing_activities": [
            {
                "activity_id": "ai-governance",
                "name": "AI Governance Processing",
                "purpose": "ai_governance",
                "legal_basis": "legitimate_interest",
                "data_categories": ["behavioral_data"],
                "data_subjects": ["Users"],
                "recipients": {
                    "processors": ["OpenAI", "Anthropic"],
                    "internal_recipients": ["Security Team"],
                },
                "retention_period": "7 years",
                "security_measures": ["Encryption", "Access Controls"],
                "transfers": [],
            }
        ],
        "version": "1.0",
    }


@pytest.fixture
def sample_soc2_data():
    """Sample SOC 2 data for template testing"""
    return {
        "organization_name": "ACGS Test Corporation",
        "report_type": "Type II",
        "audit_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "audit_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "generated_at": datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "document_version": "1.0",
        "total_mappings": 1,
        "criteria_in_scope": [
            {"criteria": "security", "description": "Security Criteria", "controls": ["CC1.1"]}
        ],
        "average_coverage": 100,
        "gaps_identified": 0,
        "control_mappings": [
            {
                "mapping_id": "M-001",
                "soc2_control_id": "CC1.1",
                "guardrail_control_id": "GR-ETHICS-001",
                "guardrail_control_name": "Ethics Guardrail",
                "coverage_percentage": 100,
                "mapping_rationale": "Direct mapping",
                "gaps": [],
            }
        ],
    }


@pytest.fixture
def sample_iso27001_data():
    """Sample ISO 27001 data for template testing"""
    return {
        "organization_name": "ACGS Test Corporation",
        "isms_scope": "Core Infrastructure",
        "audit_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "audit_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "evidence_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "evidence_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "effective_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "next_review_date": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "isms_manager_approval_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "generated_at": datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "soa_entries": [
            {
                "control_id": "A.5.1",
                "control_title": "Information Security Policy",
                "applicability": "applicable",
                "implementation_status": "implemented",
            }
        ],
        "controls": [
            {
                "control_id": "A.5.1",
                "control_name": "Policies for information security",
                "status": "compliant",
                "theme": "Organizational",
            }
        ],
        "theme_sections": [{"theme": "Organizational", "implementation_percentage": 100}],
        "iso_approval_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "exec_approval_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }


@pytest.fixture
def sample_gdpr_data():
    """Sample GDPR data for template testing"""
    activities = [
        {
            "activity_id": "PA-001",
            "name": "AI Model Training",
            "status": "compliant",
            "purposes": ["Training", "Evaluation"],
        }
    ]
    contact = {"name": "John Doe", "email": "john@example.com"}
    dpo = {"name": "Jane Doe", "email": "dpo@example.com"}
    return {
        "organization_name": "ACGS Test Corporation",
        "audit_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "audit_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "reporting_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "reporting_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "generated_at": datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "dpo_name": "Jane Doe",
        "dpo_email": "dpo@example.com",
        "controller_record": {
            "processing_activities": activities,
            "controller_representative": "John Doe",
            "controller_name": "ACGS-2",
            "controller_contact": contact,
            "dpo": dpo,
        },
        "processor_record": {
            "processing_activities": activities,
            "processor_name": "ACGS-2",
            "processor_contact": contact,
            "dpo": dpo,
        },
        "data_flows": [{"name": "User Data", "data_source": "App", "data_destination": "DB"}],
    }


@pytest.fixture
def sample_euaiact_data():
    """Sample EU AI Act data for template testing"""
    return {
        "organization_name": "ACGS Test Corporation",
        "audit_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "audit_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "reporting_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "reporting_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "generated_at": datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "ai_systems": [
            {"system_id": "AIS-001", "system_name": "Guardrail Engine", "risk_level": "high"}
        ],
    }


@pytest.fixture
def minimal_data():
    """Minimal data for template testing"""
    return {
        "organization_name": "Test Org",
        "audit_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "audit_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "reporting_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "reporting_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "evidence_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "evidence_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "generated_at": datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "controller_record": {
            "processing_activities": [],
            "controller_contact": {"name": "John Doe", "email": "john@example.com"},
        },
        "processor_record": {
            "processing_activities": [],
            "processor_contact": {"name": "John Doe", "email": "john@example.com"},
        },
    }


@pytest.fixture
def empty_data():
    """Empty data for template testing"""
    return {}


@pytest.fixture
def xss_test_data():
    """Data with XSS injection attempts for escaping tests"""
    return {
        "organization_name": "<script>alert('XSS')</script>",
        "report_title": "Report'\" onerror=alert(1)",
        "audit_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "audit_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "reporting_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "reporting_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "generated_at": datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "control_mappings": [
            {
                "soc2_control_id": "<iframe src='javascript:alert(1)'>",
                "guardrail_control_id": "XSS-001",
                "guardrail_control_name": "<script>alert(1)</script>",
                "coverage_percentage": 100,
                "gaps": [],
            }
        ],
    }
