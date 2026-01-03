"""
Pytest configuration and fixtures for compliance-docs-service tests
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app


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
                "test_results": "Passed"
            }
        ],
        "generated_at": "2024-01-01T00:00:00Z",
        "version": "1.0"
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
                    "internal_recipients": ["Security Team"]
                },
                "retention_period": "7 years",
                "security_measures": ["Encryption", "Access Controls"],
                "transfers": []
            }
        ],
        "version": "1.0"
    }
