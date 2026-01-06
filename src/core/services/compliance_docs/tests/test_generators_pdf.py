"""
Unit tests for PDF document generator in the compliance-docs-service.

Tests cover:
- PDF generator class initialization
- Custom styles for compliance documents
- Table builder functionality
- Report generation for all four compliance frameworks (SOC 2, ISO 27001, GDPR, EU AI Act)
- Buffer generation for streaming responses
- Error handling for unsupported frameworks
- Edge cases (minimal data, empty data)
- Output path handling
"""

import io
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from src.core.services.compliance_docs.src.generators.pdf_generator import (
    CompliancePDFStyles,
    PDFGenerator,
    PDFTableBuilder,
    _ensure_output_dir,
    _get_output_path,
    generate_pdf,
    generate_pdf_to_buffer,
)
from src.core.services.compliance_docs.src.models.base import ComplianceFramework


class TestCompliancePDFStyles:
    """Tests for CompliancePDFStyles class."""

    def test_styles_initialization(self):
        """Test that styles are initialized correctly."""
        styles = CompliancePDFStyles()
        assert styles is not None
        assert hasattr(styles, "_base_styles")
        assert hasattr(styles, "_custom_styles")

    def test_get_custom_style(self):
        """Test retrieving a custom style."""
        styles = CompliancePDFStyles()
        doc_title = styles.get_style("DocumentTitle")
        assert doc_title is not None
        assert doc_title.fontSize == 24

    def test_get_section_header_style(self):
        """Test retrieving section header style."""
        styles = CompliancePDFStyles()
        section_header = styles.get_style("SectionHeader")
        assert section_header is not None
        assert section_header.fontSize == 16

    def test_get_body_text_style(self):
        """Test retrieving body text style."""
        styles = CompliancePDFStyles()
        body_text = styles.get_style("BodyText")
        assert body_text is not None
        assert body_text.fontSize == 10

    def test_get_base_style(self):
        """Test retrieving a base style (from sample stylesheet)."""
        styles = CompliancePDFStyles()
        normal = styles.get_style("Normal")
        assert normal is not None

    def test_get_status_styles(self):
        """Test that status styles are available."""
        styles = CompliancePDFStyles()
        compliant = styles.get_style("StatusCompliant")
        non_compliant = styles.get_style("StatusNonCompliant")
        pending = styles.get_style("StatusPending")
        assert compliant is not None
        assert non_compliant is not None
        assert pending is not None

    def test_get_nonexistent_style_raises(self):
        """Test that getting a non-existent style raises KeyError."""
        styles = CompliancePDFStyles()
        with pytest.raises(KeyError):
            styles.get_style("NonExistentStyle")

    def test_all_styles_property(self):
        """Test the all_styles property returns all styles."""
        styles = CompliancePDFStyles()
        all_styles = styles.all_styles
        assert isinstance(all_styles, dict)
        assert "DocumentTitle" in all_styles
        assert "Normal" in all_styles


class TestPDFTableBuilder:
    """Tests for PDFTableBuilder class."""

    def test_table_builder_initialization(self):
        """Test table builder initialization."""
        styles = CompliancePDFStyles()
        builder = PDFTableBuilder(styles)
        assert builder is not None
        assert builder.styles is styles

    def test_create_simple_table(self):
        """Test creating a simple table."""
        styles = CompliancePDFStyles()
        builder = PDFTableBuilder(styles)
        headers = ["Col1", "Col2", "Col3"]
        rows = [["A", "B", "C"], ["D", "E", "F"]]
        table = builder.create_simple_table(headers, rows)
        assert table is not None

    def test_create_simple_table_with_col_widths(self):
        """Test creating table with custom column widths."""
        styles = CompliancePDFStyles()
        builder = PDFTableBuilder(styles)
        headers = ["ID", "Name"]
        rows = [["1", "Test"]]
        table = builder.create_simple_table(headers, rows, col_widths=[1.0, 3.0])
        assert table is not None

    def test_create_evidence_table(self):
        """Test creating an evidence table."""
        styles = CompliancePDFStyles()
        builder = PDFTableBuilder(styles)
        records = [
            {
                "control_id": "CC1.1",
                "description": "Test evidence",
                "evidence_type": "document",
                "collected_at": datetime(2024, 6, 15, tzinfo=timezone.utc),
                "status": "compliant",
            }
        ]
        table = builder.create_evidence_table(records)
        assert table is not None

    def test_create_evidence_table_without_status(self):
        """Test creating evidence table without status column."""
        styles = CompliancePDFStyles()
        builder = PDFTableBuilder(styles)
        records = [{"control_id": "A.5.1", "description": "Evidence"}]
        table = builder.create_evidence_table(records, include_status=False)
        assert table is not None

    def test_create_control_mapping_table(self):
        """Test creating a control mapping table."""
        styles = CompliancePDFStyles()
        builder = PDFTableBuilder(styles)
        mappings = [
            {
                "soc2_control_id": "CC1.1",
                "guardrail_control_name": "GR-001",
                "mapping_rationale": "Test mapping",
                "coverage_percentage": 100,
            }
        ]
        table = builder.create_control_mapping_table(mappings, "soc2")
        assert table is not None

    def test_format_date_with_datetime(self):
        """Test date formatting with datetime object."""
        styles = CompliancePDFStyles()
        builder = PDFTableBuilder(styles)
        dt = datetime(2024, 6, 15, tzinfo=timezone.utc)
        result = builder._format_date(dt)
        assert result == "2024-06-15"

    def test_format_date_with_none(self):
        """Test date formatting with None value."""
        styles = CompliancePDFStyles()
        builder = PDFTableBuilder(styles)
        result = builder._format_date(None)
        assert result == "N/A"

    def test_format_status(self):
        """Test status formatting."""
        styles = CompliancePDFStyles()
        builder = PDFTableBuilder(styles)
        assert builder._format_status("in_progress") == "In Progress"
        assert builder._format_status("") == "N/A"
        assert builder._format_status(None) == "N/A"


class TestPDFGenerator:
    """Tests for PDFGenerator class."""

    def test_generator_initialization(self):
        """Test PDF generator initialization."""
        generator = PDFGenerator()
        assert generator is not None
        assert generator.styles is not None
        assert generator.table_builder is not None

    def test_generator_initialization_custom_margins(self):
        """Test PDF generator with custom margins."""
        margins = {"left": 1.0, "right": 1.0, "top": 1.0, "bottom": 1.0}
        generator = PDFGenerator(margins=margins)
        assert generator.margins == margins

    def test_reset_story(self):
        """Test resetting the document story."""
        generator = PDFGenerator()
        generator._story = ["test"]
        generator._reset_story()
        assert generator._story == []

    def test_add_section(self):
        """Test adding a section to the document."""
        generator = PDFGenerator()
        generator._reset_story()
        generator._add_section("Test Section")
        assert len(generator._story) > 0

    def test_add_paragraph(self):
        """Test adding a paragraph to the document."""
        generator = PDFGenerator()
        generator._reset_story()
        generator._add_paragraph("Test paragraph content")
        assert len(generator._story) > 0

    def test_add_bullet_list(self):
        """Test adding a bullet list to the document."""
        generator = PDFGenerator()
        generator._reset_story()
        generator._add_bullet_list(["Item 1", "Item 2", "Item 3"])
        assert len(generator._story) > 0

    def test_add_spacer(self):
        """Test adding a spacer to the document."""
        generator = PDFGenerator()
        generator._reset_story()
        initial_len = len(generator._story)
        generator._add_spacer()
        assert len(generator._story) == initial_len + 1

    def test_add_page_break(self):
        """Test adding a page break to the document."""
        generator = PDFGenerator()
        generator._reset_story()
        initial_len = len(generator._story)
        generator._add_page_break()
        assert len(generator._story) == initial_len + 1


class TestPDFGeneratorSOC2:
    """Tests for SOC 2 PDF report generation."""

    def test_generate_soc2_report(self, tmp_path, sample_soc2_report_data):
        """Test generating a SOC 2 PDF report."""
        output_path = tmp_path / "soc2_test.pdf"
        generator = PDFGenerator()
        result = generator.generate_soc2_report(sample_soc2_report_data, output_path)
        assert result == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_soc2_report_default_path(self, sample_soc2_report_data):
        """Test generating SOC 2 report with default output path."""
        generator = PDFGenerator()
        result = generator.generate_soc2_report(sample_soc2_report_data)
        assert result.exists()
        assert "soc2_report" in result.name
        # Clean up
        result.unlink(missing_ok=True)

    def test_generate_soc2_report_with_system_description(self, tmp_path):
        """Test SOC 2 report with system description section."""
        data = {
            "organization_name": "Test Org",
            "audit_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "audit_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
            "system_description": {
                "system_description": "Test system description",
                "principal_service_commitments": ["Commitment 1", "Commitment 2"],
                "components": ["Component A", "Component B"],
            },
        }
        output_path = tmp_path / "soc2_sys_desc.pdf"
        generator = PDFGenerator()
        result = generator.generate_soc2_report(data, output_path)
        assert result.exists()

    def test_generate_soc2_report_with_criteria_sections(self, tmp_path):
        """Test SOC 2 report with trust service criteria sections."""
        data = {
            "organization_name": "Test Org",
            "criteria_sections": [
                {
                    "criteria": "security",
                    "controls": [
                        {"control_id": "CC1.1", "title": "Test", "control_objective": "Obj"},
                    ],
                },
            ],
        }
        output_path = tmp_path / "soc2_criteria.pdf"
        generator = PDFGenerator()
        result = generator.generate_soc2_report(data, output_path)
        assert result.exists()


class TestPDFGeneratorISO27001:
    """Tests for ISO 27001 PDF report generation."""

    def test_generate_iso27001_report(self, tmp_path, sample_iso27001_report_data):
        """Test generating an ISO 27001 PDF report."""
        output_path = tmp_path / "iso27001_test.pdf"
        generator = PDFGenerator()
        result = generator.generate_iso27001_report(sample_iso27001_report_data, output_path)
        assert result == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_iso27001_report_with_soa(self, tmp_path):
        """Test ISO 27001 report with Statement of Applicability."""
        data = {
            "organization_name": "Test Org",
            "isms_scope": "Test ISMS Scope",
            "statement_of_applicability": {
                "entries": [
                    {
                        "control_id": "A.5.1",
                        "control_title": "Security Policies",
                        "applicability": "applicable",
                        "implementation_status": "implemented",
                    },
                ],
            },
        }
        output_path = tmp_path / "iso27001_soa.pdf"
        generator = PDFGenerator()
        result = generator.generate_iso27001_report(data, output_path)
        assert result.exists()

    def test_generate_iso27001_report_with_themes(self, tmp_path):
        """Test ISO 27001 report with theme sections."""
        data = {
            "organization_name": "Test Org",
            "theme_sections": [
                {"theme": "organizational", "implementation_percentage": 85.5},
                {"theme": "people", "implementation_percentage": 90.0},
            ],
        }
        output_path = tmp_path / "iso27001_themes.pdf"
        generator = PDFGenerator()
        result = generator.generate_iso27001_report(data, output_path)
        assert result.exists()


class TestPDFGeneratorGDPR:
    """Tests for GDPR PDF report generation."""

    def test_generate_gdpr_report(self, tmp_path, sample_gdpr_report_data):
        """Test generating a GDPR PDF report."""
        output_path = tmp_path / "gdpr_test.pdf"
        generator = PDFGenerator()
        result = generator.generate_gdpr_report(sample_gdpr_report_data, output_path)
        assert result == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_gdpr_report_with_controller_record(self, tmp_path):
        """Test GDPR report with controller record section."""
        data = {
            "organization_name": "Test Org",
            "entity_role": "controller",
            "controller_record": {
                "controller_name": "Test Controller",
                "controller_contact": {"name": "John Doe", "email": "john@test.com"},
                "dpo": {"name": "Jane Doe", "email": "jane@test.com"},
                "processing_activities": [
                    {"name": "Activity 1", "purposes": ["Purpose 1"], "status": "active"},
                ],
            },
        }
        output_path = tmp_path / "gdpr_controller.pdf"
        generator = PDFGenerator()
        result = generator.generate_gdpr_report(data, output_path)
        assert result.exists()

    def test_generate_gdpr_report_with_data_flows(self, tmp_path):
        """Test GDPR report with data flows section."""
        data = {
            "organization_name": "Test Org",
            "data_flows": [
                {
                    "name": "Flow 1",
                    "data_source": "Source A",
                    "data_destination": "Dest B",
                    "crosses_border": True,
                },
            ],
        }
        output_path = tmp_path / "gdpr_flows.pdf"
        generator = PDFGenerator()
        result = generator.generate_gdpr_report(data, output_path)
        assert result.exists()


class TestPDFGeneratorEUAIAct:
    """Tests for EU AI Act PDF report generation."""

    def test_generate_euaiact_report(self, tmp_path, sample_euaiact_report_data):
        """Test generating an EU AI Act PDF report."""
        output_path = tmp_path / "euaiact_test.pdf"
        generator = PDFGenerator()
        result = generator.generate_euaiact_report(sample_euaiact_report_data, output_path)
        assert result == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_euaiact_report_with_risk_assessments(self, tmp_path):
        """Test EU AI Act report with risk assessments."""
        data = {
            "organization_name": "Test Org",
            "ai_systems": [{"system_id": "AIS-001"}],
            "high_risk_systems_count": 1,
            "limited_risk_systems_count": 2,
            "minimal_risk_systems_count": 3,
            "risk_assessments": [
                {
                    "system_name": "AI System 1",
                    "risk_level": "high_risk",
                    "high_risk_category": "Category A",
                    "assessment_date": datetime(2024, 6, 15, tzinfo=timezone.utc),
                },
            ],
        }
        output_path = tmp_path / "euaiact_risk.pdf"
        generator = PDFGenerator()
        result = generator.generate_euaiact_report(data, output_path)
        assert result.exists()

    def test_generate_euaiact_report_with_conformity_assessments(self, tmp_path):
        """Test EU AI Act report with conformity assessments."""
        data = {
            "organization_name": "Test Org",
            "ai_systems": [],
            "conformity_assessments": [
                {
                    "system_id": "AIS-001",
                    "assessment_type": "internal_control",
                    "assessment_result": "passed",
                    "certificate_number": "CERT-001",
                },
            ],
        }
        output_path = tmp_path / "euaiact_conformity.pdf"
        generator = PDFGenerator()
        result = generator.generate_euaiact_report(data, output_path)
        assert result.exists()


class TestGeneratePDFFunction:
    """Tests for the generate_pdf() main entry point function."""

    def test_generate_pdf_soc2(self, tmp_path, sample_soc2_report_data):
        """Test generate_pdf with SOC 2 framework."""
        output_path = tmp_path / "soc2.pdf"
        result = generate_pdf(sample_soc2_report_data, "soc2", output_path)
        assert result == output_path
        assert output_path.exists()

    def test_generate_pdf_iso27001(self, tmp_path, sample_iso27001_report_data):
        """Test generate_pdf with ISO 27001 framework."""
        output_path = tmp_path / "iso27001.pdf"
        result = generate_pdf(sample_iso27001_report_data, "iso27001", output_path)
        assert result == output_path
        assert output_path.exists()

    def test_generate_pdf_gdpr(self, tmp_path, sample_gdpr_report_data):
        """Test generate_pdf with GDPR framework."""
        output_path = tmp_path / "gdpr.pdf"
        result = generate_pdf(sample_gdpr_report_data, "gdpr", output_path)
        assert result == output_path
        assert output_path.exists()

    def test_generate_pdf_euaiact(self, tmp_path, sample_euaiact_report_data):
        """Test generate_pdf with EU AI Act framework."""
        output_path = tmp_path / "euaiact.pdf"
        result = generate_pdf(sample_euaiact_report_data, "euaiact", output_path)
        assert result == output_path
        assert output_path.exists()

    def test_generate_pdf_with_framework_enum(self, tmp_path, sample_soc2_report_data):
        """Test generate_pdf with ComplianceFramework enum."""
        output_path = tmp_path / "soc2_enum.pdf"
        result = generate_pdf(sample_soc2_report_data, ComplianceFramework.SOC2, output_path)
        assert result == output_path
        assert output_path.exists()

    def test_generate_pdf_unsupported_framework(self, sample_soc2_report_data):
        """Test generate_pdf raises error for unsupported framework."""
        with pytest.raises(ValueError) as exc_info:
            generate_pdf(sample_soc2_report_data, "unsupported")
        assert "Unsupported framework" in str(exc_info.value)

    def test_generate_pdf_case_insensitive_framework(self, tmp_path, sample_soc2_report_data):
        """Test generate_pdf is case insensitive for framework."""
        output_path = tmp_path / "soc2_upper.pdf"
        result = generate_pdf(sample_soc2_report_data, "SOC2", output_path)
        assert result.exists()


class TestGeneratePDFToBuffer:
    """Tests for generate_pdf_to_buffer() function."""

    def test_generate_pdf_to_buffer_soc2(self, sample_soc2_report_data):
        """Test generating SOC 2 PDF to buffer."""
        buffer = generate_pdf_to_buffer(sample_soc2_report_data, "soc2")
        assert isinstance(buffer, io.BytesIO)
        content = buffer.getvalue()
        assert len(content) > 0
        assert content[:4] == b"%PDF"  # PDF magic bytes

    def test_generate_pdf_to_buffer_iso27001(self, sample_iso27001_report_data):
        """Test generating ISO 27001 PDF to buffer."""
        buffer = generate_pdf_to_buffer(sample_iso27001_report_data, "iso27001")
        assert isinstance(buffer, io.BytesIO)
        assert buffer.getvalue()[:4] == b"%PDF"

    def test_generate_pdf_to_buffer_gdpr(self, sample_gdpr_report_data):
        """Test generating GDPR PDF to buffer."""
        buffer = generate_pdf_to_buffer(sample_gdpr_report_data, "gdpr")
        assert isinstance(buffer, io.BytesIO)
        assert buffer.getvalue()[:4] == b"%PDF"

    def test_generate_pdf_to_buffer_euaiact(self, sample_euaiact_report_data):
        """Test generating EU AI Act PDF to buffer."""
        buffer = generate_pdf_to_buffer(sample_euaiact_report_data, "euaiact")
        assert isinstance(buffer, io.BytesIO)
        assert buffer.getvalue()[:4] == b"%PDF"

    def test_generate_pdf_to_buffer_unsupported_framework(self):
        """Test buffer generation raises error for unsupported framework."""
        with pytest.raises(ValueError) as exc_info:
            generate_pdf_to_buffer({}, "unsupported")
        assert "Unsupported framework" in str(exc_info.value)

    def test_generate_pdf_to_buffer_seek_position(self, sample_soc2_report_data):
        """Test that buffer seek position is at start after generation."""
        buffer = generate_pdf_to_buffer(sample_soc2_report_data, "soc2")
        assert buffer.tell() == 0


class TestOutputPathHandling:
    """Tests for output path handling functions."""

    def test_get_output_path_default(self):
        """Test getting default output path."""
        path = _get_output_path()
        assert path is not None
        assert "compliance-reports" in str(path)

    def test_get_output_path_from_env(self):
        """Test getting output path from environment variable."""
        with patch.dict("os.environ", {"COMPLIANCE_OUTPUT_PATH": "/custom/path"}):
            path = _get_output_path()
            assert str(path) == "/custom/path"

    def test_ensure_output_dir(self, tmp_path):
        """Test ensuring output directory exists."""
        custom_path = tmp_path / "compliance-test"
        with patch.dict("os.environ", {"COMPLIANCE_OUTPUT_PATH": str(custom_path)}):
            result = _ensure_output_dir()
            assert result.exists()
            assert result.is_dir()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_generate_pdf_empty_data(self, tmp_path):
        """Test generating PDF with empty data."""
        output_path = tmp_path / "empty.pdf"
        result = generate_pdf({}, "soc2", output_path)
        assert result.exists()

    def test_generate_pdf_minimal_data(self, tmp_path, minimal_pdf_data):
        """Test generating PDF with minimal data."""
        output_path = tmp_path / "minimal.pdf"
        result = generate_pdf(minimal_pdf_data, "soc2", output_path)
        assert result.exists()

    def test_generate_pdf_none_values(self, tmp_path):
        """Test generating PDF with None values in data."""
        data = {
            "organization_name": None,
            "audit_period_start": None,
            "audit_period_end": None,
        }
        output_path = tmp_path / "none_values.pdf"
        result = generate_pdf(data, "soc2", output_path)
        assert result.exists()

    def test_generate_pdf_special_characters(self, tmp_path):
        """Test generating PDF with special characters in data."""
        data = {
            "organization_name": "Test & Company <Corp>",
            "report_title": 'Report "Test" 2024',
        }
        output_path = tmp_path / "special_chars.pdf"
        result = generate_pdf(data, "soc2", output_path)
        assert result.exists()

    def test_generate_pdf_unicode_characters(self, tmp_path):
        """Test generating PDF with unicode characters."""
        data = {
            "organization_name": "Test Org - Société Française",
            "report_title": "日本語テスト Report",
        }
        output_path = tmp_path / "unicode.pdf"
        result = generate_pdf(data, "soc2", output_path)
        assert result.exists()


class TestDateFormatting:
    """Tests for date formatting in PDF generator."""

    def test_format_date_with_string(self):
        """Test formatting a date string."""
        generator = PDFGenerator()
        result = generator._format_date("2024-06-15")
        assert result == "2024-06-15"

    def test_format_date_with_datetime(self):
        """Test formatting a datetime object."""
        generator = PDFGenerator()
        dt = datetime(2024, 6, 15, tzinfo=timezone.utc)
        result = generator._format_date(dt)
        assert result == "2024-06-15"

    def test_format_date_with_none(self):
        """Test formatting None returns N/A."""
        generator = PDFGenerator()
        result = generator._format_date(None)
        assert result == "N/A"


# Fixtures for PDF generator tests
@pytest.fixture
def sample_soc2_report_data():
    """Sample SOC 2 report data for PDF testing."""
    return {
        "organization_name": "ACGS Test Corporation",
        "audit_period_start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "audit_period_end": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "criteria_sections": [
            {
                "criteria": "security",
                "controls": [
                    {
                        "control_id": "CC1.1",
                        "title": "Commitment to Integrity",
                        "control_objective": "The entity demonstrates commitment.",
                    },
                ],
            },
        ],
        "control_mappings": [
            {
                "soc2_control_id": "CC1.1",
                "guardrail_control_id": "GR-001",
                "guardrail_control_name": "Ethics Guardrail",
                "mapping_rationale": "Maps to integrity commitment",
                "coverage_percentage": 100,
            },
        ],
    }


@pytest.fixture
def sample_iso27001_report_data():
    """Sample ISO 27001 report data for PDF testing."""
    return {
        "organization_name": "ACGS Test Corporation",
        "isms_scope": "AI Guardrails Platform",
        "statement_of_applicability": {
            "entries": [
                {
                    "control_id": "A.5.1",
                    "control_title": "Information Security Policy",
                    "applicability": "applicable",
                    "implementation_status": "implemented",
                },
            ],
        },
        "theme_sections": [
            {"theme": "organizational", "implementation_percentage": 85.5},
        ],
    }


@pytest.fixture
def sample_gdpr_report_data():
    """Sample GDPR report data for PDF testing."""
    return {
        "organization_name": "ACGS Test Corporation",
        "entity_role": "controller",
        "controller_record": {
            "controller_name": "ACGS Test Corporation",
            "controller_contact": {"name": "John Doe", "email": "john@test.com"},
            "dpo": {"name": "Jane Doe", "email": "dpo@test.com"},
            "processing_activities": [
                {
                    "name": "AI Model Training",
                    "purposes": ["Training", "Evaluation"],
                    "status": "active",
                },
            ],
        },
        "data_flows": [
            {
                "name": "User Data Flow",
                "data_source": "Application",
                "data_destination": "Cloud Storage",
                "crosses_border": False,
            },
        ],
    }


@pytest.fixture
def sample_euaiact_report_data():
    """Sample EU AI Act report data for PDF testing."""
    return {
        "organization_name": "ACGS Test Corporation",
        "organization_role": "provider",
        "ai_systems": [
            {"system_id": "AIS-001", "system_name": "Guardrail Engine"},
        ],
        "high_risk_systems_count": 1,
        "limited_risk_systems_count": 2,
        "minimal_risk_systems_count": 0,
        "risk_assessments": [
            {
                "system_name": "Guardrail Engine",
                "risk_level": "high_risk",
                "high_risk_category": "Safety Component",
                "assessment_date": datetime(2024, 6, 15, tzinfo=timezone.utc),
            },
        ],
        "conformity_assessments": [
            {
                "system_id": "AIS-001",
                "assessment_type": "internal_control",
                "assessment_result": "passed",
                "certificate_number": "CERT-001",
            },
        ],
    }


@pytest.fixture
def minimal_pdf_data():
    """Minimal data for PDF testing."""
    return {"organization_name": "Test Org"}
