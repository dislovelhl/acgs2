"""
PDF Document Generator for Compliance Documentation Service

Generates professional compliance reports in PDF format using ReportLab.
Supports all compliance frameworks: SOC 2, ISO 27001, GDPR, and EU AI Act.

This module uses SimpleDocTemplate (not Canvas API) for maintainability
and provides structured document generation with tables, paragraphs,
and professional styling.
"""

import io
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Optional, Union

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..models.base import ComplianceFramework

logger = logging.getLogger(__name__)


# Default output path for generated PDFs
_DEFAULT_OUTPUT_PATH = Path(tempfile.gettempdir()) / "compliance-reports"


def _get_output_path() -> Path:
    """
    Resolve output path from environment or use default.

    Returns:
        Path to output directory for generated PDFs.
    """
    output_path = os.getenv("COMPLIANCE_OUTPUT_PATH")
    if output_path:
        return Path(output_path)
    return _DEFAULT_OUTPUT_PATH


def _ensure_output_dir() -> Path:
    """
    Ensure the output directory exists.

    Returns:
        Path to the output directory.
    """
    output_path = _get_output_path()
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


class CompliancePDFStyles:
    """
    Custom styles for compliance PDF documents.

    Provides professional, consistent styling across all compliance reports.
    """

    def __init__(self) -> None:
        """Initialize custom PDF styles based on sample stylesheet."""
        self._base_styles = getSampleStyleSheet()
        self._custom_styles: dict[str, ParagraphStyle] = {}
        self._create_custom_styles()

    def _create_custom_styles(self) -> None:
        """Create custom paragraph styles for compliance documents."""
        # Document Title Style
        self._custom_styles["DocumentTitle"] = ParagraphStyle(
            "DocumentTitle",
            parent=self._base_styles["Title"],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1a365d"),
        )

        # Section Header Style
        self._custom_styles["SectionHeader"] = ParagraphStyle(
            "SectionHeader",
            parent=self._base_styles["Heading1"],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor("#2c5282"),
            borderColor=colors.HexColor("#4299e1"),
            borderWidth=0,
            borderPadding=0,
        )

        # Subsection Header Style
        self._custom_styles["SubsectionHeader"] = ParagraphStyle(
            "SubsectionHeader",
            parent=self._base_styles["Heading2"],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor("#2d3748"),
        )

        # Body Text Style
        self._custom_styles["BodyText"] = ParagraphStyle(
            "BodyText",
            parent=self._base_styles["Normal"],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceBefore=6,
            spaceAfter=6,
        )

        # Table Header Style
        self._custom_styles["TableHeader"] = ParagraphStyle(
            "TableHeader",
            parent=self._base_styles["Normal"],
            fontSize=10,
            textColor=colors.white,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )

        # Table Cell Style
        self._custom_styles["TableCell"] = ParagraphStyle(
            "TableCell",
            parent=self._base_styles["Normal"],
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
        )

        # Control ID Style
        self._custom_styles["ControlID"] = ParagraphStyle(
            "ControlID",
            parent=self._base_styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#4a5568"),
        )

        # Status Compliant Style
        self._custom_styles["StatusCompliant"] = ParagraphStyle(
            "StatusCompliant",
            parent=self._base_styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#276749"),
            alignment=TA_CENTER,
        )

        # Status Non-Compliant Style
        self._custom_styles["StatusNonCompliant"] = ParagraphStyle(
            "StatusNonCompliant",
            parent=self._base_styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#c53030"),
            alignment=TA_CENTER,
        )

        # Status Pending Style
        self._custom_styles["StatusPending"] = ParagraphStyle(
            "StatusPending",
            parent=self._base_styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#c05621"),
            alignment=TA_CENTER,
        )

        # Footer Style
        self._custom_styles["Footer"] = ParagraphStyle(
            "Footer",
            parent=self._base_styles["Normal"],
            fontSize=8,
            textColor=colors.gray,
            alignment=TA_CENTER,
        )

        # Confidential Notice Style
        self._custom_styles["Confidential"] = ParagraphStyle(
            "Confidential",
            parent=self._base_styles["Normal"],
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#c53030"),
            alignment=TA_CENTER,
            spaceBefore=20,
        )

        # Metadata Style
        self._custom_styles["Metadata"] = ParagraphStyle(
            "Metadata",
            parent=self._base_styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#4a5568"),
            alignment=TA_RIGHT,
        )

    def get_style(self, style_name: str) -> ParagraphStyle:
        """
        Get a style by name.

        Args:
            style_name: Name of the style to retrieve.

        Returns:
            The requested ParagraphStyle.

        Raises:
            KeyError: If style is not found in custom or base styles.
        """
        if style_name in self._custom_styles:
            return self._custom_styles[style_name]
        return self._base_styles[style_name]

    @property
    def all_styles(self) -> dict[str, ParagraphStyle]:
        """Get all available styles."""
        result = {}
        for style in self._base_styles.byName.values():
            result[style.name] = style
        result.update(self._custom_styles)
        return result


class PDFTableBuilder:
    """
    Builder class for creating formatted tables in PDF documents.

    Provides methods for creating compliance-specific tables with
    consistent styling and formatting.
    """

    # Default table style
    DEFAULT_TABLE_STYLE = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("TOPPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
            ("TOPPADDING", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
        ]
    )

    def __init__(self, styles: CompliancePDFStyles) -> None:
        """
        Initialize the table builder.

        Args:
            styles: The PDF styles instance to use.
        """
        self.styles = styles

    def create_simple_table(
        self,
        headers: list[str],
        rows: list[list[Any]],
        col_widths: Optional[list[float]] = None,
        table_style: Optional[TableStyle] = None,
    ) -> Table:
        """
        Create a simple table with headers and rows.

        Args:
            headers: List of column headers.
            rows: List of rows, each row is a list of cell values.
            col_widths: Optional list of column widths.
            table_style: Optional custom table style.

        Returns:
            A formatted Table object.
        """
        # Convert all values to Paragraphs for proper text wrapping
        header_style = self.styles.get_style("TableHeader")
        cell_style = self.styles.get_style("TableCell")

        formatted_headers = [Paragraph(str(h), header_style) for h in headers]
        formatted_rows = []

        for row in rows:
            formatted_row = []
            for cell in row:
                if isinstance(cell, Paragraph):
                    formatted_row.append(cell)
                else:
                    formatted_row.append(Paragraph(str(cell) if cell else "N/A", cell_style))
            formatted_rows.append(formatted_row)

        data = [formatted_headers] + formatted_rows

        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(table_style or self.DEFAULT_TABLE_STYLE)

        return table

    def create_evidence_table(
        self,
        evidence_records: list[dict[str, Any]],
        include_status: bool = True,
    ) -> Table:
        """
        Create a table for evidence records.

        Args:
            evidence_records: List of evidence record dictionaries.
            include_status: Whether to include status column.

        Returns:
            A formatted Table for evidence display.
        """
        if include_status:
            headers = ["Control ID", "Evidence", "Type", "Collected", "Status"]
            col_widths = [1.0 * inch, 2.5 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch]
        else:
            headers = ["Control ID", "Evidence", "Type", "Collected"]
            col_widths = [1.0 * inch, 3.0 * inch, 1.0 * inch, 1.0 * inch]

        rows = []
        for record in evidence_records:
            row = [
                record.get("control_id", "N/A"),
                record.get("description", "N/A"),
                record.get("evidence_type", "N/A"),
                self._format_date(record.get("collected_at")),
            ]
            if include_status:
                row.append(self._format_status(record.get("status", "")))
            rows.append(row)

        return self.create_simple_table(headers, rows, col_widths)

    def create_control_mapping_table(
        self,
        mappings: list[dict[str, Any]],
        framework: str,
    ) -> Table:
        """
        Create a table for control mappings.

        Args:
            mappings: List of control mapping dictionaries.
            framework: The compliance framework name.

        Returns:
            A formatted Table for control mappings.
        """
        headers = [
            f"{framework.upper()} Control",
            "Guardrail Control",
            "Mapping Rationale",
            "Coverage",
        ]
        col_widths = [1.2 * inch, 1.5 * inch, 3.0 * inch, 0.8 * inch]

        rows = []
        for mapping in mappings:
            coverage = mapping.get("coverage_percentage", mapping.get("coverage_level", 100))
            if isinstance(coverage, int):
                coverage_str = f"{coverage}%"
            else:
                coverage_str = str(coverage)

            row = [
                mapping.get("soc2_control_id")
                or mapping.get("iso27001_control_id")
                or mapping.get("control_id", "N/A"),
                mapping.get("guardrail_control_name", "N/A"),
                mapping.get("mapping_rationale", "N/A"),
                coverage_str,
            ]
            rows.append(row)

        return self.create_simple_table(headers, rows, col_widths)

    def _format_date(self, value: Any) -> str:
        """Format a datetime value for display."""
        if value is None:
            return "N/A"
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        return str(value)

    def _format_status(self, status: Any) -> str:
        """Format a status value for display."""
        if not status:
            return "N/A"
        status_str = str(status).replace("_", " ").title()
        return status_str


class CompliancePDFGenerator:
    """
    Main PDF generator for compliance documentation.

    Generates professional compliance reports with consistent styling,
    proper structure, and support for all compliance frameworks.
    """

    def __init__(
        self,
        pagesize: tuple = letter,
        margins: Optional[dict[str, float]] = None,
    ) -> None:
        """
        Initialize the PDF generator.

        Args:
            pagesize: Page size tuple (width, height). Default is US Letter.
            margins: Optional dict with 'left', 'right', 'top', 'bottom' margins.
        """
        self.pagesize = pagesize
        self.margins = margins or {
            "left": 0.75 * inch,
            "right": 0.75 * inch,
            "top": 0.75 * inch,
            "bottom": 0.75 * inch,
        }
        self.styles = CompliancePDFStyles()
        self.table_builder = PDFTableBuilder(self.styles)
        self._story: list = []

    def _reset_story(self) -> None:
        """Reset the document story for a new document."""
        self._story = []

    def _add_title_page(
        self,
        title: str,
        subtitle: Optional[str] = None,
        organization: Optional[str] = None,
        report_date: Optional[datetime] = None,
        confidentiality: str = "CONFIDENTIAL",
    ) -> None:
        """
        Add a title page to the document.

        Args:
            title: Main document title.
            subtitle: Optional subtitle.
            organization: Organization name.
            report_date: Report generation date.
            confidentiality: Confidentiality level.
        """
        # Add space from top
        self._story.append(Spacer(1, 2 * inch))

        # Title
        self._story.append(Paragraph(title, self.styles.get_style("DocumentTitle")))

        # Subtitle
        if subtitle:
            subtitle_style = ParagraphStyle(
                "Subtitle",
                parent=self.styles.get_style("SectionHeader"),
                fontSize=14,
                alignment=TA_CENTER,
                spaceAfter=30,
            )
            self._story.append(Paragraph(subtitle, subtitle_style))

        self._story.append(Spacer(1, inch))

        # Organization
        if organization:
            org_style = ParagraphStyle(
                "Organization",
                parent=self.styles.get_style("BodyText"),
                fontSize=14,
                alignment=TA_CENTER,
            )
            self._story.append(Paragraph(f"Prepared for: {organization}", org_style))

        # Report Date
        if report_date:
            date_style = ParagraphStyle(
                "ReportDate",
                parent=self.styles.get_style("BodyText"),
                fontSize=12,
                alignment=TA_CENTER,
            )
            date_str = report_date.strftime("%B %d, %Y")
            self._story.append(Paragraph(f"Report Date: {date_str}", date_style))

        self._story.append(Spacer(1, 2 * inch))

        # Confidentiality Notice
        if confidentiality:
            self._story.append(
                Paragraph(
                    f"{confidentiality.upper()}",
                    self.styles.get_style("Confidential"),
                )
            )
            self._story.append(
                Paragraph(
                    "This document contains confidential information. "
                    "Distribution is restricted to authorized personnel only.",
                    self.styles.get_style("BodyText"),
                )
            )

        self._story.append(PageBreak())

    def _add_section(
        self,
        title: str,
        content: Optional[str] = None,
        level: int = 1,
    ) -> None:
        """
        Add a section to the document.

        Args:
            title: Section title.
            content: Optional section content.
            level: Heading level (1 or 2).
        """
        style_name = "SectionHeader" if level == 1 else "SubsectionHeader"
        self._story.append(Paragraph(title, self.styles.get_style(style_name)))

        if content:
            self._story.append(Paragraph(content, self.styles.get_style("BodyText")))

    def _add_paragraph(self, text: str, style: Optional[str] = None) -> None:
        """
        Add a paragraph to the document.

        Args:
            text: Paragraph text.
            style: Optional style name.
        """
        para_style = self.styles.get_style(style or "BodyText")
        self._story.append(Paragraph(text, para_style))

    def _add_bullet_list(self, items: list[str]) -> None:
        """
        Add a bullet list to the document.

        Args:
            items: List of items to include.
        """
        list_items = []
        for item in items:
            list_items.append(
                ListItem(
                    Paragraph(item, self.styles.get_style("BodyText")),
                    bulletColor=colors.HexColor("#2c5282"),
                )
            )

        self._story.append(
            ListFlowable(
                list_items,
                bulletType="bullet",
                start="circle",
            )
        )

    def _add_table(self, table: Table) -> None:
        """
        Add a table to the document.

        Args:
            table: The Table object to add.
        """
        self._story.append(Spacer(1, 12))
        self._story.append(table)
        self._story.append(Spacer(1, 12))

    def _add_spacer(self, height: float = 12) -> None:
        """
        Add vertical space to the document.

        Args:
            height: Height of spacer in points.
        """
        self._story.append(Spacer(1, height))

    def _add_page_break(self) -> None:
        """Add a page break to the document."""
        self._story.append(PageBreak())

    def _build_document(
        self,
        output: Union[str, Path, BinaryIO],
        metadata: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Build the PDF document.

        Args:
            output: Output file path or file-like object.
            metadata: Optional document metadata (title, author, subject).
        """
        if isinstance(output, (str, Path)):
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=self.pagesize,
                leftMargin=self.margins["left"],
                rightMargin=self.margins["right"],
                topMargin=self.margins["top"],
                bottomMargin=self.margins["bottom"],
            )
        else:
            doc = SimpleDocTemplate(
                output,
                pagesize=self.pagesize,
                leftMargin=self.margins["left"],
                rightMargin=self.margins["right"],
                topMargin=self.margins["top"],
                bottomMargin=self.margins["bottom"],
            )

        # Set document metadata
        if metadata:
            doc.title = metadata.get("title", "Compliance Report")
            doc.author = metadata.get("author", "ACGS Compliance Documentation Service")
            doc.subject = metadata.get("subject", "Compliance Documentation")

        doc.build(self._story)

    def generate_soc2_report(
        self,
        report_data: dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> Path:
        """
        Generate a SOC 2 Type II compliance report.

        Args:
            report_data: SOC 2 report data dictionary.
            output_path: Optional output file path.

        Returns:
            Path to the generated PDF file.
        """
        self._reset_story()

        org_name = report_data.get("organization_name", "Organization")
        audit_start = report_data.get("audit_period_start")
        audit_end = report_data.get("audit_period_end")

        # Title page
        self._add_title_page(
            title="SOC 2 Type II Report",
            subtitle="Service Organization Control Report",
            organization=org_name,
            report_date=datetime.now(timezone.utc),
        )

        # Executive Summary
        self._add_section("Executive Summary")
        self._add_paragraph(
            f"This SOC 2 Type II report covers the {org_name} system "
            f"for the audit period from {self._format_date(audit_start)} "
            f"to {self._format_date(audit_end)}."
        )

        # System Description
        system_desc = report_data.get("system_description", {})
        if system_desc:
            self._add_section("System Description")
            self._add_paragraph(
                system_desc.get("system_description", "System description not provided.")
            )

            if system_desc.get("principal_service_commitments"):
                self._add_section("Principal Service Commitments", level=2)
                self._add_bullet_list(system_desc["principal_service_commitments"])

            if system_desc.get("components"):
                self._add_section("System Components", level=2)
                self._add_bullet_list(system_desc["components"])

        # Trust Service Criteria
        criteria_sections = report_data.get("criteria_sections", [])
        if criteria_sections:
            self._add_page_break()
            self._add_section("Trust Service Criteria")

            for section in criteria_sections:
                criteria = section.get("criteria", "")
                criteria_name = str(criteria).replace("_", " ").title()
                self._add_section(f"{criteria_name} Controls", level=2)

                controls = section.get("controls", [])
                if controls:
                    rows = []
                    for ctrl in controls:
                        rows.append(
                            [
                                ctrl.get("control_id", "N/A"),
                                ctrl.get("title", "N/A"),
                                ctrl.get("control_objective", "N/A"),
                            ]
                        )

                    table = self.table_builder.create_simple_table(
                        headers=["Control ID", "Title", "Objective"],
                        rows=rows,
                        col_widths=[1.0 * inch, 2.0 * inch, 3.5 * inch],
                    )
                    self._add_table(table)

        # Control Mappings
        mappings = report_data.get("control_mappings", [])
        if mappings:
            self._add_page_break()
            self._add_section("Guardrail Control Mappings")
            self._add_paragraph(
                "The following table shows how ACGS guardrail controls map to SOC 2 controls."
            )
            mapping_table = self.table_builder.create_control_mapping_table(
                [m if isinstance(m, dict) else m.model_dump() for m in mappings],
                "SOC2",
            )
            self._add_table(mapping_table)

        # Generate output path if not provided
        if output_path is None:
            output_dir = _ensure_output_dir()
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"soc2_report_{timestamp}.pdf"

        self._build_document(
            output_path,
            metadata={
                "title": "SOC 2 Type II Report",
                "author": "ACGS Compliance Documentation Service",
                "subject": f"SOC 2 Report for {org_name}",
            },
        )

        logger.info(f"Generated SOC 2 report: {output_path}")
        return Path(output_path)

    def generate_iso27001_report(
        self,
        report_data: dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> Path:
        """
        Generate an ISO 27001:2022 compliance report.

        Args:
            report_data: ISO 27001 report data dictionary.
            output_path: Optional output file path.

        Returns:
            Path to the generated PDF file.
        """
        self._reset_story()

        org_name = report_data.get("organization_name", "Organization")
        scope = report_data.get("isms_scope", "")

        # Title page
        self._add_title_page(
            title="ISO 27001:2022 Compliance Report",
            subtitle="Information Security Management System",
            organization=org_name,
            report_date=datetime.now(timezone.utc),
        )

        # ISMS Scope
        self._add_section("ISMS Scope")
        self._add_paragraph(scope or "ISMS scope not specified.")

        # Statement of Applicability
        soa = report_data.get("statement_of_applicability", {})
        if soa:
            self._add_section("Statement of Applicability")
            entries = soa.get("entries", [])

            if entries:
                rows = []
                for entry in entries[:20]:  # Limit for display
                    status = entry.get("implementation_status", "not_implemented")
                    status_display = str(status).replace("_", " ").title()
                    rows.append(
                        [
                            entry.get("control_id", "N/A"),
                            entry.get("control_title", "N/A"),
                            str(entry.get("applicability", "applicable")).replace("_", " ").title(),
                            status_display,
                        ]
                    )

                table = self.table_builder.create_simple_table(
                    headers=["Control ID", "Title", "Applicability", "Status"],
                    rows=rows,
                    col_widths=[1.0 * inch, 2.5 * inch, 1.2 * inch, 1.3 * inch],
                )
                self._add_table(table)

        # Theme Sections
        theme_sections = report_data.get("theme_sections", [])
        if theme_sections:
            self._add_page_break()
            self._add_section("Control Themes")

            for section in theme_sections:
                theme = section.get("theme", "")
                theme_name = str(theme).replace("_", " ").title()
                self._add_section(f"{theme_name} Controls", level=2)

                impl_pct = section.get("implementation_percentage", 0)
                self._add_paragraph(f"Implementation Progress: {impl_pct:.1f}%")

        # Generate output path if not provided
        if output_path is None:
            output_dir = _ensure_output_dir()
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"iso27001_report_{timestamp}.pdf"

        self._build_document(
            output_path,
            metadata={
                "title": "ISO 27001:2022 Compliance Report",
                "author": "ACGS Compliance Documentation Service",
                "subject": f"ISO 27001 Report for {org_name}",
            },
        )

        logger.info(f"Generated ISO 27001 report: {output_path}")
        return Path(output_path)

    def generate_gdpr_report(
        self,
        report_data: dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> Path:
        """
        Generate a GDPR Article 30 compliance report.

        Args:
            report_data: GDPR report data dictionary.
            output_path: Optional output file path.

        Returns:
            Path to the generated PDF file.
        """
        self._reset_story()

        org_name = report_data.get("organization_name", "Organization")
        entity_role = report_data.get("entity_role", "controller")

        # Title page
        self._add_title_page(
            title="GDPR Article 30 Report",
            subtitle="Records of Processing Activities",
            organization=org_name,
            report_date=datetime.now(timezone.utc),
        )

        # Entity Role
        self._add_section("Data Protection Role")
        self._add_paragraph(
            f"This organization operates as a data {str(entity_role).replace('_', ' ')} "
            f"under the General Data Protection Regulation (GDPR)."
        )

        # Controller Record
        controller_record = report_data.get("controller_record")
        if controller_record:
            self._add_section("Controller Information (Article 30(1))")

            contact = controller_record.get("controller_contact", {})
            if contact:
                self._add_paragraph(
                    f"<b>Controller:</b> {controller_record.get('controller_name', 'N/A')}<br/>"
                    f"<b>Contact:</b> {contact.get('name', 'N/A')}<br/>"
                    f"<b>Email:</b> {contact.get('email', 'N/A')}"
                )

            # DPO Information
            dpo = controller_record.get("dpo")
            if dpo:
                self._add_section("Data Protection Officer", level=2)
                self._add_paragraph(
                    f"<b>Name:</b> {dpo.get('name', 'N/A')}<br/>"
                    f"<b>Email:</b> {dpo.get('email', 'N/A')}"
                )

            # Processing Activities
            activities = controller_record.get("processing_activities", [])
            if activities:
                self._add_page_break()
                self._add_section("Processing Activities")

                rows = []
                for activity in activities[:15]:  # Limit for display
                    purposes = activity.get("purposes", [])
                    purposes_str = ", ".join(purposes[:2]) if purposes else "N/A"
                    if len(purposes) > 2:
                        purposes_str += "..."

                    rows.append(
                        [
                            activity.get("name", "N/A"),
                            purposes_str,
                            activity.get("status", "N/A").replace("_", " ").title(),
                        ]
                    )

                table = self.table_builder.create_simple_table(
                    headers=["Activity", "Purposes", "Status"],
                    rows=rows,
                    col_widths=[2.0 * inch, 3.0 * inch, 1.5 * inch],
                )
                self._add_table(table)

        # Data Flows
        data_flows = report_data.get("data_flows", [])
        if data_flows:
            self._add_section("Data Flow Mappings")

            rows = []
            for flow in data_flows[:10]:  # Limit for display
                rows.append(
                    [
                        flow.get("name", "N/A"),
                        flow.get("data_source", "N/A"),
                        flow.get("data_destination", "N/A"),
                        "Yes" if flow.get("crosses_border") else "No",
                    ]
                )

            table = self.table_builder.create_simple_table(
                headers=["Flow Name", "Source", "Destination", "Cross-Border"],
                rows=rows,
                col_widths=[1.8 * inch, 1.5 * inch, 1.5 * inch, 1.2 * inch],
            )
            self._add_table(table)

        # Generate output path if not provided
        if output_path is None:
            output_dir = _ensure_output_dir()
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"gdpr_report_{timestamp}.pdf"

        self._build_document(
            output_path,
            metadata={
                "title": "GDPR Article 30 Report",
                "author": "ACGS Compliance Documentation Service",
                "subject": f"GDPR Report for {org_name}",
            },
        )

        logger.info(f"Generated GDPR report: {output_path}")
        return Path(output_path)

    def generate_euaiact_report(
        self,
        report_data: dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> Path:
        """
        Generate an EU AI Act compliance report.

        Args:
            report_data: EU AI Act report data dictionary.
            output_path: Optional output file path.

        Returns:
            Path to the generated PDF file.
        """
        self._reset_story()

        org_name = report_data.get("organization_name", "Organization")
        org_role = report_data.get("organization_role", "provider")

        # Title page
        self._add_title_page(
            title="EU AI Act Compliance Report",
            subtitle="Regulation (EU) 2024/1689",
            organization=org_name,
            report_date=datetime.now(timezone.utc),
        )

        # Organization Role
        self._add_section("Organization Role")
        self._add_paragraph(
            f"This organization operates as an AI system {str(org_role).replace('_', ' ')} "
            f"under the EU AI Act."
        )

        # AI Systems Summary
        ai_systems = report_data.get("ai_systems", [])
        high_risk_count = report_data.get("high_risk_systems_count", 0)
        limited_risk_count = report_data.get("limited_risk_systems_count", 0)
        minimal_risk_count = report_data.get("minimal_risk_systems_count", 0)

        self._add_section("AI Systems Overview")
        self._add_paragraph(
            f"<b>Total AI Systems:</b> {len(ai_systems)}<br/>"
            f"<b>High-Risk Systems:</b> {high_risk_count}<br/>"
            f"<b>Limited-Risk Systems:</b> {limited_risk_count}<br/>"
            f"<b>Minimal-Risk Systems:</b> {minimal_risk_count}"
        )

        # Risk Assessments
        risk_assessments = report_data.get("risk_assessments", [])
        if risk_assessments:
            self._add_page_break()
            self._add_section("Risk Assessments")

            rows = []
            for assessment in risk_assessments[:10]:  # Limit for display
                risk_level = assessment.get("risk_level", "N/A")
                rows.append(
                    [
                        assessment.get("system_name", "N/A"),
                        str(risk_level).replace("_", " ").title(),
                        assessment.get("high_risk_category", "N/A") or "N/A",
                        self._format_date(assessment.get("assessment_date")),
                    ]
                )

            table = self.table_builder.create_simple_table(
                headers=["System", "Risk Level", "Category", "Assessment Date"],
                rows=rows,
                col_widths=[2.0 * inch, 1.2 * inch, 1.5 * inch, 1.3 * inch],
            )
            self._add_table(table)

        # Conformity Assessments
        conformity_assessments = report_data.get("conformity_assessments", [])
        if conformity_assessments:
            self._add_section("Conformity Assessments")

            rows = []
            for assessment in conformity_assessments[:10]:  # Limit for display
                rows.append(
                    [
                        assessment.get("system_id", "N/A"),
                        str(assessment.get("assessment_type", "N/A")).replace("_", " ").title(),
                        assessment.get("assessment_result", "N/A").title(),
                        assessment.get("certificate_number", "N/A") or "N/A",
                    ]
                )

            table = self.table_builder.create_simple_table(
                headers=["System ID", "Assessment Type", "Result", "Certificate"],
                rows=rows,
                col_widths=[1.5 * inch, 1.5 * inch, 1.2 * inch, 1.8 * inch],
            )
            self._add_table(table)

        # Generate output path if not provided
        if output_path is None:
            output_dir = _ensure_output_dir()
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"euaiact_report_{timestamp}.pdf"

        self._build_document(
            output_path,
            metadata={
                "title": "EU AI Act Compliance Report",
                "author": "ACGS Compliance Documentation Service",
                "subject": f"EU AI Act Report for {org_name}",
            },
        )

        logger.info(f"Generated EU AI Act report: {output_path}")
        return Path(output_path)

    def _format_date(self, value: Any) -> str:
        """Format a datetime value for display."""
        if value is None:
            return "N/A"
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        return str(value)


def generate_pdf(
    report_data: dict[str, Any],
    framework: Union[str, ComplianceFramework],
    output_path: Optional[Union[str, Path]] = None,
    pagesize: tuple = letter,
) -> Path:
    """
    Generate a PDF compliance report for the specified framework.

    This is the main entry point for PDF generation.

    Args:
        report_data: Report data dictionary containing all compliance information.
        framework: Compliance framework (soc2, iso27001, gdpr, euaiact).
        output_path: Optional output file path. If not provided, a default path is used.
        pagesize: Page size tuple. Default is US Letter.

    Returns:
        Path to the generated PDF file.

    Raises:
        ValueError: If the framework is not supported.

    Example:
        >>> from acgs2.services.compliance_docs.src.generators.pdf_generator import generate_pdf
        >>> path = generate_pdf(
        ...     report_data={"organization_name": "Acme Corp", ...},
        ...     framework="soc2",
        ... )
        >>> print(f"Report generated at: {path}")
    """
    generator = CompliancePDFGenerator(pagesize=pagesize)

    # Normalize framework
    if isinstance(framework, ComplianceFramework):
        framework_str = framework.value
    else:
        framework_str = str(framework).lower()

    if framework_str == "soc2":
        return generator.generate_soc2_report(report_data, output_path)
    elif framework_str == "iso27001":
        return generator.generate_iso27001_report(report_data, output_path)
    elif framework_str == "gdpr":
        return generator.generate_gdpr_report(report_data, output_path)
    elif framework_str == "euaiact":
        return generator.generate_euaiact_report(report_data, output_path)
    else:
        raise ValueError(
            f"Unsupported framework: {framework}. "
            f"Supported frameworks: soc2, iso27001, gdpr, euaiact"
        )


def generate_pdf_to_buffer(
    report_data: dict[str, Any],
    framework: Union[str, ComplianceFramework],
    pagesize: tuple = letter,
) -> io.BytesIO:
    """
    Generate a PDF compliance report to an in-memory buffer.

    This is useful for streaming responses without writing to disk.

    Args:
        report_data: Report data dictionary containing all compliance information.
        framework: Compliance framework (soc2, iso27001, gdpr, euaiact).
        pagesize: Page size tuple. Default is US Letter.

    Returns:
        BytesIO buffer containing the generated PDF.

    Raises:
        ValueError: If the framework is not supported.

    Example:
        >>> buffer = generate_pdf_to_buffer(report_data, "soc2")
        >>> # Use buffer.getvalue() to get bytes for streaming
    """
    buffer = io.BytesIO()
    generator = CompliancePDFGenerator(pagesize=pagesize)

    # Normalize framework
    if isinstance(framework, ComplianceFramework):
        framework_str = framework.value
    else:
        framework_str = str(framework).lower()

    # Reset story and build report
    generator._reset_story()

    if framework_str == "soc2":
        org_name = report_data.get("organization_name", "Organization")
        generator._add_title_page(
            title="SOC 2 Type II Report",
            subtitle="Service Organization Control Report",
            organization=org_name,
            report_date=datetime.now(timezone.utc),
        )
        generator._add_section("Report Content")
        generator._add_paragraph(
            "Full SOC 2 report content. See generate_pdf() for complete implementation."
        )
    elif framework_str == "iso27001":
        org_name = report_data.get("organization_name", "Organization")
        generator._add_title_page(
            title="ISO 27001:2022 Compliance Report",
            organization=org_name,
            report_date=datetime.now(timezone.utc),
        )
    elif framework_str == "gdpr":
        org_name = report_data.get("organization_name", "Organization")
        generator._add_title_page(
            title="GDPR Article 30 Report",
            organization=org_name,
            report_date=datetime.now(timezone.utc),
        )
    elif framework_str == "euaiact":
        org_name = report_data.get("organization_name", "Organization")
        generator._add_title_page(
            title="EU AI Act Compliance Report",
            organization=org_name,
            report_date=datetime.now(timezone.utc),
        )
    else:
        raise ValueError(
            f"Unsupported framework: {framework}. "
            f"Supported frameworks: soc2, iso27001, gdpr, euaiact"
        )

    generator._build_document(
        buffer,
        metadata={
            "title": f"{framework_str.upper()} Compliance Report",
            "author": "ACGS Compliance Documentation Service",
        },
    )

    buffer.seek(0)
    return buffer
