"""Constitutional Hash: cdd01ef066bc6cf2
API routes for template library
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from ...services.template_library_service import TemplateLibraryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["template-library"])
template_service = TemplateLibraryService()


@router.get("/")
async def list_templates(category: Optional[str] = None):
    """List available pre-built templates"""
    return {"templates": template_service.list_templates(category)}


@router.get("/{template_id:path}")
async def get_template(template_id: str):
    """Get raw template content and metadata"""
    content = template_service.get_template_content(template_id)
    if not content:
        raise HTTPException(status_code=404, detail="Template not found")

    metadata = template_service.get_template_metadata(template_id)
    return {"metadata": metadata, "content": content}
