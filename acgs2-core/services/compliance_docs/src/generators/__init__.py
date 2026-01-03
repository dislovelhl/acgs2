"""
Document generators for Compliance Documentation Service

Generators for PDF (ReportLab), DOCX (python-docx), and XLSX (openpyxl) formats.
"""

from .docx_generator import (
    ComplianceDOCXGenerator,
    ComplianceDOCXStyles,
    DOCXTableBuilder,
    generate_docx,
    generate_docx_to_buffer,
)
from .pdf_generator import (
    CompliancePDFGenerator,
    CompliancePDFStyles,
    PDFTableBuilder,
    generate_pdf,
    generate_pdf_to_buffer,
)

__all__ = [
    # PDF Generator
    "CompliancePDFGenerator",
    "CompliancePDFStyles",
    "PDFTableBuilder",
    "generate_pdf",
    "generate_pdf_to_buffer",
    # DOCX Generator
    "ComplianceDOCXGenerator",
    "ComplianceDOCXStyles",
    "DOCXTableBuilder",
    "generate_docx",
    "generate_docx_to_buffer",
]
