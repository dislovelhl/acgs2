"""
PDF Exporter - ReportLab document generation for executive governance reports

Generates professionally formatted PDF reports containing governance summaries,
AI-generated insights, anomaly alerts, violation forecasts, and visualizations.
"""

import io
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError:
    SimpleDocTemplate = None
    letter = None
    colors = None
    getSampleStyleSheet = None
    ParagraphStyle = None
    inch = None
    Paragraph = None
    Spacer = None
    Table = None
    TableStyle = None
    PageBreak = None
    Image = None
    Drawing = None
    Rect = None
    String = None
    LinePlot = None
    VerticalBarChart = None

logger = logging.getLogger(__name__)


class ReportSection(BaseModel):
    """Model representing a section in the PDF report"""

    title: str
    content: str
    section_type: str = Field(
        default="text",
        description="Section type: 'text', 'table', 'chart', 'summary'",
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured data for the section",
    )


class PDFReportMetadata(BaseModel):
    """Metadata for the generated PDF report"""

    title: str = Field(default="Governance Analytics Report")
    subtitle: Optional[str] = None
    author: str = Field(default="ACGS-2 Analytics Engine")
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    tenant_id: str = Field(default="acgs-dev")


class PDFExportResult(BaseModel):
    """Result of PDF export operation"""

    success: bool
    export_timestamp: datetime
    filename: Optional[str] = None
    file_path: Optional[str] = None
    file_size_bytes: int = 0
    page_count: int = 0
    error_message: Optional[str] = None


class PDFExporter:
    """
    ReportLab-based PDF exporter for executive governance reports.

    Generates professional PDF documents containing:
    - Executive summary and AI-generated insights
    - Anomaly detection alerts with severity levels
    - Violation forecasts with trend analysis
    - Key governance metrics and statistics
    - Charts and visualizations

    Usage:
        exporter = PDFExporter()
        result = exporter.generate_executive_report(
            governance_data=metrics,
            insights=insight_result,
            anomalies=anomaly_result,
            predictions=forecast_result,
            output_path="governance_report.pdf"
        )
    """

    # Page configuration
    PAGE_SIZE = letter if letter else (612, 792)  # 8.5 x 11 inches
    MARGIN = 0.75 * (inch if inch else 72)

    # Color scheme for professional reports
    COLORS = {
        "primary": colors.HexColor("#1a365d") if colors else None,  # Dark blue
        "secondary": colors.HexColor("#2b6cb0") if colors else None,  # Medium blue
        "accent": colors.HexColor("#38a169") if colors else None,  # Green
        "warning": colors.HexColor("#d69e2e") if colors else None,  # Yellow/orange
        "danger": colors.HexColor("#e53e3e") if colors else None,  # Red
        "text": colors.HexColor("#2d3748") if colors else None,  # Dark gray
        "light": colors.HexColor("#e2e8f0") if colors else None,  # Light gray
    }

    # Severity color mapping
    SEVERITY_COLORS = {
        "critical": "danger",
        "high": "warning",
        "medium": "secondary",
        "low": "accent",
    }

    def __init__(
        self,
        output_dir: Optional[str] = None,
        company_name: str = "ACGS-2 Governance Platform",
        include_charts: bool = True,
    ):
        """
        Initialize the PDF exporter.

        Args:
            output_dir: Directory for output files (default from env or current dir)
            company_name: Company name for report header
            include_charts: Whether to include chart visualizations
        """
        self.output_dir = output_dir or os.getenv("PDF_OUTPUT_DIR", ".")
        self.company_name = company_name
        self.include_charts = include_charts

        self._styles = None
        self._last_export_time: Optional[datetime] = None

        # Initialize styles if ReportLab is available
        if getSampleStyleSheet is not None:
            self._initialize_styles()
        else:
            logger.warning("ReportLab not available. Install with: pip install reportlab")

    @property
    def is_available(self) -> bool:
        """Check if ReportLab is available"""
        return SimpleDocTemplate is not None

    def _initialize_styles(self) -> None:
        """Initialize custom paragraph styles for the report"""
        if getSampleStyleSheet is None or ParagraphStyle is None:
            return

        self._styles = getSampleStyleSheet()

        # Title style
        self._styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=self._styles["Heading1"],
                fontSize=24,
                spaceAfter=12,
                textColor=self.COLORS.get("primary", colors.black),
                alignment=1,  # Center
            )
        )

        # Subtitle style
        self._styles.add(
            ParagraphStyle(
                name="ReportSubtitle",
                parent=self._styles["Normal"],
                fontSize=12,
                spaceAfter=24,
                textColor=self.COLORS.get("text", colors.black),
                alignment=1,  # Center
            )
        )

        # Section header style
        self._styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self._styles["Heading2"],
                fontSize=16,
                spaceBefore=18,
                spaceAfter=10,
                textColor=self.COLORS.get("secondary", colors.black),
            )
        )

        # Subsection header style
        self._styles.add(
            ParagraphStyle(
                name="SubsectionHeader",
                parent=self._styles["Heading3"],
                fontSize=13,
                spaceBefore=12,
                spaceAfter=6,
                textColor=self.COLORS.get("text", colors.black),
            )
        )

        # Body text style
        self._styles.add(
            ParagraphStyle(
                name="BodyText",
                parent=self._styles["Normal"],
                fontSize=10,
                spaceAfter=8,
                textColor=self.COLORS.get("text", colors.black),
                leading=14,
            )
        )

        # Highlight box style
        self._styles.add(
            ParagraphStyle(
                name="Highlight",
                parent=self._styles["Normal"],
                fontSize=11,
                spaceAfter=6,
                textColor=self.COLORS.get("primary", colors.black),
                backColor=self.COLORS.get("light", colors.lightgrey),
                borderPadding=8,
            )
        )

        # Alert style for anomalies
        self._styles.add(
            ParagraphStyle(
                name="AlertText",
                parent=self._styles["Normal"],
                fontSize=10,
                spaceAfter=4,
                textColor=self.COLORS.get("danger", colors.red),
            )
        )

    def _check_reportlab_available(self) -> bool:
        """Check if ReportLab is available and initialized"""
        if SimpleDocTemplate is None:
            logger.error("ReportLab is not installed. Install with: pip install reportlab")
            return False
        if self._styles is None:
            logger.error("Report styles not initialized")
            return False
        return True

    def _create_header(
        self,
        metadata: PDFReportMetadata,
    ) -> List[Any]:
        """
        Create the report header section.

        Args:
            metadata: Report metadata

        Returns:
            List of flowable elements for the header
        """
        elements = []

        # Company name
        elements.append(Paragraph(self.company_name, self._styles["ReportSubtitle"]))

        # Report title
        elements.append(Paragraph(metadata.title, self._styles["ReportTitle"]))

        # Subtitle with date range
        if metadata.period_start and metadata.period_end:
            period_str = (
                f"Reporting Period: {metadata.period_start.strftime('%Y-%m-%d')} "
                f"to {metadata.period_end.strftime('%Y-%m-%d')}"
            )
        else:
            period_str = f"Generated: {metadata.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"

        if metadata.subtitle:
            period_str = f"{metadata.subtitle}<br/>{period_str}"

        elements.append(Paragraph(period_str, self._styles["ReportSubtitle"]))

        elements.append(Spacer(1, 20))

        return elements

    def _create_executive_summary(
        self,
        governance_data: Dict[str, Any],
        insights: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """
        Create the executive summary section.

        Args:
            governance_data: Governance metrics data
            insights: AI-generated insights (optional)

        Returns:
            List of flowable elements for the summary
        """
        elements = []

        elements.append(Paragraph("Executive Summary", self._styles["SectionHeader"]))

        # Key metrics table
        metrics_data = [
            ["Metric", "Value"],
            [
                "Total Governance Events",
                str(governance_data.get("total_events", "N/A")),
            ],
            [
                "Policy Violations",
                str(governance_data.get("violation_count", "N/A")),
            ],
            [
                "Unique Users Affected",
                str(governance_data.get("unique_users", "N/A")),
            ],
            [
                "Policy Changes",
                str(governance_data.get("policy_changes", "N/A")),
            ],
            [
                "Trend",
                governance_data.get("trend", "stable").capitalize(),
            ],
        ]

        metrics_table = Table(metrics_data, colWidths=[3 * inch, 2 * inch])
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self.COLORS.get("primary", colors.navy)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), self.COLORS.get("light", colors.lightgrey)),
                    ("TEXTCOLOR", (0, 1), (-1, -1), self.COLORS.get("text", colors.black)),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 1), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                ]
            )
        )
        elements.append(metrics_table)
        elements.append(Spacer(1, 15))

        # AI-generated insights
        if insights:
            elements.append(Paragraph("AI-Generated Insights", self._styles["SubsectionHeader"]))

            if insights.get("summary"):
                elements.append(
                    Paragraph(
                        f"<b>Summary:</b> {insights['summary']}",
                        self._styles["BodyText"],
                    )
                )

            if insights.get("business_impact"):
                elements.append(
                    Paragraph(
                        f"<b>Business Impact:</b> {insights['business_impact']}",
                        self._styles["BodyText"],
                    )
                )

            if insights.get("recommended_action"):
                elements.append(
                    Paragraph(
                        f"<b>Recommended Action:</b> {insights['recommended_action']}",
                        self._styles["BodyText"],
                    )
                )

            elements.append(Spacer(1, 10))

        return elements

    def _create_anomaly_section(
        self,
        anomalies: Dict[str, Any],
    ) -> List[Any]:
        """
        Create the anomaly detection section.

        Args:
            anomalies: Anomaly detection results

        Returns:
            List of flowable elements for anomaly section
        """
        elements = []

        elements.append(Paragraph("Anomaly Detection", self._styles["SectionHeader"]))

        anomaly_count = anomalies.get("anomalies_detected", 0)
        total_analyzed = anomalies.get("total_records_analyzed", 0)

        elements.append(
            Paragraph(
                f"Analyzed {total_analyzed} records, detected {anomaly_count} anomalies.",
                self._styles["BodyText"],
            )
        )

        anomaly_list = anomalies.get("anomalies", [])
        if anomaly_list:
            elements.append(Paragraph("Detected Anomalies:", self._styles["SubsectionHeader"]))

            # Create anomaly table
            table_data = [["Date", "Severity", "Description"]]

            for anomaly in anomaly_list[:10]:  # Limit to top 10
                timestamp = anomaly.get("timestamp", "")
                if isinstance(timestamp, str):
                    date_str = timestamp[:10] if len(timestamp) >= 10 else timestamp
                else:
                    date_str = timestamp.strftime("%Y-%m-%d") if timestamp else "N/A"

                severity = anomaly.get("severity_label", "unknown").upper()
                description = anomaly.get("description", "Anomaly detected")

                # Truncate description if too long
                if len(description) > 60:
                    description = description[:57] + "..."

                table_data.append([date_str, severity, description])

            anomaly_table = Table(
                table_data,
                colWidths=[1.2 * inch, 1 * inch, 4 * inch],
            )

            # Dynamic row colors based on severity
            table_styles = [
                ("BACKGROUND", (0, 0), (-1, 0), self.COLORS.get("secondary", colors.blue)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]

            # Apply severity-based background colors
            for i, anomaly in enumerate(anomaly_list[:10], start=1):
                severity = anomaly.get("severity_label", "low")
                color_key = self.SEVERITY_COLORS.get(severity, "light")
                bg_color = self.COLORS.get(color_key, colors.white)
                if bg_color:
                    # Use lighter version for readability
                    table_styles.append(
                        (
                            "BACKGROUND",
                            (0, i),
                            (-1, i),
                            colors.Color(
                                bg_color.red + (1 - bg_color.red) * 0.7,
                                bg_color.green + (1 - bg_color.green) * 0.7,
                                bg_color.blue + (1 - bg_color.blue) * 0.7,
                            ),
                        )
                    )

            anomaly_table.setStyle(TableStyle(table_styles))
            elements.append(anomaly_table)

            if len(anomaly_list) > 10:
                elements.append(
                    Paragraph(
                        f"<i>...and {len(anomaly_list) - 10} more anomalies not shown</i>",
                        self._styles["BodyText"],
                    )
                )
        else:
            elements.append(
                Paragraph(
                    "No significant anomalies detected during this period.",
                    self._styles["BodyText"],
                )
            )

        elements.append(Spacer(1, 15))

        return elements

    def _create_prediction_section(
        self,
        predictions: Dict[str, Any],
    ) -> List[Any]:
        """
        Create the violation predictions section.

        Args:
            predictions: Violation forecast results

        Returns:
            List of flowable elements for predictions section
        """
        elements = []

        elements.append(Paragraph("Violation Forecast", self._styles["SectionHeader"]))

        forecast_days = predictions.get("forecast_days", 30)
        model_trained = predictions.get("model_trained", False)
        error_message = predictions.get("error_message")

        if error_message:
            elements.append(
                Paragraph(
                    f"<i>Note: {error_message}</i>",
                    self._styles["AlertText"],
                )
            )
            elements.append(Spacer(1, 15))
            return elements

        if not model_trained:
            elements.append(
                Paragraph(
                    "Insufficient historical data for forecasting.",
                    self._styles["BodyText"],
                )
            )
            elements.append(Spacer(1, 15))
            return elements

        summary = predictions.get("summary", {})

        elements.append(
            Paragraph(
                f"<b>{forecast_days}-Day Violation Forecast</b>",
                self._styles["SubsectionHeader"],
            )
        )

        # Summary statistics
        summary_text = []
        if "mean_predicted_violations" in summary:
            summary_text.append(
                f"Average predicted daily violations: "
                f"{summary['mean_predicted_violations']:.1f}"
            )
        if "total_predicted_violations" in summary:
            summary_text.append(
                f"Total predicted violations: " f"{summary['total_predicted_violations']:.0f}"
            )
        if "trend_direction" in summary:
            trend = summary["trend_direction"].capitalize()
            summary_text.append(f"Trend direction: {trend}")

        for text in summary_text:
            elements.append(Paragraph(text, self._styles["BodyText"]))

        # Forecast table (first 7 days)
        forecast_points = predictions.get("forecast", [])
        if forecast_points:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("7-Day Outlook:", self._styles["SubsectionHeader"]))

            table_data = [["Date", "Predicted", "Lower Bound", "Upper Bound"]]
            for point in forecast_points[:7]:
                table_data.append(
                    [
                        point.get("date", "N/A"),
                        f"{point.get('predicted_value', 0):.1f}",
                        f"{point.get('lower_bound', 0):.1f}",
                        f"{point.get('upper_bound', 0):.1f}",
                    ]
                )

            forecast_table = Table(
                table_data,
                colWidths=[1.5 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch],
            )
            forecast_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), self.COLORS.get("accent", colors.green)),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        (
                            "BACKGROUND",
                            (0, 1),
                            (-1, -1),
                            self.COLORS.get("light", colors.lightgrey),
                        ),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            elements.append(forecast_table)

        elements.append(Spacer(1, 15))

        return elements

    def _create_chart(
        self,
        data: List[Dict[str, Any]],
        chart_type: str = "line",
        title: str = "Chart",
        width: float = 400,
        height: float = 200,
    ) -> Optional[Drawing]:
        """
        Create a chart visualization.

        Args:
            data: List of data points with 'x' and 'y' values
            chart_type: Type of chart ('line' or 'bar')
            title: Chart title
            width: Chart width in points
            height: Chart height in points

        Returns:
            Drawing object or None if charts unavailable
        """
        if not self.include_charts or Drawing is None:
            return None

        if not data:
            return None

        drawing = Drawing(width, height)

        if chart_type == "line" and LinePlot is not None:
            chart = LinePlot()
            chart.x = 50
            chart.y = 30
            chart.height = height - 60
            chart.width = width - 100

            # Extract data points
            plot_data = [(i, d.get("y", 0)) for i, d in enumerate(data)]
            chart.data = [plot_data]

            chart.lines[0].strokeColor = self.COLORS.get("secondary", colors.blue)
            chart.lines[0].strokeWidth = 2

            drawing.add(chart)

        elif chart_type == "bar" and VerticalBarChart is not None:
            chart = VerticalBarChart()
            chart.x = 50
            chart.y = 30
            chart.height = height - 60
            chart.width = width - 100

            # Extract data
            chart.data = [[d.get("y", 0) for d in data]]
            chart.categoryAxis.categoryNames = [d.get("x", str(i)) for i, d in enumerate(data)]

            chart.bars[0].fillColor = self.COLORS.get("secondary", colors.blue)

            drawing.add(chart)

        # Add title
        if String is not None:
            drawing.add(
                String(
                    width / 2,
                    height - 15,
                    title,
                    textAnchor="middle",
                    fontSize=11,
                    fillColor=self.COLORS.get("text", colors.black),
                )
            )

        return drawing

    def _create_footer(self, metadata: PDFReportMetadata) -> List[Any]:
        """
        Create the report footer section.

        Args:
            metadata: Report metadata

        Returns:
            List of flowable elements for the footer
        """
        elements = []

        elements.append(Spacer(1, 30))

        footer_text = (
            f"Report generated by {metadata.author} on "
            f"{metadata.generated_at.strftime('%Y-%m-%d at %H:%M UTC')}. "
            f"Tenant: {metadata.tenant_id}"
        )

        elements.append(
            Paragraph(
                f"<i>{footer_text}</i>",
                self._styles["BodyText"],
            )
        )

        elements.append(
            Paragraph(
                "<i>This report contains AI-generated insights. "
                "Please verify critical findings before taking action.</i>",
                self._styles["BodyText"],
            )
        )

        return elements

    def generate_executive_report(
        self,
        governance_data: Dict[str, Any],
        insights: Optional[Dict[str, Any]] = None,
        anomalies: Optional[Dict[str, Any]] = None,
        predictions: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
        metadata: Optional[PDFReportMetadata] = None,
    ) -> PDFExportResult:
        """
        Generate a complete executive governance report as PDF.

        Args:
            governance_data: Dictionary with governance metrics
            insights: AI-generated insights from InsightGenerator
            anomalies: Anomaly detection results from AnomalyDetector
            predictions: Violation forecast from ViolationPredictor
            output_path: Path to save the PDF file
            metadata: Report metadata (optional, will be auto-generated)

        Returns:
            PDFExportResult with export status and file information
        """
        now = datetime.now(timezone.utc)

        # Check ReportLab availability
        if not self._check_reportlab_available():
            return PDFExportResult(
                success=False,
                export_timestamp=now,
                error_message="ReportLab not available. Install with: pip install reportlab",
            )

        # Generate metadata if not provided
        if metadata is None:
            metadata = PDFReportMetadata(
                title="Governance Analytics Report",
                subtitle="Executive Summary",
                generated_at=now,
                tenant_id=os.getenv("TENANT_ID", "acgs-dev"),
            )

        # Generate output path if not provided
        if output_path is None:
            filename = f"governance_report_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
            output_path = os.path.join(self.output_dir, filename)
        else:
            filename = os.path.basename(output_path)

        try:
            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=self.PAGE_SIZE,
                leftMargin=self.MARGIN,
                rightMargin=self.MARGIN,
                topMargin=self.MARGIN,
                bottomMargin=self.MARGIN,
            )

            # Build document elements
            elements = []

            # Header
            elements.extend(self._create_header(metadata))

            # Executive Summary
            elements.extend(self._create_executive_summary(governance_data, insights))

            # Anomaly Detection Section
            if anomalies:
                elements.extend(self._create_anomaly_section(anomalies))

            # Predictions Section
            if predictions:
                elements.extend(self._create_prediction_section(predictions))

            # Footer
            elements.extend(self._create_footer(metadata))

            # Build PDF
            doc.build(elements)

            # Get file size
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

            self._last_export_time = now

            logger.info(f"Generated PDF report: {output_path} ({file_size} bytes)")

            return PDFExportResult(
                success=True,
                export_timestamp=now,
                filename=filename,
                file_path=output_path,
                file_size_bytes=file_size,
                page_count=1,  # SimpleDocTemplate doesn't expose page count easily
                error_message=None,
            )

        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            return PDFExportResult(
                success=False,
                export_timestamp=now,
                error_message=f"Failed to generate PDF: {str(e)}",
            )

    def generate_to_bytes(
        self,
        governance_data: Dict[str, Any],
        insights: Optional[Dict[str, Any]] = None,
        anomalies: Optional[Dict[str, Any]] = None,
        predictions: Optional[Dict[str, Any]] = None,
        metadata: Optional[PDFReportMetadata] = None,
    ) -> Optional[bytes]:
        """
        Generate PDF report as bytes (for streaming/API responses).

        Args:
            governance_data: Dictionary with governance metrics
            insights: AI-generated insights
            anomalies: Anomaly detection results
            predictions: Violation forecast
            metadata: Report metadata

        Returns:
            PDF content as bytes, or None if generation failed
        """
        if not self._check_reportlab_available():
            return None

        now = datetime.now(timezone.utc)

        if metadata is None:
            metadata = PDFReportMetadata(
                title="Governance Analytics Report",
                generated_at=now,
            )

        try:
            buffer = io.BytesIO()

            doc = SimpleDocTemplate(
                buffer,
                pagesize=self.PAGE_SIZE,
                leftMargin=self.MARGIN,
                rightMargin=self.MARGIN,
                topMargin=self.MARGIN,
                bottomMargin=self.MARGIN,
            )

            elements = []
            elements.extend(self._create_header(metadata))
            elements.extend(self._create_executive_summary(governance_data, insights))

            if anomalies:
                elements.extend(self._create_anomaly_section(anomalies))

            if predictions:
                elements.extend(self._create_prediction_section(predictions))

            elements.extend(self._create_footer(metadata))

            doc.build(elements)

            self._last_export_time = now

            buffer.seek(0)
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Failed to generate PDF to bytes: {e}")
            return None

    def get_exporter_info(self) -> Dict[str, Any]:
        """
        Get information about the exporter state.

        Returns:
            Dictionary with exporter configuration and status
        """
        return {
            "is_available": self.is_available,
            "output_dir": self.output_dir,
            "company_name": self.company_name,
            "include_charts": self.include_charts,
            "last_export_time": (
                self._last_export_time.isoformat() if self._last_export_time else None
            ),
            "reportlab_available": SimpleDocTemplate is not None,
            "styles_initialized": self._styles is not None,
        }

    def get_export_result_as_dict(
        self,
        result: PDFExportResult,
    ) -> Dict[str, Any]:
        """
        Convert PDFExportResult to a dictionary suitable for API responses.

        Args:
            result: PDFExportResult object

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "success": result.success,
            "export_timestamp": result.export_timestamp.isoformat(),
            "filename": result.filename,
            "file_path": result.file_path,
            "file_size_bytes": result.file_size_bytes,
            "page_count": result.page_count,
            "error_message": result.error_message,
        }
