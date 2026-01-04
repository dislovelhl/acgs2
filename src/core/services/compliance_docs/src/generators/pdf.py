"""
PDF/A document generator using ReportLab
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from pathlib import Path
from typing import Any, Dict

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from .base import BaseGenerator

logger = logging.getLogger(__name__)


class PDFGenerator(BaseGenerator):
    """PDF/A document generator for compliance documents"""

    def __init__(self, output_dir: str = "/app/documents"):
        super().__init__(output_dir)
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab not available, PDF generation will fail")

    def generate(self, data: Dict[str, Any], filename: str) -> Path:
        """
        Generate a PDF document from data.

        Args:
            data: Document data dictionary
            filename: Output filename (without extension)

        Returns:
            Path to generated PDF file
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("ReportLab not available")

        output_path = self._get_output_path(filename, "pdf")

        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )

        # Build story (content)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=1,  # Center
        )

        title = data.get("title", "Compliance Document")
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.2 * inch))

        # Add content based on document type
        doc_type = data.get("document_type", "generic")

        if doc_type == "risk_assessment":
            story.extend(self._build_risk_assessment(data, styles))
        elif doc_type == "human_oversight":
            story.extend(self._build_human_oversight(data, styles))
        elif doc_type == "compliance_checklist":
            story.extend(self._build_compliance_checklist(data, styles))
        elif doc_type == "quarterly_report":
            story.extend(self._build_quarterly_report(data, styles))
        else:
            # Generic document
            story.extend(self._build_generic(data, styles))

        # Build PDF
        doc.build(story)

        logger.info(f"Generated PDF: {output_path}")
        return output_path

    def _build_risk_assessment(self, data: Dict[str, Any], styles) -> list:
        """Build risk assessment document content."""
        story = []

        # Metadata
        story.append(Paragraph(f"<b>System:</b> {data.get('system_name', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"<b>Assessment Date:</b> {data.get('assessment_date', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"<b>Assessor:</b> {data.get('assessor_name', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

        # Risk factors table
        risk_factors = data.get("risk_factors", [])
        if risk_factors:
            story.append(Paragraph("<b>Risk Factors</b>", styles['Heading2']))
            table_data = [["Category", "Description", "Likelihood", "Impact", "Risk Level"]]
            for factor in risk_factors:
                table_data.append([
                    factor.get("category", ""),
                    factor.get("description", "")[:50] + "..." if len(factor.get("description", "")) > 50 else factor.get("description", ""),
                    factor.get("likelihood", ""),
                    factor.get("impact", ""),
                    factor.get("risk_level", ""),
                ])

            table = Table(table_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.2 * inch))

        # Mitigation measures
        mitigations = data.get("mitigation_measures", [])
        if mitigations:
            story.append(Paragraph("<b>Mitigation Measures</b>", styles['Heading2']))
            for i, measure in enumerate(mitigations, 1):
                story.append(Paragraph(f"{i}. {measure}", styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

        return story

    def _build_human_oversight(self, data: Dict[str, Any], styles) -> list:
        """Build human oversight document content."""
        story = []

        # Metadata
        story.append(Paragraph(f"<b>System:</b> {data.get('system_name', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"<b>Assessment Date:</b> {data.get('assessment_date', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

        # Oversight measures
        measures = data.get("oversight_measures", [])
        if measures:
            story.append(Paragraph("<b>Human Oversight Measures</b>", styles['Heading2']))
            for measure in measures:
                story.append(Paragraph(f"<b>{measure.get('measure_type', 'N/A')}</b>", styles['Heading3']))
                story.append(Paragraph(f"Description: {measure.get('description', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"Responsible Role: {measure.get('responsible_role', 'N/A')}", styles['Normal']))
                story.append(Paragraph(f"Frequency: {measure.get('frequency', 'N/A')}", styles['Normal']))
                story.append(Spacer(1, 0.1 * inch))

        return story

    def _build_compliance_checklist(self, data: Dict[str, Any], styles) -> list:
        """Build compliance checklist document content."""
        story = []

        # Metadata
        story.append(Paragraph(f"<b>System:</b> {data.get('system_name', 'N/A')}", styles['Normal']))
        story.append(Paragraph(f"<b>Overall Status:</b> {data.get('overall_status', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

        # Findings table
        findings = data.get("findings", [])
        if findings:
            story.append(Paragraph("<b>Compliance Findings</b>", styles['Heading2']))
            table_data = [["Article", "Requirement", "Status", "Severity"]]
            for finding in findings:
                table_data.append([
                    finding.get("article", ""),
                    finding.get("requirement", "")[:40] + "..." if len(finding.get("requirement", "")) > 40 else finding.get("requirement", ""),
                    finding.get("status", ""),
                    finding.get("severity", ""),
                ])

            table = Table(table_data, colWidths=[1*inch, 3*inch, 1*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(table)

        return story

    def _build_quarterly_report(self, data: Dict[str, Any], styles) -> list:
        """Build quarterly report document content."""
        story = []

        # Executive summary
        story.append(Paragraph("<b>Executive Summary</b>", styles['Heading2']))
        story.append(Paragraph(data.get("executive_summary", "N/A"), styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

        # Metrics
        metrics = data.get("report_period", {})
        if metrics:
            story.append(Paragraph("<b>Quarterly Metrics</b>", styles['Heading2']))
            story.append(Paragraph(f"Total Assessments: {metrics.get('total_assessments', 0)}", styles['Normal']))
            story.append(Paragraph(f"Compliant Systems: {metrics.get('compliant_systems', 0)}", styles['Normal']))
            story.append(Paragraph(f"Non-Compliant Systems: {metrics.get('non_compliant_systems', 0)}", styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

        return story

    def _build_generic(self, data: Dict[str, Any], styles) -> list:
        """Build generic document content."""
        story = []
        content = data.get("content", "")
        if content:
            story.append(Paragraph(content, styles['Normal']))
        return story
