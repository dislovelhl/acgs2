"""
SOC 2 and ISO 27001 Compliance API Routes
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from ..generators.docx_generator import DOCXGenerator
from ..generators.pdf_generator import PDFGenerator
from ..generators.xlsx_generator import XLSXGenerator
from ..models.iso27001 import ISO27001ComplianceReport
from ..models.soc2 import SOC2ComplianceReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/compliance", tags=["SOC 2 & ISO 27001 Compliance"])


@router.post("/soc2/generate")
async def generate_soc2_report(
    report: SOC2ComplianceReport, format: str = Query(default="pdf", regex="^(pdf|docx|xlsx)$")
) -> FileResponse:
    """
    Generate SOC 2 Type II compliance report.
    """
    try:
        output_dir = "/tmp/compliance-reports"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        filename = f"soc2_report_{int(datetime.now().timestamp())}"

        content = report.model_dump()
        content["document_type"] = "soc2_report"
        content["title"] = f"SOC 2 Type II Report - {report.metadata.organization_name}"

        if format == "pdf":
            gen = PDFGenerator()
            file_path = gen.generate(content, f"{output_dir}/{filename}.pdf")
        elif format == "docx":
            gen = DOCXGenerator()
            file_path = gen.generate(content, f"{output_dir}/{filename}.docx")
        elif format == "xlsx":
            gen = XLSXGenerator()
            file_path = gen.generate(content, f"{output_dir}/{filename}.xlsx")
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")

        return FileResponse(path=file_path, filename=Path(file_path).name)

    except Exception as e:
        logger.error(f"SOC 2 generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/iso27001/generate")
async def generate_iso27001_report(
    report: ISO27001ComplianceReport, format: str = Query(default="pdf", regex="^(pdf|docx|xlsx)$")
) -> FileResponse:
    """
    Generate ISO 27001:2022 compliance report.
    """
    try:
        output_dir = "/tmp/compliance-reports"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        filename = f"iso27001_report_{int(datetime.now().timestamp())}"

        content = report.model_dump()
        content["document_type"] = "iso27001_report"
        content["title"] = f"ISO 27001:2022 Report - {report.organization_name}"

        if format == "pdf":
            gen = PDFGenerator()
            file_path = gen.generate(content, f"{output_dir}/{filename}.pdf")
        elif format == "docx":
            gen = DOCXGenerator()
            file_path = gen.generate(content, f"{output_dir}/{filename}.docx")
        elif format == "xlsx":
            gen = XLSXGenerator()
            file_path = gen.generate(content, f"{output_dir}/{filename}.xlsx")
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")

        return FileResponse(path=file_path, filename=Path(file_path).name)

    except Exception as e:
        logger.error(f"ISO 27001 generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
