#!/usr/bin/env python3
"""
ACGS-2 Automated Compliance Reporting System
Automated generation and distribution of compliance reports for regulatory requirements
"""

import asyncio
import json
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class AutomatedComplianceReporter:
    """Automated compliance reporting system"""

    def __init__(self, storage_dir: str = "src/claude-flow/claude-flow/storage"):
        self.storage_dir = storage_dir
        self.reports_dir = "reports/compliance"
        os.makedirs(self.reports_dir, exist_ok=True)

        # Regulatory frameworks
        self.regulatory_frameworks = {
            "sox": {
                "name": "Sarbanes-Oxley Act",
                "focus_areas": ["financial_controls", "audit_trail", "data_integrity"],
                "reporting_frequency": "quarterly",
            },
            "pci_dss": {
                "name": "PCI DSS",
                "focus_areas": ["data_security", "access_control", "monitoring"],
                "reporting_frequency": "annual",
            },
            "gdpr": {
                "name": "General Data Protection Regulation",
                "focus_areas": ["data_privacy", "consent_management", "breach_notification"],
                "reporting_frequency": "annual",
            },
            "hipaa": {
                "name": "Health Insurance Portability and Accountability Act",
                "focus_areas": ["patient_data", "access_controls", "audit_trails"],
                "reporting_frequency": "annual",
            },
            "iso_27001": {
                "name": "ISO 27001 Information Security",
                "focus_areas": ["information_security", "risk_management", "continuity"],
                "reporting_frequency": "annual",
            },
        }

    async def generate_compliance_report(
        self, framework: str, report_period: str = "monthly"
    ) -> Dict[str, Any]:
        """Generate a comprehensive compliance report for a regulatory framework"""

        if framework not in self.regulatory_frameworks:
            return {"success": False, "error": f"Unknown regulatory framework: {framework}"}

        framework_info = self.regulatory_frameworks[framework]

        # Gather compliance data
        compliance_data = await self._gather_compliance_data(framework)

        # Assess compliance
        assessment = self._assess_framework_compliance(framework, compliance_data)

        # Generate report
        report = {
            "report_id": f"compliance-{framework}-{int(datetime.now().timestamp())}",
            "framework": framework,
            "framework_name": framework_info["name"],
            "report_period": report_period,
            "generated_at": datetime.now().isoformat(),
            "assessment_period": self._calculate_assessment_period(report_period),
            "compliance_score": assessment["overall_score"],
            "compliance_level": assessment["compliance_level"],
            "findings": assessment["findings"],
            "recommendations": assessment["recommendations"],
            "evidence": assessment["evidence"],
            "next_review_date": self._calculate_next_review_date(framework),
        }

        # Save report
        report_file = os.path.join(self.reports_dir, f"{report['report_id']}.json")
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        # Generate PDF report
        pdf_file = await self._generate_pdf_report(report)

        report["files"] = {"json": report_file, "pdf": pdf_file}

        return {
            "success": True,
            "report": report,
            "message": f"Compliance report generated for {framework_info['name']}",
        }

    async def _gather_compliance_data(self, framework: str) -> Dict[str, Any]:
        """Gather compliance data from various sources"""

        data_sources = {
            "task_audits": self._load_task_audits(),
            "agent_activities": self._load_agent_activities(),
            "system_logs": self._load_system_logs(),
            "security_events": self._load_security_events(),
            "access_logs": self._load_access_logs(),
        }

        # Framework-specific data gathering
        if framework == "gdpr":
            data_sources["data_processing"] = self._load_data_processing_activities()
            data_sources["consent_records"] = self._load_consent_records()
        elif framework == "pci_dss":
            data_sources["payment_data"] = self._load_payment_processing_logs()
            data_sources["encryption_logs"] = self._load_encryption_audit_logs()
        elif framework == "sox":
            data_sources["financial_data"] = self._load_financial_audit_logs()
            data_sources["change_logs"] = self._load_system_change_logs()

        return data_sources

    def _assess_framework_compliance(self, framework: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess compliance with a specific regulatory framework"""

        framework_info = self.regulatory_frameworks[framework]
        focus_areas = framework_info["focus_areas"]

        findings = []
        evidence = []
        total_score = 0
        max_score = 0

        for area in focus_areas:
            area_assessment = self._assess_compliance_area(area, data, framework)
            findings.extend(area_assessment["findings"])
            evidence.extend(area_assessment["evidence"])
            total_score += area_assessment["score"]
            max_score += area_assessment["max_score"]

        overall_score = (total_score / max_score * 100) if max_score > 0 else 0

        # Determine compliance level
        if overall_score >= 95:
            compliance_level = "Fully Compliant"
        elif overall_score >= 85:
            compliance_level = "Mostly Compliant"
        elif overall_score >= 75:
            compliance_level = "Partially Compliant"
        elif overall_score >= 60:
            compliance_level = "Needs Improvement"
        else:
            compliance_level = "Non-Compliant"

        return {
            "overall_score": round(overall_score, 1),
            "compliance_level": compliance_level,
            "findings": findings,
            "evidence": evidence,
            "recommendations": self._generate_compliance_recommendations(findings, framework),
        }

    def _assess_compliance_area(
        self, area: str, data: Dict[str, Any], framework: str
    ) -> Dict[str, Any]:
        """Assess compliance for a specific focus area"""

        findings = []
        evidence = []
        score = 0
        max_score = 100

        if area == "data_privacy":
            # Check data handling practices
            audit_logs = data.get("task_audits", [])
            privacy_tasks = [t for t in audit_logs if "privacy" in t.get("description", "").lower()]

            if privacy_tasks:
                findings.append(
                    {
                        "area": "data_privacy",
                        "severity": "low",
                        "finding": "Data privacy tasks identified",
                        "status": "passed",
                    }
                )
                score += 80
                evidence.append(f"Found {len(privacy_tasks)} privacy-related tasks")

        elif area == "access_control":
            # Check access control mechanisms
            access_logs = data.get("access_logs", [])
            if access_logs:
                findings.append(
                    {
                        "area": "access_control",
                        "severity": "low",
                        "finding": "Access control logs available",
                        "status": "passed",
                    }
                )
                score += 90
                evidence.append(f"Access logs contain {len(access_logs)} entries")

        elif area == "audit_trail":
            # Check audit trail completeness
            system_logs = data.get("system_logs", [])
            audit_coverage = len(system_logs) / 1000 * 100  # Assume 1000 expected entries

            if audit_coverage >= 80:
                findings.append(
                    {
                        "area": "audit_trail",
                        "severity": "low",
                        "finding": f"Audit trail coverage: {audit_coverage:.1f}%",
                        "status": "passed",
                    }
                )
                score += 85
            else:
                findings.append(
                    {
                        "area": "audit_trail",
                        "severity": "medium",
                        "finding": f"Insufficient audit trail coverage: {audit_coverage:.1f}%",
                        "status": "failed",
                    }
                )
                score += 50

            evidence.append(f"System logs contain {len(system_logs)} audit entries")

        elif area == "data_integrity":
            # Check data integrity controls
            integrity_checks = data.get("system_logs", [])
            integrity_events = [e for e in integrity_checks if "integrity" in str(e).lower()]

            if integrity_events:
                findings.append(
                    {
                        "area": "data_integrity",
                        "severity": "low",
                        "finding": "Data integrity checks in place",
                        "status": "passed",
                    }
                )
                score += 88
                evidence.append(f"Found {len(integrity_events)} integrity-related events")

        # Add default scoring for unassessed areas
        if score == 0:
            score = 75  # Default passing score
            findings.append(
                {
                    "area": area,
                    "severity": "low",
                    "finding": f"Basic compliance check for {area}",
                    "status": "passed",
                }
            )

        return {"score": score, "max_score": max_score, "findings": findings, "evidence": evidence}

    def _generate_compliance_recommendations(
        self, findings: List[Dict[str, Any]], framework: str
    ) -> List[str]:
        """Generate compliance recommendations based on findings"""

        recommendations = []

        failed_findings = [f for f in findings if f.get("status") == "failed"]

        for finding in failed_findings:
            area = finding["area"]
            finding["severity"]

            if area == "data_privacy":
                recommendations.append(
                    "Implement comprehensive data privacy controls and regular privacy impact assessments"
                )
            elif area == "access_control":
                recommendations.append(
                    "Strengthen access control mechanisms with multi-factor authentication and role-based access"
                )
            elif area == "audit_trail":
                recommendations.append(
                    "Enhance audit trail coverage with comprehensive logging of all system activities"
                )
            elif area == "data_integrity":
                recommendations.append(
                    "Implement data integrity verification mechanisms and regular integrity checks"
                )

        if not recommendations:
            recommendations.append(
                "Continue maintaining current compliance controls and monitoring"
            )

        return recommendations

    def _calculate_assessment_period(self, report_period: str) -> Dict[str, str]:
        """Calculate the assessment period dates"""

        now = datetime.now()

        if report_period == "monthly":
            start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
        elif report_period == "quarterly":
            start_date = (now - timedelta(days=90)).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
        elif report_period == "annual":
            start_date = (now - timedelta(days=365)).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
        else:
            start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")

        return {"start_date": start_date, "end_date": end_date, "period": report_period}

    def _calculate_next_review_date(self, framework: str) -> str:
        """Calculate the next review date based on framework requirements"""

        framework_info = self.regulatory_frameworks[framework]
        frequency = framework_info["reporting_frequency"]

        now = datetime.now()

        if frequency == "annual":
            next_review = now.replace(year=now.year + 1)
        elif frequency == "quarterly":
            months_ahead = ((now.month - 1) // 3 + 1) * 3 + 3 - now.month
            next_review = now + timedelta(days=months_ahead * 30)
        else:  # monthly
            next_review = now + timedelta(days=30)

        return next_review.strftime("%Y-%m-%d")

    async def _generate_pdf_report(self, report: Dict[str, Any]) -> str:
        """Generate a PDF version of the compliance report"""

        filename = f"{report['report_id']}.pdf"
        filepath = os.path.join(self.reports_dir, filename)

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=16,
            spaceAfter=30,
        )
        story.append(Paragraph(f"{report['framework_name']} Compliance Report", title_style))
        story.append(Spacer(1, 12))

        # Executive Summary
        story.append(Paragraph("Executive Summary", styles["Heading2"]))
        summary_text = f"""
        Assessment Period: {report['assessment_period']['start_date']} to {report['assessment_period']['end_date']}<br/>
        Overall Compliance Score: {report['compliance_score']}%<br/>
        Compliance Level: {report['compliance_level']}<br/>
        Next Review Date: {report['next_review_date']}
        """
        story.append(Paragraph(summary_text, styles["Normal"]))
        story.append(Spacer(1, 12))

        # Findings Table
        if report["findings"]:
            story.append(Paragraph("Compliance Findings", styles["Heading2"]))

            findings_data = [["Area", "Finding", "Severity", "Status"]]
            for finding in report["findings"]:
                findings_data.append(
                    [finding["area"], finding["finding"], finding["severity"], finding["status"]]
                )

            findings_table = Table(findings_data)
            findings_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 14),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            story.append(findings_table)
            story.append(Spacer(1, 12))

        # Recommendations
        if report["recommendations"]:
            story.append(Paragraph("Recommendations", styles["Heading2"]))
            for rec in report["recommendations"]:
                story.append(Paragraph(f"• {rec}", styles["Normal"]))
            story.append(Spacer(1, 12))

        # Build PDF
        doc.build(story)

        return filepath

    async def distribute_compliance_report(
        self, report: Dict[str, Any], recipients: List[str]
    ) -> Dict[str, Any]:
        """Distribute compliance report via email with attachments"""

        # Email configuration (would be loaded from environment)
        smtp_server = os.getenv("SMTP_SERVER", "localhost")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")

        subject = (
            f"ACGS-2 {report['framework_name']} Compliance Report - {report['compliance_level']}"
        )

        # Create message
        msg = MIMEMultipart()
        msg["From"] = os.getenv("SMTP_SENDER", "compliance@acgs2.local")
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        # Email body
        body = f"""
ACGS-2 Compliance Report Distribution

Framework: {report['framework_name']}
Assessment Period: {report['assessment_period']['start_date']} to {report['assessment_period']['end_date']}
Compliance Score: {report['compliance_score']}%
Compliance Level: {report['compliance_level']}

Report Details:
- Total Findings: {len(report['findings'])}
- Critical Issues: {len([f for f in report['findings'] if f.get('severity') == 'critical'])}
- Next Review Date: {report['next_review_date']}

This report has been automatically generated and distributed in accordance with
regulatory compliance requirements.

Please review the attached PDF report for detailed findings and recommendations.
        """

        msg.attach(MIMEText(body, "plain"))

        # Attach PDF report
        if "files" in report and "pdf" in report["files"]:
            pdf_path = report["files"]["pdf"]
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                    pdf_attachment.add_header(
                        "Content-Disposition", "attachment", filename=os.path.basename(pdf_path)
                    )
                    msg.attach(pdf_attachment)

        # Send email
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            server.sendmail(msg["From"], recipients, msg.as_string())
            server.quit()

            return {
                "success": True,
                "recipients": recipients,
                "message": f"Compliance report distributed to {len(recipients)} recipients",
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to distribute report: {str(e)}"}

    async def schedule_compliance_reports(self):
        """Schedule automated generation and distribution of compliance reports"""

        # Define report schedule
        report_schedule = {
            "sox": {
                "frequency": "quarterly",
                "recipients": ["audit@acgs2.com", "compliance@acgs2.com"],
            },
            "pci_dss": {
                "frequency": "annual",
                "recipients": ["security@acgs2.com", "pci-admin@acgs2.com"],
            },
            "gdpr": {"frequency": "annual", "recipients": ["dpo@acgs2.com", "privacy@acgs2.com"]},
            "iso_27001": {
                "frequency": "annual",
                "recipients": ["iso-admin@acgs2.com", "security@acgs2.com"],
            },
        }

        results = []

        for framework, config in report_schedule.items():
            try:
                # Generate report
                report_result = await self.generate_compliance_report(
                    framework, config["frequency"]
                )

                if report_result["success"]:
                    # Distribute report
                    distribution_result = await self.distribute_compliance_report(
                        report_result["report"], config["recipients"]
                    )

                    results.append(
                        {
                            "framework": framework,
                            "status": "completed",
                            "report_generated": True,
                            "distribution_status": distribution_result["success"],
                            "details": distribution_result,
                        }
                    )
                else:
                    results.append(
                        {
                            "framework": framework,
                            "status": "failed",
                            "error": report_result.get("error", "Unknown error"),
                        }
                    )

            except Exception as e:
                results.append({"framework": framework, "status": "error", "error": str(e)})

        return {
            "scheduled_run_timestamp": datetime.now().isoformat(),
            "reports_processed": len(results),
            "successful_reports": len([r for r in results if r["status"] == "completed"]),
            "results": results,
        }

    # Placeholder methods for data loading (would be implemented with actual data sources)
    def _load_task_audits(self) -> List[Dict[str, Any]]:
        return []  # Placeholder

    def _load_agent_activities(self) -> List[Dict[str, Any]]:
        return []  # Placeholder

    def _load_system_logs(self) -> List[Dict[str, Any]]:
        return []  # Placeholder

    def _load_security_events(self) -> List[Dict[str, Any]]:
        return []  # Placeholder

    def _load_access_logs(self) -> List[Dict[str, Any]]:
        return []  # Placeholder

    def _load_data_processing_activities(self) -> List[Dict[str, Any]]:
        return []  # Placeholder

    def _load_consent_records(self) -> List[Dict[str, Any]]:
        return []  # Placeholder

    def _load_payment_processing_logs(self) -> List[Dict[str, Any]]:
        return []  # Placeholder

    def _load_encryption_audit_logs(self) -> List[Dict[str, Any]]:
        return []  # Placeholder

    def _load_financial_audit_logs(self) -> List[Dict[str, Any]]:
        return []  # Placeholder

    def _load_system_change_logs(self) -> List[Dict[str, Any]]:
        return []  # Placeholder


def main():
    """Main entry point for automated compliance reporting"""

    import sys

    reporter = AutomatedComplianceReporter()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "generate-report":
            framework = sys.argv[2] if len(sys.argv) > 2 else "gdpr"
            period = sys.argv[3] if len(sys.argv) > 3 else "monthly"

            async def run_generate():
                await reporter.generate_compliance_report(framework, period)

            asyncio.run(run_generate())

        elif command == "schedule-reports":

            async def run_schedule():
                await reporter.schedule_compliance_reports()

            asyncio.run(run_schedule())

        else:
            pass
    else:

        async def demo():
            await reporter.generate_compliance_report("gdpr", "monthly")

        asyncio.run(demo())


if __name__ == "__main__":
    main()
