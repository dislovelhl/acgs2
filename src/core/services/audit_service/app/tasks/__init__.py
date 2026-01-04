"""
Celery Tasks for Audit Service
Constitutional Hash: cdd01ef066bc6cf2

This package contains Celery tasks for:
- Scheduled report generation
- Email delivery
- Background processing
"""

from .report_tasks import (
    ReportGenerationResult,
    generate_report_async,
    generate_scheduled_report,
)

__all__ = [
    "generate_scheduled_report",
    "generate_report_async",
    "ReportGenerationResult",
]
