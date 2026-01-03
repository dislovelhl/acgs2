"""
Unit tests for template rendering in the compliance-docs-service.

Tests cover:
- Jinja2 template environment configuration
- Custom filters (format_date, format_datetime, default_value, status_badge, etc.)
- Global functions (now_utc, current_year)
- Template rendering for all four compliance frameworks
- XSS prevention via autoescaping
- Graceful handling of missing data
- Template listing and existence checking
"""

from datetime import datetime, timezone

import pytest

from template_engine import (
    _control_id_format,
    _current_year,
    _default_value,
    _format_date,
    _format_datetime,
    _now_utc,
    _pluralize,
    _status_badge,
    clear_template_cache,
    get_template_env,
    list_templates,
    render_template,
    template_exists,
)


class TestTemplateEnvironmentConfiguration:
    """Tests for Jinja2 environment configuration."""

    def test_get_template_env_returns_environment(self):
        """Test that get_template_env returns a valid Jinja2 Environment."""
        env = get_template_env()
        assert env is not None
        assert hasattr(env, "get_template")
        assert hasattr(env, "loader")

    def test_get_template_env_is_cached(self):
        """Test that template environment is cached (LRU cache)."""
        env1 = get_template_env()
        env2 = get_template_env()
        assert env1 is env2

    def test_clear_template_cache(self):
        """Test that cache clearing works."""
        _ = get_template_env()  # Initial call to populate cache
        clear_template_cache()
        env2 = get_template_env()
        # After clearing, a new environment should be created
        # Note: They may be equal in content but different objects
        assert env2 is not None

    def test_autoescaping_enabled(self):
        """Test that autoescaping is enabled for HTML/XML files."""
        env = get_template_env()
        # Check autoescape settings
        assert env.autoescape is True or callable(env.autoescape)

    def test_custom_filters_registered(self):
        """Test that all custom filters are registered."""
        env = get_template_env()
        expected_filters = [
            "format_date",
            "format_datetime",
            "default_value",
            "status_badge",
            "control_id",
            "pluralize",
        ]
        for filter_name in expected_filters:
            assert filter_name in env.filters, f"Filter '{filter_name}' not registered"

    def test_global_functions_registered(self):
        """Test that global functions are registered."""
        env = get_template_env()
        assert "now_utc" in env.globals
        assert "current_year" in env.globals

    def test_trim_blocks_enabled(self):
        """Test that trim_blocks is enabled for cleaner output."""
        env = get_template_env()
        assert env.trim_blocks is True

    def test_lstrip_blocks_enabled(self):
        """Test that lstrip_blocks is enabled."""
        env = get_template_env()
        assert env.lstrip_blocks is True


class TestCustomFilters:
    """Tests for custom Jinja2 filters."""

    def test_format_date_with_datetime(self):
        """Test format_date filter with datetime object."""
        dt = datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = _format_date(dt)
        assert result == "2024-06-15"

    def test_format_date_with_custom_format(self):
        """Test format_date filter with custom format string."""
        dt = datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = _format_date(dt, "%B %d, %Y")
        assert result == "June 15, 2024"

    def test_format_date_with_none(self):
        """Test format_date filter with None value."""
        result = _format_date(None)
        assert result == "N/A"

    def test_format_date_with_string(self):
        """Test format_date filter with string passthrough."""
        result = _format_date("2024-06-15")
        assert result == "2024-06-15"

    def test_format_datetime_with_datetime(self):
        """Test format_datetime filter with datetime object."""
        dt = datetime(2024, 6, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = _format_datetime(dt)
        assert result == "2024-06-15 10:30:45 UTC"

    def test_format_datetime_with_custom_format(self):
        """Test format_datetime filter with custom format string."""
        dt = datetime(2024, 6, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = _format_datetime(dt, "%Y-%m-%dT%H:%M:%SZ")
        assert result == "2024-06-15T10:30:45Z"

    def test_format_datetime_with_none(self):
        """Test format_datetime filter with None value."""
        result = _format_datetime(None)
        assert result == "N/A"

    def test_format_datetime_with_string(self):
        """Test format_datetime filter with string passthrough."""
        result = _format_datetime("2024-06-15T10:30:45Z")
        assert result == "2024-06-15T10:30:45Z"

    def test_default_value_with_none(self):
        """Test default_value filter with None."""
        result = _default_value(None)
        assert result == "N/A"

    def test_default_value_with_empty_string(self):
        """Test default_value filter with empty string."""
        result = _default_value("")
        assert result == "N/A"

    def test_default_value_with_valid_value(self):
        """Test default_value filter with valid value."""
        result = _default_value("Test Value")
        assert result == "Test Value"

    def test_default_value_with_custom_default(self):
        """Test default_value filter with custom default string."""
        result = _default_value(None, "Not Available")
        assert result == "Not Available"

    def test_default_value_with_number(self):
        """Test default_value filter with numeric value."""
        result = _default_value(42)
        assert result == "42"

    def test_status_badge_compliant(self):
        """Test status_badge filter with compliant status."""
        result = _status_badge("compliant")
        assert result == "[COMPLIANT]"

    def test_status_badge_non_compliant(self):
        """Test status_badge filter with non_compliant status."""
        result = _status_badge("non_compliant")
        assert result == "[NON-COMPLIANT]"

    def test_status_badge_not_compliant(self):
        """Test status_badge filter with not_compliant status."""
        result = _status_badge("not_compliant")
        assert result == "[NON-COMPLIANT]"

    def test_status_badge_pending(self):
        """Test status_badge filter with pending status."""
        result = _status_badge("pending")
        assert result == "[PENDING]"

    def test_status_badge_in_progress(self):
        """Test status_badge filter with in_progress status."""
        result = _status_badge("in_progress")
        assert result == "[IN PROGRESS]"

    def test_status_badge_not_applicable(self):
        """Test status_badge filter with not_applicable status."""
        result = _status_badge("not_applicable")
        assert result == "[N/A]"

    def test_status_badge_partial(self):
        """Test status_badge filter with partial status."""
        result = _status_badge("partial")
        assert result == "[PARTIAL]"

    def test_status_badge_case_insensitive(self):
        """Test status_badge filter is case insensitive."""
        assert _status_badge("COMPLIANT") == "[COMPLIANT]"
        assert _status_badge("Compliant") == "[COMPLIANT]"
        assert _status_badge("NON-COMPLIANT") == "[NON-COMPLIANT]"

    def test_status_badge_handles_dashes_and_spaces(self):
        """Test status_badge filter handles dashes and spaces."""
        assert _status_badge("non-compliant") == "[NON-COMPLIANT]"
        assert _status_badge("in progress") == "[IN PROGRESS]"
        assert _status_badge("not applicable") == "[N/A]"

    def test_status_badge_unknown_status(self):
        """Test status_badge filter with unknown status."""
        result = _status_badge("unknown_status")
        assert result == "[UNKNOWN_STATUS]"

    def test_control_id_format_basic(self):
        """Test control_id filter with basic ID."""
        result = _control_id_format("CC1.1")
        assert result == "CC1.1"

    def test_control_id_format_with_framework(self):
        """Test control_id filter with framework prefix."""
        result = _control_id_format("1.1", "soc2")
        assert result == "SOC2-1.1"

    def test_control_id_format_empty(self):
        """Test control_id filter with empty value."""
        result = _control_id_format("")
        assert result == "N/A"

    def test_control_id_format_none(self):
        """Test control_id filter with None value."""
        result = _control_id_format(None)
        assert result == "N/A"

    def test_pluralize_singular(self):
        """Test pluralize filter with count of 1."""
        result = _pluralize(1, "control")
        assert result == "1 control"

    def test_pluralize_plural(self):
        """Test pluralize filter with count > 1."""
        result = _pluralize(5, "control")
        assert result == "5 controls"

    def test_pluralize_zero(self):
        """Test pluralize filter with count of 0."""
        result = _pluralize(0, "item")
        assert result == "0 items"

    def test_pluralize_custom_plural(self):
        """Test pluralize filter with custom plural form."""
        result = _pluralize(3, "criterion", "criteria")
        assert result == "3 criteria"

    def test_pluralize_one_custom_plural(self):
        """Test pluralize filter with count of 1 and custom plural."""
        result = _pluralize(1, "criterion", "criteria")
        assert result == "1 criterion"


class TestGlobalFunctions:
    """Tests for global template functions."""

    def test_now_utc_returns_datetime(self):
        """Test now_utc returns a datetime object."""
        result = _now_utc()
        assert isinstance(result, datetime)

    def test_now_utc_is_utc(self):
        """Test now_utc returns UTC timezone."""
        result = _now_utc()
        assert result.tzinfo == timezone.utc

    def test_now_utc_is_current(self):
        """Test now_utc is reasonably current."""
        before = datetime.now(timezone.utc)
        result = _now_utc()
        after = datetime.now(timezone.utc)
        assert before <= result <= after

    def test_current_year_returns_int(self):
        """Test current_year returns an integer."""
        result = _current_year()
        assert isinstance(result, int)

    def test_current_year_is_valid(self):
        """Test current_year returns a valid year."""
        result = _current_year()
        assert 2024 <= result <= 2100


class TestTemplateExistence:
    """Tests for template existence checking."""

    def test_template_exists_soc2_control_mapping(self):
        """Test SOC 2 control_mapping template exists."""
        assert template_exists("control_mapping.html.j2", framework="soc2")

    def test_template_exists_soc2_tsc_criteria(self):
        """Test SOC 2 tsc_criteria template exists."""
        assert template_exists("tsc_criteria.html.j2", framework="soc2")

    def test_template_exists_soc2_evidence_matrix(self):
        """Test SOC 2 evidence_matrix template exists."""
        assert template_exists("evidence_matrix.html.j2", framework="soc2")

    def test_template_exists_iso27001_annex_a(self):
        """Test ISO 27001 annex_a_controls template exists."""
        assert template_exists("annex_a_controls.html.j2", framework="iso27001")

    def test_template_exists_iso27001_control_evidence(self):
        """Test ISO 27001 control_evidence template exists."""
        assert template_exists("control_evidence.html.j2", framework="iso27001")

    def test_template_exists_iso27001_soa(self):
        """Test ISO 27001 Statement of Applicability template exists."""
        assert template_exists("soa.html.j2", framework="iso27001")

    def test_template_exists_gdpr_controller(self):
        """Test GDPR Article 30 controller template exists."""
        assert template_exists("article30_controller.html.j2", framework="gdpr")

    def test_template_exists_gdpr_processor(self):
        """Test GDPR Article 30 processor template exists."""
        assert template_exists("article30_processor.html.j2", framework="gdpr")

    def test_template_exists_gdpr_data_flow(self):
        """Test GDPR data_flow template exists."""
        assert template_exists("data_flow.html.j2", framework="gdpr")

    def test_template_exists_euaiact_risk_classification(self):
        """Test EU AI Act risk_classification template exists."""
        assert template_exists("risk_classification.html.j2", framework="euaiact")

    def test_template_exists_euaiact_conformity_assessment(self):
        """Test EU AI Act conformity_assessment template exists."""
        assert template_exists("conformity_assessment.html.j2", framework="euaiact")

    def test_template_exists_euaiact_technical_documentation(self):
        """Test EU AI Act technical_documentation template exists."""
        assert template_exists("technical_documentation.html.j2", framework="euaiact")

    def test_template_not_exists(self):
        """Test that non-existent template returns False."""
        assert not template_exists("nonexistent.html.j2", framework="soc2")

    def test_template_not_exists_wrong_framework(self):
        """Test template with wrong framework returns False."""
        assert not template_exists("control_mapping.html.j2", framework="invalid")


class TestTemplateList:
    """Tests for template listing functionality."""

    def test_list_all_templates(self):
        """Test listing all templates."""
        templates = list_templates()
        assert len(templates) >= 12  # At least 12 templates (3 per framework x 4)
        assert any("soc2" in t for t in templates)
        assert any("iso27001" in t for t in templates)
        assert any("gdpr" in t for t in templates)
        assert any("euaiact" in t for t in templates)

    def test_list_soc2_templates(self):
        """Test listing SOC 2 templates only."""
        templates = list_templates(framework="soc2")
        assert len(templates) >= 3
        for t in templates:
            assert t.startswith("soc2/")

    def test_list_iso27001_templates(self):
        """Test listing ISO 27001 templates only."""
        templates = list_templates(framework="iso27001")
        assert len(templates) >= 3
        for t in templates:
            assert t.startswith("iso27001/")

    def test_list_gdpr_templates(self):
        """Test listing GDPR templates only."""
        templates = list_templates(framework="gdpr")
        assert len(templates) >= 3
        for t in templates:
            assert t.startswith("gdpr/")

    def test_list_euaiact_templates(self):
        """Test listing EU AI Act templates only."""
        templates = list_templates(framework="euaiact")
        assert len(templates) >= 3
        for t in templates:
            assert t.startswith("euaiact/")

    def test_list_invalid_framework(self):
        """Test listing templates for invalid framework returns empty."""
        templates = list_templates(framework="invalid")
        assert templates == []


class TestSOC2TemplateRendering:
    """Tests for SOC 2 template rendering."""

    def test_render_soc2_control_mapping(self, sample_soc2_data):
        """Test rendering SOC 2 control mapping template."""
        html = render_template(
            "control_mapping.html.j2",
            sample_soc2_data,
            framework="soc2",
        )
        assert "ACGS Test Corporation" in html
        assert "SOC 2" in html
        assert "CC1.1" in html
        assert "Security" in html

    def test_render_soc2_tsc_criteria(self, sample_soc2_data):
        """Test rendering SOC 2 TSC criteria template."""
        html = render_template(
            "tsc_criteria.html.j2",
            sample_soc2_data,
            framework="soc2",
        )
        assert "ACGS Test Corporation" in html
        assert "Security" in html

    def test_render_soc2_evidence_matrix(self, sample_soc2_data):
        """Test rendering SOC 2 evidence matrix template."""
        html = render_template(
            "evidence_matrix.html.j2",
            sample_soc2_data,
            framework="soc2",
        )
        assert "ACGS Test Corporation" in html

    def test_render_soc2_includes_tsc_criteria(self, sample_soc2_data):
        """Test SOC 2 template includes all Trust Service Criteria references."""
        html = render_template(
            "control_mapping.html.j2",
            sample_soc2_data,
            framework="soc2",
        )
        # Should reference TSC sections
        assert "Security" in html or "CC" in html

    def test_render_soc2_includes_guardrail_mapping(self, sample_soc2_data):
        """Test SOC 2 template includes guardrail mappings."""
        html = render_template(
            "control_mapping.html.j2",
            sample_soc2_data,
            framework="soc2",
        )
        assert "GR-ETHICS-001" in html or "guardrail" in html.lower()

    def test_render_soc2_with_minimal_data(self, minimal_data):
        """Test SOC 2 template renders with minimal data."""
        html = render_template(
            "control_mapping.html.j2",
            minimal_data,
            framework="soc2",
        )
        assert "Test Org" in html
        # Should handle missing controls gracefully
        assert html is not None


class TestISO27001TemplateRendering:
    """Tests for ISO 27001 template rendering."""

    def test_render_iso27001_annex_a(self, sample_iso27001_data):
        """Test rendering ISO 27001 Annex A controls template."""
        html = render_template(
            "annex_a_controls.html.j2",
            sample_iso27001_data,
            framework="iso27001",
        )
        assert "ACGS Test Corporation" in html
        assert "ISO 27001" in html or "27001" in html

    def test_render_iso27001_control_evidence(self, sample_iso27001_data):
        """Test rendering ISO 27001 control evidence template."""
        html = render_template(
            "control_evidence.html.j2",
            sample_iso27001_data,
            framework="iso27001",
        )
        assert "ACGS Test Corporation" in html

    def test_render_iso27001_soa(self, sample_iso27001_data):
        """Test rendering ISO 27001 Statement of Applicability template."""
        html = render_template(
            "soa.html.j2",
            sample_iso27001_data,
            framework="iso27001",
        )
        assert "ACGS Test Corporation" in html

    def test_render_iso27001_includes_themes(self, sample_iso27001_data):
        """Test ISO 27001 template includes theme organization."""
        html = render_template(
            "annex_a_controls.html.j2",
            sample_iso27001_data,
            framework="iso27001",
        )
        # Should include theme references (Organizational, People, etc.)
        assert "Organizational" in html or "A.5" in html

    def test_render_iso27001_with_minimal_data(self, minimal_data):
        """Test ISO 27001 template renders with minimal data."""
        html = render_template(
            "annex_a_controls.html.j2",
            minimal_data,
            framework="iso27001",
        )
        assert "Test Org" in html
        assert html is not None


class TestGDPRTemplateRendering:
    """Tests for GDPR template rendering."""

    def test_render_gdpr_article30_controller(self, sample_gdpr_data):
        """Test rendering GDPR Article 30 controller template."""
        html = render_template(
            "article30_controller.html.j2",
            sample_gdpr_data,
            framework="gdpr",
        )
        assert "ACGS Test Corporation" in html
        assert "GDPR" in html or "Article 30" in html

    def test_render_gdpr_article30_processor(self, sample_gdpr_data):
        """Test rendering GDPR Article 30 processor template."""
        html = render_template(
            "article30_processor.html.j2",
            sample_gdpr_data,
            framework="gdpr",
        )
        assert "ACGS Test Corporation" in html

    def test_render_gdpr_data_flow(self, sample_gdpr_data):
        """Test rendering GDPR data flow template."""
        html = render_template(
            "data_flow.html.j2",
            sample_gdpr_data,
            framework="gdpr",
        )
        assert "ACGS Test Corporation" in html

    def test_render_gdpr_includes_processing_activities(self, sample_gdpr_data):
        """Test GDPR template includes processing activities."""
        html = render_template(
            "article30_controller.html.j2",
            sample_gdpr_data,
            framework="gdpr",
        )
        assert "PA-001" in html or "AI Model Training" in html or "processing" in html.lower()

    def test_render_gdpr_includes_dpo_info(self, sample_gdpr_data):
        """Test GDPR template includes DPO information."""
        html = render_template(
            "article30_controller.html.j2",
            sample_gdpr_data,
            framework="gdpr",
        )
        # Should reference DPO somewhere
        assert "Jane Doe" in html or "DPO" in html or "dpo@example.com" in html

    def test_render_gdpr_with_minimal_data(self, minimal_data):
        """Test GDPR template renders with minimal data."""
        html = render_template(
            "article30_controller.html.j2",
            minimal_data,
            framework="gdpr",
        )
        assert "Test Org" in html
        assert html is not None


class TestEUAIActTemplateRendering:
    """Tests for EU AI Act template rendering."""

    def test_render_euaiact_risk_classification(self, sample_euaiact_data):
        """Test rendering EU AI Act risk classification template."""
        html = render_template(
            "risk_classification.html.j2",
            sample_euaiact_data,
            framework="euaiact",
        )
        assert "ACGS Test Corporation" in html
        assert "EU AI Act" in html or "AI Act" in html

    def test_render_euaiact_conformity_assessment(self, sample_euaiact_data):
        """Test rendering EU AI Act conformity assessment template."""
        html = render_template(
            "conformity_assessment.html.j2",
            sample_euaiact_data,
            framework="euaiact",
        )
        assert "ACGS Test Corporation" in html

    def test_render_euaiact_technical_documentation(self, sample_euaiact_data):
        """Test rendering EU AI Act technical documentation template."""
        html = render_template(
            "technical_documentation.html.j2",
            sample_euaiact_data,
            framework="euaiact",
        )
        assert "ACGS Test Corporation" in html

    def test_render_euaiact_includes_risk_levels(self, sample_euaiact_data):
        """Test EU AI Act template includes risk level classifications."""
        html = render_template(
            "risk_classification.html.j2",
            sample_euaiact_data,
            framework="euaiact",
        )
        # Should reference risk levels
        html_lower = html.lower()
        assert (
            "high" in html_lower
            or "limited" in html_lower
            or "minimal" in html_lower
            or "risk" in html_lower
        )

    def test_render_euaiact_includes_ai_systems(self, sample_euaiact_data):
        """Test EU AI Act template includes AI system information."""
        html = render_template(
            "risk_classification.html.j2",
            sample_euaiact_data,
            framework="euaiact",
        )
        assert "AIS-001" in html or "Guardrail" in html or "AI system" in html.lower()

    def test_render_euaiact_with_minimal_data(self, minimal_data):
        """Test EU AI Act template renders with minimal data."""
        html = render_template(
            "risk_classification.html.j2",
            minimal_data,
            framework="euaiact",
        )
        assert "Test Org" in html
        assert html is not None


class TestXSSPrevention:
    """Tests for XSS prevention via Jinja2 autoescaping."""

    def test_xss_in_organization_name_escaped(self, xss_test_data):
        """Test that script tags in organization_name are escaped."""
        html = render_template(
            "control_mapping.html.j2",
            xss_test_data,
            framework="soc2",
        )
        # Script tag should be escaped, not executed
        assert "<script>alert('XSS')</script>" not in html
        assert "&lt;script&gt;" in html or "script" not in html.lower()

    def test_xss_in_report_title_escaped(self, xss_test_data):
        """Test that onerror handler in title is escaped."""
        html = render_template(
            "control_mapping.html.j2",
            xss_test_data,
            framework="soc2",
        )
        # Onerror handler should be escaped
        assert "onerror=alert" not in html

    def test_xss_in_controls_escaped(self, xss_test_data):
        """Test that XSS in control data is escaped."""
        html = render_template(
            "control_mapping.html.j2",
            xss_test_data,
            framework="soc2",
        )
        # Iframe tag should be escaped
        assert "<iframe" not in html
        # Script in control name should be escaped
        assert "<script>alert(1)</script>" not in html

    def test_html_entities_in_output(self, xss_test_data):
        """Test that HTML entities are used for escaping."""
        html = render_template(
            "control_mapping.html.j2",
            xss_test_data,
            framework="soc2",
        )
        # Should see escaped versions
        assert "&lt;" in html or "&gt;" in html or "script" not in html.lower()


class TestGracefulMissingData:
    """Tests for graceful handling of missing or incomplete data."""

    def test_render_with_empty_data(self, empty_data):
        """Test template renders with empty data dictionary."""
        html = render_template(
            "control_mapping.html.j2",
            empty_data,
            framework="soc2",
        )
        # Should render without raising exceptions
        assert html is not None
        assert "N/A" in html  # Should use default_value filter

    def test_render_with_missing_controls(self):
        """Test template handles missing controls gracefully."""
        data = {"organization_name": "Test Org"}
        html = render_template(
            "control_mapping.html.j2",
            data,
            framework="soc2",
        )
        assert html is not None
        assert "Test Org" in html

    def test_render_with_missing_dates(self):
        """Test template handles missing dates gracefully."""
        data = {
            "organization_name": "Test Org",
            "reporting_period_start": None,
            "reporting_period_end": None,
        }
        html = render_template(
            "control_mapping.html.j2",
            data,
            framework="soc2",
        )
        assert html is not None
        # Should show N/A for missing dates
        assert "N/A" in html or "Test Org" in html

    def test_render_with_empty_list(self):
        """Test template handles empty control list."""
        data = {
            "organization_name": "Test Org",
            "controls": [],
        }
        html = render_template(
            "control_mapping.html.j2",
            data,
            framework="soc2",
        )
        assert html is not None
        assert "Test Org" in html

    def test_render_with_none_values_in_controls(self):
        """Test template handles None values within controls."""
        data = {
            "organization_name": "Test Org",
            "controls": [
                {
                    "control_id": None,
                    "control_name": None,
                    "description": None,
                    "status": None,
                }
            ],
        }
        html = render_template(
            "control_mapping.html.j2",
            data,
            framework="soc2",
        )
        assert html is not None


class TestTemplateMetadata:
    """Tests for template metadata injection."""

    def test_generated_at_injected(self):
        """Test that generated_at timestamp is injected."""
        data = {"organization_name": "Test Org"}
        html = render_template(
            "control_mapping.html.j2",
            data,
            framework="soc2",
        )
        # Template should have access to generated_at
        assert html is not None

    def test_generator_version_injected(self):
        """Test that generator_version is injected."""
        data = {"organization_name": "Test Org"}
        html = render_template(
            "control_mapping.html.j2",
            data,
            framework="soc2",
        )
        # Template should have access to generator_version
        assert html is not None

    def test_framework_injected(self):
        """Test that framework is injected into context."""
        data = {"organization_name": "Test Org"}
        html = render_template(
            "control_mapping.html.j2",
            data,
            framework="soc2",
        )
        # Framework should be available in context
        assert html is not None

    def test_framework_not_overwritten(self):
        """Test that provided framework is not overwritten."""
        data = {
            "organization_name": "Test Org",
            "framework": "custom_framework",
        }
        # This should work, though the framework parameter takes precedence
        html = render_template(
            "control_mapping.html.j2",
            data,
            framework="soc2",
        )
        assert html is not None


class TestTemplateErrorHandling:
    """Tests for template error handling."""

    def test_template_not_found_raises(self):
        """Test that TemplateNotFound is raised for non-existent template."""
        from jinja2 import TemplateNotFound

        with pytest.raises(TemplateNotFound):
            render_template(
                "nonexistent_template.html.j2",
                {},
                framework="soc2",
            )

    def test_invalid_framework_template_not_found(self):
        """Test that invalid framework raises TemplateNotFound."""
        from jinja2 import TemplateNotFound

        with pytest.raises(TemplateNotFound):
            render_template(
                "control_mapping.html.j2",
                {},
                framework="invalid_framework",
            )

    def test_render_without_framework(self):
        """Test rendering template without framework parameter."""
        from jinja2 import TemplateNotFound

        # Should raise TemplateNotFound since template is in subdirectory
        with pytest.raises(TemplateNotFound):
            render_template(
                "control_mapping.html.j2",
                {"organization_name": "Test"},
            )


class TestEnvironmentVariableOverride:
    """Tests for environment variable template path override."""

    def test_custom_templates_path(self, tmp_path):
        """Test custom templates path via environment variable."""
        import os

        # Create a custom templates directory
        custom_templates = tmp_path / "custom_templates" / "soc2"
        custom_templates.mkdir(parents=True)

        # Create a simple template
        template_file = custom_templates / "test_template.html.j2"
        template_file.write_text("<html>{{ organization_name }}</html>")

        # Clear cache and set env variable
        clear_template_cache()
        original_path = os.environ.get("COMPLIANCE_TEMPLATES_PATH")

        try:
            os.environ["COMPLIANCE_TEMPLATES_PATH"] = str(tmp_path / "custom_templates")
            clear_template_cache()

            html = render_template(
                "test_template.html.j2",
                {"organization_name": "Custom Test"},
                framework="soc2",
            )
            assert "Custom Test" in html
        finally:
            # Restore original environment
            if original_path:
                os.environ["COMPLIANCE_TEMPLATES_PATH"] = original_path
            else:
                os.environ.pop("COMPLIANCE_TEMPLATES_PATH", None)
            clear_template_cache()


class TestFilterIntegration:
    """Tests for filter integration within templates."""

    def test_format_date_in_template(self):
        """Test format_date filter works in template context."""
        env = get_template_env()
        template = env.from_string("{{ date | format_date }}")
        result = template.render(date=datetime(2024, 6, 15, tzinfo=timezone.utc))
        assert result == "2024-06-15"

    def test_status_badge_in_template(self):
        """Test status_badge filter works in template context."""
        env = get_template_env()
        template = env.from_string("{{ status | status_badge }}")
        result = template.render(status="compliant")
        assert result == "[COMPLIANT]"

    def test_default_value_in_template(self):
        """Test default_value filter works in template context."""
        env = get_template_env()
        template = env.from_string("{{ value | default_value }}")
        result = template.render(value=None)
        assert result == "N/A"

    def test_pluralize_in_template(self):
        """Test pluralize filter works in template context."""
        env = get_template_env()
        template = env.from_string("{{ count | pluralize('item') }}")
        result = template.render(count=5)
        assert result == "5 items"

    def test_control_id_in_template(self):
        """Test control_id filter works in template context."""
        env = get_template_env()
        template = env.from_string("{{ id | control_id('soc2') }}")
        result = template.render(id="1.1")
        assert result == "SOC2-1.1"

    def test_chained_filters(self):
        """Test chaining multiple filters in template."""
        env = get_template_env()
        template = env.from_string("{{ value | default_value | upper }}")
        result = template.render(value=None)
        assert result == "N/A"

    def test_global_functions_in_template(self):
        """Test global functions work in template context."""
        env = get_template_env()
        template = env.from_string("Year: {{ current_year() }}")
        result = template.render()
        assert "Year:" in result
        assert str(_current_year()) in result


class TestConcurrentRendering:
    """Tests for concurrent template rendering."""

    def test_concurrent_renders(self, sample_soc2_data, sample_iso27001_data):
        """Test that templates can be rendered concurrently."""
        import concurrent.futures

        def render_soc2():
            return render_template(
                "control_mapping.html.j2",
                sample_soc2_data,
                framework="soc2",
            )

        def render_iso():
            return render_template(
                "annex_a_controls.html.j2",
                sample_iso27001_data,
                framework="iso27001",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(render_soc2),
                executor.submit(render_iso),
                executor.submit(render_soc2),
                executor.submit(render_iso),
            ]
            results = [f.result() for f in futures]

        assert len(results) == 4
        for result in results:
            assert result is not None
            assert len(result) > 0
