"""
API routes for policy templates
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...database import get_db
from ...models.template import PolicyTemplate, TemplateVersion
from ...schemas.template import TemplateCreate, TemplateDetailResponse, TemplateResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("/", response_model=TemplateResponse, status_code=201)
async def create_template(template_in: TemplateCreate, db: AsyncSession = Depends(get_db)):
    """Create a new policy template with initial version"""
    # Create template
    template = PolicyTemplate(
        name=template_in.name,
        description=template_in.description,
        category=template_in.category,
        is_public=template_in.is_public,
        organization_id=template_in.organization_id,
        author_id=template_in.author_id,
    )
    db.add(template)
    await db.flush()

    # Create initial version
    version = TemplateVersion(
        template_id=template.id,
        version_string=template_in.initial_version.version_string,
        content=template_in.initial_version.content,
        changelog=template_in.initial_version.changelog,
    )
    db.add(version)

    await db.commit()
    await db.refresh(template)
    return template


@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[str] = None, verified_only: bool = False, db: AsyncSession = Depends(get_db)
):
    """List available templates"""
    query = select(PolicyTemplate).where(PolicyTemplate.is_public)

    if category:
        query = query.where(PolicyTemplate.category == category)
    if verified_only:
        query = query.where(PolicyTemplate.is_verified)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(template_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get detailed template information including versions"""
    query = (
        select(PolicyTemplate)
        .where(PolicyTemplate.id == template_id)
        .options(selectinload(PolicyTemplate.versions))
    )
    result = await db.execute(query)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template
