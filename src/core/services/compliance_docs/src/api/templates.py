"""Constitutional Hash: cdd01ef066bc6cf2
Template Listing API for Compliance Documentation Service

Provides REST API endpoints for listing available compliance templates
for all supported frameworks (SOC 2, ISO 27001, GDPR, EU AI Act).

Endpoints:
- GET /api/v1/templates/{framework} - List templates for a specific framework
- GET /api/v1/templates - List all available templates
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from ..models.base import ComplianceFramework
from ..template_engine import list_templates, template_exists

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/templates", tags=["Templates"])


# Response models
class TemplateInfo(BaseModel):
    """Information about a single compliance template."""

    name: str = Field(..., description="Template filename")
    display_name: str = Field(..., description="Human-readable template name")
    description: str = Field(..., description="Template description")
    framework: str = Field(..., description="Compliance framework")
    supported_formats: list[str] = Field(
        ..., description="Supported export formats (pdf, docx, xlsx)"
    )
    version: str = Field(default="1.0.0", description="Template version")


class TemplateListResponse(BaseModel):
    """Response model for template listing."""

    framework: str = Field(..., description="Compliance framework")
    framework_display_name: str = Field(..., description="Human-readable framework name")
    total_templates: int = Field(..., description="Total number of templates")
    templates: list[TemplateInfo] = Field(..., description="List of available templates")
    retrieved_at: str = Field(..., description="Timestamp of the request")


class AllTemplatesResponse(BaseModel):
    """Response model for listing all templates across all frameworks."""

    total_templates: int = Field(..., description="Total number of templates")
    frameworks: dict[str, TemplateListResponse] = Field(
        ..., description="Templates grouped by framework"
    )
    retrieved_at: str = Field(..., description="Timestamp of the request")


# Template metadata for each framework
# Maps template filename to display name and description
TEMPLATE_METADATA: dict[str, dict[str, Any]] = {
    # SOC 2 Templates
    "soc2/control_mapping.html.j2": {
        "display_name": "SOC 2 Control Mapping",
        "description": "Maps guardrail controls to SOC 2 Trust Service Criteria controls with evidence linkage",
        "supported_formats": ["pdf", "docx"],
    },
    "soc2/tsc_criteria.html.j2": {
        "display_name": "Trust Service Criteria Report",
        "description": "Detailed documentation of all five Trust Service Criteria (Security, Availability, Processing Integrity, Confidentiality, Privacy)",
        "supported_formats": ["pdf", "docx"],
    },
    "soc2/evidence_matrix.html.j2": {
        "display_name": "SOC 2 Evidence Matrix",
        "description": "Comprehensive evidence collection matrix for SOC 2 Type II audit preparation",
        "supported_formats": ["pdf", "docx", "xlsx"],
    },
    # ISO 27001 Templates
    "iso27001/annex_a_controls.html.j2": {
        "display_name": "ISO 27001:2022 Annex A Controls",
        "description": "Complete listing of all 93 ISO 27001:2022 Annex A controls organized by theme",
        "supported_formats": ["pdf", "docx"],
    },
    "iso27001/control_evidence.html.j2": {
        "display_name": "ISO 27001 Control Evidence",
        "description": "Evidence collection and tracking for ISO 27001 controls implementation",
        "supported_formats": ["pdf", "docx", "xlsx"],
    },
    "iso27001/soa.html.j2": {
        "display_name": "Statement of Applicability (SoA)",
        "description": "ISO 27001 Statement of Applicability with control justifications and implementation status",
        "supported_formats": ["pdf", "docx", "xlsx"],
    },
    # GDPR Templates
    "gdpr/article30_controller.html.j2": {
        "display_name": "Article 30 Controller Record",
        "description": "GDPR Article 30(1) Records of Processing Activities for Data Controllers",
        "supported_formats": ["pdf", "docx"],
    },
    "gdpr/article30_processor.html.j2": {
        "display_name": "Article 30 Processor Record",
        "description": "GDPR Article 30(2) Records of Processing Activities for Data Processors",
        "supported_formats": ["pdf", "docx"],
    },
    "gdpr/data_flow.html.j2": {
        "display_name": "Data Flow Mapping",
        "description": "Visual data flow mapping with cross-border transfer identification and security assessment",
        "supported_formats": ["pdf", "docx"],
    },
    # EU AI Act Templates
    "euaiact/risk_classification.html.j2": {
        "display_name": "AI System Risk Classification",
        "description": "EU AI Act risk classification assessment (unacceptable, high, limited, minimal risk levels)",
        "supported_formats": ["pdf", "docx"],
    },
    "euaiact/conformity_assessment.html.j2": {
        "display_name": "Conformity Assessment",
        "description": "EU AI Act conformity assessment procedures including internal control and notified body assessments",
        "supported_formats": ["pdf", "docx"],
    },
    "euaiact/technical_documentation.html.j2": {
        "display_name": "Technical Documentation (Annex IV)",
        "description": "EU AI Act Annex IV technical documentation requirements for high-risk AI systems",
        "supported_formats": ["pdf", "docx"],
    },
}

# Framework display names
FRAMEWORK_DISPLAY_NAMES: dict[str, str] = {
    "soc2": "SOC 2 Type II",
    "iso27001": "ISO 27001:2022",
    "gdpr": "GDPR (General Data Protection Regulation)",
    "euaiact": "EU AI Act (Regulation 2024/1689)",
}


def _get_template_info(template_path: str, framework: str) -> TemplateInfo:
    """
    Get template information for a given template path.

    Args:
        template_path: Full template path (e.g., 'soc2/control_mapping.html.j2').
        framework: Framework identifier.

    Returns:
        TemplateInfo with template metadata.
    """
    metadata = TEMPLATE_METADATA.get(template_path, {})

    # Extract template filename without framework prefix and extension
    template_name = template_path.split("/")[-1]
    base_name = template_name.replace(".html.j2", "").replace("_", " ").title()

    return TemplateInfo(
        name=template_name,
        display_name=metadata.get("display_name", base_name),
        description=metadata.get("description", f"Compliance template for {framework.upper()}"),
        framework=framework,
        supported_formats=metadata.get("supported_formats", ["pdf", "docx"]),
        version=metadata.get("version", "1.0.0"),
    )


@router.get("/{framework}", response_model=TemplateListResponse)
async def list_framework_templates(
    framework: str = Path(
        ...,
        description="Compliance framework (soc2, iso27001, gdpr, euaiact)",
        examples=["soc2", "iso27001", "gdpr", "euaiact"],
    ),
) -> TemplateListResponse:
    """
    List available templates for a specific compliance framework.

    Returns a list of all templates available for the specified framework,
    including template metadata such as display name, description, and
    supported export formats.

    - **framework**: Required. One of: soc2, iso27001, gdpr, euaiact

    Returns:
        TemplateListResponse with list of available templates.

    Raises:
        HTTPException 400: If the framework is invalid.
        HTTPException 404: If no templates are found for the framework.
    """
    # Normalize framework
    framework_lower = framework.lower()

    # Validate framework
    valid_frameworks = [f.value for f in ComplianceFramework]
    if framework_lower not in valid_frameworks:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid framework: {framework}. Valid options: {', '.join(valid_frameworks)}",
        )

    try:
        # Get templates for framework
        templates = list_templates(framework=framework_lower)

        if not templates:
            # Return empty list with 200 status (templates may not be created yet)
            logger.info(f"No templates found for framework: {framework_lower}")

        # Build template info list
        template_list = [
            _get_template_info(template_path, framework_lower)
            for template_path in sorted(templates)
        ]

        return TemplateListResponse(
            framework=framework_lower,
            framework_display_name=FRAMEWORK_DISPLAY_NAMES.get(
                framework_lower, framework_lower.upper()
            ),
            total_templates=len(template_list),
            templates=template_list,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error(f"Error listing templates for framework {framework}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list templates. Please try again later.",
        ) from e


@router.get("", response_model=AllTemplatesResponse)
async def list_all_templates() -> AllTemplatesResponse:
    """
    List all available templates across all compliance frameworks.

    Returns a comprehensive list of all templates organized by framework,
    including template metadata such as display name, description, and
    supported export formats.

    Returns:
        AllTemplatesResponse with templates grouped by framework.
    """
    try:
        frameworks_data: dict[str, TemplateListResponse] = {}
        total_count = 0

        for framework_enum in ComplianceFramework:
            framework = framework_enum.value
            templates = list_templates(framework=framework)

            template_list = [
                _get_template_info(template_path, framework) for template_path in sorted(templates)
            ]

            frameworks_data[framework] = TemplateListResponse(
                framework=framework,
                framework_display_name=FRAMEWORK_DISPLAY_NAMES.get(framework, framework.upper()),
                total_templates=len(template_list),
                templates=template_list,
                retrieved_at=datetime.now(timezone.utc).isoformat(),
            )

            total_count += len(template_list)

        return AllTemplatesResponse(
            total_templates=total_count,
            frameworks=frameworks_data,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error(f"Error listing all templates: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list templates. Please try again later.",
        ) from e


@router.get("/{framework}/{template_name}")
async def get_template_details(
    framework: str = Path(
        ...,
        description="Compliance framework (soc2, iso27001, gdpr, euaiact)",
    ),
    template_name: str = Path(
        ...,
        description="Template filename (e.g., control_mapping.html.j2)",
    ),
) -> TemplateInfo:
    """
    Get detailed information about a specific template.

    Returns metadata for a specific template including display name,
    description, and supported export formats.

    - **framework**: Required. One of: soc2, iso27001, gdpr, euaiact
    - **template_name**: Template filename (e.g., control_mapping.html.j2)

    Returns:
        TemplateInfo with template metadata.

    Raises:
        HTTPException 400: If the framework is invalid.
        HTTPException 404: If the template is not found.
    """
    # Normalize framework
    framework_lower = framework.lower()

    # Validate framework
    valid_frameworks = [f.value for f in ComplianceFramework]
    if framework_lower not in valid_frameworks:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid framework: {framework}. Valid options: {', '.join(valid_frameworks)}",
        )

    # Check if template exists
    if not template_exists(template_name, framework=framework_lower):
        raise HTTPException(
            status_code=404,
            detail=f"Template not found: {template_name} in framework {framework_lower}",
        )

    # Build full template path for metadata lookup
    template_path = f"{framework_lower}/{template_name}"

    return _get_template_info(template_path, framework_lower)
