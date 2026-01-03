"""
Pytest configuration and fixtures for compliance-docs-service tests.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Add src directory to Python path for imports
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(autouse=True)
def reset_template_cache():
    """Reset template cache before each test to ensure clean state."""
    from template_engine import clear_template_cache

    clear_template_cache()
    yield
    clear_template_cache()


@pytest.fixture
def sample_soc2_data():
    """Sample SOC 2 Type II control mapping data for testing."""
    return {
        "organization_name": "ACGS Test Corporation",
        "report_title": "SOC 2 Type II Control Mapping Report",
        "reporting_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "reporting_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "auditor_name": "Test Auditor Firm",
        "version": "1.0",
        "controls": [
            {
                "control_id": "CC1.1",
                "tsc_criteria": "Security",
                "control_name": "Commitment to Integrity",
                "description": (
                    "The entity demonstrates commitment to integrity " "and ethical values."
                ),
                "implementation": "Code of conduct policy implemented",
                "evidence": ["Policy document", "Training records"],
                "status": "compliant",
                "guardrail_mapping": ["GR-ETHICS-001", "GR-ETHICS-002"],
            },
            {
                "control_id": "CC2.1",
                "tsc_criteria": "Availability",
                "control_name": "Information and Communication",
                "description": "The entity obtains or generates relevant information.",
                "implementation": "Centralized logging system",
                "evidence": ["System logs", "Monitoring dashboards"],
                "status": "compliant",
                "guardrail_mapping": ["GR-LOG-001"],
            },
        ],
        "tsc_sections": [
            {
                "name": "Security",
                "code": "CC",
                "total_controls": 10,
                "compliant_controls": 8,
                "non_compliant_controls": 1,
                "pending_controls": 1,
            },
            {
                "name": "Availability",
                "code": "A",
                "total_controls": 5,
                "compliant_controls": 5,
                "non_compliant_controls": 0,
                "pending_controls": 0,
            },
        ],
    }


@pytest.fixture
def sample_iso27001_data():
    """Sample ISO 27001:2022 Annex A data for testing."""
    return {
        "organization_name": "ACGS Test Corporation",
        "report_title": "ISO 27001:2022 Annex A Controls",
        "certification_scope": "AI Guardrails Platform",
        "reporting_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "reporting_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "version": "1.0",
        "themes": [
            {
                "theme_name": "Organizational Controls",
                "theme_code": "A.5",
                "controls": [
                    {
                        "control_id": "A.5.1",
                        "control_name": "Policies for information security",
                        "description": "Information security policy shall be defined.",
                        "implementation_status": "implemented",
                        "evidence": ["Security policy document"],
                        "applicability": "applicable",
                    },
                ],
            },
            {
                "theme_name": "People Controls",
                "theme_code": "A.6",
                "controls": [
                    {
                        "control_id": "A.6.1",
                        "control_name": "Screening",
                        "description": "Background verification checks shall be carried out.",
                        "implementation_status": "implemented",
                        "evidence": ["HR procedures"],
                        "applicability": "applicable",
                    },
                ],
            },
        ],
        "soa_entries": [
            {
                "control_id": "A.5.1",
                "control_name": "Policies for information security",
                "applicable": True,
                "justification": "Required for ISMS",
                "implementation_status": "implemented",
            },
        ],
    }


@pytest.fixture
def sample_gdpr_data():
    """Sample GDPR Article 30 data for testing."""
    return {
        "organization_name": "ACGS Test Corporation",
        "report_title": "GDPR Article 30 Records of Processing",
        "controller_name": "ACGS Test Corporation",
        "controller_address": "123 Test Street, Brussels, Belgium",
        "dpo_name": "Jane Doe",
        "dpo_email": "dpo@example.com",
        "report_date": datetime(2024, 6, 15, tzinfo=timezone.utc),
        "version": "1.0",
        "processing_activities": [
            {
                "activity_id": "PA-001",
                "activity_name": "AI Model Training",
                "purpose": "Training AI models for guardrail evaluation",
                "lawful_basis": "Legitimate interest",
                "data_subjects": ["Employees", "Contractors"],
                "data_categories": ["Professional information", "Usage data"],
                "recipients": ["Cloud provider", "Analytics team"],
                "retention_period": "2 years",
                "security_measures": ["Encryption", "Access controls"],
                "third_country_transfers": False,
            },
        ],
        "data_flows": [
            {
                "source": "User Input",
                "destination": "AI Processing Engine",
                "data_types": ["Text prompts"],
                "encryption_in_transit": True,
            },
        ],
    }


@pytest.fixture
def sample_euaiact_data():
    """Sample EU AI Act data for testing."""
    return {
        "organization_name": "ACGS Test Corporation",
        "report_title": "EU AI Act Risk Classification",
        "assessment_date": datetime(2024, 6, 15, tzinfo=timezone.utc),
        "assessor_name": "AI Compliance Team",
        "version": "1.0",
        "ai_systems": [
            {
                "system_id": "AIS-001",
                "system_name": "Guardrail Evaluation Engine",
                "description": "AI system for evaluating guardrail compliance",
                "risk_level": "limited",
                "intended_purpose": "Automated compliance checking",
                "ai_techniques": ["Machine Learning", "Natural Language Processing"],
                "prohibited_practices_check": False,
                "high_risk_category": None,
                "transparency_obligations": True,
            },
            {
                "system_id": "AIS-002",
                "system_name": "Content Moderation AI",
                "description": "AI for moderating user-generated content",
                "risk_level": "high",
                "intended_purpose": "Content safety filtering",
                "ai_techniques": ["Deep Learning", "Text Classification"],
                "prohibited_practices_check": False,
                "high_risk_category": "Safety components",
                "transparency_obligations": True,
            },
        ],
        "conformity_assessments": [
            {
                "system_id": "AIS-002",
                "assessment_type": "Internal control",
                "status": "passed",
                "assessment_date": datetime(2024, 5, 1, tzinfo=timezone.utc),
                "nonconformities": [],
            },
        ],
        "risk_summary": {
            "unacceptable": 0,
            "high": 1,
            "limited": 1,
            "minimal": 0,
        },
    }


@pytest.fixture
def xss_test_data():
    """Data containing potential XSS payloads for security testing."""
    return {
        "organization_name": "<script>alert('XSS')</script>",
        "report_title": "<img src=x onerror=alert('XSS')>",
        "description": "Normal text with <script>malicious</script> code",
        "controls": [
            {
                "control_id": "<b>CC1.1</b>",
                "control_name": "Test <script>alert(1)</script>",
                "description": "<iframe src='evil.com'></iframe>",
                "status": "compliant",
            }
        ],
    }


@pytest.fixture
def minimal_data():
    """Minimal data to test graceful handling of missing fields."""
    return {
        "organization_name": "Test Org",
    }


@pytest.fixture
def empty_data():
    """Empty data dictionary for edge case testing."""
    return {}
