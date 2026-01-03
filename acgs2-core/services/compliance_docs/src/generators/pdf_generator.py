"""
PDF Document Generator using ReportLab
"""

import logging
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Generates PDF compliance reports."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Define custom paragraph styles."""
        self.styles.add(
            ParagraphStyle(
                name="Header1", parent=self.styles["Heading1"], fontSize=18, spaceAfter=12
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="Header2", parent=self.styles["Heading2"], fontSize=14, spaceAfter=10
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="NormalText", parent=self.styles["Normal"], fontSize=10, spaceAfter=6
            )
        )

    def generate(self, content: Dict[str, Any], output_path: str) -> str:
        """
        Generate PDF report from content dictionary.

        Args:
            content: Dictionary containing report data (title, sections, etc.)
            output_path: Path to save the generated PDF

        Returns:
            Path to the generated file
        """
        try:
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18,
            )

            story = []

            # Title Page
            if "title" in content:
                story.append(Paragraph(content["title"], self.styles["Title"]))
                story.append(Spacer(1, 12))

            if "metadata" in content:
                meta_data = [[k, v] for k, v in content["metadata"].items()]
                t = Table(meta_data, colWidths=[150, 300])
                t.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 0), (-1, -1), 10),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )
                story.append(t)
                story.append(PageBreak())

            # Specific handlers for compliance frameworks
            doc_type = content.get("document_type")
            if doc_type == "euaiact_risk_assessment":
                story.extend(self._build_euaiact_risk_assessment(content))
            elif doc_type == "euaiact_human_oversight":
                story.extend(self._build_euaiact_human_oversight(content))
            elif doc_type == "soc2_report":
                story.extend(self._build_soc2_report(content))
            elif doc_type == "iso27001_report":
                story.extend(self._build_iso27001_report(content))

            # General Sections (if any)
            if "sections" in content:
                for section in content["sections"]:
                    story.append(Paragraph(section.get("title", ""), self.styles["Header1"]))
                    story.append(Paragraph(section.get("content", ""), self.styles["NormalText"]))

                    if "table" in section:
                        table_data = section["table"]
                        if table_data:
                            t = Table(table_data)
                            t.setStyle(
                                TableStyle(
                                    [
                                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                                    ]
                                )
                            )
                            story.append(t)

                    story.append(Spacer(1, 12))

            doc.build(story)
            logger.info(f"PDF generated successfully at {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise

    def _build_euaiact_risk_assessment(self, content: Dict[str, Any]) -> List[Any]:
        story = []
        story.append(Paragraph("EU AI Act Risk Assessment (Article 9)", self.styles["Header1"]))
        # ... implementation ...
        return story

    def _build_euaiact_human_oversight(self, content: Dict[str, Any]) -> List[Any]:
        story = []
        story.append(Paragraph("EU AI Act Human Oversight (Article 14)", self.styles["Header1"]))
        # ... implementation ...
        return story

    def _build_soc2_report(self, content: Dict[str, Any]) -> List[Any]:
        story = []
        story.append(Paragraph("SOC 2 Type II Compliance Report", self.styles["Header1"]))
        # ... implementation ...
        return story

    def _build_iso27001_report(self, content: Dict[str, Any]) -> List[Any]:
        story = []
        story.append(Paragraph("ISO 27001:2022 Compliance Report", self.styles["Header1"]))
        # ... implementation ...
        return story
