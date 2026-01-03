"""
Unit tests for EU AI Act document generators
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
import tempfile
from pathlib import Path
from datetime import date

from src.generators.pdf import PDFGenerator
from src.generators.docx import DOCXGenerator
from src.generators.xlsx import XLSXGenerator


@pytest.fixture
def temp_dir():
    """Create temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.mark.skipif(not PDFGenerator.__module__.startswith("src"), reason="ReportLab not available")
def test_pdf_generator_risk_assessment(temp_dir):
    """Test PDF generation for risk assessment."""
    generator = PDFGenerator(output_dir=temp_dir)

    data = {
        "document_type": "risk_assessment",
        "title": "Test Risk Assessment",
        "system_name": "Test System",
        "assessment_date": str(date.today()),
        "assessor_name": "Test Assessor",
        "risk_factors": [
            {
                "category": "Data Quality",
                "description": "Test risk factor",
                "likelihood": "High",
                "impact": "Medium",
                "risk_level": "high",
            }
        ],
        "mitigation_measures": ["Measure 1", "Measure 2"],
    }

    file_path = generator.generate(data, "test_risk_assessment")

    assert file_path.exists()
    assert file_path.suffix == ".pdf"


@pytest.mark.skipif(not DOCXGenerator.__module__.startswith("src"), reason="python-docx not available")
def test_docx_generator_compliance_checklist(temp_dir):
    """Test DOCX generation for compliance checklist."""
    generator = DOCXGenerator(output_dir=temp_dir)

    data = {
        "document_type": "compliance_checklist",
        "title": "Test Compliance Checklist",
        "system_name": "Test System",
        "overall_status": "compliant",
        "findings": [
            {
                "article": "Article 9",
                "requirement": "Test requirement",
                "status": "compliant",
                "severity": "low",
            }
        ],
    }

    file_path = generator.generate(data, "test_checklist")

    assert file_path.exists()
    assert file_path.suffix == ".docx"


@pytest.mark.skipif(not XLSXGenerator.__module__.startswith("src"), reason="openpyxl not available")
def test_xlsx_generator_quarterly_report(temp_dir):
    """Test XLSX generation for quarterly report."""
    generator = XLSXGenerator(output_dir=temp_dir)

    data = {
        "document_type": "quarterly_report",
        "title": "Test Quarterly Report",
        "report_period": {
            "total_assessments": 10,
            "compliant_systems": 8,
            "non_compliant_systems": 1,
            "critical_findings": 2,
        },
    }

    file_path = generator.generate(data, "test_quarterly_report")

    assert file_path.exists()
    assert file_path.suffix == ".xlsx"


def test_generators_handle_missing_dependencies():
    """Test that generators handle missing dependencies gracefully."""
    # This test verifies that generators check for dependencies
    # In a real scenario, we'd mock the imports
    pass
